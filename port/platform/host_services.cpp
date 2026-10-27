// Win32 file metadata and directory enumeration mapped onto the host/MEMFS.
#include "windows.h"
#include "io.h"
#include "host_path.h"
#include <dirent.h>
#include <fnmatch.h>
#include <sys/statvfs.h>
#include <vector>
#include <algorithm>
#include <string>
#include <cstdio>
#include <ctime>
#include <cerrno>
#include <limits>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace Port {
void notifySave(const char* path){
#ifdef __EMSCRIPTEN__
    EM_ASM({window.dispatchEvent(new CustomEvent('homm3-save',{detail:UTF8ToString($0)}));},path);
#else
    (void)path;
#endif
}

std::string hostPath(const char* path){
    std::string s=path?path:".";
    std::replace(s.begin(),s.end(),'\\','/');
    // Original Windows paths use mixed case. Resolve existing components while
    // preserving a new filename's spelling (saves), on case-sensitive MEMFS too.
    std::string resolved;
    size_t start=0;
    while(start<s.size()){
        auto end=s.find('/',start);if(end==std::string::npos)end=s.size();
        std::string part=s.substr(start,end-start);
        std::string parent=resolved.empty()?".":resolved;
        if(!part.empty() && part!="." && part!=".."){
            if(DIR* d=opendir(parent.c_str())){
                while(auto* e=readdir(d)){if(!strcasecmp(e->d_name,part.c_str())){part=e->d_name;break;}}
                closedir(d);
            }
        }
        resolved+=part;if(end<s.size())resolved+='/';start=end+1;
    }
    return resolved;
}
}
namespace {
struct Search {std::vector<std::string> names;size_t index=0;};
void filetime(time_t seconds,FILETIME* out){
    if(!out)return;
    uint64_t value=(uint64_t(seconds)+11644473600ull)*10000000ull;
    out->dwLowDateTime=uint32_t(value);out->dwHighDateTime=uint32_t(value>>32);
}
int found(Search* search,_finddata_t* out){
    if(!search || search->index>=search->names.size())return -1;
    const auto& path=search->names[search->index++];struct stat s{};
    if(stat(path.c_str(),&s))return -1;
    *out={};out->attrib=S_ISDIR(s.st_mode)?0x10:0x20;
    out->time_create=s.st_ctime;out->time_access=s.st_atime;out->time_write=s.st_mtime;out->size=uint32_t(s.st_size);
    auto name=path.substr(path.find_last_of('/')+1);std::snprintf(out->name,sizeof(out->name),"%s",name.c_str());return 0;
}
}
long _findfirst(const char* pattern,_finddata_t* out){
    std::string path=Port::hostPath(pattern);auto sep=path.find_last_of('/');
    std::string dir=sep==std::string::npos?".":path.substr(0,sep),mask=path.substr(sep+1);
    DIR* d=opendir(dir.c_str());if(!d)return -1;
    auto* search=new Search;
    for(dirent* e; (e=readdir(d));){
        if(fnmatch(mask.c_str(),e->d_name,FNM_CASEFOLD)==0)search->names.push_back(dir+"/"+e->d_name);
    }
    closedir(d);std::sort(search->names.begin(),search->names.end());
    if(found(search,out)){delete search;return -1;}return reinterpret_cast<intptr_t>(search);
}
int _findnext(long handle,_finddata_t* out){return found(reinterpret_cast<Search*>(intptr_t(handle)),out);}
int _findclose(long handle){delete reinterpret_cast<Search*>(intptr_t(handle));return 0;}
extern "C" HANDLE CreateFileA(const char* path,DWORD access,DWORD,void*,DWORD creation,DWORD,HANDLE){
    auto name=Port::hostPath(path);
    const char* mode=(access&GENERIC_WRITE)?(creation==OPEN_EXISTING?"r+b":"w+b"):"rb";
    if(creation==CREATE_NEW && ::access(name.c_str(),F_OK)==0)return INVALID_HANDLE_VALUE;
    FILE* f=fopen(name.c_str(),mode);return f?f:INVALID_HANDLE_VALUE;
}
extern "C" BOOL CloseHandle(HANDLE h){return h && h!=INVALID_HANDLE_VALUE && fclose(static_cast<FILE*>(h))==0;}
extern "C" BOOL WriteFile(HANDLE h,const void* data,DWORD n,DWORD* written,void*){
    if(!h || h==INVALID_HANDLE_VALUE || !written)return FALSE;
    *written=uint32_t(fwrite(data,1,n,static_cast<FILE*>(h)));return !ferror(static_cast<FILE*>(h));
}
extern "C" BOOL GetFileTime(HANDLE h,FILETIME* created,FILETIME* accessed,FILETIME* modified){
    struct stat s{};if(!h || h==INVALID_HANDLE_VALUE || fstat(fileno(static_cast<FILE*>(h)),&s))return FALSE;
    filetime(s.st_ctime,created);filetime(s.st_atime,accessed);filetime(s.st_mtime,modified);return TRUE;
}
extern "C" BOOL FileTimeToLocalFileTime(const FILETIME* in,FILETIME* out){*out=*in;return TRUE;}
extern "C" BOOL FileTimeToSystemTime(const FILETIME* in,SYSTEMTIME* out){
    uint64_t value=(uint64_t(in->dwHighDateTime)<<32)|in->dwLowDateTime;
    time_t seconds=time_t(value/10000000ull)-11644473600ll;tm t{};
    if(!localtime_r(&seconds,&t))return FALSE;
    *out={WORD(t.tm_year+1900),WORD(t.tm_mon+1),WORD(t.tm_wday),WORD(t.tm_mday),WORD(t.tm_hour),WORD(t.tm_min),WORD(t.tm_sec),WORD((value/10000)%1000)};return TRUE;
}
extern "C" BOOL GetDiskFreeSpaceA(const char* path,DWORD* sectors,DWORD* bytes,DWORD* free,DWORD* total){
    struct statvfs s{};if(statvfs(Port::hostPath(path).c_str(),&s))return FALSE;
    *sectors=1;*bytes=uint32_t(s.f_frsize);*free=uint32_t(std::min<uint64_t>(s.f_bavail,UINT32_MAX/(*bytes?*bytes:1)));*total=*free;return TRUE;
}
extern "C" BOOL IntersectRect(RECT* out,const RECT* a,const RECT* b){
    *out={std::max(a->left,b->left),std::max(a->top,b->top),std::min(a->right,b->right),std::min(a->bottom,b->bottom)};
    if(out->left>=out->right || out->top>=out->bottom){*out={};return FALSE;}return TRUE;
}
// No Windows registry or PE version resources exist in this client. The original
// readPrefs path uses its own defaults when a key is absent.
#ifndef HOMM3_FULL_GAME
extern "C" LONG RegOpenKeyExA(HKEY,const char*,DWORD,DWORD,HKEY*){return 2;}
extern "C" LONG RegCreateKeyA(HKEY,const char*,HKEY*){return 2;}
extern "C" LONG RegCloseKey(HKEY){return 0;}
extern "C" LONG RegQueryValueExA(HKEY,const char*,DWORD*,DWORD*,BYTE*,DWORD*){return 2;}
extern "C" LONG RegSetValueExA(HKEY,const char*,DWORD,DWORD,const BYTE*,DWORD){return 2;}
#endif
extern "C" DWORD GetModuleFileNameA(HMODULE,char* out,DWORD size){const char* name="homm3-port";if(size<=strlen(name))return 0;strcpy(out,name);return DWORD(strlen(name));}
extern "C" DWORD GetFileVersionInfoSizeA(const char*,DWORD*){return 0;}
extern "C" BOOL GetFileVersionInfoA(const char*,DWORD,DWORD,void*){return FALSE;}
extern "C" BOOL VerQueryValueA(const void*,const char*,void**,UINT*){return FALSE;}
