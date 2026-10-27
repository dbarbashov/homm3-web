// Integration check: actual recovered LOD, bitmap, DEF and FNT code.
#include "lodfile.h"
#include "resourcemanager.h"
#include "resourcemanager_sprite_headers.h"
#include "resourcemanager_archive.h"
#include "bitmap16.h"
#include "csprite.h"
#include "font.h"
#include "font_disk.h"
#include <cstdio>
static_assert(sizeof(LODHeader)==92,"LOD header disk layout");
static_assert(sizeof(LODEntry)==32,"LOD directory disk layout");
static_assert(sizeof(SpriteDefHeader)==784,"DEF header disk layout");
static_assert(sizeof(TCroppedSpriteFrameHeader)==32,"DEF frame disk layout");
static_assert(sizeof(TBitmapResourceHeader)==12,"bitmap header disk layout");
static unsigned hashFrame(Bitmap16Bit& screen,unsigned hash=2166136261u){
    auto* bytes=reinterpret_cast<const unsigned char*>(screen.GetMap(0,0));
    for(int i=0;i<screen.GetPitch()*screen.GetHeight();++i)hash=(hash^bytes[i])*16777619u;
    return hash;
}
int main(int argc,char** argv){
    if(argc<2){fprintf(stderr,"Usage: resource-probe DATA_DIRECTORY/\n");return 2;}
    ResourceManager::SetPath(argv[1]);ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
    int error=-1;if(!ResourceManager::Open(true,true,&error)){fprintf(stderr,"Archive open failed: %d\n",error);return 3;}
    Bitmap16Bit screen(800,600);
    printf("{\"checks\":[");bool first=true;
    auto result=[&](const char* name,int frames,unsigned hash){if(!first)printf(",");first=false;printf("{\"asset\":\"%s\",\"frames\":%d,\"fnv1a\":\"%08x\"}",name,frames,hash);};
    for(const char* name:{"mainmenu.pcx","GamSelBk.pcx"}){
        auto* bitmap=ResourceManager::GetBitmap16(name);if(!bitmap)return 4;
        screen.FillRect(0,0,800,600,0);
        bitmap->Draw(0,0,bitmap->GetWidth(),bitmap->GetHeight(),&screen,0,0,false);
        result(name,1,hashFrame(screen));ResourceManager::Dispose(bitmap);
    }
    for(const char* name:{"mmenung.def","mmenulg.def","mmenuhs.def","mmenucr.def","mmenuqt.def","crdeflt.def","cangel.def","Cpixie.def","DIRTTL.def","GRASTL.def","AVA0001.def"}){
        auto* sprite=ResourceManager::GetSprite(name);if(!sprite)return 4;
        unsigned hash=2166136261u;int frames=0;
        for(int sequence=0;sequence<22;++sequence)for(int frame=0;frame<sprite->GetNumFrames(sequence);++frame){
            screen.FillRect(0,0,800,600,0x1082);
            sprite->Draw(sequence,frame,0,0,sprite->GetWidth(),sprite->GetHeight(),&screen,8,8,false,true);
            hash=hashFrame(screen,hash);++frames;
        }
        result(name,frames,hash);ResourceManager::Dispose(sprite);
    }
    for(const char* name:{"BIGFONT.FNT","CALLI10R.FNT","CREDITS.FNT","HISCORE.FNT","MEDFONT.FNT","SMALFONT.FNT","TIMES08R.FNT","TINY.FNT","VERD10B.FNT"}){
        auto* face=ResourceManager::GetFont(name);if(!face)return 4;
        screen.FillRect(0,0,800,600,0);
        face->DrawBoundedString("Heroes III 0123456789 / \xC3\xE5\xF0\xEE\xE8",&screen,10,10,780,580,font::WHITE,font::LEFT_JUSTIFIED,-1);
        result(name,1,hashFrame(screen));ResourceManager::Dispose(face);
    }
    printf("]}\n");ResourceManager::Close();return 0;
}
