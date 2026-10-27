#pragma once
#include "armygrp.h"
#include <algorithm>
#include <climits>

// HD-style operations on the original army storage. No UI or network state.
namespace Port { namespace HD {
enum ArmyAction { None, Single, Singles, Balance, Gather, Transfer, TransferAll };
inline int emptySlot(const armyGroup& a) {
    for(int i=0;i<7;++i)if(a.m_armies[i]<0 || a.m_numTroops[i]<=0)return i;
    return -1;
}
inline int destination(const armyGroup& a,int type) {
    for(int i=0;i<7;++i)if(a.m_armies[i]==type)return i;
    return emptySlot(a);
}
inline bool moveStack(armyGroup& from,int slot,armyGroup& to,bool keepOne) {
    if(&from==&to || slot<0 || slot>=7 || from.m_armies[slot]<0)return false;
    int dest=destination(to,from.m_armies[slot]);if(dest<0)return false;
    int retain=keepOne && from.getNumArmies()==1 ? 1:0;
    int count=from.m_numTroops[slot]-retain;
    if(count<=0 || to.m_numTroops[dest]>INT_MAX-count)return false;
    to.m_armies[dest]=from.m_armies[slot];to.m_numTroops[dest]+=count;
    from.m_numTroops[slot]=retain;if(!retain)from.m_armies[slot]=CREATURE_NONE;
    return true;
}
inline bool armyAction(armyGroup& a,int slot,ArmyAction action,armyGroup* other=nullptr,bool keepOne=true) {
    if(slot<0 || slot>=7 || a.m_armies[slot]<0 || a.m_numTroops[slot]<=0)return false;
    const int type=a.m_armies[slot];bool changed=false;
    if(action==Transfer)return other && moveStack(a,slot,*other,keepOne);
    if(action==TransferAll){
        if(!other || other==&a)return false;
        // Transfer the clicked stack last so its creature is retained on a hero.
        for(int i=0;i<7;++i)if(i!=slot)changed=moveStack(a,i,*other,keepOne)||changed;
        return moveStack(a,slot,*other,keepOne)||changed;
    }
    if(action==Single || action==Singles){
        do {int dest=emptySlot(a);if(dest<0 || a.m_numTroops[slot]<2)break;
            a.m_armies[dest]=type;a.m_numTroops[dest]=1;--a.m_numTroops[slot];changed=true;
        }while(action==Singles);
        return changed;
    }
    if(action==Gather){
        long long total=0;for(int i=0;i<7;++i)if(a.m_armies[i]==type)total+=a.m_numTroops[i];
        if(total>INT_MAX)return false;
        for(int i=0;i<7;++i)if(i!=slot && a.m_armies[i]==type){a.m_armies[i]=CREATURE_NONE;a.m_numTroops[i]=0;changed=true;}
        a.m_numTroops[slot]=int(total);return changed;
    }
    if(action==Balance){
        int dest=emptySlot(a);if(dest<0 || a.m_numTroops[slot]<2)return false;
        // Add one balanced stack; preserve deliberate single-unit blockers.
        int slots[7],n=0;long long total=0;
        for(int i=0;i<7;++i)if(a.m_armies[i]==type && a.m_numTroops[i]>1){slots[n++]=i;total+=a.m_numTroops[i];}
        slots[n++]=dest;
        for(int k=0;k<n;++k){a.m_armies[slots[k]]=type;a.m_numTroops[slots[k]]=int(total/n+(k<total%n));}
        return true;
    }
    return false;
}
inline ArmyAction actionForModifiers(bool ctrl,bool shift,bool alt) {
    if(ctrl&&alt)return shift?TransferAll:Transfer;
    if(ctrl)return shift?Singles:Single;
    if(alt&&!shift)return Gather;
    if(shift&&!alt)return Balance;
    return None;
}
// UI adapter is shared by hero, town, garrison and exchange handlers.
bool quickArmy(armyGroup& army,int slot,armyGroup* other,bool keepOne,bool selected);
} }
