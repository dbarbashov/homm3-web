// Host filesystem boundary. Original resource loading remains in ResourceManager/LODFile.
#include "windows.h"
#include "host_path.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <unistd.h>
#include <chrono>
#include <thread>
#include <mutex>

extern "C" char* _fullpath(char* dst,const char* path,size_t capacity) {
    if (!dst || !path || !capacity) return nullptr;
    std::string result(path);
    if (result.empty() || result[0]!='/') { char cwd[4096]; if (!getcwd(cwd,sizeof(cwd))) return nullptr; result=std::string(cwd)+"/"+result; }
    if (result.size()>=capacity) return nullptr;
    std::memcpy(dst,result.c_str(),result.size()+1);return dst;
}
extern "C" DWORD GetTickCount() {
    using namespace std::chrono;
    static auto epoch=steady_clock::now();
    return static_cast<DWORD>(duration_cast<milliseconds>(steady_clock::now()-epoch).count());
}
extern "C" HWND GetForegroundWindow() {return nullptr;}
extern "C" int MessageBoxA(HWND,const char* message,const char* title,UINT) {
    std::fprintf(stderr,"%s: %s\n",title?title:"Heroes III",message?message:"");return 1;
}
extern "C" DWORD SetFilePointer(HANDLE handle,LONG offset,LONG* high,DWORD origin) {
    auto* file=static_cast<FILE*>(handle);
    if (!file || (high && *high) || fseek(file,offset,origin)) return 0xffffffff;
    return static_cast<DWORD>(ftell(file));
}
extern "C" BOOL ReadFile(HANDLE handle,void* data,DWORD size,DWORD* bytes,void*) {
    if (!handle || !bytes) return FALSE;
    *bytes=static_cast<DWORD>(fread(data,1,size,static_cast<FILE*>(handle)));
    return !ferror(static_cast<FILE*>(handle));
}
extern "C" DWORD GetFileAttributesA(const char* path) {struct stat s;return stat(Port::hostPath(path).c_str(),&s)?0xffffffff:S_ISDIR(s.st_mode)?0x10:0x80;}
extern "C" BOOL DeleteFileA(const char* path) {return unlink(Port::hostPath(path).c_str())==0;}
extern "C" BOOL CreateDirectoryA(const char* path,void*) {return mkdir(Port::hostPath(path).c_str(),0700)==0;}
extern "C" void Sleep(DWORD ms) {std::this_thread::sleep_for(std::chrono::milliseconds(ms));}
extern "C" void InitializeCriticalSection(CRITICAL_SECTION* s) {s->portableMutex=new std::recursive_mutex;}
extern "C" void DeleteCriticalSection(CRITICAL_SECTION* s) {delete static_cast<std::recursive_mutex*>(s->portableMutex);}
extern "C" void EnterCriticalSection(CRITICAL_SECTION* s) {static_cast<std::recursive_mutex*>(s->portableMutex)->lock();}
extern "C" void LeaveCriticalSection(CRITICAL_SECTION* s) {static_cast<std::recursive_mutex*>(s->portableMutex)->unlock();}

#ifndef HOMM3_FULL_GAME
unsigned long getAvailableDiskSpace(){
    struct statvfs s{};
    if(statvfs(".",&s))return 0;
    const uint64_t bytes=uint64_t(s.f_bavail)*s.f_frsize;
    return static_cast<unsigned long>(std::min<uint64_t>(bytes,0xffffffffu));
}

#endif
