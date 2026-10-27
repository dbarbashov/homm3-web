// Portable replacement for the external Victor PCX library (not game logic).
// Retains its bottom-up DIB contract; supports the 8/24-bit PCX formats used here.
#include "pcx.h"
#include <vector>
#include <cstdio>
#include <cstring>
#include <algorithm>
#include <memory>
namespace {
using File=std::unique_ptr<FILE,decltype(&fclose)>;
unsigned u16(const unsigned char* p){return p[0]|(p[1]<<8);}
bool header(FILE* f,unsigned char* h){return fread(h,1,128,f)==128 && h[0]==10 && h[2]==1 && h[3]==8 && (h[65]==1||h[65]==3) && u16(h+8)>=u16(h+4) && u16(h+10)>=u16(h+6);}
}
int pcxinfo(const char* filename,PcxData* data){
    File f(fopen(filename,"rb"),fclose);unsigned char h[128];
    if(!f||!header(f.get(),h))return -1;
    *data={h[1],u16(h+8)-u16(h+4)+1,u16(h+10)-u16(h+6)+1,h[3],h[65],(int)u16(h+66),(int)u16(h+68),h[3]*h[65]};return 0;
}
int allocimage(imgdes* image,int width,int height,int bits){
    if(!image || width<=0 || height<=0 || width>16384 || height>16384 || (bits!=8&&bits!=24))return -1;
    *image={};image->m_endx=width-1;image->m_endy=height-1;image->m_buffwidth=(width*(bits/8)+3)&~3;
    image->m_colors=bits==8?256:0;image->m_imgtype=bits;
    image->m_ibuff=new unsigned char[(size_t)image->m_buffwidth*height]();
    image->m_palette=image->m_colors?new RGBQUAD[image->m_colors]():nullptr;
    image->m_bmh=new BITMAPINFOHEADER{};
    image->m_bmh->biSize=sizeof(BITMAPINFOHEADER);image->m_bmh->biWidth=width;image->m_bmh->biHeight=height;
    image->m_bmh->biPlanes=1;image->m_bmh->biBitCount=bits;return 0;
}
void freeimage(imgdes* image){delete[] image->m_ibuff;delete[] image->m_palette;delete image->m_bmh;*image={};}
int loadpcx(const char* filename,imgdes* image){
    File f(fopen(filename,"rb"),fclose);unsigned char h[128];
    if(!f||!header(f.get(),h)||!image||!image->m_ibuff)return -1;
    unsigned width=u16(h+8)-u16(h+4)+1,height=u16(h+10)-u16(h+6)+1,planes=h[65],pitch=u16(h+66);
    if(width!=image->m_endx+1 || height!=image->m_endy+1 || width>pitch || image->m_imgtype!=8*(int)planes)return -1;
    std::vector<unsigned char> row(pitch*planes);
    for(unsigned y=0;y<height;++y){
        for(size_t n=0;n<row.size();){int c=fgetc(f.get());if(c==EOF)return -1;unsigned count=1;
            if((c&0xc0)==0xc0){count=c&63;c=fgetc(f.get());if(c==EOF||!count)return -1;}
            if(n+count>row.size())return -1;std::fill(row.begin()+n,row.begin()+n+count,(unsigned char)c);n+=count;
        }
        auto* dst=image->m_ibuff+(height-1-y)*image->m_buffwidth;
        for(unsigned x=0;x<width;++x){if(planes==1)dst[x]=row[x];else for(unsigned p=0;p<3;++p)dst[x*3+(2-p)]=row[p*pitch+x];}
    }
    if(planes==1){if(fseek(f.get(),-769,SEEK_END)||fgetc(f.get())!=12)return -1;
        for(int i=0;i<256;++i){unsigned char rgb[3];if(fread(rgb,1,3,f.get())!=3)return -1;image->m_palette[i]={rgb[2],rgb[1],rgb[0],0};}}
    return 0;
}
int flipimage(imgdes* src,imgdes* dst){
    if(!src||!dst||!src->m_ibuff||!dst->m_ibuff||src->m_buffwidth!=dst->m_buffwidth||src->m_endy!=dst->m_endy)return -1;
    unsigned height=src->m_endy+1,pitch=src->m_buffwidth;
    if(src==dst){for(unsigned y=0;y<height/2;++y)for(unsigned x=0;x<pitch;++x)std::swap(src->m_ibuff[y*pitch+x],src->m_ibuff[(height-1-y)*pitch+x]);}
    else {for(unsigned y=0;y<height;++y)memcpy(dst->m_ibuff+y*pitch,src->m_ibuff+(height-1-y)*pitch,pitch);}
    return 0;
}
