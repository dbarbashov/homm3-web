// Front-end platform media state. No video stream is opened by this bootstrap.
// The original Bink/Smacker/Miles playback backends remain a separate port task.
#include "soundmgr.h"
#include "sample.h"
#include <SDL.h>
#include <stdexcept>
struct ds_memsample { SDL_AudioDeviceID device; };
bool videoPlaying(){return false;}
void videoDrawCurrentFrame(){}
void pollSound(){} // SDL queued audio progresses independently of the game pump.
ds_memsample* soundManager::memorySample(sample* value){
    if(!value || !value->memSample.m_data)return nullptr;
    SDL_AudioSpec spec;Uint8* data=nullptr;Uint32 size=0;
    auto* source=SDL_RWFromConstMem(value->memSample.m_data,value->memSample.m_size);
    if(!SDL_LoadWAV_RW(source,1,&spec,&data,&size))throw std::runtime_error(SDL_GetError());
    // One click channel; close the previous handle before starting another.
    static ds_memsample handle{};
    if(handle.device)SDL_CloseAudioDevice(handle.device);
    handle.device=SDL_OpenAudioDevice(nullptr,0,&spec,nullptr,0);
    if(!handle.device){SDL_FreeWAV(data);throw std::runtime_error(SDL_GetError());}
    SDL_QueueAudio(handle.device,data,size);SDL_FreeWAV(data);SDL_PauseAudioDevice(handle.device,0);
    return &handle;
}

bool videoNeedsUpdate(){return false;}
void videoDrawRects(){}
void videoPause(){}
void videoResume(){}
