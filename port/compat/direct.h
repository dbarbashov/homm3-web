#pragma once
#include <unistd.h>
#include <sys/stat.h>
inline int _mkdir(const char* path){return mkdir(path,0700);}
inline int _chdir(const char* path){return chdir(path);}
inline char* _getcwd(char* buffer,int size){return getcwd(buffer,size);}
