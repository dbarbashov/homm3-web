// DirectPlay transport boundary. Original CNetMsg serialization and handlers remain C++.
#include "remote.h"
#include "netgame.h"
#include "netmsg.h"
#include "singleselectionwindow.h"
#include <vector>
#include <cstdint>
#include <cstdio>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace {
struct NetPlayer {char name[21];uint32_t id;};
std::vector<NetPlayer> netPlayers;
uint32_t netSelf=0,netHost=0;
DPSESSIONDESC2 netSession{};
}
#include "network_methods.inc"
#include "network_unsupported.inc"
bool portableNetworkStart(){
#ifdef __EMSCRIPTEN__
    netSelf=EM_ASM_INT({return window.homm3Network.self;});
    netHost=EM_ASM_INT({return window.homm3Network.host;});
    int count=EM_ASM_INT({return window.homm3Network.players.length;});
    if(!netSelf || count<2 || count>8)return false;
    netPlayers.resize(count);
    for(int i=0;i<count;++i){
        netPlayers[i].id=i+1;
        EM_ASM({const p=window.homm3Network.players[$0];const codes=Array.from(p.name).slice(0,20).map(c=>{const n=c.charCodeAt(0);return n<128?n:n>=0x410&&n<=0x44f?n-0x410+0xc0:n===0x401?0xa8:n===0x451?0xb8:63;});HEAPU8.set(codes,$1);HEAPU8[$1+codes.length]=0;},i,netPlayers[i].name);
    }
    netSession={};netSession.m_size=sizeof(netSession);netSession.m_maxPlayers=count;netSession.m_currentPlayers=count;
    g_dPlay=new CDPlayHeroes;g_dPlay->init();g_dPlay->setGuid(guidHeroes3);
    g_thisNetPlayerInfo.m_dpid=netSelf;g_thisNetPlayerInfo.m_version=g_videoGameState;
    snprintf(g_thisNetPlayerInfo.m_name,sizeof(g_thisNetPlayerInfo.m_name),"%s",netPlayers[netSelf-1].name);
    g_mpNetProtocol=MP_TCP;g_remoteOn=1;g_numHumanPlayers=count;
    printf("WebSocket network: self=%u host=%u players=%d\n",netSelf,netHost,count);
    return true;
#else
    return false;
#endif
}
