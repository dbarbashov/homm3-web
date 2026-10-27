#include "hd_army.h"
#include "windows.h"
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace Port { namespace HD {
bool quickArmy(armyGroup& army,int slot,armyGroup* other,bool keepOne,bool selected) {
    bool ctrl=GetKeyState(VK_CONTROL)<0,shift=GetKeyState(VK_SHIFT)<0,alt=GetKeyState(VK_MENU)<0;
    ArmyAction action=actionForModifiers(ctrl,shift,alt);
    bool touchAction=false;
#ifdef __EMSCRIPTEN__
    int touch=EM_ASM_INT({return window.homm3ArmyAction||0;});
    if(touch>=Single && touch<=TransferAll){action=static_cast<ArmyAction>(touch);touchAction=true;}
#endif
    // Preserve the original select-stack, Shift-click-destination split dialog.
    if(action==None || (selected && action==Balance && !ctrl && !alt && !touchAction))return false;
    armyAction(army,slot,action,other,keepOne);
    return true; // A full army/no compatible destination is a handled no-op.
}
} }
#include "hd_recruit.h"
#include "game.h"
#include "town.h"
#include "recruit.h"
#include "creaturetype.h"
#include "kb.h"
#include "remote.h"
#include "exec.h"
#include "winmgr.h"
#include "textresource.h"
#include <sstream>
namespace Port { namespace HD {
// The original Russian bitmap fonts accept Windows-1251, not UTF-8.
// {Найм войск}
static const char recruitTitle[] =
    "{\xcd\xe0\xe9\xec \xe2\xee\xe9\xf1\xea}\n\n";
// Нет доступных для найма существ. Проверьте прирост, ресурсы и свободные места в гарнизоне.
static const char recruitUnavailable[] =
    "\xcd\xe5\xf2 \xe4\xee\xf1\xf2\xf3\xef\xed\xfb\xf5 \xe4\xeb\xff \xed\xe0\xe9\xec\xe0 \xf1\xf3\xf9\xe5\xf1\xf2\xe2. \xcf\xf0\xee\xe2\xe5\xf0\xfc\xf2\xe5 \xef\xf0\xe8\xf0\xee\xf1\xf2, \xf0\xe5\xf1\xf3\xf0\xf1\xfb \xe8 \xf1\xe2\xee\xe1\xee\xe4\xed\xfb\xe5 \xec\xe5\xf1\xf2\xe0 \xe2 \xe3\xe0\xf0\xed\xe8\xe7\xee\xed\xe5.";
// Сначала нанимаются сильнейшие существа. / Нанять войска в гарнизон города?
static const char recruitConfirm[] =
    "\n\n\xd1\xed\xe0\xf7\xe0\xeb\xe0 \xed\xe0\xed\xe8\xec\xe0\xfe\xf2\xf1\xff \xf1\xe8\xeb\xfc\xed\xe5\xe9\xf8\xe8\xe5 \xf1\xf3\xf9\xe5\xf1\xf2\xe2\xe0.\n\xcd\xe0\xed\xff\xf2\xfc \xe2\xee\xe9\xf1\xea\xe0 \xe2 \xe3\xe0\xf0\xed\xe8\xe7\xee\xed \xe3\xee\xf0\xee\xe4\xe0?";

static int dwelling(town* target,int level) {
    if(target->hasBuilding(DWELLING_0_UPG_ID+level,false))return level+7;
    if(target->hasBuilding(DWELLING_0_ID+level,false))return level;
    return -1;
}
void recruitLevel(town* target,int level) {
    if(!target || level<0 || level>=7)return;
    int index=dwelling(target,level);if(index<0)return;
    recruitUnit unit(target,index,1);g_executive->doDialog(&unit);
}
void recruitAll(town* target,bool baseCreatures,bool skipConfirmation) {
    if(!target || !g_currentPlayer->isLocalHuman() || target->m_owner!=g_netLocalGamePos)return;
    std::array<RecruitOffer,7> offers;
    for(int i=0;i<7;++i){int index=dwelling(target,i);if(index<0)continue;
        offers[i].creature=g_dwellingType[target->m_type][baseCreatures?i:index];
        offers[i].available=target->m_population[index];offers[i].populationSlot=index;
        getMonsterCost(offers[i].creature,offers[i].cost.data());
    }
    auto plan=planRecruitment(target->getArmy(),g_currentPlayer->m_resources,offers);
    if(!plan.total){normalDialog(recruitUnavailable,1,-1,-1,-1,0,-1,0,-1,0,-1,0);return;}
    std::ostringstream text;text<<recruitTitle;
    for(int i=6;i>=0;--i)if(plan.counts[i])text<<plan.counts[i]<<" "<<getArmyName(offers[i].creature,plan.counts[i])<<"\n";
    text<<"\n"<<g_generalText->GetText(GENERAL_TEXT_TOTAL_COST)<<" ";for(int r=0;r<7;++r)if(plan.spent[r])text<<g_generalText->GetText(GENERAL_TEXT_VIEW_WORLD_WOOD+r)<<" "<<plan.spent[r]<<"  ";
    text<<recruitConfirm;
    if(!skipConfirmation) { normalDialog(text.str().c_str(),2,-1,-1,-1,0,-1,0,-1,0,-1,0); if(g_windowManager->m_dialogReturn!=DIALOG_RETURN_ACCEPT)return; }
    // Revalidate after a modal/network pump; never apply a stale budget or army.
    auto current=planRecruitment(target->getArmy(),g_currentPlayer->m_resources,offers);
    for(int i=0;i<7;++i)if(current.counts[i]!=plan.counts[i] || (offers[i].creature>=0 && target->m_population[offers[i].populationSlot]!=offers[i].available))return;
    if(!g_currentPlayer->isLocalHuman() || target->m_owner!=g_netLocalGamePos)return;
    target->getArmy()=current.army;
    std::copy(current.remaining.begin(),current.remaining.end(),g_currentPlayer->m_resources);
    for(int i=0;i<7;++i)if(current.counts[i])target->m_population[offers[i].populationSlot]-=current.counts[i];
}
} }
