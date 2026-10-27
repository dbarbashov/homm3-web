#include "lod_cache.h"
#include <zlib.h>
#include <vector>
#include <cstdio>
#include <stdexcept>
#include <cstring>
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
struct Member {long offset;std::vector<unsigned char> raw,packed;};
Member append(FILE* file,size_t size,int seed){
    Member m;m.raw.resize(size);
    for(size_t i=0;i<size;++i)m.raw[i]=static_cast<unsigned char>((i*17+seed)%251);
    uLongf count=compressBound(size);m.packed.resize(count);
    require(compress(m.packed.data(),&count,m.raw.data(),size)==Z_OK,"compress fixture");m.packed.resize(count);
    fseek(file,0,SEEK_END);m.offset=ftell(file);fwrite(m.packed.data(),1,count,file);fflush(file);return m;
}
void read(FILE* file,const Member& m){
    fseek(file,m.offset,SEEK_SET);std::vector<unsigned char> out(m.raw.size());
    require(Port::readCompressedLod(file,m.offset,out.data(),out.size(),m.packed.size()),"decode");
    require(out==m.raw,"bytes differ");require(ftell(file)==m.offset+long(m.packed.size()),"stream position");
    // The game's buffer may be modified after decoding; the cache owns its copy.
    out[0]^=255;
}
int main(){try{
    FILE* a=tmpfile();FILE* b=tmpfile();require(a&&b,"temporary files");
    auto one=append(a,65536,1),two=append(b,65536,2);read(a,one);read(b,two);
    auto stats=Port::lodCacheStats();read(a,one);require(Port::lodCacheStats().hits==stats.hits+1,"cache reuse");
    for(int i=0;i<12;++i){auto m=append(a,2*1024*1024,i);read(a,m);require(Port::lodCacheStats().bytes<=16*1024*1024,"cache exceeds budget");}
    read(a,one);read(b,two);Port::forgetLod(a);fclose(a);
    read(b,two);Port::forgetLod(b);require(Port::lodCacheStats().bytes==0&&Port::lodCacheStats().entries==0,"close invalidation");
    fseek(b,two.offset,SEEK_SET);std::vector<unsigned char> bad(two.raw.size());
    require(!Port::readCompressedLod(b,two.offset,bad.data(),bad.size(),two.packed.size()-5),"truncated data accepted");
    require(Port::lodCacheStats().entries==0,"failed decode cached");fclose(b);
    puts("PASS: decompression, reuse, immutable copies, archive separation, stream position, eviction, close and truncation");
}catch(const std::exception& e){fprintf(stderr,"%s\n",e.what());return 1;}}
