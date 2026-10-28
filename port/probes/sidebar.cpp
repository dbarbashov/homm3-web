// Render real locator widgets after fixture state changes, then check committed pixels.
#include "../platform/sdl_backend.h"
#include "hd_view.h"
#include "adventuremapwindow.h"
#include "game.h"
#include "hero.h"
#include "town.h"
#include "winmgr.h"
#include "widget.h"
#include "bitmap16.h"
#include "resourcemanager.h"
#include "kb.h"
#include "palette.h"
#include "font.h"
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <unistd.h>
extern Bitmap16Bit g_initWin;
bool portableLoadGameData();
static void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
static void matches(widget* item){
    bool painted=false;
    for(int y=item->m_y;y<item->m_y+item->m_height;++y){
        const auto* row=g_initWin.GetMap(item->m_x,y);
        for(int x=0;x<item->m_width;++x)painted|=row[x]!=0x2104;
        require(!std::memcmp(row,Port::committedFrame().GetMap(item->m_x,y),item->m_width*2),"locator pixels remain stale after update");
        require(!std::memcmp(row,Port::presentedFrame().GetMap(item->m_x,y),item->m_width*2),"locator composition remains stale");
    }
    require(painted,"fixture did not draw widget");
}
int main(int argc,char** argv){try{
    require(argc==2 && chdir(argv[1])==0,"runtime directory");initMainClasses();
    ResourceManager::SetPath("data/");ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
    int error=0;require(ResourceManager::Open(true,true,&error),"original resources");require(portableLoadGameData(),"game tables");
    g_playerPalette=ResourceManager::GetPalette("Players.pal");g_playerPalette24=ResourceManager::GetPalette24("Players.pal");
    g_smallFont=ResourceManager::GetFont("smalfont.fnt");g_mediumFont=ResourceManager::GetFont("medfont.fnt");
    require(Port::openDisplay(),"display");
    g_windowManager->m_screenBitmap=new Bitmap16Bit(0,0);
    g_windowManager->m_screenBitmap->reference(800,600,g_initWin.GetPitch(),g_initWin.GetMap(0,0));
    g_localGamePos=0;g_currentPlayer=&g_game->m_players[0];auto& player=*g_currentPlayer;
    player.m_isHuman=player.m_isLocal=1;player.m_numHeroes=player.m_numTowns=1;
    for(int i=0;i<8;++i)player.m_heroes[i]=HeroId(-1);
    player.m_heroes[0]=HeroId(0);player.m_townIds[0]=0;player.m_currHeroId=HeroId(0);player.m_currTownId=-1;
    g_game->m_towns.resize(1);auto& town=g_game->m_towns[0];town.m_type=0;town.m_builtThisTurn=0;
    auto& hero=g_game->m_heroes[0];hero.m_portrait=0;hero.m_mana=20;hero.m_movePoints=1936;
    for(auto size:{std::pair<int,int>{1200,600},{800,1200},{800,600}}){
        Port::resizeDisplay(size.first,size.second);
        auto* map=new TAdventureMapWindow;g_advManager->m_advWindow=map;
        g_windowManager->addWindow(map,0,0);
        g_initWin.FillRect(0,0,size.first,size.second,0x2104);Port::commitFrame(0,0,size.first,size.second);
        for(int step=0;step<3;++step){
            hero.m_movePoints=1936-step*300;hero.m_mana=25-step*5;town.m_builtThisTurn=step%2;
            g_advManager->m_status=1;hero.useSpell(5);g_advManager->m_status=0;
            matches(map->getWidget(TAdventureMapWindow::HERO_MANA_0_ID));
            map->updateHeroLocator(0,1,1);map->updateTownLocator(0,1,1);
            matches(map->getWidget(TAdventureMapWindow::HERO_MOVEMENT_0_ID));
            matches(map->getWidget(TAdventureMapWindow::HERO_MANA_0_ID));
            matches(map->getWidget(TAdventureMapWindow::TOWN_0_ID));
        }
        // Batched updates use the no-argument full-screen commit.
        hero.m_movePoints=1900;hero.m_mana=25;town.m_builtThisTurn=0;
        map->updateHeroLocators(-1,1,1);map->updateTownLocators(-1,1,1);
        matches(map->getWidget(TAdventureMapWindow::HERO_MANA_0_ID));matches(map->getWidget(TAdventureMapWindow::TOWN_0_ID));
        g_windowManager->removeWindow(map);delete map;g_advManager->m_advWindow=nullptr;
    }
    puts("{\"passed\":true,\"movement\":true,\"mana\":true,\"townBuilt\":true,\"widePortraitClassic\":true}");
}catch(const std::exception& e){fprintf(stderr,"Sidebar regression: %s\n",e.what());return 1;}}
