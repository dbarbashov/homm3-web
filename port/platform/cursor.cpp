// Original DEF graphics and hotspots, composited onto the committed frame.
#include "cursor.h"
#include "mousemgr.h"
#include "bitmap16.h"
#include "resourcemanager.h"
#include "port_cursor_tables.h"
#include <SDL.h>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace {
bool inside=false; Uint32 lastAnimation=0;
bool pointerIsInside(){
#ifdef __EMSCRIPTEN__
    // SDL window-enter events can mean browser focus, including over page UI.
    return inside && EM_ASM_INT({return (window.homm3TouchPointerActive || Module.canvas.matches(':hover'))?1:0;});
#else
    return inside;
#endif
}
}
namespace Port {
void cursorInside(bool value){inside=value;if(g_mouseManager)g_mouseManager->showSystemCursor(!value);}
void drawCursor(Bitmap16Bit& target,int offsetX,int offsetY){
    auto* m=g_mouseManager;
    const bool visible=pointerIsInside() && m && m->m_status==1 && m->isVis() && m->m_sprite && m->m_frame>=0;
    if(visible){
        const auto hot=g_mouseHotSpots[m->m_set][m->m_frame];
        m->m_imageX=m->m_currentX-hot.x;m->m_imageY=m->m_currentY-hot.y;
        m->m_sprite->Draw(0,m->m_frame,0,0,m->m_sprite->GetWidth(),m->m_sprite->GetHeight(),&target,m->m_imageX+offsetX,m->m_imageY+offsetY,false,true);
    }
#ifdef __EMSCRIPTEN__
    if(m)EM_ASM({window.homm3CursorState=({set:$0,frame:$1,x:$2,y:$3,imageX:$4,imageY:$5,visible:!!$6});},m->m_set,m->m_frame,m->m_currentX,m->m_currentY,m->m_imageX,m->m_imageY,visible);
#endif
}
}
mouseManager::mouseManager():m_noChangePointer(0),m_savedRect{},m_set(INVALID_SET),m_frame(-1),m_sprite(nullptr),m_imageX(0),m_imageY(0),m_disableCount(0),m_systemPointerIsOn(1),m_hideCount(0),m_currentX(0),m_currentY(0),m_busy(0){InitializeCriticalSection(&m_sectionMouse);}
mouseManager::~mouseManager(){close();DeleteCriticalSection(&m_sectionMouse);}
int mouseManager::open(int priority){m_priority=priority;m_status=STATUS_ACTIVE;return 0;}
void mouseManager::close(){if(m_sprite)ResourceManager::Dispose(m_sprite);m_sprite=nullptr;m_set=INVALID_SET;m_frame=-1;m_status=0;showSystemCursor(true);}
int mouseManager::main(message&){return 0;}
void mouseManager::hidePointer(){++m_hideCount;}
void mouseManager::showPointer(bool force){m_hideCount=force?0:std::max(0,m_hideCount-1);}
void mouseManager::setPointer(int frame,EPointerSet set){
    if(m_status!=STATUS_ACTIVE || m_noChangePointer || m_busy)return;
    if(set!=SAME_SET && set!=m_set){
        if(set<0 || set>=MAX_POINTER_SETS)return;
        auto* sprite=ResourceManager::GetSprite(g_pointerSetSprites[set]);
        if(m_sprite)ResourceManager::Dispose(m_sprite);
        m_sprite=sprite;m_set=set;m_frame=-1;
    }
    if(frame<0 || !m_sprite)return;
    loadFrame(m_set==SPELL_SET?0:frame);
}
void mouseManager::loadFrame(int frame){if(m_sprite && frame>=0 && frame<m_sprite->GetNumFrames(0) && frame<144)m_frame=frame;}
// Outside the canvas there is no game cursor. Returning (0,0) would
// continuously scroll the original adventure map to its top-left corner.
void mouseManager::mouseCoords(int& x,int& y){const bool active=pointerIsInside();x=active?m_currentX:-1;y=active?m_currentY:-1;}
void mouseManager::getPointerPosition(){}
void mouseManager::update(bool){checkUpdate();}
void mouseManager::checkUpdate(){
    if(m_set==SPELL_SET && m_sprite && SDL_GetTicks()-lastAnimation>=100){loadFrame((m_frame+1)%m_sprite->GetNumFrames(0));lastAnimation=SDL_GetTicks();}
}
void mouseManager::showSystemCursor(bool show){m_systemPointerIsOn=show;SDL_ShowCursor(show?SDL_ENABLE:SDL_DISABLE);}
void mouseManager::reset(){setPointer(0,DEFAULT_SET);}
