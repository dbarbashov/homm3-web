// Platform media boundary: original MP3 selection with host audio playback.
// Original sound effects and MP3 music use platform playback services.
// Video decoding is implemented in video.cpp; force feedback is unavailable.
#include "soundmgr.h"
#include "music.h"
#include "sfx.h"
#include "prefs.h"
#include "smackmgr.h"
#include "imm_mouse.h"
#include "sample.h"
#include <algorithm>
int g_noSound=0;
HSTREAM g_mp3Stream=nullptr;
unsigned char g_terrainMusicIds[9]={8,7,3,4,5,9,10,6,2};
soundManager::soundManager():m_mssHandle(0),m_ds(nullptr),m_samples(0),m_sampleNum(0),m_currentTerrainMusic(-1),m_playSounds(1),m_changeSounds(0),m_mp3Playing(0){
    std::fill_n(m_sampleHandles,14,nullptr);
    InitializeCriticalSection(&m_sectionSoundCall);InitializeCriticalSection(&m_sectionMp3Change);InitializeCriticalSection(&m_sectionMp3NameChange);
}
int soundManager::open(int priority){m_priority=priority;m_status=STATUS_ACTIVE;initializeSamples();return 0;}
void soundManager::close(){stopAllSamples(1);Port::Sfx::close();Port::Music::close();m_samples=0;m_ds=nullptr;m_status=0;}
int soundManager::main(message&){return 0;}
int soundManager::musicPlaying(){return Port::Music::playing();}
void soundManager::resumeStream(){Port::Music::resume();}
namespace { float musicVolume(){int v=g_config.m_musicVolume;return v>=1 && v<=10?std::min(1.f,(v+1)/10.f):0.f;} }
void soundManager::adjustMusicVolumes(){Port::Music::volume(musicVolume());}
void soundManager::switchAmbientMusic(int id){
    static const char* tracks[]={"Water","Grass","Snow","Swamp","Lava","Sand","Dirt","Rough","Underground"};
    m_currentTerrainMusic=static_cast<signed char>(id);if(id>=2 && id<=10)startMP3(tracks[id-2],0,0);
}
void soundManager::stopMP3(){Port::Music::stop();}
void soundManager::startMP3(const char* name,int loops,unsigned char stopSamples){if(stopSamples)stopAllSamples(0);if(name)Port::Music::play(name,loops,musicVolume());}
extern "C" int AIL_stream_status(HSTREAM){return 0;}
namespace force_feedback { class t_enclosure {}; }
TImmMouseEffect::TImmMouseEffect(const RECT*,long,unsigned long,unsigned long,unsigned char,unsigned char){}
TImmMouseEffect::~TImmMouseEffect(){}
unsigned char TImmMouseEffect::start(){return 0;}
void TImmMouseEffect::stop(){}
unsigned char playImmEffect(const char*,int){return 0;}
SAMPLE2 g_nullSample2{nullptr,nullptr};
