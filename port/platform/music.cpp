#include "music.h"
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
namespace Port { namespace Music {
void play(const char* name,int loops,float v){EM_ASM({window.homm3Music?.play(UTF8ToString($0),$1,$2);},name,loops,v);}
void stop(){EM_ASM({window.homm3Music?.stop();});}
void resume(){EM_ASM({window.homm3Music?.resume();});}
void volume(float v){EM_ASM({window.homm3Music?.volume($0);},v);}
bool playing(){return EM_ASM_INT({return window.homm3Music?.state.playing?1:0;});}
void close(){EM_ASM({window.homm3Music?.close();});}
}}
#else
#include <SDL.h>
#include "sfx.h"
#include <dirent.h>
#include <strings.h>
#include <algorithm>
#include <map>
#include <string>
#include <vector>
#define DR_MP3_IMPLEMENTATION
#include "../vendor/dr_mp3.h"
namespace {
bool device=false,active=false,queued=false;
std::vector<float> samples,nextSamples;
size_t position=0,nextPosition=0;
int remaining=0,nextLoops=0;
float gain=1,envelope=1,fadeStart=1;
// Match the original Miles worker: nine 100 ms volume steps each way.
constexpr int stepFrames=4410,fadeFrames=9*stepFrames;
int fadeDirection=0,fadeFrame=0;
std::string current,nextName;
std::map<std::string,size_t> positions;
void activateQueued(){
    samples.swap(nextSamples);current.swap(nextName);
    position=nextPosition;remaining=nextLoops;queued=false;active=true;
    fadeDirection=remaining==0?1:0;fadeFrame=0;envelope=remaining==0?.1f:1.f;
}
void beginFadeOut(){
    if(!active || fadeDirection==-1)return;
    positions[current]=position; // Original remembers the position before fading.
    fadeStart=envelope;fadeFrame=0;fadeDirection=-1;
}
void output(float* dst,int count){
    std::fill_n(dst,count,0.f);
    for(int i=0;i+1<count;i+=2){
        if(!active || samples.empty())break;
        if(fadeDirection==-1 && (fadeFrame>=fadeFrames || gain==0)){
            active=false;
            if(queued)activateQueued();else break;
        }
        if(position>=samples.size()){
            if(remaining==1){
                active=false;
                if(queued)activateQueued();else break;
            }else{
                if(remaining>1)--remaining;
                position=0;
            }
        }
        if(fadeDirection==1){
            envelope=std::min(1.f,(fadeFrame/stepFrames+1)/10.f);
            if(fadeFrame>=fadeFrames)fadeDirection=0;
        }else if(fadeDirection==-1)envelope=fadeStart*(9-fadeFrame/stepFrames)/10.f;
        dst[i]=samples[position++]*gain*envelope;
        dst[i+1]=samples[position++]*gain*envelope;
        if(fadeDirection)++fadeFrame;
    }
}
std::string pathFor(const char* name){
    std::string wanted=std::string(name)+".mp3",result;
    if(auto* dir=opendir("mp3")){while(auto* e=readdir(dir))if(!strcasecmp(e->d_name,wanted.c_str())){result=std::string("mp3/")+e->d_name;break;}closedir(dir);}
    return result;
}
}
namespace Port { namespace Music {
void stop(){if(device){Sfx::lockAudio();queued=false;beginFadeOut();Sfx::unlockAudio();}}
void volume(float v){if(device)Sfx::lockAudio();gain=std::max(0.f,std::min(1.f,v));if(device)Sfx::unlockAudio();}
void resume(){
    if(!device)return;
    Sfx::lockAudio();auto name=current;int loops=remaining;float v=gain;Sfx::unlockAudio();
    if(!name.empty())play(name.c_str(),loops,v);
}
bool playing(){if(!device)return false;Sfx::lockAudio();bool value=active;Sfx::unlockAudio();return value;}
void close(){Sfx::setMusicMixer(nullptr);device=active=queued=false;samples.clear();nextSamples.clear();current.clear();nextName.clear();positions.clear();}
void play(const char* name,int loops,float v){
    if(device){
        Sfx::lockAudio();gain=std::max(0.f,std::min(1.f,v));
        const bool same=(queued && nextName==name) || (active && fadeDirection!=-1 && current==name);
        Sfx::unlockAudio();if(same)return;
    }
    drmp3_config config{};drmp3_uint64 frames=0;
    auto path=pathFor(name);
    float* decoded=path.empty()?nullptr:drmp3_open_file_and_read_pcm_frames_f32(path.c_str(),&config,&frames,nullptr);
    if(!decoded){SDL_Log("Cannot decode music: %s",name);return;}
    SDL_AudioCVT cvt{};
    SDL_BuildAudioCVT(&cvt,AUDIO_F32SYS,config.channels,config.sampleRate,AUDIO_F32SYS,2,44100);
    std::vector<Uint8> converted(frames*config.channels*sizeof(float)*cvt.len_mult);
    std::memcpy(converted.data(),decoded,frames*config.channels*sizeof(float));drmp3_free(decoded,nullptr);
    cvt.buf=converted.data();cvt.len=frames*config.channels*sizeof(float);
    if(SDL_ConvertAudio(&cvt)<0 || !cvt.len_cvt)return;
    device=Sfx::open();if(!device)return;
    std::vector<float> prepared(cvt.len_cvt/sizeof(float));std::memcpy(prepared.data(),converted.data(),cvt.len_cvt);
    Sfx::setMusicMixer(output);Sfx::lockAudio();
    beginFadeOut();
    nextSamples.swap(prepared);nextName=name;nextLoops=loops;
    nextPosition=loops==0?positions[name]:0;if(nextPosition>=nextSamples.size())nextPosition=0;
    queued=true;gain=std::max(0.f,std::min(1.f,v));
    if(!active)activateQueued();
    Sfx::unlockAudio();
}
}}
#endif
