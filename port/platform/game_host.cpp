// Window/menu services are SDL-owned; there is no separate Win32 menu bar.
#include "sdl_backend.h"
#include "kbwin.h"
#include "mousemgr.h"
#include "wingraph.h"
#include <SDL.h>
#include <stdexcept>
HMENU g_activeMenu=nullptr,g_currMenu=nullptr,g_dfltMenu=nullptr,g_gameMenu=nullptr;
HINSTANCE g_instance=nullptr;
HANDLE g_gameEvent=nullptr;
int g_remoteOn=0,g_closingApp=0;
unsigned char g_shutDownDone=0;
void kbChangeMenu(HMENU menu){g_currMenu=menu;}
unsigned char setFullScreenStatus(int enabled){return Port::setFullscreen(enabled!=0); }
void appExit(){throw std::runtime_error("Original game requested shutdown");}
extern "C" UINT timeEndPeriod(UINT){return 0;}
extern "C" HMENU LoadMenuA(HINSTANCE,const char*){return nullptr;}
extern "C" DWORD CheckMenuItem(HMENU,UINT,UINT){return 0;}
extern "C" BOOL IsIconic(HWND){return FALSE;}
extern "C" BOOL SetForegroundWindow(HWND){return TRUE;}
extern "C" BOOL ShowWindow(HWND,int){return TRUE;}
int g_inSetupDialog=0;
int g_mpExtendedType=10,g_waitForRemoteReceive=0;
