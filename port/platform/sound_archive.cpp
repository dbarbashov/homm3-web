// Original 48-byte SND directory exposed to ResourceManager::GetSoundFile.
// Whole archive transport stays outside the engine; lookup/decode stay in C++.
#include "smackmgr.h"
#include "host_path.h"
#include <cstdio>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <vector>
namespace {
bool openArchive(const char* path,void*& file,SoundHeaderStruct*& headers,int& count,bool required){
    using File=std::unique_ptr<FILE,decltype(&fclose)>;
    File input(fopen(Port::hostPath(path).c_str(),"rb"),fclose);
    if(!input){if(required)throw std::runtime_error(std::string("Missing sound archive: ")+path);return false;}
    fseek(input.get(),0,SEEK_END);long length=ftell(input.get());rewind(input.get());
    uint32_t n=0;
    if(fread(&n,4,1,input.get())!=1 || n>100000 || 4+uint64_t(n)*48>uint64_t(length))throw std::runtime_error("Invalid SND directory");
    static_assert(sizeof(SoundHeaderStruct)==48,"SND disk layout");
    std::unique_ptr<SoundHeaderStruct[]> entries(new SoundHeaderStruct[n]);
    if(fread(entries.get(),48,n,input.get())!=n)throw std::runtime_error("Truncated SND directory");
    for(uint32_t i=0;i<n;++i){const auto& e=entries[i];
        if(!memchr(e.m_filename,0,40) || e.m_offset<int(4+n*48) || e.m_size<12 || uint64_t(e.m_offset)+e.m_size>uint64_t(length))throw std::runtime_error("Invalid SND member");
    }
    count=n;headers=entries.release();file=input.release();return true;
}
void closeArchive(void*& file,SoundHeaderStruct*& headers,int& count){if(file)fclose(static_cast<FILE*>(file));file=nullptr;delete[] headers;headers=nullptr;count=0;}
}
unsigned char loadSoundHeaders(){
    openArchive("data/heroes3.snd",g_soundFile,g_soundHeader,g_soundCount,true);
    openArchive("data/h3ab_ahd.snd",g_soundFileCd,g_soundHeaderCd,g_soundCountCd,false);
    return 1;
}
void deleteSoundHeaders(){closeArchive(g_soundFile,g_soundHeader,g_soundCount);closeArchive(g_soundFileCd,g_soundHeaderCd,g_soundCountCd);closeArchive(g_soundFileCampaign,g_soundHeaderCampaign,g_soundCountCampaign);}
