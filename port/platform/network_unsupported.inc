// Unsupported legacy modem/IPX/lobby operations fail explicitly.
unsigned char CDPlay::initConnection(CDPlayConnection* connection) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::hostSession(char* sessionName, unsigned long flags,
                                  unsigned long maxPlayers, char* password) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::joinSession(GUID* sessionGuid, char* password) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned long CDPlay::createPlayer(char* playerName, void* data, unsigned long size, void* event) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::destroyPlayer(unsigned long playerId) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned long CDPlay::createGroup(char* groupName, void* groupData, unsigned long groupDataSize, unsigned char stagingArea) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned long CDPlay::createGroupInGroup(unsigned long dpidParent, char* groupName, void* groupData, unsigned long dataSize, unsigned char stagingArea) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::destroyGroup(unsigned long groupId) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::deleteGroupFromGroup(unsigned long dpidParent, unsigned long dpidGroup) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::enumConnections(CAutoArray<CDPlayConnection>* connectionArray) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::startSession(unsigned long groupId) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::enumGroups(CAutoArray<CDPlayGroup>* groupArray, GUID* guidInstance, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::enumGroupPlayers(CAutoArray<CDPlayPlayer>* playerArray, unsigned long dpidGroup, GUID* guidInstance, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::enumSessions(CAutoArray<CDPlaySession>* sessionArray, unsigned long timeOut, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::sendChat(char* msg, unsigned long idFrom, unsigned long idTo) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::addSessionEnum(const DPSESSIONDESC2* dpSessionDesc, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::receiveSystemMsg(unsigned long toID, CDPlayMsg* msg) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::addGroupEnum(unsigned long dpid, const DPNAME* name, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::addPlayerEnum(unsigned long dpid, const DPNAME* name, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::addConnectionEnum(const GUID* lpguidSP, void* connection, unsigned long connectionSize, const DPNAME* name, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::addPlayerToGroup(unsigned long groupId, unsigned long playerId) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::deletePlayerFromGroup(unsigned long groupId, unsigned long playerId) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::setPlayerName(unsigned long playerId, char* shortName, char* longName, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::setGroupData(unsigned long groupId, void* data, unsigned long dataSize, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
void* CDPlay::getGroupData(unsigned long groupId, unsigned long* pdwSize, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::setGroupName(unsigned long groupId, char* shortName, char* longName, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::getGroupName(unsigned long groupId, char* shortName, int maxShort, char* longName, int maxLong) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::setPlayerData(unsigned long playerId, void* data, unsigned long dataSize, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char* CDPlay::getPlayerAddress(unsigned long dpid, unsigned long* sizeOut) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlay::getCaps(DPCAPS* dpCaps, unsigned char guaranteed) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::registerApp(char* appName, char* fileName, char* commandLine, GUID appGuid, char* executableName) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
DPLCONNECTION* CDPlayLobby::getConnectionSettings(unsigned long appId, unsigned long* sizeOut) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
bool CDPlayLobby::testLobbied() { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::setConnectionSettings(unsigned long appId, DPLCONNECTION* connection) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::setGroupConnectionSettings(unsigned long dpidGroup, DPLCONNECTION* connection) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
DPLCONNECTION* CDPlayLobby::getGroupConnectionSettings(unsigned long dpidGroup) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::connect() { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::sendStandardLobbyMsg(
    unsigned long appId, void* data, unsigned long size) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::sendLobbyMsg(
    unsigned long appId, void* data, unsigned long size) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::receiveLobbyMsg(unsigned long appId, CDPlayMsg* msg) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
CDPlayConnection* CDPlayLobby::createTCPIPConnection(
    char* ipAddress, char* name, CDPlayConnection* append) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
CDPlayConnection* CDPlayLobby::createIPXConnection(char* name, CDPlayConnection* connAppend) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
CDPlayConnection* CDPlayLobby::createModemConnection(char* name, char* phoneNbr, char* modemString) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
CDPlayConnection* CDPlayLobby::createSerialConnection(char* name, _DPCOMPORTADDRESS* comPortInfo) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::handleSystemLobbyMsg(unsigned long appId, CDPlayMsg* msg) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::enumLobbyConnections(CAutoArray<CDPlayConnection>* connectionArray) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::enumGroupsInGroup(CAutoArray<CDPlayGroup>* groupArray, unsigned long dpidParent, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::enumGroupPlayers(CAutoArray<CDPlayPlayer>* playerArray, unsigned long dpidGroup, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::enumGroupPlayersRemote(CAutoArray<CDPlayPlayer>* playerArray, unsigned long dpidGroup, GUID* guidInstance, unsigned long flags) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::enumAddress(void* conn, unsigned long size, CAutoArray<CDPlayAddressElement>* array) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::addAddressEnum(const GUID* guid, unsigned long dataSize, const void* data) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
unsigned char CDPlayLobby::getIPAddress(unsigned long dpid, char* ipAddress) { m_res = DPLAY_SEND_ERROR_INVALID_PARAMETER; return 0; }
