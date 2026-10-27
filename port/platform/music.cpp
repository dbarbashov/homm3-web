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
bool device=false;
std::vector<float> samples;
size_t position=0;
int channels=2, remaining=0;
float gain=1;
bool active=false;
std::string current;
std::map<std::string,size_t> positions;
void output(float* dst,int count){
    std::fill_n(dst,count,0.f);
    if(!active || samples.empty())return;
    for(size_t i=0;i<count;++i){
        if(position>=samples.size()){
            if(remaining==1){active=false;break;}
            if(remaining>1)--remaining;
            position=0;
        }
        dst[i]=samples[position++]*gain;
    }
}
std::string pathFor(const char* name){
    std::string wanted=std::string(name)+".mp3",result;
    if(auto* dir=opendir("mp3")){while(auto* e=readdir(dir))if(!strcasecmp(e->d_name,wanted.c_str())){result=std::string("mp3/")+e->d_name;break;}closedir(dir);}
    return result;
}
}
namespace Port { namespace Music {
void stop(){if(device){Sfx::lockAudio();active=false;positions[current]=position;Sfx::unlockAudio();}}
void volume(float v){if(device)Sfx::lockAudio();gain=std::max(0.f,std::min(1.f,v));if(device)Sfx::unlockAudio();}
void resume(){if(device){Sfx::lockAudio();active=!samples.empty();Sfx::unlockAudio();}}
bool playing(){if(!device)return false;Sfx::lockAudio();bool value=active;Sfx::unlockAudio();return value;}
void close(){Sfx::setMusicMixer(nullptr);device=false;active=false;samples.clear();current.clear();}
void play(const char* name,int loops,float v){
    if(current==name && device){volume(v);resume();return;}
    stop();
    drmp3_config config{};drmp3_uint64 frames=0;
    auto path=pathFor(name);
    float* decoded=path.empty()?nullptr:drmp3_open_file_and_read_pcm_frames_f32(path.c_str(),&config,&frames,nullptr);
    if(!decoded){SDL_Log("Cannot decode music: %s",name);return;}
    SDL_AudioCVT cvt{};
    SDL_BuildAudioCVT(&cvt,AUDIO_F32SYS,config.channels,config.sampleRate,AUDIO_F32SYS,2,44100);
    std::vector<Uint8> converted(frames*config.channels*sizeof(float)*cvt.len_mult);
    std::memcpy(converted.data(),decoded,frames*config.channels*sizeof(float));drmp3_free(decoded,nullptr);
    cvt.buf=converted.data();cvt.len=frames*config.channels*sizeof(float);
    if(SDL_ConvertAudio(&cvt)<0)return;
    device=Sfx::open();if(!device)return;
    Sfx::setMusicMixer(output);Sfx::lockAudio();
    samples.resize(cvt.len_cvt/sizeof(float));std::memcpy(samples.data(),converted.data(),cvt.len_cvt);
    current=name;remaining=loops;position=positions[current];
    if(position>=samples.size())position=0;
    gain=std::max(0.f,std::min(1.f,v));active=true;
    Sfx::unlockAudio();
}
}}
#endif
