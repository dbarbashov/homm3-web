// Platform boundary: SDL replaces the Windows window, event queue and presentation.
#include "sdl_backend.h"
#include "cursor.h"
#include <SDL.h>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
#include "bitmap16.h"
#include "inputmgr.h"
#include "winmgr.h"
#include "mousemgr.h"
#include "kbwin.h"
#include "palette.h"
#include "message.h"
#include "remote.h"
#include "gametypewindow.h"
#include "soundmgr.h"
#include "advmgr.h"
#ifdef HOMM3_FULL_GAME
#include "game.h"
#include "hero.h"
#include "cmbtmgr.h"
#include "frontend_bridge.h"
#include "music.h"
#include "prefs.h"
#endif
#include "wingraph.h"
#include "kb.h"
#include <stdexcept>
#include <vector>
#include <memory>
#include "window.h"
#include "hd_view.h"

#ifndef HOMM3_FULL_GAME
heroWindowManager* g_windowManager=nullptr;
inputManager* g_inputManager=nullptr;
mouseManager* g_mouseManager=nullptr;
soundManager* g_soundManager=nullptr;
advManager* g_advManager=nullptr;
CDPlayHeroes* g_dPlay=nullptr;
bool g_lobbyLaunched=false;
class game;
game* g_game=nullptr;

unsigned long g_timers[10]={};
TPalette16* g_playerPalette=nullptr;
TPalette24* g_playerPalette24=nullptr;
#endif
HWND g_hwndApp=nullptr;
Bitmap16Bit g_initWin(800,600);
DDPIXELFORMAT g_pixelFormat={32,0x40,0,16,0xf800,0x07e0,0x001f,0};
static SDL_Window* window=nullptr;
static SDL_Renderer* renderer=nullptr;
static SDL_Texture* texture=nullptr;
static bool quit=false;
static Bitmap16Bit frontBuffer(800,600), displayBuffer(800,600);
static int menuSuppression=0;
namespace {
struct Overlay {
    heroWindow* window;
    int x,y,w,h;
    bool ready=false,shadow=false;
    std::unique_ptr<Bitmap16Bit> backdrop;
};
std::vector<Overlay> overlays;
heroWindow* adventureWindow=nullptr;
bool closingOverlay=false;
void composeFrame(Bitmap16Bit& source,Bitmap16Bit& target){
    const int w=source.GetWidth(),h=source.GetHeight();
    if(!overlays.empty()){
        auto& layer=overlays.back();
        layer.backdrop->Draw(0,0,w,h,&target,0,0,false);
        if(layer.ready){
            const int x=layer.x+(w-800)/2,y=layer.y+(h-600)/2;
            // Shadows darken the displayed backdrop, not pixels at the old
            // 800x600 source position (which may show a different map tile).
            if(layer.shadow){
                target.Darken(x+layer.w,y+9,7,layer.h-9);
                target.Darken(x+layer.w,y+8,8,layer.h-8);
                target.Darken(x+9,y+layer.h,layer.w-2,7);
                target.Darken(x+8,y+layer.h,layer.w,8);
            }
            source.Draw(layer.x,layer.y,layer.w,layer.h,&target,x,y,false);
        }
    }else if(adventureWindow){
        source.Draw(0,0,w,h,&target,0,0,false);
    }else{
        target.FillRect(0,0,w,h,0x1082);
        source.Draw(0,0,800,600,&target,(w-800)/2,(h-600)/2,false);
    }
}
}
namespace Port { namespace HD {
bool hasAdventureBackdrop(){return adventureWindow!=nullptr;}
int overlayOffsetX(){return (!adventureWindow || !overlays.empty())?(g_initWin.GetWidth()-800)/2:0;}
int overlayOffsetY(){return (!adventureWindow || !overlays.empty())?(g_initWin.GetHeight()-600)/2:0;}
void windowOpening(heroWindow* win,bool adventure){
    if(adventure){
        const int oldX=overlayOffsetX(),oldY=overlayOffsetY();
        overlays.clear();adventureWindow=win;
        if(g_mouseManager){g_mouseManager->m_currentX+=oldX;g_mouseManager->m_currentY+=oldY;}
        return;
    }
    if(!adventureWindow || win==adventureWindow || (win->m_status & WINDOW_STATE_OPEN))return;
    Overlay layer;
    layer.window=win;
    layer.x=std::max(0,win->m_x);layer.y=std::max(0,win->m_y);
    layer.shadow=(win->m_type & WINDOW_FLAG_SHADOWED)!=0;
    layer.w=std::max(0,std::min(800,win->m_x+win->m_width)-layer.x);
    layer.h=std::max(0,std::min(600,win->m_y+win->m_height)-layer.y);
    layer.backdrop.reset(new Bitmap16Bit(g_initWin.GetWidth(),g_initWin.GetHeight()));
    composeFrame(frontBuffer,*layer.backdrop);
    const int oldX=overlayOffsetX(),oldY=overlayOffsetY();
    overlays.push_back(std::move(layer));
    // Keep the physical pointer still even before the next SDL motion event.
    if(g_mouseManager){g_mouseManager->m_currentX+=oldX-overlayOffsetX();g_mouseManager->m_currentY+=oldY-overlayOffsetY();}
}
void windowClosing(heroWindow* win){
    closingOverlay=win==adventureWindow || (!overlays.empty() && overlays.back().window==win);
}
void windowClosed(heroWindow* win){
    const int oldX=overlayOffsetX(),oldY=overlayOffsetY();
    for(auto it=overlays.begin();it!=overlays.end();++it){
        if(it->window!=win)continue;
        // Full scene windows do not save/restore the adventure framebuffer.
        // Restore its committed pixels while the engine prepares its redraw.
        if(it==overlays.begin())it->backdrop->Draw(0,0,g_initWin.GetWidth(),g_initWin.GetHeight(),&frontBuffer,0,0,false);
        overlays.erase(it,overlays.end());break;
    }
    if(win==adventureWindow){adventureWindow=nullptr;overlays.clear();}
    closingOverlay=false;
    if(g_mouseManager){g_mouseManager->m_currentX+=oldX-overlayOffsetX();g_mouseManager->m_currentY+=oldY-overlayOffsetY();}
    Port::present();
}
} }

namespace Port {
void displaySize(int& w,int& h){SDL_GetWindowSize(window,&w,&h);}
void resizeDisplay(int w,int h){
    std::vector<unsigned short> blank(w*h,0);
    g_initWin.import(w,h,blank.data(),0);
    if(g_windowManager && g_windowManager->m_screenBitmap)
        g_windowManager->m_screenBitmap->reference(w,h,g_initWin.GetPitch(),g_initWin.GetMap(0,0));
    frontBuffer.import(w,h,blank.data(),0);displayBuffer.import(w,h,blank.data(),0);
    SDL_DestroyTexture(texture);
    texture=SDL_CreateTexture(renderer,SDL_PIXELFORMAT_RGB565,SDL_TEXTUREACCESS_STREAMING,w,h);
#ifdef __EMSCRIPTEN__
    SDL_SetWindowSize(window,w,h);
    EM_ASM({window.dispatchEvent(new Event('homm3-resolution'));},w,h);
#endif
    SDL_RenderSetLogicalSize(renderer,w,h);
}
bool openDisplay(){
    SDL_SetMainReady();
    if(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_TIMER|SDL_INIT_AUDIO))return false;
    // CSS owns browser presentation size. A resizable SDL canvas would shrink
    // the framebuffer to CSS pixels and permanently discard small text details.
#ifdef __EMSCRIPTEN__
    const Uint32 windowFlags=0;
#else
    const Uint32 windowFlags=SDL_WINDOW_RESIZABLE;
#endif
    window=SDL_CreateWindow("Heroes III — portable C++ engine",SDL_WINDOWPOS_CENTERED,SDL_WINDOWPOS_CENTERED,800,600,windowFlags);
    if(!window)return false;
    renderer=SDL_CreateRenderer(window,-1,SDL_RENDERER_ACCELERATED);
    if(!renderer)renderer=SDL_CreateRenderer(window,-1,SDL_RENDERER_SOFTWARE);
    if(!renderer)return false;
    SDL_RenderSetLogicalSize(renderer,800,600);
    texture=SDL_CreateTexture(renderer,SDL_PIXELFORMAT_RGB565,SDL_TEXTUREACCESS_STREAMING,800,600);
    return texture!=nullptr;
}
bool setFullscreen(bool enabled){return window && SDL_SetWindowFullscreen(window,enabled?SDL_WINDOW_FULLSCREEN_DESKTOP:0)==0;}
// The renderer's back buffer may contain an unfinished animation. Only
// robAppBlit's dirty rectangle commits pixels to the visible front buffer.
void commitFrame(int x,int y,int width,int height){
    const int right=std::min(g_initWin.GetWidth(),x+width),bottom=std::min(g_initWin.GetHeight(),y+height);
    x=std::max(0,x);y=std::max(0,y);
    if(right<=x || bottom<=y)return;
    g_initWin.Draw(x,y,right-x,bottom-y,&frontBuffer,x,y,false);
    if(!overlays.empty() && !closingOverlay){
        auto& layer=overlays.back();
        // An idle pump during widget construction must keep the old scene.
        if(x<layer.x+layer.w && right>layer.x && y<layer.y+layer.h && bottom>layer.y)
            layer.ready=true;
    }
    present();
}
void present(){
    if(!texture || closingOverlay)return;
    composeFrame(frontBuffer,displayBuffer);
    drawCursor(displayBuffer,HD::overlayOffsetX(),HD::overlayOffsetY());
    SDL_UpdateTexture(texture,nullptr,displayBuffer.GetMap(0,0),displayBuffer.GetPitch());
    SDL_RenderClear(renderer);SDL_RenderCopy(renderer,texture,nullptr,nullptr);SDL_RenderPresent(renderer);
}
const Bitmap16Bit& committedFrame(){return frontBuffer;}
const Bitmap16Bit& presentedFrame(){return displayBuffer;}

void closeDisplay(){
    if(g_mouseManager)g_mouseManager->close();
#ifdef HOMM3_FULL_GAME
    if(g_soundManager)g_soundManager->close();
#endif
    SDL_DestroyTexture(texture);SDL_DestroyRenderer(renderer);SDL_DestroyWindow(window);SDL_Quit();
#ifdef __EMSCRIPTEN__
    EM_ASM({window.dispatchEvent(new Event('homm3-exit'));});
#endif
}
bool shouldQuit(){return quit;}
void announceCommand(int id,const char* screen){
    printf("Original widget command: %d\n",id);
#ifdef __EMSCRIPTEN__
    EM_ASM({window.dispatchEvent(new CustomEvent('homm3-command',{detail:({id:$0,screen:UTF8ToString($1)})}));},id,screen);
#else
    char title[160];snprintf(title,sizeof(title),"Heroes III / C++ — menu command %d",id);SDL_SetWindowTitle(window,title);
#endif
}
}
void robAppBlit(tagRECT* r){if(r)Port::commitFrame(r->left,r->top,r->right-r->left,r->bottom-r->top);}
#ifndef HOMM3_FULL_GAME
void memError(){throw std::bad_alloc();}
#endif
void setNoDialogMenus(int value){menuSuppression=value;}
extern "C" unsigned long timeGetTime(){return SDL_GetTicks();}
extern "C" HWND SetCapture(HWND h){SDL_CaptureMouse(SDL_TRUE);return h;}
extern "C" BOOL ReleaseCapture(){SDL_CaptureMouse(SDL_FALSE);return TRUE;}
extern "C" SHORT GetKeyState(int key){auto m=SDL_GetModState();return ((key==VK_SHIFT&&(m&KMOD_SHIFT))||(key==VK_CONTROL&&(m&KMOD_CTRL))||(key==VK_MENU&&(m&KMOD_ALT)))?static_cast<SHORT>(0x8000):0;}
LRESULT appCommand(HWND,UINT,WPARAM command,LPARAM){
    if(command==KBWIN_MENU_FULLSCREEN){auto flags=SDL_GetWindowFlags(window);SDL_SetWindowFullscreen(window,flags&SDL_WINDOW_FULLSCREEN_DESKTOP?0:SDL_WINDOW_FULLSCREEN_DESKTOP);}
    else if(command==KBWIN_MENU_HELP)SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_INFORMATION,"Heroes III port","Original menu and resource engine. Gameplay is not connected yet.",window);
    return 0;
}
static int pcScanCode(SDL_Scancode code){
    if(code>=SDL_SCANCODE_A && code<=SDL_SCANCODE_Z){
        static const int letters[]={30,48,46,32,18,33,34,35,23,36,37,38,50,49,24,25,16,19,31,20,22,47,17,45,21,44};
        return letters[code-SDL_SCANCODE_A];
    }
    if(code>=SDL_SCANCODE_F1 && code<=SDL_SCANCODE_F10)return 59+code-SDL_SCANCODE_F1;
    if(code>=SDL_SCANCODE_1 && code<=SDL_SCANCODE_9)return 2+code-SDL_SCANCODE_1;
    switch(code){case SDL_SCANCODE_0:return 11;case SDL_SCANCODE_BACKSPACE:return 14;
    case SDL_SCANCODE_KP_1:return 79;case SDL_SCANCODE_KP_2:return 80;case SDL_SCANCODE_KP_3:return 81;
    case SDL_SCANCODE_KP_4:return 75;case SDL_SCANCODE_KP_5:return 76;case SDL_SCANCODE_KP_6:return 77;
    case SDL_SCANCODE_KP_7:return 71;case SDL_SCANCODE_KP_8:return 72;case SDL_SCANCODE_KP_9:return 73;
    case SDL_SCANCODE_HOME:return 71;case SDL_SCANCODE_END:return 79;case SDL_SCANCODE_PAGEUP:return 73;case SDL_SCANCODE_PAGEDOWN:return 81;
    case SDL_SCANCODE_SPACE:return 57;case SDL_SCANCODE_UP:return 72;case SDL_SCANCODE_DOWN:return 80;case SDL_SCANCODE_LEFT:return 75;case SDL_SCANCODE_RIGHT:return 77;case SDL_SCANCODE_TAB:return 15;case SDL_SCANCODE_ESCAPE:return 1;case SDL_SCANCODE_N:return 49;case SDL_SCANCODE_S:return 31;case SDL_SCANCODE_M:return 50;case SDL_SCANCODE_T:return 20;case SDL_SCANCODE_L:return 38;case SDL_SCANCODE_H:return 35;case SDL_SCANCODE_C:return 46;case SDL_SCANCODE_F1:return 59;case SDL_SCANCODE_F4:return 62;case SDL_SCANCODE_RETURN:return 28;default:return 0;}
}
void process1WindowsMessage(){
    SDL_Event e;
    while(SDL_PollEvent(&e)){
        if(e.type==SDL_WINDOWEVENT && (e.window.event==SDL_WINDOWEVENT_ENTER || e.window.event==SDL_WINDOWEVENT_LEAVE)){Port::cursorInside(e.window.event==SDL_WINDOWEVENT_ENTER);}
        else if(e.type==SDL_QUIT){
            quit=true;
#ifdef HOMM3_FULL_GAME
            throw Port::ExitRequested{};
#endif
        }
        else if(e.type==SDL_KEYDOWN||e.type==SDL_KEYUP){int code=pcScanCode(e.key.keysym.scancode);if(code)keyboardMessageHandler(nullptr,e.type==SDL_KEYDOWN?WM_KEYDOWN:WM_KEYUP,0,code<<16);}
        else if(e.type==SDL_MOUSEMOTION||e.type==SDL_MOUSEBUTTONDOWN||e.type==SDL_MOUSEBUTTONUP){
            int x=e.type==SDL_MOUSEMOTION?e.motion.x:e.button.x,y=e.type==SDL_MOUSEMOTION?e.motion.y:e.button.y;
            Port::cursorInside(x>=0 && x<g_initWin.GetWidth() && y>=0 && y<g_initWin.GetHeight());
            x-=Port::HD::overlayOffsetX();y-=Port::HD::overlayOffsetY();
            if(g_mouseManager){g_mouseManager->m_currentX=x;g_mouseManager->m_currentY=y;}
            unsigned type=WM_MOUSEMOVE;
            if(e.type!=SDL_MOUSEMOTION){if(e.button.button!=SDL_BUTTON_LEFT&&e.button.button!=SDL_BUTTON_RIGHT)continue;bool left=e.button.button==SDL_BUTTON_LEFT;type=e.type==SDL_MOUSEBUTTONDOWN?(left?WM_LBUTTONDOWN:WM_RBUTTONDOWN):(left?WM_LBUTTONUP:WM_RBUTTONUP);}
            mouseMessageHandler(nullptr,type,0,(x&0xffff)|((y&0xffff)<<16));
        }
    }
    if(g_mouseManager)g_mouseManager->checkUpdate();
#ifdef HOMM3_FULL_GAME
    Port::Music::serviceScene();
    if(g_soundManager)g_soundManager->serviceSounds();
#endif
#ifdef __EMSCRIPTEN__
    // WebGL back buffers are discarded after the browser composites a frame.
    // Keep the original framebuffer visible even while the game is idle.
#ifdef HOMM3_FULL_GAME
    static uint32_t lastSettings=0;
    if(SDL_GetTicks()-lastSettings>=250){
        lastSettings=SDL_GetTicks();
    if(g_game && g_currentPlayer) {
        auto* h=g_game->getCurrHero();
        if(h)for(int i=0;i<7;++i)EM_ASM({if(!window.homm3Army)window.homm3Army=[];window.homm3Army[$0]=({type:$1,count:$2});},i,h->m_army.m_armies[i],h->m_army.m_numTroops[i]);
    }

        EM_ASM({window.homm3Settings=({music:$0,sound:$1,heroSpeed:$2,aiSpeed:$3,scrollSpeed:$4,showRoute:$5,combatSpeed:$6,combatGrid:$7});},g_config.m_musicVolume,g_config.m_soundVolume,g_config.m_walkSpeed[1],g_config.m_walkSpeed[0],g_config.m_windowScrollSpeed,g_config.m_showRoute,g_config.m_combatSpeed,g_config.m_showCombatGrid);
    }
    static bool lastCombat=false;
    if(bool(g_combatActive)!=lastCombat){lastCombat=bool(g_combatActive);Port::notifyScreen(lastCombat?"combat":"adventure");}
    EM_ASM({window.homm3HDState=({width:$0,height:$1,mapWidth:$2,mapHeight:$3,adventure:!!$4,overlayX:$5,overlayY:$6,layers:$7});},Port::HD::width(),Port::HD::height(),Port::HD::mapRight()-8,Port::HD::mapHeight(),Port::HD::adventureVisible(),Port::HD::overlayOffsetX(),Port::HD::overlayOffsetY(),int(overlays.size()));
    EM_ASM({Object.assign(window.homm3HDState,{status:$0,inDialog:$1,nest:$2,topIsMap:!!$3,activeIsMap:!!$4});},g_advManager?g_advManager->m_status:-1,g_inDialog,g_dialogNestCount,g_windowManager && g_advManager && g_windowManager->topWindow()==g_advManager->m_advWindow,g_windowManager && g_advManager && g_windowManager->m_activeWindow==g_advManager->m_advWindow);
    static uint32_t lastState=0;
    if(g_game && g_currentPlayer && g_advManager && (g_advManager->m_status==1 || g_combatActive) && SDL_GetTicks()-lastState>=250){
        lastState=SDL_GetTicks();
        hero* h=g_game->getCurrHero();
        EM_ASM({window.homm3GameState=({day:$0,week:$1,month:$2,player:$3,hero:$4,x:$5,y:$6,z:$7,movement:$8,gold:$9,combat:$10,round:$11,autoCombat:$12,action:$13,experience:$14,moving:$15});},
            g_game->m_day,g_game->m_week,g_game->m_month,g_playerTurn,h?int(h->m_id):-1,
            h?h->m_x:-1,h?h->m_y:-1,h?h->m_z:-1,h?h->m_movePoints:0,g_currentPlayer->m_resources[6],g_combatActive,g_combatManager?g_combatManager->m_turnNumber:0,g_combatManager?g_combatManager->m_autoCombatOn:0,g_combatManager?g_combatManager->m_nextAction:0,h?h->m_experience:0,g_advManager->m_heroMoving);
        // Keep each EM_ASM within the toolchain's 16 positional argument limit.
        EM_ASM({Object.assign(window.homm3GameState,{localPlayer:$0,remote:$1,humans:$2});},g_localGamePos,g_remoteOn,g_numHumanPlayers);
        EM_ASM({window.homm3NetworkState=({control:$0,currentLocal:$1,visibility:$2,radarX:$3,radarY:$4});},g_thisNetGotAdventureControl,g_currentPlayer->isLocalHuman(),g_mapVisibilityBit,g_advManager->m_radarOrigin.m_x,g_advManager->m_radarOrigin.m_y);
        EM_ASM({Object.assign(window.homm3NetworkState,{turnSlot:$0,aiOwner:$1,map:UTF8ToString($2)});},g_netLocalGamePos,g_game->getLastHuman(),g_game->m_setup.m_filename);
        EM_ASM({window.homm3HeroStates=[];});
        for(int i=0;i<8;++i){auto& player=g_game->m_players[i];hero* first=player.m_numHeroes>0?&g_game->m_heroes[player.m_heroes[0]]:nullptr;
            EM_ASM({window.homm3HeroStates.push({player:$0,local:$1,human:$2,hero:$3,x:$4,y:$5,movement:$6,visibility:$7,experience:$8,dpid:$9,disabled:$10});},i,player.m_isLocal,player.m_isHuman,first?int(first->m_id):-1,first?first->m_x:-1,first?first->m_y:-1,first?first->m_movePoints:0,first?getMapExtra(first->m_x,first->m_y,first->m_z):0,first?first->m_experience:0,player.m_dpid,g_game->m_playerDisabled[i]);
            if(first)EM_ASM({window.homm3HeroStates[$0].army=Array.from({length:7},function(_,n){return new DataView(HEAPU8.buffer).getInt32($1+4*n,true);});window.homm3HeroStates[$0].counts=Array.from({length:7},function(_,n){return new DataView(HEAPU8.buffer).getInt32($2+4*n,true);});},i,first->m_army.m_armies,first->m_army.m_numTroops);
        }
    }
#endif
    static uint32_t lastPresent=0;
    if(SDL_GetTicks()-lastPresent>=16){Port::present();lastPresent=SDL_GetTicks();}
    emscripten_sleep(8); // Original button::main has a nested synchronous message pump.
#else
    Port::present();
    SDL_Delay(8);
#endif
}


#ifdef HOMM3_FULL_GAME
int getDesktopWidth(){SDL_DisplayMode mode{};return SDL_GetCurrentDisplayMode(0,&mode)==0?mode.w:800;}
int getDesktopHeight(){SDL_DisplayMode mode{};return SDL_GetCurrentDisplayMode(0,&mode)==0?mode.h:600;}
#endif
