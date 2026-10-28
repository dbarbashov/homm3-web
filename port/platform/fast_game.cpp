// Opt-in concurrent adventure controller. One original engine owns the world;
// native windows are projections, browser controls submit authenticated intents.
#include "fast_game.h"
#include "game.h"
#include "hero.h"
#include "town.h"
#include "advmgr.h"
#include "adventuremapwindow.h"
#include "findpath.h"
#include "philai.h"
#include "creaturetype.h"
#include "recruit.h"
#include "host_path.h"
#include "castle.h"
#include "gzfile.h"
#include "kb.h"
#include "remote.h"
#include "inputmgr.h"
#include "winmgr.h"
#include "message.h"
#include <sstream>
#include <vector>
#include <stdexcept>
#include <climits>
#include <zlib.h>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace Port { namespace Fast {
namespace {
int localSlot=-1;
bool authority=false,failed=false;
int selectedHero=-1,selectedTown=-1;
type_point camera;
struct Running { Running(){state().running=true;} ~Running(){state().running=false;} };
int day(){return (g_game->m_month-1)*28+(g_game->m_week-1)*7+g_game->m_day;}
void require(bool condition,const char* text){if(!condition)throw std::runtime_error(text);}
std::string quote(const char* s){
    std::ostringstream out;out<<'"';
    for(const unsigned char* p=reinterpret_cast<const unsigned char*>(s?s:"");*p;++p){
        if(*p=='"'||*p=='\\')out<<'\\'<<char(*p);
        else if(*p<32){const char* h="0123456789abcdef";out<<"\\u00"<<h[*p>>4]<<h[*p&15];}
        else out<<char(*p);
    }out<<'"';return out.str();
}
void context(int slot){
    g_localGamePos=slot;g_netLocalGamePos=slot;g_playerTurn=slot;
    g_currentPlayer=&g_game->m_players[slot];g_curPlayerBit=1<<slot;
    g_curWatchPlayer=slot;g_mapVisibilityBit=1<<slot;
    for(int i=0;i<8;++i)g_game->m_players[i].m_isLocal=0;
    g_thisNetGotAdventureControl=authority?1:0;g_completeDrawEnabled=0;g_remoteOn=0;
    g_goSolo=0;g_turnDuration.clear();
}
void demobilize(){g_advManager->demobilizeCurrHero(false,false);}
void restoreView(bool center=false){
    context(localSlot);
    auto& p=g_game->m_players[localSlot];
    const bool townSelected=selectedHero<0 && selectedTown>=0 && selectedTown<int(g_game->m_towns.size()) && g_game->m_towns[selectedTown].m_owner==localSlot;
    if(!townSelected && (selectedHero<0 || selectedHero>=game::HERO_COUNT || g_game->m_heroes[selectedHero].m_owner!=localSlot)){
        selectedHero=p.m_numHeroes?int(p.m_heroes[0]):-1;
    }
    if(selectedTown<0 || selectedTown>=int(g_game->m_towns.size()) || g_game->m_towns[selectedTown].m_owner!=localSlot)
        selectedTown=p.m_numTowns?int(p.m_townIds[0]):-1;
    p.m_currHeroId=static_cast<HeroId>(selectedHero);p.m_currTownId=selectedHero<0?selectedTown:-1;
    g_advManager->m_curHeroMobile=0;
    if(center && selectedHero>=0){auto& h=g_game->m_heroes[selectedHero];camera=type_point(h.m_x-9,h.m_y-8,h.m_z);}
    else if(center && selectedTown>=0){auto& t=g_game->m_towns[selectedTown];camera=type_point(t.m_mapX-9,t.m_mapY-8,t.m_mapZ);}
    camera.m_x=std::max(-9,std::min(g_mapWidth-10,int(camera.m_x)));
    camera.m_y=std::max(-8,std::min(g_mapHeight-9,int(camera.m_y)));
    g_advManager->m_radarOrigin=camera;
    g_completeDrawEnabled=1;
    g_advManager->m_advWindow->updateHeroLocators(-1,1,1);
    g_advManager->m_advWindow->updateTownLocators(-1,1,1);
    g_advManager->m_advWindow->updateResourceDisplay(1,1);
    g_advManager->updateRadar(1,1,0,0,0);
    g_advManager->redrawAdvScreen(0,0);g_advManager->updateScreen(1,0);
}
hero* grailCarrier(const town& t){
    int id=t.m_visitingHeroId>=0?t.m_visitingHeroId:t.m_garrisonHeroId;
    if(id<0||id>=game::HERO_COUNT)return nullptr;
    auto& h=g_game->m_heroes[id];return h.m_owner==t.m_owner&&h.hasArtifact(ARTIFACT_HOLY_GRAIL)?&h:nullptr;
}
bool canPurchaseBuilding(const town& t,int building){
    if(building<0||building>=MAX_BUILDING_TYPE)return false;
    if(building==HOLY_GRAIL_ID)return !t.hasBuilding(HOLY_GRAIL_ID,true)&&t.isLegalBuilding(HOLY_GRAIL_ID)&&grailCarrier(t);
    // These entries are rendered automatically with other structures/boats.
    if(building==DOCK_WITH_BOAT_ID||(building>=EXTRA_3_ID&&building<=EXTRA_5_ID))return false;
    return !g_game->townAlreadyBuiltOn(t.m_id)&&(t.getBuildableMask()&g_bitNumber[building]);
}
template<class T> void resources(std::ostream& o,const T* r){o<<'[';for(int i=0;i<7;++i){if(i)o<<',';o<<r[i];}o<<']';}
void army(std::ostream& o,const armyGroup& a){o<<'[';for(int i=0;i<7;++i){if(i)o<<',';o<<"{\"type\":"<<a.m_armies[i]<<",\"count\":"<<a.m_numTroops[i]<<",\"name\":"<<quote(a.m_armies[i]>=0&&a.m_numTroops[i]>0?getArmyName(a.m_armies[i],a.m_numTroops[i]):"")<<'}';}o<<']';}
std::string view(){
    std::ostringstream o;o<<"{\"day\":"<<g_game->m_day<<",\"week\":"<<g_game->m_week<<",\"month\":"<<g_game->m_month
      <<",\"absoluteDay\":"<<day()<<",\"localPlayer\":"<<localSlot<<",\"mapSize\":"<<g_mapWidth
      <<",\"gameOver\":"<<(g_gameOver?"true":"false")<<",\"selectedHero\":"<<selectedHero<<",\"selectedTown\":"<<selectedTown
      <<",\"camera\":{\"x\":"<<camera.m_x<<",\"y\":"<<camera.m_y<<",\"z\":"<<camera.m_z<<"},\"players\":[";
    for(int i=0;i<8;++i){if(i)o<<',';auto& p=g_game->m_players[i];
        o<<"{\"slot\":"<<i<<",\"dpid\":"<<p.m_dpid<<",\"human\":"<<(p.isHuman()?"true":"false")<<",\"alive\":"<<(!g_game->m_playerDisabled[i]?"true":"false")<<",\"name\":"<<quote(p.m_name)<<",\"resources\":";resources(o,p.m_resources);o<<'}';}
    o<<"],\"heroes\":[";bool comma=false;
    for(int i=0;i<game::HERO_COUNT;++i){auto& h=g_game->m_heroes[i];if(h.m_owner!=localSlot)continue;if(comma)o<<',';comma=true;
        o<<"{\"id\":"<<i<<",\"owner\":"<<int(h.m_owner)<<",\"name\":"<<quote(h.m_name)<<",\"x\":"<<h.m_x<<",\"y\":"<<h.m_y<<",\"z\":"<<h.m_z<<",\"experience\":"<<h.m_experience<<",\"movement\":"<<h.m_movePoints<<",\"mana\":"<<h.m_mana<<",\"portrait\":"<<int(h.m_portrait)<<",\"army\":";army(o,h.m_army);o<<'}';}
    o<<"],\"towns\":[";comma=false;
    for(int i=0;i<int(g_game->m_towns.size());++i){auto& t=g_game->m_towns[i];if(t.m_owner!=localSlot)continue;if(comma)o<<',';comma=true;
        o<<"{\"id\":"<<i<<",\"owner\":"<<int(t.m_owner)<<",\"name\":"<<quote(t.m_name.c_str())<<",\"x\":"<<int(t.m_mapX)<<",\"y\":"<<int(t.m_mapY)<<",\"z\":"<<int(t.m_mapZ)<<",\"type\":"<<int(t.m_type)<<",\"army\":";army(o,t.getArmy());o<<",\"buildings\":[";
        for(int b=0;b<MAX_BUILDING_TYPE;++b){if(b)o<<',';int cost[7]={};
            // Grail and hall-art variants have no entry in the nine-row special cost table.
            if(b<HOLY_GRAIL_ID||b>=DWELLING_0_ID)t.getBuildCost(static_cast<type_building_id>(b),cost);
            o<<"{\"id\":"<<b<<",\"name\":"<<quote(getBuildingName(t.m_type,b))<<",\"allowed\":"<<(canPurchaseBuilding(t,b)?"true":"false")<<",\"cost\":";resources(o,cost);o<<'}';}
        o<<"],\"offers\":[";bool c=false;auto& p=g_game->m_players[localSlot];
        if(t.hasBuilding(TAVERN_ID,true))for(int j=0;j<2;++j){int id=p.m_recruits[j];if(id<0||id>=game::HERO_COUNT)continue;if(c)o<<',';c=true;o<<"{\"id\":"<<id<<",\"name\":"<<quote(g_game->m_heroes[id].m_name)<<'}';}
        o<<"],\"creatures\":[";c=false;
        for(int s=0;s<14;++s){if(!t.hasBuilding(DWELLING_0_ID+s,true))continue;int type=g_dwellingType[t.m_type][s];if(type<0)continue;
            if(c)o<<',';c=true;o<<"{\"slot\":"<<s<<",\"type\":"<<type<<",\"name\":"<<quote(getArmyName(type,2))<<",\"available\":"<<t.m_population[s]<<",\"cost\":";int cost[7];getMonsterCost(type,cost);resources(o,cost);o<<'}';}
        o<<"]}";
    }o<<"]}";return o.str();
}
void complete(int seq,bool ok,const char* error,bool snapshot){
    std::string json="{\"seq\":"+std::to_string(seq)+",\"ok\":"+(ok?"true":"false")+",\"error\":"+quote(error)+",\"gameOver\":"+(g_gameOver?"true":"false")+",\"day\":"+std::to_string(day())+",\"view\":"+view()+"}";
    std::vector<unsigned char> bytes;
    if(snapshot){
        require(g_game->saveGame("RMTfast-outgoing.gm2",false,false,true,true),"Cannot serialize canonical game");
        auto path=Port::hostPath("data/RMTfast-outgoing.gm2");FILE* file=fopen(path.c_str(),"rb");require(file,"Cannot read canonical game");
        fseek(file,0,SEEK_END);long size=ftell(file);rewind(file);
        if(size<=0||size>16*1024*1024){fclose(file);throw std::runtime_error("Invalid canonical save size");}
        bytes.resize(size);const size_t count=fread(bytes.data(),1,bytes.size(),file);fclose(file);require(count==bytes.size(),"Cannot read canonical game");
    }
#ifdef __EMSCRIPTEN__
    EM_ASM({const meta=JSON.parse(new TextDecoder('windows-1251').decode(HEAPU8.subarray($0,$0+$1)));const bytes=$2?HEAPU8.slice($3,$3+$4):null;window.homm3FastNative.complete(meta,bytes);},json.data(),json.size(),snapshot,bytes.data(),bytes.size());
#endif
}
void fault(const char* error){failed=true;
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3FastNative.fault(UTF8ToString($0));},error);
#endif
}
void resetMovement(int slot){auto& p=g_game->m_players[slot];for(int n=0;n<p.m_numHeroes;++n){auto& h=g_game->m_heroes[p.m_heroes[n]];h.m_maxMovePoints=h.m_movePoints=h.getMobility();}}
void nextDay(){
    for(int i=0;i<8;++i)if(!g_game->m_playerDisabled[i]){
        auto& p=g_game->m_players[i];if(p.m_deathCountDown>0)--p.m_deathCountDown;
    }
    for(int i=0;i<8 && !g_gameOver;++i)if(!g_game->m_playerDisabled[i]&&!g_game->isHuman(i)){
        context(i);resetMovement(i);g_game->checkForTimeEvent();g_game->checkForTownEvent();g_philAI->doAI(i);demobilize();
    }
    if(g_gameOver)return;
    g_game->perDay();
    for(int i=0;i<8 && !g_gameOver;++i)if(!g_game->m_playerDisabled[i]){context(i);resetMovement(i);g_game->checkForTimeEvent();g_game->checkForTownEvent();checkEndGame(0);}
}
// Validate the complete gzip member (including CRC) before the original loader
// can replace any world pools. Authority packets use the current save version.
void validateSnapshotFile(const char* filename){
    auto path=Port::hostPath(filename);FILE* file=fopen(path.c_str(),"rb");require(file,"Missing canonical snapshot");
    fseek(file,0,SEEK_END);long compressed=ftell(file);rewind(file);unsigned char magic[2]={};fread(magic,1,2,file);fclose(file);
    require(compressed>=18&&compressed<=4*1024*1024&&magic[0]==0x1f&&magic[1]==0x8b,"Invalid canonical snapshot envelope");
    gzFile gzip=gzopen(path.c_str(),"rb");require(gzip,"Cannot open canonical snapshot");
    unsigned char prefix[16]={},buffer[16384];int prefixSize=gzread(gzip,prefix,sizeof(prefix));
    int count=0;size_t total=prefixSize>0?prefixSize:0;
    while((count=gzread(gzip,buffer,sizeof(buffer)))>0){total+=count;if(total>128*1024*1024)break;}
    int code=Z_OK;gzerror(gzip,&code);int closed=gzclose(gzip);int version=0;memcpy(&version,prefix+8,sizeof(version));
    require(prefixSize==16&&!memcmp(prefix,"H3SVG",5)&&version==42&&count>=0&&code==Z_OK&&closed==Z_OK&&total<=128*1024*1024,"Corrupt canonical snapshot");
}
void apply(const int* c){
    const int op=c[0],actor=c[1],id=c[2],a=c[3],b=c[4];
    if(op==6){
        require(!authority,"Authority cannot import a peer snapshot");
        // Use original loader to clear ancillary pools as well as deserialize.
        // It expects RMT-prefixed files in DATA; copy incoming into that path.
#ifdef __EMSCRIPTEN__
        EM_ASM({FS.writeFile('/runtime/data/RMTfast.gm2',FS.readFile('/runtime/fast-incoming.gm2'));});
#endif
        validateSnapshotFile("data/RMTfast.gm2");
        require(g_game->loadGame("RMTfast.gm2",0,1)!=0,"Cannot load canonical snapshot");
        require(day()==c[7],"Snapshot day does not match canonical metadata");
        g_gameOver=c[5]!=0;return;
    }
    if(op==7){require(id>=0&&id<game::HERO_COUNT&&g_game->m_heroes[id].m_owner==localSlot,"Hero unavailable");selectedHero=id;selectedTown=-1;restoreView(true);return;}
    if(op==8){require(id>=0&&id<int(g_game->m_towns.size())&&g_game->m_towns[id].m_owner==localSlot,"Town unavailable");selectedTown=id;selectedHero=-1;auto& t=g_game->m_towns[id];camera=type_point(t.m_mapX-9,t.m_mapY-8,t.m_mapZ);return;}
    if(op==9){camera.m_x+=std::max(-20,std::min(20,a));camera.m_y+=std::max(-20,std::min(20,b));return;}
    if(op==10)return;
    require(authority,"Only authority executes world commands");require(c[7]==day(),"Command belongs to another day");
    require(!g_gameOver,"Game has ended");
    if(op==5){nextDay();return;}
    require(actor>=0&&actor<8&&!g_game->m_playerDisabled[actor]&&g_game->isHuman(actor),"Player is inactive");
    context(actor);
    if(op==1){
        require(id>=0&&id<game::HERO_COUNT&&g_game->m_heroes[id].m_owner==actor,"Hero is not yours");require(a>=0&&a<8,"Invalid direction");
        auto& h=g_game->m_heroes[id];require(h.m_movePoints>0,"No movement points");
        g_advManager->setHeroContext(id,0,false,false);
        h.m_pathTargetX=h.m_x+g_normalDirTable[a].m_x;h.m_pathTargetY=h.m_y+g_normalDirTable[a].m_y;h.m_pathTargetZ=h.m_z;
        require(g_advManager->validMove(&h,a,0,true)||g_advManager->validMoveWithEvent(&h,a),"Step is blocked");
        type_point trigger;int noMove=0,battle=0;
        NewmapCell* event=g_advManager->moveHero(a,true,trigger,&noMove,true,&battle,false);
        if(event&&h.m_owner==actor)g_advManager->doAIEvent(event,&h,trigger);
        demobilize();if(actor==localSlot){selectedHero=id;camera=g_advManager->m_radarOrigin;}return;
    }
    require(id>=0&&id<int(g_game->m_towns.size()),"Town unavailable");auto& t=g_game->m_towns[id];
    require(t.m_owner==actor,"Town is not yours");
    if(op==2){
        require(canPurchaseBuilding(t,a),"Building prerequisites, daily limit or Grail requirement not met");
        if(a==HOLY_GRAIL_ID){
            grailCarrier(t)->removeArtifact(ARTIFACT_HOLY_GRAIL);t.buildBuilding(a,true,true);
            if(g_game->m_mapHeader.m_victoryCondition.checkForGrailBuildingWin())checkEndGame(0);
        }else require(t.buyBuilding(static_cast<type_building_id>(a)),"Building unavailable or insufficient resources");
        return;
    }
    if(op==3){
        auto& p=g_game->m_players[actor];require(a>=0&&a<game::HERO_COUNT&&(p.m_recruits[0]==a||p.m_recruits[1]==a),"Hero offer has changed");
        require(t.hasBuilding(TAVERN_ID,true),"Tavern required");require(p.m_numHeroes<playerData::HERO_SLOT_COUNT,"Hero limit reached");
        require(t.m_visitingHeroId<0,"Town entrance is occupied");require(p.m_resources[GOLD]>=g_heroGoldCost,"Not enough gold");
        auto& h=g_game->m_heroes[a];require(h.m_owner<0,"Hero already hired");
        t.hire(&h,actor);t.applySpecialBuildingEffect(&h);h.m_movePoints=h.m_maxMovePoints=h.getMobility();return;
    }
    if(op==4){
        require(a>=0&&a<14&&b>0&&b<=1000000,"Invalid recruitment");require(t.hasBuilding(DWELLING_0_ID+a,true),"Dwelling required");
        require(t.m_population[a]>=b,"Not enough creatures");int type=g_dwellingType[t.m_type][a];require(type>=0,"Creature unavailable");
        auto& army=t.getArmy();require(army.canJoin(static_cast<TCreatureType>(type)),"Army is full");
        int cost[7];getMonsterCost(type,cost);auto& p=g_game->m_players[actor];
        for(int r=0;r<7;++r)require(cost[r]>=0&&int64_t(cost[r])*b<=p.m_resources[r],"Not enough resources");
        require(army.getCreatureTotal(static_cast<TCreatureType>(type))<=INT_MAX-b,"Army count overflow");
        army.add(static_cast<TCreatureType>(type),b,-1);for(int r=0;r<7;++r)p.m_resources[r]-=cost[r]*b;t.m_population[a]-=b;return;
    }
    throw std::runtime_error("Unknown command");
}
}
void begin(){
#ifdef __EMSCRIPTEN__
    if(enabled()||!EM_ASM_INT({return !!(window.homm3Network&&window.homm3Network.fastGame);} ))return;
    require(g_localGamePos>=0&&g_localGamePos<8,"Missing local player");localSlot=g_localGamePos;
    authority=EM_ASM_INT({return window.homm3Network.self===window.homm3Network.host;});
    state().active=true;Running running;camera=g_advManager->m_radarOrigin;
    const int firstActor=g_netLocalGamePos;
    demobilize();context(localSlot);g_inputManager->flush();
    if(authority)for(int i=0;i<8 && !g_gameOver;++i)if(i!=firstActor&&!g_game->m_playerDisabled[i]&&g_game->isHuman(i)){
        context(i);g_game->checkForTimeEvent();g_game->checkForTownEvent();
    }
    restoreView(true);
    EM_ASM({window.homm3FastNative.started($0,!!$1);},localSlot,authority);
#endif
}
int adventureMain(message&){
#ifdef __EMSCRIPTEN__
    if(!enabled()||executing()||failed)return MESSAGE_DISPATCH_CONSUME;
    if(!EM_ASM_INT({return !!window.homm3FastNative && window.homm3FastNative.canRun!==false;}))return MESSAGE_DISPATCH_CONSUME;
    int command[8]={};
    if(!EM_ASM_INT({const c=window.homm3FastNative.take();if(!c)return 0;for(let i=0;i<8;++i)HEAP32[($0>>2)+i]=c[i]||0;return 1;},command))return MESSAGE_DISPATCH_CONSUME;
    Running running;bool ok=true;std::string error;
    try{demobilize();apply(command);}catch(const std::exception& e){
        ok=false;error=e.what();
        if(command[0]==6){fault(error.c_str());return MESSAGE_DISPATCH_CONSUME;}
    }
    try{
        demobilize();restoreView();
        bool snapshot=authority && (command[0]<=5||command[0]==10);
        complete(command[6],ok,error.c_str(),snapshot);
    }catch(const std::exception& e){fault(e.what());}
#endif
    return MESSAGE_DISPATCH_CONSUME;
}
} }
