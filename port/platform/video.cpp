// Portable Bink/Smacker decoding. Assets stay in the user's original VID archives.
#include "smackmgr.h"
#include "binkmanager.h"
#include "bitmap16.h"
#include "winmgr.h"
#include "inputmgr.h"
#include "kbwin.h"
#include "message.h"
#include "prefs.h"
#include "host_path.h"
#include "sdl_backend.h"
#include "sfx.h"
#include "port_video_descriptors.h"
#include <SDL.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <memory>
#include <unordered_map>
#include <vector>
extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libswscale/swscale.h>
#include <libswresample/swresample.h>
}
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
EM_ASYNC_JS(uintptr_t, readBrowserVideo, (const char* name, uint32_t* size), {
    const filename=UTF8ToString(name);
    if(!window.homm3VideoNames?.has(filename.toLowerCase()))return 0;
    try {
        const response=await window.homm3Assets.fetch('/api/video?name='+encodeURIComponent(filename));
        if(!response.ok)return 0;
        const bytes=new Uint8Array(await response.arrayBuffer());
        if(!bytes.length || bytes.length>64*1024*1024)return 0;
        const ptr=_malloc(bytes.length);if(!ptr)return 0;
        HEAPU8.set(bytes,ptr);HEAPU32[size>>>2]=bytes.length;return ptr;
    } catch { return 0; }
});
#endif
namespace BinkManager {
BinkManagerStruct g_playingBink{};
bool g_needsUpdate=false,g_updateScreen=false,g_playingBinkActive=false;
int g_surfaceType=0;
}
namespace SmackManager { SmackManagerStruct g_playingSmack{}; }
namespace {
constexpr int audioSlot=12;
int pauseDepth=0;
std::vector<uint8_t> resource(const std::string& name){
#ifdef __EMSCRIPTEN__
    uint32_t size=0;auto* bytes=reinterpret_cast<uint8_t*>(readBrowserVideo(name.c_str(),&size));
    if(!bytes)return {};
    std::vector<uint8_t> result(bytes,bytes+size);free(bytes);return result;
#else
    for(const char* archive:{"data/h3ab_ahd.vid","data/video.vid","data/heroes3.vid"}){
        std::unique_ptr<FILE,decltype(&fclose)> file(fopen(Port::hostPath(archive).c_str(),"rb"),fclose);
        if(!file)continue;
        fseek(file.get(),0,SEEK_END);long length=ftell(file.get());rewind(file.get());
        uint32_t count=0;if(fread(&count,4,1,file.get())!=1 || count>10000 || 4ull+count*44>uint64_t(length))continue;
        struct Entry{char name[40];uint32_t offset;};static_assert(sizeof(Entry)==44,"VID directory layout");
        std::vector<Entry> entries(count);if(fread(entries.data(),44,count,file.get())!=count)continue;
        for(const auto& entry:entries){
            if(!memchr(entry.name,0,40) || strcasecmp(entry.name,name.c_str()))continue;
            uint32_t end=length;for(const auto& next:entries)if(next.offset>entry.offset)end=std::min(end,next.offset);
            if(entry.offset<4+44*count || end<=entry.offset || end>length || end-entry.offset>64*1024*1024)return {};
            std::vector<uint8_t> bytes(end-entry.offset);fseek(file.get(),entry.offset,SEEK_SET);
            if(fread(bytes.data(),1,bytes.size(),file.get())!=bytes.size())return {};
            return bytes;
        }
    }
    return {};
#endif
}
struct Movie {
    std::vector<uint8_t> bytes,pixels,wave;
    size_t position=0;
    AVFormatContext* format=nullptr;AVIOContext* io=nullptr;AVCodecContext* codec=nullptr;
    AVFrame* frame=av_frame_alloc();AVPacket* packet=av_packet_alloc();SwsContext* scale=nullptr;
    int stream=-1,width=0,height=0,frameMs=67,id=-1,decoded=0;
    uint32_t next=0;bool finished=false,paused=false,loop=false,sound=false;
    ~Movie(){sws_freeContext(scale);av_packet_free(&packet);av_frame_free(&frame);avcodec_free_context(&codec);avformat_close_input(&format);if(io){av_freep(&io->buffer);avio_context_free(&io);}}
    static int read(void* opaque,uint8_t* buffer,int count){
        auto& m=*static_cast<Movie*>(opaque);size_t n=std::min(size_t(count),m.bytes.size()-m.position);
        if(!n)return AVERROR_EOF;memcpy(buffer,m.bytes.data()+m.position,n);m.position+=n;return int(n);
    }
    static int64_t seek(void* opaque,int64_t offset,int whence){
        auto& m=*static_cast<Movie*>(opaque);if(whence==AVSEEK_SIZE)return m.bytes.size();
        whence&=~AVSEEK_FORCE;int64_t at=offset;
        if(whence==SEEK_CUR)at+=m.position;else if(whence==SEEK_END)at+=m.bytes.size();else if(whence!=SEEK_SET)return AVERROR(EINVAL);
        if(at<0 || uint64_t(at)>m.bytes.size())return AVERROR(EINVAL);m.position=size_t(at);return at;
    }
    void rewind(){av_seek_frame(format,stream,0,AVSEEK_FLAG_BACKWARD);avcodec_flush_buffers(codec);finished=false;next=SDL_GetTicks();}
    bool decode(){
        while(av_read_frame(format,packet)>=0){
            int index=packet->stream_index;
            int result=index==stream?avcodec_send_packet(codec,packet):AVERROR(EAGAIN);av_packet_unref(packet);
            if(result<0)continue;
            if(avcodec_receive_frame(codec,frame)<0)continue;
            scale=sws_getCachedContext(scale,frame->width,frame->height,AVPixelFormat(frame->format),width,height,AV_PIX_FMT_RGB565LE,SWS_BILINEAR,nullptr,nullptr,nullptr);
            if(!scale)return false;
            uint8_t* output[]={pixels.data(),nullptr,nullptr,nullptr};int strides[]={width*2,0,0,0};
            sws_scale(scale,frame->data,frame->linesize,0,frame->height,output,strides);++decoded;return true;
        }
        return false;
    }
    void readAudio(){
        int audio=av_find_best_stream(format,AVMEDIA_TYPE_AUDIO,-1,-1,nullptr,0);if(audio<0)return;
        auto* params=format->streams[audio]->codecpar;const AVCodec* decoder=avcodec_find_decoder(params->codec_id);if(!decoder)return;
        AVCodecContext* context=avcodec_alloc_context3(decoder);if(!context)return;
        SwrContext* resample=nullptr;AVChannelLayout stereo=AV_CHANNEL_LAYOUT_STEREO;
        if(avcodec_parameters_to_context(context,params)>=0 && avcodec_open2(context,decoder,nullptr)>=0 &&
           swr_alloc_set_opts2(&resample,&stereo,AV_SAMPLE_FMT_S16,44100,&context->ch_layout,context->sample_fmt,context->sample_rate,0,nullptr)>=0 && swr_init(resample)>=0){
            wave.resize(44);AVFrame* samples=av_frame_alloc();AVPacket* pkt=av_packet_alloc();
            while(av_read_frame(format,pkt)>=0 && wave.size()<24*1024*1024){
                if(pkt->stream_index==audio && avcodec_send_packet(context,pkt)>=0){
                    while(avcodec_receive_frame(context,samples)>=0){
                        int count=swr_get_out_samples(resample,samples->nb_samples);
                        std::vector<uint8_t> out(size_t(std::max(count,0))*4);uint8_t* dest=out.data();
                        int n=swr_convert(resample,&dest,count,const_cast<const uint8_t**>(samples->extended_data),samples->nb_samples);
                        if(n>0)wave.insert(wave.end(),out.begin(),out.begin()+n*4);
                    }
                }
                av_packet_unref(pkt);
            }
            av_packet_free(&pkt);av_frame_free(&samples);
            if(wave.size()>44){
                auto put=[this](int at,uint32_t value,int n){for(int i=0;i<n;++i)wave[at+i]=uint8_t(value>>(i*8));};
                memcpy(wave.data(),"RIFF",4);put(4,wave.size()-8,4);memcpy(wave.data()+8,"WAVEfmt ",8);put(16,16,4);put(20,1,2);put(22,2,2);put(24,44100,4);put(28,176400,4);put(32,4,2);put(34,16,2);memcpy(wave.data()+36,"data",4);put(40,wave.size()-44,4);
            }else wave.clear();
        }
        swr_free(&resample);avcodec_free_context(&context);av_seek_frame(format,stream,0,AVSEEK_FLAG_BACKWARD);
    }
    bool open(int number,int w,int h,bool repeat){
        id=number;loop=repeat;
        for(const char* suffix:{".smk",".bik"}){bytes=resource(std::string(g_videoDescriptors[id].m_smkStem)+suffix);if(!bytes.empty())break;}
        if(bytes.empty())return false;
        io=avio_alloc_context(static_cast<unsigned char*>(av_malloc(32768)),32768,0,this,read,nullptr,seek);
        format=avformat_alloc_context();if(!io || !format)return false;
        format->pb=io;format->flags|=AVFMT_FLAG_CUSTOM_IO;
        if(avformat_open_input(&format,nullptr,nullptr,nullptr)<0 || avformat_find_stream_info(format,nullptr)<0)return false;
        stream=av_find_best_stream(format,AVMEDIA_TYPE_VIDEO,-1,-1,nullptr,0);if(stream<0)return false;
        auto* parameters=format->streams[stream]->codecpar;
        if(parameters->width<=0 || parameters->height<=0 || parameters->width>2048 || parameters->height>2048)return false;
        width=w?w:parameters->width;height=h?h:parameters->height;if(width>2048 || height>2048)return false;
        pixels.resize(size_t(width)*height*2);
        const AVCodec* decoder=avcodec_find_decoder(parameters->codec_id);if(!decoder)return false;
        codec=avcodec_alloc_context3(decoder);
        if(!codec || avcodec_parameters_to_context(codec,parameters)<0 || avcodec_open2(codec,decoder,nullptr)<0)return false;
        double fps=av_q2d(av_guess_frame_rate(format,format->streams[stream],nullptr));if(fps>0 && fps<=120)frameMs=std::max(8,int(1000/fps));
        if(id<7 || id>26)readAudio();
        next=SDL_GetTicks();return decode();
    }
};
std::unordered_map<BINK*,std::unique_ptr<Movie>> movies;
Movie* current(){auto it=movies.find(BinkManager::g_playingBink.m_bink);return it==movies.end()?nullptr:it->second.get();}
void draw(){
    auto* m=current();auto& state=BinkManager::g_playingBink;if(!m || !g_windowManager || !g_windowManager->m_screenBitmap)return;
    auto* screen=g_windowManager->m_screenBitmap;int x=state.m_x,y=state.m_y;
    int width=std::min(m->width,screen->GetWidth()-x),height=std::min(m->height,screen->GetHeight()-y);
    // The credits scroller owns the right-hand text strip.
    if(m->id==33)width=std::min(width,460-x);
    if(m->id==35 && m->decoded>1)height=std::min(height,450-y);
    if(x<0 || y<0 || width<=0 || height<=0)return;
    for(int row=0;row<height;++row)memcpy(screen->GetMap(x,y+row),m->pixels.data()+row*m->width*2,width*2);
    g_windowManager->updateScreen(x,y,width,height);BinkManager::g_needsUpdate=true;
#ifdef __EMSCRIPTEN__
    EM_ASM({window.homm3VideoState=({id:$0,frames:$1,width:$2,height:$3,playing:!!$4});},m->id,m->decoded,m->width,m->height,!m->finished);
#endif
}
}
namespace BinkManager {
void closeBink(){
    auto* m=current();if(m && m->sound)Port::Sfx::stop(audioSlot);
    movies.erase(g_playingBink.m_bink);g_playingBink={};SmackManager::g_playingSmack={};g_needsUpdate=false;
}
void restartBink(){if(auto* m=current()){m->rewind();m->decode();draw();if(m->sound)Port::Sfx::restart(audioSlot);}}
void drawCurrentBinkFrame(){draw();}
void nextBinkFrame(){
    auto* m=current();g_needsUpdate=false;if(!m || m->paused || m->finished)return;
    uint32_t now=SDL_GetTicks();if(int32_t(now-m->next)<0)return;
    m->next=now+m->frameMs;
    if(!m->decode()){
        if(m->loop){m->rewind();if(!m->decode())m->finished=true;}
        else m->finished=true;
        if(m->finished){SmackManager::g_playingSmack.m_smack=nullptr;if(m->sound)Port::Sfx::stop(audioSlot);}
    }
    if(!m->finished)draw();
}
}
extern "C" int BinkPause(BINK* handle,int paused){
    auto it=movies.find(handle);if(it==movies.end())return 0;
    auto& m=*it->second;int old=m.paused;m.paused=paused!=0;m.next=SDL_GetTicks()+m.frameMs;
    if(m.sound){if(paused)Port::Sfx::pause(audioSlot);else Port::Sfx::resume(audioSlot);}return old;
}
bool videoPlaying(){auto* m=current();return m && !m->finished;}
bool videoNeedsUpdate(){return BinkManager::g_needsUpdate;}
void videoDrawCurrentFrame(){auto* m=current();if(m && !m->paused)draw();}
void videoDrawRects(){videoDrawCurrentFrame();}
void videoPause(){if(++pauseDepth==1){BinkManager::g_playingBink.m_paused=1;BinkPause(BinkManager::g_playingBink.m_bink,1);}}
void videoResume(){if(pauseDepth && --pauseDepth==0){BinkManager::g_playingBink.m_paused=0;BinkPause(BinkManager::g_playingBink.m_bink,0);}}
void videoRestart(){BinkManager::restartBink();}
void videoNextFrame(){BinkManager::nextBinkFrame();}
void videoClose(){BinkManager::closeBink();pauseDepth=0;
#ifdef __EMSCRIPTEN__
 EM_ASM({if(window.homm3VideoState)window.homm3VideoState.playing=false;});
#endif
}
void videoOpen(int id,int x,int y,int w,int h,int loop,bool,bool){
    videoClose();if(id<0 || id>=141)return;
    auto movie=std::unique_ptr<Movie>(new Movie);
    if(!movie->open(id,w,h,loop!=0)){fprintf(stderr,"Video unavailable: %s\n",g_videoDescriptors[id].m_smkStem);return;}
    auto* key=reinterpret_cast<BINK*>(movie.get());
    auto& state=BinkManager::g_playingBink;state={};state.m_bink=key;state.m_x=x;state.m_y=y;state.m_w=movie->width;state.m_h=movie->height;state.m_id=id;state.m_loop=loop;
    if(id<7 || id>26)SmackManager::g_playingSmack.m_smack=reinterpret_cast<Smack*>(movie.get());
    if(!movie->wave.empty())movie->sound=Port::Sfx::play(audioSlot,g_videoDescriptors[id].m_smkStem,movie->wave.data(),movie->wave.size(),loop?0:1,std::max(0,std::min(127,g_config.m_soundVolume*127/10)));
    movies.emplace(key,std::move(movie));draw();
}
int videoPlay(int id,int x,int y,int w,int h){
    videoOpen(id,x,y,w,h,0,false,true);g_inputManager->flush();bool completed=true;
    while(videoPlaying()){
        process1WindowsMessage();message msg=g_inputManager->getEvent();
        if(msg.m_id==MESSAGE_KEY_DOWN || msg.m_id==MESSAGE_LEFT_BUTTON_DOWN || msg.m_id==MESSAGE_RIGHT_BUTTON_DOWN){completed=false;break;}
    }
    videoClose();return completed;
}
void openSmackerVideo(int id,int x,int y,int w,int h,int loop,bool a,bool b){videoOpen(id,x,y,w,h,loop,a,b);}
void deleteAnimHeaders(){}
namespace SmackManager {
void closeSmacker(){videoClose();}
void drawSmackerFrame(){videoNextFrame();}
void gotoSmackerFrame(unsigned long frame){if(auto* m=current()){m->rewind();for(unsigned long i=0;i<=frame && i<10000;++i)if(!m->decode())break;draw();}}
}
