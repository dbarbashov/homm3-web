// Progress frames must replace prior text and restore the covered game panel.
#include "../platform/sdl_backend.h"
#include "bitmap16.h"
#include "remotedlg.h"
#include "resourcemanager.h"
#include "winmgr.h"
#include "font.h"
#include "textresource.h"
#include "kb.h"
#include <cstdio>
#include <stdexcept>
#include <vector>
#include <unistd.h>
extern Bitmap16Bit g_initWin;
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
int main(int argc,char** argv){
    try {
        require(argc==2 && chdir(argv[1])==0,"runtime directory");initMainClasses();
        ResourceManager::SetPath("data/");ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
        int error=0;require(ResourceManager::Open(true,true,&error),"original resources");
        require(Port::openDisplay(),"SDL display");
        g_generalText=ResourceManager::GetText("genrltxt.txt");g_mediumFont=ResourceManager::GetFont("medfont.fnt");
        g_windowManager->m_screenBitmap=&g_initWin;
        g_initWin.FillRect(0,0,800,600,0x5ad6);
        {
            CGameTransferSmack panel;panel.setup(620,400,1,1);panel.saveScreen();panel.setPercentage(.75f);
            std::vector<unsigned short> expected;
            for(int y=400;y<560;++y)for(int x=620;x<780;++x)expected.push_back(*g_initWin.GetMap(x,y));
            panel.setPercentage(.25f);panel.setPercentage(.75f);
            unsigned i=0;for(int y=400;y<560;++y)for(int x=620;x<780;++x)require(*g_initWin.GetMap(x,y)==expected[i++],"progress text accumulates");
            require(*g_initWin.GetMap(625,405)!=0x5ad6,"underlying player panel shows through");
            require(*g_initWin.GetMap(619,400)==0x5ad6,"progress paints outside its panel");
            panel.restoreScreen();
            for(int y=400;y<560;++y)for(int x=620;x<780;++x)require(*g_initWin.GetMap(x,y)==0x5ad6,"covered panel not restored");
        }
        Port::closeDisplay();puts("{\"passed\":true,\"opaqueBackground\":true,\"noAccumulatedText\":true,\"restoresCoveredPanel\":true}");return 0;
    }catch(const std::exception& e){fprintf(stderr,"Transfer panel regression: %s\n",e.what());return 1;}
}
