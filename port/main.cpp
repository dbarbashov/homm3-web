// Shared native/WASM bootstrap. Menu handlers, widgets, input and drawing are
// recovered upstream C++; adventure/battle initialization is the next stage.
#include "platform/sdl_backend.h"
#include "frontend_bridge.h"
#include "frontend/messages.h"
#include "resourcemanager.h"
#include "mainmenu.h"
#include "gametypewindow.h"
#include "winmgr.h"
#include "inputmgr.h"
#include "mousemgr.h"
#include "widget.h"
#include "wingraph.h"
#include "font.h"
#include "text.h"
#include "kb.h"
#include <cstdio>
#include <exception>
TPalette16* g_systemPalette=nullptr;
namespace {
void background(){
    auto* image=ResourceManager::GetBitmap16("GamSelBk.pcx");
    image->Draw(0,0,image->GetWidth(),image->GetHeight(),g_windowManager->m_screenBitmap,0,0,false);
    ResourceManager::Dispose(image);
}
void unavailable(){normalDialog(unavailableText,NORMAL_DIALOG_DEFAULT,-1,-1,-1,0,-1,0,-1,0,-1,0);}
void gameTypes(bool load){
    Port::setGameTypeMode(load);
    while(!Port::shouldQuit()){
        background();
        {TGameTypeWindow menu(load);menu.doModal();}
        int command=g_windowManager->m_dialogReturn;
        if(command==TGameTypeWindow::QUIT_ID || command==-1)return;
        unavailable();
    }
}
}
int main(int argc,char** argv){
    if(argc<2){std::fprintf(stderr,"Usage: homm3-port DATA_DIRECTORY/ [--snapshot [main|new|load] [hover-id]]\n");return 2;}
    try{
        ResourceManager::SetPath(argv[1]);ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
        int error=-1;if(!ResourceManager::Open(true,true,&error))return 3;
        if(!Port::openDisplay())return 4;
        inputManager input;mouseManager mouse;heroWindowManager windows;
        g_inputManager=&input;g_mouseManager=&mouse;g_windowManager=&windows;
        input.open(1);mouse.open(0);windows.open(0);
        g_systemPalette=ResourceManager::GetPalette("game.pal");
        g_playerPalette=ResourceManager::GetPalette("Players.pal");
        g_playerPalette24=ResourceManager::GetPalette24("Players.pal");
        g_mediumFont=ResourceManager::GetFont("medfont.fnt");
        if(!initializeGeneralText() || !initializeHelpText())throw std::runtime_error("Missing front-end text resources");
        bool snapshot=argc>2 && std::string(argv[2])=="--snapshot";
        if(snapshot){
            background();
            const char* screen=argc>3?argv[3]:"main";
            std::unique_ptr<heroWindow> menu(std::string(screen)=="main"?static_cast<heroWindow*>(new TMainMenu):static_cast<heroWindow*>(new TGameTypeWindow(std::string(screen)=="load")));
            if(argc>4){auto* w=menu->getWidget(std::atoi(argv[4]));if(!w)return 6;w->sendMessage(widget::WIDGET_SET_STATUS,widget::WIDGET_HIGHLIGHTED);}
            menu->drawWindow(true,WINDOW_ALL_WIDGETS_LOW,WINDOW_ALL_WIDGETS_HIGH);
            Port::notifySnapshot(screen);
            auto* out=fopen("build/menu-native.rgb565","wb");if(!out)return 5;fwrite(g_initWin.GetMap(0,0),2,800*600,out);fclose(out);
            menu->close(0);
        }else{
            bool done=false;
            while(!done && !Port::shouldQuit()){
                background();
                {TMainMenu menu;menu.doModal();}
                switch(g_windowManager->m_dialogReturn){
                    case TMainMenu::NEW_GAME_ID:gameTypes(false);break;
                    case TMainMenu::LOAD_GAME_ID:gameTypes(true);break;
                    case TMainMenu::QUIT_ID:done=true;break;
                    default:if(!Port::shouldQuit())unavailable();break;
                }
            }
        }
        windows.close();input.close();mouse.close();ResourceManager::Close();Port::closeDisplay();return 0;
    }catch(const std::exception& e){fprintf(stderr,"Portable engine: %s\n",e.what());return 1;}
}
