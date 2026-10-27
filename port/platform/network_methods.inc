CDPlay::CDPlay() : m_dp(nullptr),m_guid{},m_res(0),m_sessionArray(nullptr),m_connectionArray(nullptr),m_groupArray(nullptr),m_playerArray(nullptr),m_connected(0),m_inSession(0),m_isHost(false),m_tailPadding(0) { memset(m_caps,0,sizeof(m_caps)); }
CDPlay::~CDPlay() {}
CDPlayLobby::CDPlayLobby() : m_lobby(nullptr),m_addressArray(nullptr) {}
CDPlayLobby::~CDPlayLobby() {}
unsigned char CDPlay::init() { m_connected=1;m_inSession=1;m_isHost=netSelf==netHost;return 1; }
unsigned char CDPlayLobby::init() { return CDPlay::init(); }
unsigned char CDPlay::closeSession() { m_inSession=0;return 1; }
unsigned char CDPlay::enumPlayers(CAutoArray<CDPlayPlayer>* players, GUID*, unsigned long) {
    players->destroy(1);for(auto& p:netPlayers)players->add(new CDPlayPlayer(p.name,p.id));return 1;
}
void* CDPlay::getPlayerData(unsigned long id,unsigned long* size,unsigned long) {
    for(auto& p:netPlayers)if(p.id==id){if(size)*size=sizeof(int);return new int(g_videoGameState);}return nullptr;
}
unsigned char CDPlay::getPlayerName(unsigned long id,char* shortName,int maxShort,char* longName,int maxLong) {
    for(auto& p:netPlayers)if(p.id==id){if(shortName && maxShort>0)snprintf(shortName,maxShort,"%s",p.name);if(longName && maxLong>0)snprintf(longName,maxLong,"%s",p.name);return 1;}return 0;
}
DPSESSIONDESC2* CDPlay::getCurrSession() { return new DPSESSIONDESC2(netSession); }
unsigned char CDPlay::updateSessionDesc(DPSESSIONDESC2* desc) { if(!desc)return 0;netSession=*desc;return 1; }
unsigned char CDPlay::send(void* data,unsigned long size,unsigned long from,unsigned long to,unsigned char) {
#ifdef __EMSCRIPTEN__
    if(from!=netSelf || size<sizeof(CNetMsg) || size>4*1024*1024){m_res=DPLAY_SEND_ERROR_INVALID_PARAMETER;return 0;}
    bool ok=EM_ASM_INT({return window.homm3Network.send($0,HEAPU8.subarray($1,$1+$2))?1:0;},to,data,size);
    m_res=ok?0:DPLAY_SEND_ERROR_INVALID_PARAMETER;return ok;
#else
    m_res=DPLAY_SEND_ERROR_INVALID_PARAMETER;return 0;
#endif
}
unsigned char CDPlay::receive(unsigned long* from,unsigned long* to,CDPlayMsg* msg,unsigned long) {
    m_res=DPLAY_RECEIVE_ERROR_NO_MESSAGES;
#ifdef __EMSCRIPTEN__
    const int size=EM_ASM_INT({return window.homm3Network.peek();});
    if(!size)return 0;
    std::vector<unsigned char> packet(size);
    EM_ASM({HEAPU8.set(window.homm3Network.pop(),$0);},packet.data());
    if(size<8+int(sizeof(CNetMsg)) || size>4*1024*1024)return 0;
    uint32_t src=0,dest=0;memcpy(&src,packet.data(),4);memcpy(&dest,packet.data()+4,4);
    CNetMsg header(RS_CHAT_MSG,0);memcpy(&header,packet.data()+8,sizeof(header));
    if(src<1 || src>netPlayers.size() || (dest!=0 && dest!=netSelf) || header.m_size!=size-8 || header.m_uncompressedSize>32*1024*1024)return 0;
    // Sender identity comes from the authenticated relay, not from peer bytes.
    header.m_dpidFrom=src;
    if(header.m_from < -1 || header.m_from > 7)return 0;
    if(msg->m_dataSize<header.m_size){delete[] msg->m_data;msg->m_data=new unsigned char[header.m_size];msg->m_dataSize=header.m_size;}
    memcpy(msg->m_data,packet.data()+8,header.m_size);memcpy(msg->m_data,&header,sizeof(header));
    *from=src;*to=dest;m_res=0;return 1;
#else
    return 0;
#endif
}
void CDPlay::getErrorDesc(long,char* out) { strcpy(out,"WebSocket transport disconnected or invalid message"); }
unsigned char CDPlay::getSendQueueSize(unsigned long,unsigned long,unsigned long* msgs,unsigned long* bytes) {
    if(msgs)*msgs=0;if(bytes)*bytes=0;return 1;
}
unsigned char CDPlay::getReceiveQueueSize(unsigned long,unsigned long,unsigned long* msgs,unsigned long* bytes) {
    if(msgs)*msgs=0;if(bytes)*bytes=0;return 1;
}
unsigned char CDPlay::flushReceiveQueue() { return 1; }
unsigned char CDPlay::sysMsgHost(DPMSG_GENERIC*,unsigned long) {m_isHost=netSelf==netHost;return 1;}
unsigned char CDPlay::sysMsgCreatePlayerOrGroup(DPMSG_CREATEPLAYERORGROUP*,unsigned long){return 1;}
unsigned char CDPlay::sysMsgDestroyPlayerOrGroup(DPMSG_DESTROYPLAYERORGROUP*,unsigned long){return 1;}
