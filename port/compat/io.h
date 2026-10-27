#pragma once
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <cstdint>
#include <ctime>
#ifndef O_BINARY
#define O_BINARY 0
#endif
#ifndef S_IREAD
#define S_IREAD S_IRUSR
#define S_IWRITE S_IWUSR
#endif
struct _finddata_t {
    unsigned attrib;
    time_t time_create, time_access, time_write;
    uint32_t size;
    char name[260];
};
long _findfirst(const char*, _finddata_t*);
int _findnext(long, _finddata_t*);
int _findclose(long);
#define _O_BINARY O_BINARY
#define _O_CREAT O_CREAT
#define _O_TRUNC O_TRUNC
#define _O_WRONLY O_WRONLY
#define _S_IWRITE S_IWUSR
