#include "prefs.h"
#include "misc.h"
#include <cstdio>
#include <stdexcept>
#include <unistd.h>
void readPrefs();
int main(int argc,char** argv){
    if(argc!=3 || chdir(argv[1]))return 2;
    readPrefs();
    if(std::string(argv[2])=="write"){
        g_config.m_musicVolume=7;g_config.m_soundVolume=3;
        g_config.m_walkSpeed[1]=4;g_config.m_walkSpeed[0]=5;
        g_config.m_combatSpeed=2;g_config.m_showCombatGrid=1;g_config.m_showRoute=0;writePrefs();
    }else if(std::string(argv[2])=="read"){
        if(g_config.m_musicVolume!=7 || g_config.m_soundVolume!=3 || g_config.m_walkSpeed[1]!=4 || g_config.m_walkSpeed[0]!=5 || g_config.m_combatSpeed!=2 || g_config.m_showCombatGrid!=1 || g_config.m_showRoute!=0)return 1;
    }else if(std::string(argv[2])=="write-slow"){
        g_config.m_combatSpeed=0;writePrefs();
    }else if(std::string(argv[2])=="read-slow"){
        if(g_config.m_combatSpeed!=0)return 1;
    }else if(g_config.m_musicVolume!=5 || g_config.m_soundVolume!=5 || g_config.m_combatSpeed!=2)return 1;
    puts("{\"passed\":true}");
}
