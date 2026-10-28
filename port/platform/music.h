#pragma once
namespace Port { namespace Music {
void play(const char* name,int loops,float volume);
void stop();
void resume();
void volume(float value);
bool playing();
void close();
}}
