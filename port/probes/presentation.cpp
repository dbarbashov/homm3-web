// Regression: partial animation commits must not expose a scratch back buffer.
#include "../platform/sdl_backend.h"
#include "../platform/cursor.h"
#include "../platform/music.h"
#include "bitmap16.h"
#include "mousemgr.h"
#include "resourcemanager.h"
#include <SDL.h>
#include <cstdio>
#include <stdexcept>
#include <unistd.h>
extern Bitmap16Bit g_initWin;
void require(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
int main(int argc,char** argv){
    try {
        require(argc==2,"runtime path required");require(chdir(argv[1])==0,"runtime directory");
        ResourceManager::SetPath("data/");ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
        int error=0;require(ResourceManager::Open(true,true,&error),"original LODs");
        require(Port::openDisplay(),"SDL display");
        for(int y=0;y<600;++y)for(int x=0;x<800;++x)*g_initWin.GetMap(x,y)=0x1234;
        Port::commitFrame(0,0,800,600);
        for(int y=0;y<600;++y)for(int x=0;x<800;++x)*g_initWin.GetMap(x,y)=0x5678;
        Port::present();require(*Port::committedFrame().GetMap(400,300)==0x1234,"idle exposed unfinished frame");
        Port::commitFrame(20,30,10,12);
        for(int y=0;y<600;++y)for(int x=0;x<800;++x)
            require(*Port::committedFrame().GetMap(x,y)==(x>=20&&x<30&&y>=30&&y<42?0x5678:0x1234),"dirty rectangle corrupted stationary pixels");
        Port::commitFrame(-5,-5,10,10);
        require(*Port::committedFrame().GetMap(0,0)==0x5678 && *Port::committedFrame().GetMap(5,5)==0x1234,"clipped dirty rectangle");
        g_mouseManager=new mouseManager;g_mouseManager->open(0);Port::cursorInside(true);
        Bitmap16Bit image(800,600);
        for(int set=0;set<5;++set){
            g_mouseManager->setPointer(0,static_cast<mouseManager::EPointerSet>(set));
            require(g_mouseManager->m_sprite && g_mouseManager->getFrame()==0,"original cursor DEF not loaded");
            g_mouseManager->m_currentX=400;g_mouseManager->m_currentY=300;
            g_initWin.Draw(0,0,800,600,&image,0,0,false);Port::drawCursor(image);
            bool changed=false;for(int y=250;y<350;++y)for(int x=350;x<450;++x)changed|=*image.GetMap(x,y)!=0x5678;
            require(changed,"original cursor invisible");
            static const int hotX[]={0,0,8,18,22},hotY[]={0,0,9,27,22};
            require(g_mouseManager->m_imageX==400-hotX[set] && g_mouseManager->m_imageY==300-hotY[set],"cursor hotspot");
            for(int edge: {0,799}){g_mouseManager->m_currentX=edge;g_mouseManager->m_currentY=edge?599:0;Port::drawCursor(image);}
            g_mouseManager->m_currentX=400;g_mouseManager->m_currentY=300;
        }
        // A retained texture must still repaint cursor moves, hides and frames.
        for(int step=0;step<4;++step){
            if(step==1)g_mouseManager->m_currentX+=37;
            if(step==2)g_mouseManager->hidePointer();
            if(step==3){g_mouseManager->showPointer(true);g_mouseManager->setPointer(1,mouseManager::SPELL_SET);}
            Port::present();
            Port::committedFrame().Draw(0,0,800,600,&image,0,0,false);
            Port::drawCursor(image);
            for(int y=0;y<600;++y)
                require(!std::memcmp(image.GetMap(0,y),Port::presentedFrame().GetMap(0,y),800*2),"retained frame left a stale cursor");
        }
        g_mouseManager->setPointer(0,mouseManager::SPELL_SET);SDL_Delay(110);g_mouseManager->checkUpdate();
        require(g_mouseManager->getFrame()==1,"animated spell cursor");
        g_mouseManager->hidePointer();g_initWin.Draw(0,0,800,600,&image,0,0,false);Port::drawCursor(image);
        require(*image.GetMap(400,300)==0x5678,"hidden cursor drawn");g_mouseManager->showPointer(true);
        Port::Music::play("MainMenu",0,.4f);require(Port::Music::playing(),"native MP3 playback");
        SDL_Delay(80);Port::Music::stop();SDL_Delay(1100);require(!Port::Music::playing(),"native music stop");
        Port::Music::resume();require(Port::Music::playing(),"native music resume");Port::Music::close();
        Port::closeDisplay();delete g_mouseManager;g_mouseManager=nullptr;
        puts("{\"dirtyRectangle\":true,\"idlePreservesFrame\":true,\"clipping\":true,\"originalCursorSets\":5,\"nativeMp3\":true}");return 0;
    }catch(const std::exception& e){fprintf(stderr,"Presentation regression: %s\n",e.what());return 1;}
}
