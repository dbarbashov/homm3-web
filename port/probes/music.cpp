// Exercise the actual native mixer offline; the SFX device is replaced by a sink.
#include "../platform/music.h"
#include <vector>
#include <cmath>
#include <stdexcept>
#include <cstdio>
#include <unistd.h>
static void (*mixer)(float*,int)=nullptr;
namespace Port { namespace Sfx {
bool open(){return true;}
void lockAudio(){}
void unlockAudio(){}
void setMusicMixer(void (*callback)(float*,int)){mixer=callback;}
}}
static void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
static std::vector<float> render(int frames){std::vector<float> pcm(frames*2);require(mixer,"missing mixer");mixer(pcm.data(),pcm.size());return pcm;}
static void compare(const std::vector<float>& pcm,const std::vector<float>& reference,int offset,int direction){
    for(size_t i=0;i<pcm.size();++i){
        int step=int(i/2)/4410;
        float envelope=direction==1?std::min(1.f,(step+1)/10.f):std::max(0.f,(9-step)/10.f);
        require(std::fabs(pcm[i]-reference[offset*2+i]*envelope)<0.000001f,"PCM fade differs from original timing");
    }
}
int main(int argc,char** argv){try{
    require(argc==2 && chdir(argv[1])==0,"runtime directory");
    Port::Music::play("MainMenu",1,1);auto menu=render(4*44100);Port::Music::close();
    Port::Music::play("Dirt",1,1);auto dirt=render(2*44100);Port::Music::close();
    Port::Music::play("MainMenu",0,1);auto first=render(2*44100);compare(first,menu,0,1);
    Port::Music::stop();require(Port::Music::playing(),"stop must fade before pausing");
    auto tail=render(44100);compare(tail,menu,2*44100,-1);require(!Port::Music::playing(),"fade did not stop");
    Port::Music::resume();auto resumed=render(44100);compare(resumed,menu,2*44100,1);
    Port::Music::play("Dirt",0,1);auto old=render(39690);compare(old,menu,3*44100,-1);
    auto next=render(44100);compare(next,dirt,0,1);
    Port::Music::play("MainMenu",1,1);render(39690);auto finite=render(44100);
    for(size_t i=0;i<finite.size();++i)require(std::fabs(finite[i]-menu[i])<0.000001f,"finite music must restart without fade-in");
    Port::Music::close();require(!Port::Music::playing(),"close must stop immediately");
    puts("{\"passed\":true,\"pcmFadeSteps\":9,\"stepMilliseconds\":100,\"resumeBeforeFade\":true,\"sequentialTracks\":true,\"finiteRestart\":true}");
}catch(const std::exception& e){fprintf(stderr,"Music regression: %s\n",e.what());return 1;}}
