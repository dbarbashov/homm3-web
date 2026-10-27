#ifdef HOMM3_FULL_GAME
#include "hd_view.h"
#include "sdl_backend.h"
#include "adventuremapwindow.h"
#include "advmgr.h"
#include "bitmap16.h"
#include "bitmap816.h"
#include "bottomviewsubwindow.h"
#include "resourcedisplay.h"
#include "winmgr.h"
#include "widget.h"
#include "cmbtmgr.h"
#include "game.h"
#include "mousemgr.h"
#include <SDL.h>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
extern Bitmap16Bit g_initWin;
namespace Port { namespace HD {
int width(){return g_initWin.GetWidth();}
int height(){return g_initWin.GetHeight();}
int mapRight(){return g_drawingPuzzle?600:width()-200;}
int mapHeight(){return g_drawingPuzzle?544:height()-56;}
// Keep the animation and map camera in one coordinate system.
int centerX(){return (mapRight()-8)/64;}
int centerY(){return mapHeight()/64;}
bool isAdventureWindow(const heroWindow* win){return g_advManager && win==g_advManager->m_advWindow;}
bool adventureVisible(){return g_advManager && g_advManager->m_status==1 && !g_combatActive
    && g_windowManager && g_windowManager->topWindow()==g_advManager->m_advWindow && !g_inDialog;}
void layoutAdventure(TAdventureMapWindow* win,int dx,int dy){
    for(widget* w=win->m_headWidget;w;w=w->m_nextWidget){
        const bool sidebar=w->m_x>=width()-dx-200;
        if(sidebar)w->m_x+=dx;
        if((sidebar && w->m_y>=height()-dy-211) || w->m_y>=height()-dy-50)w->m_y+=dy;
    }
    win->m_width=width();win->m_height=height();
    win->m_mapWidget->m_width=width()-208;win->m_mapWidget->m_height=height()-56;
    if(win->m_resourceDisplay)win->m_resourceDisplay->m_y+=dy;
}
void resizeAdventure(){
    if(!adventureVisible() || g_advManager->m_heroMoving)return;
    int w=800,h=600;
#ifdef __EMSCRIPTEN__
    w=EM_ASM_INT({return window.homm3HDSize?.width||800;});
    h=EM_ASM_INT({return window.homm3HDSize?.height||600;});
#else
    Port::displaySize(w,h);
    double ratio=double(w)/std::max(1,h);
    h=ratio>=4.0/3?600:int(800/ratio);w=ratio>=4.0/3?int(600*ratio):800;
#endif
    w=std::max(800,std::min(2048,w));h=std::max(600,std::min(2048,h));
    if(w==width() && h==height())return;
    const int oldW=width(),oldH=height(),cx=centerX(),cy=centerY();
    Port::resizeDisplay(w,h);
    layoutAdventure(g_advManager->m_advWindow,w-oldW,h-oldH);
    g_advManager->m_radarOrigin.m_x+=cx-centerX();g_advManager->m_radarOrigin.m_y+=cy-centerY();
    g_advManager->redrawAdvScreen(1,0);
}
void drawAdventureFrame(Bitmap816* bmp){
    auto* target=g_windowManager->m_screenBitmap;
    target->FillRect(0,0,width(),height(),0x2104);
    // Original artwork, tiled only along stretches without controls.
    for(int x=0;x<width()-200;x+=592){int n=std::min(592,width()-200-x);
        bmp->Draw(8,0,n,8,target,x,0,0);
        bmp->Draw(8,552,n,48,target,x,height()-48,0);
    }
    for(int y=8;y<height()-48;y+=544)bmp->Draw(0,8,8,std::min(544,height()-48-y),target,0,y,0);
    bmp->Draw(600,0,200,389,target,width()-200,0,0);
    for(int y=389;y<height()-211;y+=100)
        bmp->Draw(600,420,200,std::min(100,height()-211-y),target,width()-200,y,0);
    bmp->Draw(600,389,200,211,target,width()-200,height()-211,0);
}
} }

#else
#include "hd_view.h"
namespace Port { namespace HD { bool isAdventureWindow(const heroWindow*){return false;} int width(){return 800;} int height(){return 600;} int centerX(){return 9;} int centerY(){return 8;} } }
#endif
