// Exercise actual recovered game construction and map loading outside the UI.
#include "game.h"
#include "gzfile.h"
#include "findpath.h"
#include "resourcemanager.h"
#include "kb.h"
#include <cstdio>
#include <memory>
bool portableLoadGameData();
int main(int argc,char** argv){
    try {
        setvbuf(stdout,nullptr,_IONBF,0);
        initMainClasses();
        auto current=std::unique_ptr<game>(g_game);
        std::printf("game constructed: %zu bytes\n",sizeof(game));
        if(argc>2){
            ResourceManager::SetPath(argv[1]);
            ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
            int error=0;
            if(!ResourceManager::Open(true,true,&error))return 3;
            if(!portableLoadGameData())return 4;

            current->m_worldMap.loadObjectTypeTemplates();
            TGzFile file(argv[2],"rb");
            bool result=current->loadMap(&file);
            std::printf("mapLoaded=%d size=%d layers=%d\n",result,current->m_mapHeader.m_size,current->m_mapHeader.m_hasTwoLayers);
            if(!result || current->m_mapHeader.m_size<=0)return 5;
        }
        return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
