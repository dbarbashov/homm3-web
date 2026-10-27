// Load every retail campaign and every embedded scenario using the engine reader.
#include "game.h"
#include "customcampaign.h"
#include "resourcemanager.h"
#include "kb.h"
#include "abstractfile.h"
#include "gzinflatebuf.h"
#include "remote.h"
#include <sstream>
#include <cassert>
#include <cstdio>
#include <unistd.h>
bool portableLoadGameData();
struct StreamFile : TAbstractFile {
 std::streambuf* stream; explicit StreamFile(std::streambuf* s):stream(s){}
 int read(void* data,int size)override{return stream->sgetn(static_cast<char*>(data),size);}
 int write(const void* data,int size)override{return stream->sputn(static_cast<const char*>(data),size);}
};
int main(int argc,char** argv){
 try {
  if(argc<2 || chdir(argv[1]))return 2;
  initMainClasses();ResourceManager::SetPath("data/");ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
  int error=0;if(!ResourceManager::Open(true,true,&error) || !portableLoadGameData())return 3;
  const char* files[]={"Good1.h3c","Good2.h3c","Neutral1.h3c","Good3.h3c","Evil1.h3c","Evil2.h3c","Secret1.h3c","AB.h3c","blood.h3c","slayer.h3c","festival.h3c","fool.h3c","fire.h3c","crag.h3c","yog.h3c","gem.h3c","gelu.h3c","sandro.h3c","final.h3c","secret.h3c"};
  g_game->m_worldMap.loadObjectTypeTemplates();
  if(argc==4){
   int id=atoi(argv[2]),map=atoi(argv[3]);assert(id>=0 && id<20);
   TCampaignBrief::CampaignHeaderStruct header(files[id]);assert(header.load());assert(map>=0 && map<header.getScenarioCount());
   header.m_stream->pubseekoff(header.m_scenarios[map]->m_offset,std::ios::beg,std::ios::in);
   TGzInflateBuf inflated(header.m_stream);StreamFile stream(&inflated);assert(g_game->loadMap(&stream));
   printf("Loaded campaign %d scenario %d size %d\n",id,map,g_game->m_mapHeader.m_size);return 0;
  }
  int maps=0;
  for(int id=0;id<20;++id){
   TCampaignBrief::CampaignHeaderStruct h(files[id]);assert(h.load());
   auto& c=g_game->m_campaign;c.selectCampaign(id,files[id]);
   std::vector<unsigned char> available(h.getScenarioCount());h.getAvailableScenarios(available.data());
   int count=0,starts=0;
   for(int i=0;i<h.getScenarioCount();++i){if(!h.m_scenarios[i]->hasMap())continue;
    NewSMapHeader map;assert(h.loadScenario(i,&map));assert(map.m_size==36 || map.m_size==72 || map.m_size==108 || map.m_size==144);++count;starts+=available[i]!=0;printf("SCENARIO %d %d\n",id,i);
   }
   assert(count>0 && starts>0);
   // Simulate only the victory bookkeeping, then round-trip the real campaign save.
   // Actual UI victory/continuation is covered by campaign-browser-smoke.py.
   for(auto& player:g_game->m_players)player.init();
   g_localGamePos=0;g_game->m_players[0].m_isHuman=1;g_game->m_players[0].m_isLocal=1;
   g_game->m_players[0].m_numHeroes=1;g_game->m_players[0].m_heroes[0]=HeroId(6);
   g_game->m_heroes[6].m_id=HeroId(6);g_game->m_heroes[6].m_experience=12000;g_game->m_heroes[6].m_level=8;
   g_game->m_setup.m_difficulty=4;g_game->m_day=1;g_game->m_week=1;g_game->m_month=1;
   int completed=0;
   while(!c.campaignComplete()){
    h.getAvailableScenarios(available.data());int next=-1;
    for(int i=0;i<h.getScenarioCount();++i)if(available[i] && !c.m_mapScores[i].m_completed){next=i;break;}
    assert(next>=0);c.m_currentMap=next;c.completeCurrentMap(&h);assert(c.m_mapScores[next].m_completed);++completed;
    int order=c.m_mapScores[next].m_completeOrder;c.completeCurrentMap(&h);assert(c.m_mapScores[next].m_completeOrder==order);
    std::stringbuf buffer(std::ios::in|std::ios::out|std::ios::binary);StreamFile saved(&buffer);c.save(&saved);buffer.pubseekpos(0,std::ios::in);
    hero* before=c.findCrossoverHero(6);bool retained=before!=nullptr;int experience=retained?before->m_experience:0;
    SCampaign restored;restored.load(&saved,36);
    if(retained){auto* after=restored.findCrossoverHero(6);assert(after && after->m_experience==experience);}
    if(id==0 && next==0)assert(retained && experience==12000);assert(restored.m_currentCampaign==id && restored.m_currentMap==next && restored.m_mapScores[next].m_completed);
    assert(restored.m_mapScores.size()==c.m_mapScores.size());c=restored;
   }
   assert(completed==count && c.m_campaignCompleted[id]);
   maps+=count;printf("%s: %d maps, %d starting branches\n",files[id],count,starts);fflush(stdout);
  }
  printf("{\"passed\":true,\"campaigns\":20,\"scenarioHeaders\":%d}\n",maps);return 0;
 }catch(const std::exception& e){fprintf(stderr,"%s\n",e.what());return 1;}
}
