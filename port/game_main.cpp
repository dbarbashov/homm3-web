// Portable startup and scene routing; all scenario/game rules and modal windows
// execute recovered upstream implementations, including normalDialog and executive.
#include "platform/sdl_backend.h"
#include "frontend_bridge.h"
#include "game.h"
#include "resourcemanager.h"
#include "bitmap16.h"
extern Bitmap16Bit* g_mainBack;
#include "mainmenu.h"
#include "gametypewindow.h"
#include "singleselectionwindow.h"
#include "exec.h"
#include "advmgr.h"
#include "inputmgr.h"
#include "mousemgr.h"
#include "winmgr.h"
#include "soundmgr.h"
#include "sample.h"
#include "button.h"
unsigned char loadSoundHeaders();
#include "font.h"
#include "kb.h"
#include "misc.h"
#include "savegame.h"
#include "remote.h"
#include "terrain.h"
#include "newgame.h"
#include "hiscore.h"
#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
bool portableNetworkStart();
bool portableChooseCampaign(bool load);
bool portableLoadGameData();
void portableInitVars();
void readPrefs();
void portableAdventureLoop(bool newGame);
void aiInitialize();
void portableRestartScenario();
namespace {
void background(){
    auto* b=ResourceManager::GetBitmap16("GamSelBk.pcx");
    b->Draw(0,0,b->GetWidth(),b->GetHeight(),g_windowManager->m_screenBitmap,0,0,false);
    ResourceManager::Dispose(b);
}
int scenarios(bool load){
    g_inSetupDialog=1;g_inCampaign=0;g_mpBaseType=10;if(!g_remoteOn)g_numHumanPlayers=1;
    g_game->m_isTutorial=0;
    background();
    {TSingleSelectionWindow select(load?1:0);select.doModal(false);}
    g_inSetupDialog=0;
    if(g_windowManager->m_dialogReturn==DIALOG_RETURN_CANCEL || Port::shouldQuit())return -1;
    g_gameCommand=-1;
    portableAdventureLoop(!load);
    return g_gameCommand;
}
int gameTypes(bool load){
    Port::setGameTypeMode(load);
    while(!Port::shouldQuit()){
        background();{TGameTypeWindow menu(load);menu.doModal();}
        int cmd=g_windowManager->m_dialogReturn;
        if(cmd==TGameTypeWindow::QUIT_ID || cmd<0)return -1;
        if(cmd==TGameTypeWindow::CAMPAIGN_ID){
            if(portableChooseCampaign(load)){portableAdventureLoop(!load);return g_gameCommand;}
        }
        else if(cmd==TGameTypeWindow::SINGLE_ID){int next=scenarios(load);if(next!=-1)return next;}
#ifdef __EMSCRIPTEN__
        else if(cmd==TGameTypeWindow::MULTIPLAYER_ID && !load){
            // The original menu enters the browser room flow before initializing a network game.
            EM_ASM({location.hash='multiplayer';location.reload();});
            throw Port::ExitRequested{};
        }
#endif
        else normalDialog("This mode is not connected in the portable client yet. Single scenarios are available.",1,-1,-1,-1,0,-1,0,-1,0,-1,0);
    }
    return -1;
}
}
int main(int argc,char** argv){
    if(argc<2){fprintf(stderr,"Usage: homm3-game RUNTIME_DIRECTORY\n");return 2;}
    setvbuf(stdout,nullptr,_IONBF,0);
    try{
        if(chdir(argv[1]))throw std::runtime_error("Cannot enter game runtime directory");
        initMainClasses();readPrefs();
        ResourceManager::SetPath("data/");ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
        int error=0;if(!ResourceManager::Open(true,true,&error))throw std::runtime_error("Cannot open LOD archives");
        if(!portableLoadGameData())throw std::runtime_error("Cannot initialize original game tables");
        g_game->m_worldMap.loadObjectTypeTemplates();aiInitialize();portableInitVars();
        if(!Port::openDisplay())throw std::runtime_error("Cannot open SDL display");
        loadSoundHeaders();g_executive->initSystem();g_soundManager->open(-1);
        button::s_clickSample=ResourceManager::GetSample("button.wav");
        g_systemPalette=ResourceManager::GetPalette("game.pal");
        g_playerPalette=ResourceManager::GetPalette("Players.pal");
        g_playerPalette24=ResourceManager::GetPalette24("Players.pal");
        g_tinyFont=ResourceManager::GetFont("tiny.fnt");
        g_smallFont=ResourceManager::GetFont("smalfont.fnt");
        g_mediumFont=ResourceManager::GetFont("medfont.fnt");
        g_bigFont=ResourceManager::GetFont("bigfont.fnt");
        g_calligraphicFont=ResourceManager::GetFont("Calli10R.fnt");
        g_mainBack=ResourceManager::GetBitmap16("mainmenu.pcx");
        for(auto& player:g_game->m_players)player.init();
        if(argc>2 && std::string(argv[2])=="--snapshot"){
            background();{TMainMenu menu;menu.drawWindow(true,WINDOW_ALL_WIDGETS_LOW,WINDOW_ALL_WIDGETS_HIGH);Port::notifySnapshot("main");menu.close(0);}
            ResourceManager::Dispose(g_mainBack);g_mainBack=nullptr;Port::closeDisplay();return 0;
        }
        bool done=false;int pending=-1;
        if(argc>2 && std::string(argv[2])=="--network"){
            if(!portableNetworkStart())throw std::runtime_error("Network room is not ready");
            scenarios(false);Port::closeDisplay();return 0;
        }
        while(!done && !Port::shouldQuit()){
            int command=pending;pending=-1;
            if(command==-1 || command==TMainMenu::MAIN_MENU_ID){g_mouseManager->reset();g_mouseManager->showPointer(true);g_soundManager->startMP3("MainMenu",0,0);background();TMainMenu menu;menu.doModal();command=g_windowManager->m_dialogReturn;}
            switch(command){
                case TMainMenu::NEW_GAME_ID:pending=gameTypes(false);break;
                case TMainMenu::LOAD_GAME_ID:pending=gameTypes(true);break;
                case TMainMenu::HIGH_SCORE_ID:g_highScoreManager->viewHiScore();break;
                case TMainMenu::CREDITS_ID:showCredits();break;
                case TMainMenu::RESTART_ID:portableRestartScenario();g_gameCommand=-1;portableAdventureLoop(true);pending=g_gameCommand;break;
                case TMainMenu::QUIT_ID:done=true;break;
            }
        }
        ResourceManager::Dispose(g_mainBack);g_mainBack=nullptr;
        Port::closeDisplay();return 0;
    }catch(const Port::ExitRequested&){Port::closeDisplay();return 0;}
    catch(const std::exception& e){fprintf(stderr,"Game startup: %s\n",e.what());return 1;}
}
