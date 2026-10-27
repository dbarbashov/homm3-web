#pragma once
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <strings.h>
#include <algorithm>
#include <limits>
#ifndef _WIN32
#define __cdecl
#define __stdcall
#define __fastcall
#define __thiscall
#define __forceinline inline
#define __int64 long long
#define stricmp strcasecmp
#define strcmpi strcasecmp
#define strnicmp strncasecmp
#define _stricmp strcasecmp
#define _strnicmp strncasecmp
#endif
inline char* strrev(char* s){std::reverse(s,s+std::strlen(s));return s;}
#include <cctype>
inline char* strupr(char* s){for(char* p=s;*p;++p)*p=static_cast<char>(std::toupper(static_cast<unsigned char>(*p)));return s;}
