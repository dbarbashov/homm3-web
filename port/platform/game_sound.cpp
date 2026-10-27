// Miles replacement. Original callers and sample resources keep ownership of
// event selection, channel group, volume, looping, stopping and wait semantics.
#include "soundmgr.h"
#include "sample.h"
#include "resourcemanager.h"
#include "prefs.h"
#include "sfx.h"
#include <SDL.h>
#include <vector>
class ds_memsample {public:int slot;};
struct _DIG_DRIVER {};
namespace {
ds_memsample handles[Port::Sfx::slots];
_DIG_DRIVER driver;
struct Range {int first,last,next;};
// Retail allocates twelve handles; the last range is shortened from 14 to 12.
Range ranges[]={{0,1,0},{1,2,1},{2,6,2},{6,12,6}};
int rawVolumes[Port::Sfx::slots]{},effectiveVolumes[Port::Sfx::slots]{};
bool paused[Port::Sfx::slots]{};
struct Pending {sample* resource;int slot;unsigned generation;Uint32 started,maximum;};
std::vector<Pending> pending;
int indexOf(ds_memsample* handle){for(int i=0;i<Port::Sfx::slots;++i)if(handle==&handles[i])return i;return -1;}
bool enabled(){return !g_noSound && (g_soundManager->m_playSounds || g_goSolo);}
}
void soundManager::initializeSamples(){
    m_samples=Port::Sfx::open();m_sampleNum=m_samples?Port::Sfx::slots:0;m_ds=m_samples?&driver:nullptr;
    for(int i=0;i<m_sampleNum;++i){handles[i].slot=i;m_sampleHandles[i]=&handles[i];}
}
ds_memsample* soundManager::memorySample(sample* value){
    if(!enabled() || !m_samples || !g_config.m_soundVolume || !value || !value->memSample.memVolume)return nullptr;
    auto& mem=value->memSample;int channel=mem.memCindex;
    if(channel<0 || channel>=SOUND_CHANNEL_COUNT)return nullptr;
    auto& range=ranges[channel];int slot=range.first;
    while(slot<range.last && Port::Sfx::playing(slot))++slot;
    if(slot==range.last){
        // Preserve the recovered round-robin replacement policy.
        slot=range.next++;if(range.next>=range.last)slot=range.next=range.first;
        Port::Sfx::stop(slot);
    }
    rawVolumes[slot]=mem.memVolume;effectiveVolumes[slot]=convertVolume(mem.memVolume,VOLUME_TYPE_100);
    if(!Port::Sfx::play(slot,value->get_Name(),mem.m_data,mem.m_size,mem.memLooping,convertVolume(mem.memVolume,VOLUME_TYPE_100)))return nullptr;
    mem.memHSample=&handles[slot];return &handles[slot];
}
void soundManager::stopSample(ds_memsample* handle){int slot=indexOf(handle);if(slot>=0)Port::Sfx::stop(slot);}
int soundManager::getSampleInfo(ds_memsample* handle,short op){
    int slot=indexOf(handle);if(slot<0)return 0;
    if(op==SAMPLE_INFO_PLAYING)return Port::Sfx::playing(slot);
    if(op==SAMPLE_INFO_VOLUME)return effectiveVolumes[slot];
    return 0;
}
void soundManager::modifySample(ds_memsample* handle,short op,long value){
    int slot=indexOf(handle);if(slot<0 || !enabled())return;
    if(op==SAMPLE_MODIFY_1 || op==SAMPLE_MODIFY_100){
        if(op==SAMPLE_MODIFY_100)rawVolumes[slot]=value;
        effectiveVolumes[slot]=convertVolume(value,VOLUME_TYPE_100);Port::Sfx::volume(slot,effectiveVolumes[slot]);
    }else if(op==SAMPLE_MODIFY_5)Port::Sfx::restart(slot);
}
void soundManager::adjustSoundVolumes(){
    for(int i=0;i<m_sampleNum;++i){effectiveVolumes[i]=convertVolume(rawVolumes[i],VOLUME_TYPE_100);Port::Sfx::volume(i,effectiveVolumes[i]);}
}
void soundManager::stopAllSamples(int stopMusicToo){
    for(int i=0;i<m_sampleNum;++i){Port::Sfx::stop(i);paused[i]=false;}
    serviceSounds();if(stopMusicToo)stopMP3();
}
void soundManager::pauseSamples(){for(int i=0;i<m_sampleNum;++i){paused[i]=Port::Sfx::playing(i);if(paused[i])Port::Sfx::pause(i);}}
void soundManager::resumeSamples(){for(int i=0;i<m_sampleNum;++i){if(paused[i])Port::Sfx::resume(i);paused[i]=false;}}
void soundManager::serviceSounds(){
    for(auto it=pending.begin();it!=pending.end();){
        const bool replaced=Port::Sfx::generation(it->slot)!=it->generation;
        if(replaced || !Port::Sfx::playing(it->slot) || SDL_GetTicks()-it->started>=it->maximum){
            if(!replaced)Port::Sfx::stop(it->slot);
            ResourceManager::Dispose(it->resource);it=pending.erase(it);
        }else ++it;
    }
}
void launchSample(const char* name,int maxTime,int channel){
    if(!name || !enabled() || !g_config.m_soundVolume)return;
    auto* resource=ResourceManager::GetSample(name);if(!resource)return;
    resource->memSample.memCindex=channel;
    auto* handle=g_soundManager->memorySample(resource);
    if(!handle){ResourceManager::Dispose(resource);return;}
    // The retail worker thread only waits and releases this reference. The
    // browser event pump performs that cleanup without blocking or new threads.
    pending.push_back({resource,handle->slot,Port::Sfx::generation(handle->slot),SDL_GetTicks(),static_cast<Uint32>(maxTime<0?10000:maxTime)});
    g_soundManager->serviceSounds();
}
