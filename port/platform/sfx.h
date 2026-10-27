#pragma once
#include <cstddef>
namespace Port { namespace Sfx {
constexpr int slots=13;
bool open();
void close();
bool play(int slot,const char* name,const void* wave,size_t size,int loops,int volume);
void stop(int slot);
void pause(int slot);
void resume(int slot);
void restart(int slot);
bool playing(int slot);
void volume(int slot,int value);
unsigned generation(int slot);
size_t decodedBytes();
#ifndef __EMSCRIPTEN__
void setMusicMixer(void (*callback)(float*,int));
void lockAudio();
void unlockAudio();
#endif
}}
