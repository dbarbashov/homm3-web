// Exercise real fast command transactions and original battle rules without browser UI.
// Including the bridge exposes its private dispatcher only inside this isolated probe.
#include "../platform/fast_game.cpp"
#include "resourcemanager.h"
#include "ai_combat.h"
#include "../platform/sdl_backend.h"
#include "font.h"
#include "palette.h"
#include "mousemgr.h"
#include "exec.h"
#include "bitmap16.h"
#include "soundmgr.h"
#include "prefs.h"
#include <unistd.h>
#include <sys/stat.h>
bool portableLoadGameData();
void aiInitialize();
unsigned char loadSoundHeaders();
extern Bitmap16Bit g_initWin;
struct EmptyMapStream : TAbstractFile {
 int read(void* data,int size)override{memset(data,0,size);return size;}
 int write(const void*,int)override{return 0;}
};
int main(int argc,char** argv){try{
 if(argc!=2||chdir(argv[1]))return 2;initMainClasses();
 ResourceManager::SetPath("data/");ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
 int err=0;Port::Fast::require(ResourceManager::Open(true,true,&err),"resources");Port::Fast::require(portableLoadGameData(),"tables");
 Port::Fast::state().active=true;Port::Fast::state().running=true;Port::Fast::localSlot=0;Port::Fast::authority=true;
 g_game->m_day=1;g_game->m_week=1;g_game->m_month=1;g_gameOver=0;
 auto& p=g_game->m_players[0];p.m_isHuman=1;p.m_isLocal=0;g_game->m_playerDisabled[0]=0;
 auto& q=g_game->m_players[1];q.m_isHuman=1;q.m_isLocal=0;g_game->m_playerDisabled[1]=0;
 g_game->m_heroes[0].m_owner=1;
 int tests=0;auto rejected=[&](int* c){try{Port::Fast::apply(c);}catch(const std::runtime_error&){++tests;return;}throw std::runtime_error("invalid command accepted");};
 int wrongHero[]={1,0,0,0,0,0,1,1};rejected(wrongHero);
 int oldDay[]={1,0,0,0,0,0,2,2};rejected(oldDay);
 int badActor[]={1,8,0,0,0,0,3,1};rejected(badActor);
 int badTown[]={2,0,1000,0,0,0,4,1};rejected(badTown);
 for(int i=2;i<8;++i)g_game->m_playerDisabled[i]=1;q.m_numHeroes=1;q.m_heroes[0]=HeroId(0);p.m_numTowns=1;p.m_townIds[0]=0;
 g_game->m_towns.resize(1);auto& t=g_game->m_towns[0];t.m_id=0;t.m_owner=1;t.m_type=0;t.m_garrisonHeroId=t.m_visitingHeroId=-1;
 int otherTown[]={2,0,0,TAVERN_ID,0,0,5,1};rejected(otherTown);
 t.m_owner=0;t.m_builtThisTurn=0;t.setLegalBuildings(0);
 for(int i=0;i<7;++i)p.m_resources[i]=0;
 int build[]={2,0,0,TAVERN_ID,0,0,6,1};rejected(build);
 for(int i=0;i<7;++i)p.m_resources[i]=100000;
 // The native human hall uses its hierarchy mask, not the AI canBuild shortcut.
 int noCityHall[]={2,0,0,HALL_CAPITOL_ID,0,0,20,1};rejected(noCityHall);
 Port::Fast::require(!Port::Fast::canPurchaseBuilding(t,HALL_CAPITOL_ID),"Capitol requires its prerequisite chain");
 int noGrail[]={2,0,0,HOLY_GRAIL_ID,0,0,21,1};rejected(noGrail);
 int pseudoBoat[]={2,0,0,DOCK_WITH_BOAT_ID,0,0,22,1};rejected(pseudoBoat);
 int before=p.m_resources[GOLD];int cost[7];t.getBuildCost(static_cast<type_building_id>(TAVERN_ID),cost);
 Port::Fast::apply(build);Port::Fast::require(p.m_resources[GOLD]==before-cost[GOLD],"building payment");Port::Fast::require(t.hasBuilding(TAVERN_ID,true),"building installed");++tests;
 int repeat[]={2,0,0,TAVERN_ID,0,0,7,1};rejected(repeat);
 int hireBad[]={3,0,0,155,0,0,8,1};p.m_recruits[0]=p.m_recruits[1]=heroIdNone;rejected(hireBad);
 t.buildBuilding(DWELLING_0_ID,false,false);t.m_population[0]=10;
 int troop=g_dwellingType[0][0];getMonsterCost(troop,cost);before=p.m_resources[GOLD];
 int recruit[]={4,0,0,0,3,0,9,1};Port::Fast::apply(recruit);
 Port::Fast::require(t.m_population[0]==7,"population decremented");Port::Fast::require(t.getArmy().getCreatureTotal(static_cast<TCreatureType>(troop))==3,"troops added");Port::Fast::require(p.m_resources[GOLD]==before-3*cost[GOLD],"recruitment payment");++tests;
 int negative[]={4,0,0,0,-5,0,10,1};rejected(negative);
 int tooMany[]={4,0,0,0,8,0,11,1};rejected(tooMany);
 auto& fighter=g_game->m_heroes[1];fighter.m_owner=0;fighter.m_army.initialize();fighter.m_army.add(static_cast<TCreatureType>(0),1000,-1);fighter.m_experience=0;fighter.m_level=1;
 armyGroup neutral;neutral.initialize();neutral.add(static_cast<TCreatureType>(0),1,-1);NewmapCell battleCell;
 Port::Fast::require(aiQuickCombat(&fighter,nullptr,neutral,nullptr,&battleCell),"original AI battle victory");Port::Fast::require(!neutral.hasCreatures(),"original battle casualties");Port::Fast::require(fighter.m_experience>0,"original battle XP");++tests;
 // Real adventure fixture: renderer/managers and ordinary map cells, without debug APIs.
 Port::Fast::require(Port::openDisplay(),"native display");
 g_windowManager->m_screenBitmap=new Bitmap16Bit(0,0);
 g_windowManager->m_screenBitmap->reference(800,600,g_initWin.GetPitch(),g_initWin.GetMap(0,0));
 g_systemPalette=ResourceManager::GetPalette("game.pal");
 g_playerPalette=ResourceManager::GetPalette("Players.pal");g_playerPalette24=ResourceManager::GetPalette24("Players.pal");
 g_smallFont=ResourceManager::GetFont("smalfont.fnt");g_mediumFont=ResourceManager::GetFont("medfont.fnt");
 g_tinyFont=ResourceManager::GetFont("tiny.fnt");g_bigFont=ResourceManager::GetFont("bigfont.fnt");
 loadSoundHeaders();g_executive->initSystem();g_soundManager->open(-1);
 g_game->m_worldMap.loadObjectTypeTemplates();aiInitialize();
 g_mapWidth=g_mapHeight=36;g_game->m_mapHeader.m_size=36;g_game->m_mapHeader.m_hasTwoLayers=0;
 EmptyMapStream empty;Port::Fast::require(g_game->m_worldMap.read(&empty,36,0,0x1c)==0,"empty ordinary map");g_game->m_mapHeader.m_numPlayers=2;g_game->m_mapHeader.m_numTeams=0;
 for(int i=0;i<8;++i){g_game->m_mapHeader.m_teamInfo[i]=i;g_game->m_setup.m_color[i]=i;g_game->m_setup.m_alignment[i]=static_cast<TTownType>(0);}
 for(int y=0;y<36;++y)for(int x=0;x<36;++x){auto* cell=g_game->getCell(type_point(x,y,0));cell->m_groundSet=2;cell->m_passable=1;}
 for(int i=0;i<game::HERO_COUNT;++i){g_game->m_heroes[i].m_id=static_cast<HeroId>(i);g_game->m_heroAvailability[i]=-1;}
 p.m_numHeroes=q.m_numHeroes=0;p.m_currHeroId=q.m_currHeroId=heroIdNone;p.m_currTownId=q.m_currTownId=-1;
 fighter.placeInMap(0,type_point(10,10,0),true);fighter.m_movePoints=fighter.m_maxMovePoints=2000;
 auto& defender=g_game->m_heroes[0];defender.m_army.initialize();defender.m_army.add(static_cast<TCreatureType>(0),1,-1);
 defender.placeInMap(1,type_point(11,10,0),true);defender.m_movePoints=2000;
 g_game->m_towns.resize(2);
 for(int i=0;i<2;++i){auto& town=g_game->m_towns[i];town.m_id=i;town.m_owner=i;town.m_mapX=5+20*i;town.m_mapY=5+20*i;town.m_mapZ=0;town.m_garrisonHeroId=town.m_visitingHeroId=-1;town.setLegalBuildings(0);town.buildBuilding(TAVERN_ID,false,false);town.m_builtThisTurn=0;
  auto* cell=g_game->getCell(type_point(town.m_mapX,town.m_mapY,0));cell->m_type=TOWN;cell->m_isTrigger=1;cell->m_extraInfo=i;
  auto& player=g_game->m_players[i];player.m_numTowns=1;player.m_townIds[0]=i;strcpy(player.m_name,i?"Second":"First");}
 p.m_currHeroId=static_cast<HeroId>(1);q.m_currHeroId=static_cast<HeroId>(0);
 Port::Fast::context(0);g_gameOver=0;g_config.m_blackoutComputer=1;g_game->m_setup.m_turnDuration=0;
 Port::Fast::require(g_advManager->open(-1)==0,"adventure manager");
 Port::Fast::context(0);int xpBefore=fighter.m_experience;int pvp[]={1,0,1,2,0,0,24,Port::Fast::day()};
 Port::Fast::apply(pvp);
 Port::Fast::require(defender.m_owner==-1&&q.m_numHeroes==0,"PvP removes defeated human hero");
 Port::Fast::require(fighter.m_experience>xpBefore&&fighter.m_army.hasCreatures(),"PvP XP and surviving army");++tests;
 // Deliberately stale duplicated offer represents concurrent clients' old views.
 auto& offer=g_game->m_heroes[2];offer.m_owner=-1;offer.m_army.initialize();offer.m_army.add(static_cast<TCreatureType>(0),10,-1);
 g_game->m_heroAvailability[2]=64;p.m_recruits[0]=q.m_recruits[0]=static_cast<HeroId>(2);p.m_recruits[1]=q.m_recruits[1]=heroIdNone;
 p.m_resources[GOLD]=q.m_resources[GOLD]=10000;int firstGold=p.m_resources[GOLD],secondGold=q.m_resources[GOLD];
 int firstHire[]={3,0,0,2,0,0,25,Port::Fast::day()};Port::Fast::apply(firstHire);
 Port::Fast::require(offer.m_owner==0&&p.m_resources[GOLD]==firstGold-g_heroGoldCost,"first hire commits exactly one payment");++tests;
 int secondHire[]={3,1,1,2,0,0,26,Port::Fast::day()};rejected(secondHire);
 Port::Fast::require(offer.m_owner==0&&q.m_resources[GOLD]==secondGold&&g_game->m_towns[1].m_visitingHeroId==-1,"stale losing offer cannot charge or duplicate hero");++tests;
 // Terminal worlds must reject day advancement before countdowns/AI can mutate.
 g_gameOver=1;int terminalDay=Port::Fast::day();int terminalAdvance[]={5,-1,0,0,0,0,23,terminalDay};rejected(terminalAdvance);
 Port::Fast::require(Port::Fast::day()==terminalDay,"terminal day must remain unchanged");
 // Corrupt snapshots must be reported as failed only in the opt-in controller.
 char temporary[]="/tmp/homm3-fast-load-XXXXXX";char* directory=mkdtemp(temporary);
 Port::Fast::require(directory&&chdir(directory)==0&&mkdir("data",0700)==0,"temporary save fixture");
 // Round-trip a real complete world through the guest APPLY opcode. The original
 // format lacks g_gameOver, so c[5] must restore terminal metadata after load.
 g_game->clearEventRecords();
 Port::Fast::require(g_game->saveGame("RMTfast.gm2",false,false,true,true),"canonical terminal save fixture");
 // Native LP64's original empty-event reader requests sizeof(long)=8 while
 // the recovered writer emits 4. A valid extra gzip member supplies its unused
 // high word; WASM has 32-bit long and needs no such fixture accommodation.
 gzFile nativeTail=gzopen("data/RMTfast.gm2","ab");int padding=0;gzwrite(nativeTail,&padding,4);gzclose(nativeTail);
 Port::Fast::authority=false;Port::Fast::localSlot=1;g_gameOver=0;
 int importTerminal[]={6,1,0,0,0,1,27,terminalDay};Port::Fast::apply(importTerminal);
 Port::Fast::require(g_gameOver&&Port::Fast::view().find("\"gameOver\":true")!=std::string::npos,"APPLY terminal metadata reaches native projection");++tests;
 int importLive[]={6,1,0,0,0,0,28,terminalDay};Port::Fast::apply(importLive);
 Port::Fast::require(!g_gameOver&&Port::Fast::view().find("\"gameOver\":false")!=std::string::npos,"APPLY live metadata reaches native projection");++tests;
 unlink("data/RMTfast.gm2");
 unsigned char envelope[64]={};memcpy(envelope,"H3SVG",5);int version=42;memcpy(envelope+8,&version,sizeof(version));
 gzFile valid=gzopen("data/RMTfast-crc.gm2","wb");Port::Fast::require(valid,"gzip fixture");gzwrite(valid,envelope,sizeof(envelope));gzclose(valid);
 Port::Fast::validateSnapshotFile("data/RMTfast-crc.gm2");++tests;
 FILE* damaged=fopen("data/RMTfast-crc.gm2","r+b");fseek(damaged,-8,SEEK_END);int checksum=fgetc(damaged);fseek(damaged,-1,SEEK_CUR);fputc(checksum^0x80,damaged);fclose(damaged);
 bool crcRejected=false;try{Port::Fast::validateSnapshotFile("data/RMTfast-crc.gm2");}catch(const std::runtime_error&){crcRejected=true;}
 Port::Fast::require(crcRejected,"gzip checksum must be checked before load");++tests;unlink("data/RMTfast-crc.gm2");
 FILE* bad=fopen("data/RMTfast-invalid.gm2","wb");Port::Fast::require(bad,"invalid save fixture");fputs("invalid",bad);fclose(bad);
 Port::Fast::require(g_game->loadGame("RMTfast-invalid.gm2",0,1)==0,"fast snapshot parse failure");++tests;
 Port::Fast::state().active=false;Port::Fast::state().running=false;
 Port::Fast::require(g_game->loadGame("RMTfast-invalid.gm2",0,1)==1,"legacy loader return behavior unchanged");++tests;
 unlink("data/RMTfast-invalid.gm2");rmdir("data");chdir("/");rmdir(directory);
 printf("{\"passed\":true,\"checks\":%d,\"ownership\":true,\"day\":true,\"build\":true,\"buildingPrerequisites\":true,\"terminalGuard\":true,\"recruit\":true,\"combat\":true,\"pvpCommand\":true,\"sharedHireRace\":true,\"terminalSnapshot\":true,\"invalidSnapshot\":true,\"gzipIntegrity\":true,\"legacyGuard\":true}\n",tests);
 return 0;
 }catch(const std::exception& e){fprintf(stderr,"Fast probe: %s [map=%d towns=%zu day=%d]\n",e.what(),g_mapWidth,g_game->m_towns.size(),g_game->m_day);return 1;}}
