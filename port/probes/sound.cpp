#include "../platform/sfx.h"
#include "../platform/music.h"
#include "soundmgr.h"
#include "sample.h"
#include "smackmgr.h"
#include "resourcemanager.h"
#include "prefs.h"
#include <SDL.h>
#include <vector>
#include <stdexcept>
#include <unistd.h>
unsigned char loadSoundHeaders();
void require(bool v,const char* s){if(!v)throw std::runtime_error(s);}
int main(int argc,char** argv){
    try{
        require(argc==2 && chdir(argv[1])==0,"runtime directory");SDL_Init(SDL_INIT_AUDIO|SDL_INIT_TIMER);
        ResourceManager::SetPath("data/");int error=0;require(ResourceManager::Open(true,true,&error),"LOD open");loadSoundHeaders();
        g_config.m_soundVolume=5;g_config.m_musicVolume=5;g_soundManager=new soundManager;g_soundManager->open(0);
        require(g_soundManager->m_samples,"audio device");
        int decoded=0;
        for(int archive=0;archive<2;++archive){
            auto* headers=archive?g_soundHeaderCd:g_soundHeader;int count=archive?g_soundCountCd:g_soundCount;
            auto* file=static_cast<FILE*>(archive?g_soundFileCd:g_soundFile);
            for(int i=0;i<count;++i){auto& h=headers[i];std::vector<unsigned char> bytes(h.m_size);fseek(file,h.m_offset,SEEK_SET);require(fread(bytes.data(),1,bytes.size(),file)==bytes.size(),"archive member read");require(Port::Sfx::play(0,h.m_filename,bytes.data(),bytes.size(),1,64),h.m_filename);++decoded;}
        }
        g_soundManager->stopAllSamples(0);
        auto* click=ResourceManager::GetSample("button.wav");require(click,"original button resource");
        click->memSample.memCindex=3;click->memSample.memLooping=0;
        auto* first=g_soundManager->memorySample(click);auto* second=g_soundManager->memorySample(click);
        require(first && second && first!=second,"overlapping voices");SDL_Delay(400);
        require(g_soundManager->getSampleInfo(first,4),"loop continues");
        g_soundManager->stopSample(first);require(!g_soundManager->getSampleInfo(first,4) && g_soundManager->getSampleInfo(second,4),"independent stop");
        g_config.m_soundVolume=0;g_soundManager->adjustSoundVolumes();require(!g_soundManager->memorySample(click),"mute prevents new voices");
        g_config.m_soundVolume=5;g_soundManager->adjustSoundVolumes();g_soundManager->stopAllSamples(0);click->memSample.memLooping=1;
        for(int i=0;i<200;++i)launchSample("button.wav",-1,3);
        SDL_Delay(1000);g_soundManager->serviceSounds();
        for(int i=0;i<Port::Sfx::slots;++i)require(!Port::Sfx::playing(i),"one-shots finish");
        require(Port::Sfx::decodedBytes()<=16*1024*1024,"bounded PCM cache");
        ResourceManager::Dispose(click);
        Port::Music::play("MainMenu",0,.4f);require(Port::Music::playing(),"music and SFX coexist");
        g_soundManager->close();delete g_soundManager;g_soundManager=nullptr;deleteSoundHeaders();SDL_Quit();
        printf("{\"passed\":true,\"decodedEntries\":%d,\"overlap\":true,\"loopStop\":true,\"mute\":true,\"rapidOneShots\":200,\"cacheBounded\":true}\n",decoded);
    }catch(const std::exception& e){fprintf(stderr,"SFX regression: %s\n",e.what());return 1;}
}
