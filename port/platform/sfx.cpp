// PCM decoding and playback only. Game events, channels and volumes are C++ owned.
#include "sfx.h"
#include <SDL.h>
#include <algorithm>
#include <map>
#include <memory>
#include <string>
#include <vector>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace {
struct Clip { unsigned id;std::vector<float> pcm;unsigned used; };
struct Voice {std::shared_ptr<Clip> clip;size_t position=0;int remaining=1,loops=1,volume=127;bool active=false;unsigned generation=0;};
Voice voices[Port::Sfx::slots];
std::map<std::string,std::shared_ptr<Clip>> cache;
size_t cacheBytes=0;
unsigned serial=0,stamp=0;
SDL_AudioDeviceID device=0;
constexpr size_t budget=16*1024*1024;
#ifndef __EMSCRIPTEN__
void (*musicMixer)(float*,int)=nullptr;
struct Lock {Lock(){if(device)SDL_LockAudioDevice(device);}~Lock(){if(device)SDL_UnlockAudioDevice(device);}};
void mix(void*,Uint8* bytes,int length){
    auto* out=reinterpret_cast<float*>(bytes);int count=length/sizeof(float);std::fill_n(out,count,0.f);
    if(musicMixer)musicMixer(out,count);
    for(auto& v:voices){
        if(!v.active || !v.clip)continue;
        auto& pcm=v.clip->pcm;
        for(int i=0;i<count;++i){
            if(v.position==pcm.size()){
                if(v.remaining==1){v.active=false;break;}
                if(v.remaining>1)--v.remaining;
                v.position=0;
            }
            out[i]+=pcm[v.position++]*v.volume/127.f;
        }
    }
    for(int i=0;i<count;++i)out[i]=std::max(-1.f,std::min(1.f,out[i]));
}
#else
struct Lock {};
#endif
std::shared_ptr<Clip> decode(const char* name,const void* wave,size_t size){
    if(!wave || size<12 || size>32*1024*1024)return {};
    unsigned hash=2166136261u;auto* b=static_cast<const unsigned char*>(wave);
    for(size_t i=0;i<size;++i)hash=(hash^b[i])*16777619u;
    std::string key=std::string(name)+":"+std::to_string(hash);
    auto found=cache.find(key);if(found!=cache.end()){found->second->used=++stamp;return found->second;}
    SDL_AudioSpec spec{};Uint8* data=nullptr;Uint32 length=0;
    if(!SDL_LoadWAV_RW(SDL_RWFromConstMem(wave,size),1,&spec,&data,&length)){SDL_Log("SFX decode %s: %s",name,SDL_GetError());return {};}
    SDL_AudioCVT cvt{};
    if(SDL_BuildAudioCVT(&cvt,spec.format,spec.channels,spec.freq,AUDIO_F32SYS,2,44100)<0){SDL_FreeWAV(data);return {};}
    std::vector<Uint8> converted(size_t(length)*cvt.len_mult);
    std::copy(data,data+length,converted.begin());SDL_FreeWAV(data);cvt.buf=converted.data();cvt.len=length;
    if(SDL_ConvertAudio(&cvt)<0)return {};
    auto clip=std::make_shared<Clip>();clip->id=++serial;clip->used=++stamp;
    clip->pcm.resize(cvt.len_cvt/sizeof(float));std::memcpy(clip->pcm.data(),converted.data(),cvt.len_cvt);
    if(clip->pcm.empty() || clip->pcm.size()%2)return {};
    cacheBytes+=clip->pcm.size()*sizeof(float);cache[key]=clip;
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3Sfx.load($0,UTF8ToString($1),HEAPF32.subarray($2>>>2,($2>>>2)+$3));},clip->id,name,clip->pcm.data(),clip->pcm.size());
#endif
    while(cacheBytes>budget && cache.size()>1){
        auto oldest=std::min_element(cache.begin(),cache.end(),[](const auto& a,const auto& b){return a.second->used<b.second->used;});
        cacheBytes-=oldest->second->pcm.size()*sizeof(float);
#ifdef __EMSCRIPTEN__
        EM_ASM({window.homm3Sfx.drop($0);},oldest->second->id);
#endif
        cache.erase(oldest);
    }
    return clip;
}
}
namespace Port { namespace Sfx {
#ifndef __EMSCRIPTEN__
void setMusicMixer(void (*callback)(float*,int)){Lock lock;musicMixer=callback;}
void lockAudio(){if(device)SDL_LockAudioDevice(device);}
void unlockAudio(){if(device)SDL_UnlockAudioDevice(device);}
#endif
bool open(){
#ifdef __EMSCRIPTEN__
    return EM_ASM_INT({return !!window.homm3Sfx && !!window.homm3Music.context();});
#else
    if(device)return true;
    SDL_AudioSpec spec{};spec.freq=44100;spec.format=AUDIO_F32SYS;spec.channels=2;spec.samples=1024;spec.callback=mix;
    device=SDL_OpenAudioDevice(nullptr,0,&spec,nullptr,0);
    if(device)SDL_PauseAudioDevice(device,0);else SDL_Log("SFX audio device: %s",SDL_GetError());
    return device!=0;
#endif
}
void close(){
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3Sfx?.close();});
#else
    if(device){SDL_CloseAudioDevice(device);device=0;}musicMixer=nullptr;
#endif
    for(auto& v:voices)v=Voice{};cache.clear();cacheBytes=0;
}
bool play(int slot,const char* name,const void* wave,size_t size,int loops,int value){
    auto clip=decode(name,wave,size);if(!clip)return false;
    Lock lock;auto& v=voices[slot];v.clip=clip;v.position=0;v.remaining=v.loops=loops;v.volume=value;v.active=true;++v.generation;
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3Sfx.play($0,$1,$2,$3);},slot,clip->id,loops,value/127.f);
#endif
    return true;
}
void stop(int slot){Lock lock;voices[slot].active=false;
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3Sfx.stop($0);},slot);
#endif
}
void pause(int slot){Lock lock;voices[slot].active=false;
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3Sfx.pause($0);},slot);
#endif
}
void resume(int slot){Lock lock;voices[slot].active=bool(voices[slot].clip);
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3Sfx.resume($0);},slot);
#endif
}
void restart(int slot){Lock lock;auto& v=voices[slot];v.position=0;v.remaining=v.loops;v.active=bool(v.clip);
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3Sfx.restart($0);},slot);
#endif
}
bool playing(int slot){
#ifdef __EMSCRIPTEN__
    return EM_ASM_INT({return window.homm3Sfx.playing($0);},slot);
#else
    Lock lock;return voices[slot].active;
#endif
}
void volume(int slot,int value){Lock lock;voices[slot].volume=value;
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3Sfx.volume($0,$1);},slot,value/127.f);
#endif
}
unsigned generation(int slot){return voices[slot].generation;}
size_t decodedBytes(){return cacheBytes;}
}}
