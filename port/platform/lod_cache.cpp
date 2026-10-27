// Bounded cache of decompressed archive bytes, independent of mutable sprites.
#include "lod_cache.h"
#include <zlib.h>
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <list>
#include <map>
#include <tuple>
#include <vector>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace {
constexpr size_t budget=16*1024*1024, maxEntries=256;
using Key=std::tuple<uintptr_t,long,size_t,size_t>;
struct Entry {std::vector<unsigned char> bytes;std::list<Key>::iterator recent;};
std::map<Key,Entry> cache;
std::list<Key> recency;
size_t bytes=0,hits=0,misses=0;
// Global LODFile destructors may run after this translation unit's containers.
bool cacheAlive=true;
struct CacheLifetime {~CacheLifetime(){cacheAlive=false;}} lifetime;
void yieldToBrowser(){
#ifdef __EMSCRIPTEN__
    static double lastYield=0;
    if(emscripten_get_now()-lastYield>=6){emscripten_sleep(0);lastYield=emscripten_get_now();}
#endif
}
void remove(std::map<Key,Entry>::iterator it){
    bytes-=it->second.bytes.size();recency.erase(it->second.recent);cache.erase(it);
}
bool unpack(const std::vector<unsigned char>& packed,unsigned char* out,size_t size){
    z_stream stream{};
    if(inflateInit(&stream)!=Z_OK)return false;
    stream.next_in=const_cast<unsigned char*>(packed.data());stream.avail_in=packed.size();
    int status=Z_OK;
    while(status==Z_OK && stream.total_out<size){
        stream.next_out=out+stream.total_out;
        stream.avail_out=std::min<size_t>(64*1024,size-stream.total_out);
        status=inflate(&stream,Z_NO_FLUSH);
        // Yield to browser input/compositing, never reenter the game's event
        // pump while ResourceManager is constructing an object.
        yieldToBrowser();
    }
    const bool ok=status==Z_STREAM_END && stream.total_out==size;
    inflateEnd(&stream);return ok;
}
}
namespace Port {
bool readCompressedLod(FILE* file,long offset,unsigned char* output,size_t size,size_t packedSize){
    if(!file || !output || !size || !packedSize || size>UINT32_MAX || packedSize>UINT32_MAX)return false;
    const Key key{reinterpret_cast<uintptr_t>(file),offset,size,packedSize};
    auto found=cache.find(key);
    if(found!=cache.end()){
        if(fseek(file,offset+long(packedSize),SEEK_SET))return false;
        std::memcpy(output,found->second.bytes.data(),size);
        recency.splice(recency.begin(),recency,found->second.recent);++hits;yieldToBrowser();return true;
    }
    ++misses;
    std::vector<unsigned char> packed(packedSize);
    if(fseek(file,offset,SEEK_SET) || fread(packed.data(),1,packedSize,file)!=packedSize || !unpack(packed,output,size))return false;
    // A huge one-off member should not evict every common UI/map resource.
    if(size<=budget/2){
        while(!cache.empty() && (bytes+size>budget || cache.size()>=maxEntries))remove(cache.find(recency.back()));
        recency.push_front(key);
        cache.emplace(key,Entry{std::vector<unsigned char>(output,output+size),recency.begin()});bytes+=size;
    }
    yieldToBrowser();return true;
}
void forgetLod(FILE* file){
    if(!cacheAlive)return;
    const auto id=reinterpret_cast<uintptr_t>(file);
    for(auto it=cache.begin();it!=cache.end();){auto current=it++;if(std::get<0>(current->first)==id)remove(current);}
}
LodCacheStats lodCacheStats(){return {bytes,cache.size(),hits,misses};}
}
