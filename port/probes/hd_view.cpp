#include "bitmap16.h"
#include "winmgr.h"
#include "window.h"
#include "mousemgr.h"
#include "hd_view.h"
#include "../platform/sdl_backend.h"
#include <cassert>
#include <cstdio>
extern Bitmap16Bit g_initWin;
static unsigned short mapPixel(int x,int y){return 0x2000+((x*7+y*13)%0x1000);}
static void paintMap(int w,int h){for(int y=0;y<h;++y)for(int x=0;x<w;++x)*g_initWin.GetMap(x,y)=mapPixel(x,y);}
static void checkMap(int w,int h){for(int y=0;y<h;++y)for(int x=0;x<w;++x)assert(*Port::presentedFrame().GetMap(x,y)==mapPixel(x,y));}
static void overlays(int w,int h){
    using namespace Port::HD;
    Port::resizeDisplay(w,h);
    heroWindow map(0,0,w,h,0),town(0,0,800,600,0),popup(200,180,400,240,0);
    windowOpening(&map,true);
    g_mouseManager->hidePointer();g_windowManager->m_isWaitingForFadeIn=1;
    g_windowManager->fadeScreen(1,4,1);
    assert(g_mouseManager->m_hideCount==0 && !g_windowManager->m_isWaitingForFadeIn);
    paintMap(w,h);Port::commitFrame(0,0,w,h);checkMap(w,h);
    const int dx=(w-800)/2,dy=(h-600)/2;
    g_mouseManager->m_currentX=600;g_mouseManager->m_currentY=300;
    windowOpening(&town,false);Port::present();checkMap(w,h);
    assert(g_mouseManager->m_currentX+overlayOffsetX()==600 && g_mouseManager->m_currentY+overlayOffsetY()==300);
    g_initWin.FillRect(0,0,800,600,0x7bef);
    Port::present();checkMap(w,h); // Uncommitted widget construction stays hidden.
    Port::commitFrame(0,0,800,600);
    for(int y=0;y<h;++y)for(int x=0;x<w;++x)
        assert(*Port::presentedFrame().GetMap(x,y)==(x>=dx&&x<dx+800&&y>=dy&&y<dy+600?0x7bef:mapPixel(x,y)));
    windowOpening(&popup,false);g_initWin.FillRect(200,180,400,240,0xf800);Port::commitFrame(200,180,400,240);
    assert(*Port::presentedFrame().GetMap(dx+210,dy+190)==0xf800);
    assert(*Port::presentedFrame().GetMap(dx+10,dy+10)==0x7bef);
    windowClosing(&popup);g_initWin.FillRect(200,180,400,240,0x7bef);Port::commitFrame(200,180,400,240);
    assert(*Port::presentedFrame().GetMap(dx+210,dy+190)==0xf800); // No half-restored frame.
    windowClosed(&popup);assert(*Port::presentedFrame().GetMap(dx+210,dy+190)==0x7bef);
    windowClosing(&town);windowClosed(&town);checkMap(w,h);
    assert(overlayOffsetX()==0 && overlayOffsetY()==0);
    assert(g_mouseManager->m_currentX==600 && g_mouseManager->m_currentY==300);
    // A small map popup preserves every pixel outside its actual rectangle.
    paintMap(w,h);Port::commitFrame(0,0,w,h);windowOpening(&popup,false);
    g_initWin.FillRect(200,180,400,240,0xf800);Port::commitFrame(200,180,400,240);
    for(int y=0;y<h;++y)for(int x=0;x<w;++x)
        assert(*Port::presentedFrame().GetMap(x,y)==(x>=dx+200&&x<dx+600&&y>=dy+180&&y<dy+420?0xf800:mapPixel(x,y)));
    windowClosing(&popup);paintMap(w,h);Port::commitFrame(0,0,w,h);windowClosed(&popup);checkMap(w,h);
    windowClosing(&map);windowClosed(&map);
}
int main(){
    assert(Port::openDisplay());
    g_windowManager=new heroWindowManager;
    g_windowManager->m_screenBitmap=new Bitmap16Bit(0,0);
    g_windowManager->m_screenBitmap->reference(800,600,g_initWin.GetPitch(),g_initWin.GetMap(0,0));
    for(auto size: {std::pair<int,int>{1298,600},{800,1731},{1200,600},{800,600}}){
        Port::resizeDisplay(size.first,size.second);
        auto* surface=g_windowManager->m_screenBitmap;
        assert(surface->GetWidth()==size.first && surface->GetHeight()==size.second);
        assert(surface->GetPitch()==size.first*2 && surface->GetMap(0,0)==g_initWin.GetMap(0,0));
        int x=size.first-12,y=size.second-12;
        surface->FillRect(x,y,10,10,0x07e0);Port::commitFrame(x,y,10,10);
        assert(*Port::committedFrame().GetMap(x+5,y+5)==0x07e0);
        assert(*Port::committedFrame().GetMap(x-1,y)==0);
    }
    g_mouseManager=new mouseManager;
    overlays(1200,600);overlays(800,1200);overlays(800,600);
    delete g_mouseManager;g_mouseManager=nullptr;
    delete g_windowManager->m_screenBitmap;delete g_windowManager;g_windowManager=nullptr;Port::closeDisplay();
    puts("{\"passed\":true,\"checks\":[\"landscape/portrait resize\",\"screen reference rebind\",\"actual framebuffer pitch\",\"extended dirty rectangle\",\"classic restoration\",\"map pixel invariance under small/full/nested overlays\",\"uncommitted and closing frames\",\"stationary pointer transforms\"]}");
}
