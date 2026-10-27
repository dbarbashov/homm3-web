#pragma once
// Portable declarations for the Win32 boundary. Implementations live in the
// platform backend; these declarations do not replace game algorithms.
#include <cstdint>
#include <cstddef>
#include <cstring>
using BOOL=int; using BYTE=uint8_t; using WORD=uint16_t; using DWORD=uint32_t;
using LONG=int32_t; using ULONG=uint32_t; using UINT=unsigned; using INT=int;
using SHORT=int16_t; using USHORT=uint16_t; using CHAR=char; using WCHAR=wchar_t;
using HRESULT=int32_t; using LPVOID=void*; using LPCVOID=const void*;
using HANDLE=void*; using HWND=void*; using HINSTANCE=void*; using HDC=void*;
using HICON=void*; using HCURSOR=void*; using HBITMAP=void*; using HBRUSH=void*;
using HMODULE=void*; using HPALETTE=void*; struct HMENU__; using HMENU=HMENU__*; using HGDIOBJ=void*;
using LPSTR=char*; using LPCSTR=const char*; using LPWSTR=wchar_t*;
using LPBYTE=BYTE*; using LPDWORD=DWORD*; using LPWORD=WORD*;
using WPARAM=uintptr_t; using LPARAM=intptr_t; using LRESULT=intptr_t;
using COLORREF=uint32_t; using ATOM=uint16_t; using INT_PTR=intptr_t;
struct tagPOINT { LONG x,y; }; using POINT=tagPOINT; using LPPOINT=POINT*;
struct tagRECT { LONG left,top,right,bottom; }; using RECT=tagRECT; using LPRECT=RECT*;
struct SIZE { LONG cx,cy; };
struct tagRGBQUAD { BYTE rgbBlue,rgbGreen,rgbRed,rgbReserved; }; using RGBQUAD=tagRGBQUAD;
struct PALETTEENTRY { BYTE peRed,peGreen,peBlue,peFlags; };
struct BITMAPINFOHEADER { DWORD biSize; LONG biWidth,biHeight; WORD biPlanes,biBitCount; DWORD biCompression,biSizeImage; LONG biXPelsPerMeter,biYPelsPerMeter; DWORD biClrUsed,biClrImportant; };
struct FILETIME { DWORD dwLowDateTime,dwHighDateTime; };
struct SYSTEMTIME { WORD wYear,wMonth,wDayOfWeek,wDay,wHour,wMinute,wSecond,wMilliseconds; };
struct GUID { uint32_t Data1; uint16_t Data2,Data3; uint8_t Data4[8]; };
using IID=GUID; using REFGUID=const GUID&; using REFIID=const IID&;
struct CRITICAL_SECTION { void* portableMutex; };
union LARGE_INTEGER { struct { DWORD LowPart; LONG HighPart; }; int64_t QuadPart; };
#define WINAPI
#define CALLBACK
#define APIENTRY
#define FAR
#define NEAR
#define TRUE 1
#define FALSE 0
#define MAX_PATH 260
#define _MAX_PATH 260
#define FILE_BEGIN 0
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define RGB(r,g,b) ((COLORREF)((BYTE)(r)|((WORD)(BYTE)(g)<<8)|((DWORD)(BYTE)(b)<<16)))
#define ZeroMemory(p,n) std::memset(p,0,n)
#define MB_OK 0
#define MB_ICONHAND 16
#define MB_ICONERROR 16
#define MB_ICONEXCLAMATION 48
#define S_OK 0
#define E_FAIL ((HRESULT)0x80004005)
extern "C" {
DWORD GetTickCount();
HWND GetForegroundWindow();
char* _fullpath(char*,const char*,size_t);
DWORD SetFilePointer(HANDLE,LONG,LONG*,DWORD);
BOOL ReadFile(HANDLE,void*,DWORD,DWORD*,void*);
int MessageBoxA(HWND,const char*,const char*,UINT);
DWORD GetFileAttributesA(const char*);
BOOL DeleteFileA(const char*);
BOOL CreateDirectoryA(const char*,void*);
void Sleep(DWORD);
void InitializeCriticalSection(CRITICAL_SECTION*);
void DeleteCriticalSection(CRITICAL_SECTION*);
void EnterCriticalSection(CRITICAL_SECTION*);
void LeaveCriticalSection(CRITICAL_SECTION*);
}
#define WM_KEYDOWN 0x0100
#define WM_KEYUP 0x0101
#define WM_COMMAND 0x0111
#define WM_MOUSEMOVE 0x0200
#define WM_LBUTTONDOWN 0x0201
#define WM_LBUTTONUP 0x0202
#define WM_LBUTTONDBLCLK 0x0203
#define WM_RBUTTONDOWN 0x0204
#define WM_RBUTTONUP 0x0205
#define WM_RBUTTONDBLCLK 0x0206
#define VK_SHIFT 0x10
#define VK_CONTROL 0x11
#define VK_MENU 0x12
#define HIWORD(v) ((WORD)((uintptr_t)(v)>>16))
extern "C" HWND SetCapture(HWND);
extern "C" BOOL ReleaseCapture();
extern "C" SHORT GetKeyState(int);
using _FILETIME=FILETIME; using _SYSTEMTIME=SYSTEMTIME;
#define GENERIC_READ 0x80000000u
#define GENERIC_WRITE 0x40000000u
#define FILE_SHARE_READ 1
#define OPEN_EXISTING 3
#define CREATE_ALWAYS 2
#define FILE_ATTRIBUTE_NORMAL 0x80
#define FILE_FLAG_SEQUENTIAL_SCAN 0x08000000
#define WAIT_TIMEOUT 258
#define INFINITE 0xffffffffu
extern "C" {
BOOL IntersectRect(RECT*,const RECT*,const RECT*);
HANDLE CreateFileA(const char*,DWORD,DWORD,void*,DWORD,DWORD,HANDLE);
BOOL CloseHandle(HANDLE);
BOOL GetFileTime(HANDLE,FILETIME*,FILETIME*,FILETIME*);
BOOL FileTimeToLocalFileTime(const FILETIME*,FILETIME*);
BOOL FileTimeToSystemTime(const FILETIME*,SYSTEMTIME*);
DWORD GetModuleFileNameA(HMODULE,char*,DWORD);
HANDLE CreateEvent(void*,BOOL,BOOL,const char*);
DWORD WaitForSingleObject(HANDLE,DWORD);
BOOL SetEvent(HANDLE);
}
#define FILE_END 2
#define FILE_CURRENT 1
#define CREATE_NEW 1
#define FILE_FLAG_RANDOM_ACCESS 0x10000000
#define MAKEINTRESOURCE(v) ((const char*)(uintptr_t)(uint16_t)(v))
#define PtrToLong(v) ((LONG)(intptr_t)(v))
#define SW_RESTORE 9
#define SW_SHOWNORMAL 1
#define ERROR_SUCCESS 0
#define KEY_READ 0x20019
#define KEY_ALL_ACCESS 0xf003f
#define REG_SZ 1
#define REG_DWORD 4
using HKEY=void*;
#define HKEY_LOCAL_MACHINE ((HKEY)(uintptr_t)0x80000002u)
struct WIN32_FIND_DATAA { DWORD dwFileAttributes; FILETIME ftCreationTime,ftLastAccessTime,ftLastWriteTime; DWORD nFileSizeHigh,nFileSizeLow,dwReserved0,dwReserved1; char cFileName[260],cAlternateFileName[14]; };
extern "C" {
unsigned long timeGetTime();
HMENU LoadMenuA(HINSTANCE,const char*);
BOOL IsIconic(HWND);
BOOL ShowWindow(HWND,int);
BOOL SetForegroundWindow(HWND);
DWORD CheckMenuItem(HMENU,UINT,UINT);
BOOL MessageBeep(UINT);
BOOL WriteFile(HANDLE,const void*,DWORD,DWORD*,void*);
LONG RegOpenKeyExA(HKEY,const char*,DWORD,DWORD,HKEY*);
LONG RegCreateKeyExA(HKEY,const char*,DWORD,char*,DWORD,DWORD,void*,HKEY*,DWORD*);
LONG RegCloseKey(HKEY);
LONG RegQueryValueExA(HKEY,const char*,DWORD*,DWORD*,BYTE*,DWORD*);
LONG RegSetValueExA(HKEY,const char*,DWORD,DWORD,const BYTE*,DWORD);
DWORD GetFileVersionInfoSizeA(const char*,DWORD*);
BOOL GetFileVersionInfoA(const char*,DWORD,DWORD,void*);
BOOL VerQueryValueA(const void*,const char*,void**,UINT*);
}
#define RegOpenKeyEx RegOpenKeyExA
extern "C" {
LONG RegCreateKeyA(HKEY,const char*,HKEY*);
BOOL GetDiskFreeSpaceA(const char*,DWORD*,DWORD*,DWORD*,DWORD*);
}
#define LOWORD(v) ((WORD)((uintptr_t)(v)&0xffff))
#define LoadMenu LoadMenuA
#define MessageBox MessageBoxA
#define WM_CLOSE 0x0010
#define MF_CHECKED 8
#define MF_UNCHECKED 0
extern "C" {
UINT timeEndPeriod(UINT);
LRESULT SendMessageA(HWND,UINT,WPARAM,LPARAM);
BOOL SetMenu(HWND,HMENU);
BOOL DestroyMenu(HMENU);
}
#define SendMessage SendMessageA
extern "C" BOOL PostMessageA(HWND,UINT,WPARAM,LPARAM);
