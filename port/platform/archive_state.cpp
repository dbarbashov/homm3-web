// Archive state normally owned by the Windows Smacker/Miles boundary.
// Counts stay zero until a platform audio archive is opened.
#include "smackmgr.h"
SoundHeaderStruct* g_soundHeader=nullptr;
SoundHeaderStruct* g_soundHeaderCd=nullptr;
SoundHeaderStruct* g_soundHeaderCampaign=nullptr;
int g_soundCount=0,g_soundCountCd=0,g_soundCountCampaign=0;
void* g_soundFile=nullptr;
void* g_soundFileCd=nullptr;
void* g_soundFileCampaign=nullptr;
