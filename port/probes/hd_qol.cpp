#include "hd_recruit.h"
#include <cassert>
#include <cstdio>
#include <climits>
using namespace Port::HD;
static armyGroup army(int type,int n){armyGroup a;a.m_armies[0]=type;a.m_numTroops[0]=n;return a;}
int main(){
    auto a=army(0,10);assert(armyAction(a,0,Single));assert(a.m_numTroops[0]==9 && a.m_numTroops[1]==1);
    assert(armyAction(a,0,Singles));assert(a.getNumArmies()==7 && a.getCreatureTotal()==10 && a.m_numTroops[0]==4);
    assert(!armyAction(a,0,Singles));assert(armyAction(a,0,Gather));assert(a.getNumArmies()==1 && a.m_numTroops[0]==10);
    armyAction(a,0,Single);armyAction(a,0,Balance);assert(a.m_numTroops[1]==1 && a.m_numTroops[0]==5 && a.m_numTroops[2]==4);
    armyAction(a,0,Balance);assert(a.m_numTroops[0]==3 && a.m_numTroops[1]==1 && a.m_numTroops[2]==3 && a.m_numTroops[3]==3);
    auto b=army(1,7);assert(armyAction(a,0,TransferAll,&b,true));assert(a.getCreatureTotal()==1 && a.m_armies[0]==0 && b.getCreatureTotal()==16);
    assert(!armyAction(a,0,Transfer,&b,true));assert(armyAction(a,0,Transfer,&b,false));assert(!a.hasCreatures() && b.getCreatureTotal()==17);
    a=army(0,50);for(int i=0;i<7;++i){b.m_armies[i]=i+1;b.m_numTroops[i]=1;}
    assert(!armyAction(a,0,Transfer,&b,true));assert(a.getCreatureTotal()==50);
    b.m_armies[0]=0;b.m_numTroops[0]=INT_MAX;assert(!armyAction(a,0,Transfer,&b,true));
    a=army(0,1);assert(!armyAction(a,0,Single));assert(!armyAction(a,-1,Gather));assert(!armyAction(a,7,Gather));
    std::array<RecruitOffer,7> offers;offers[0].creature=0;offers[0].available=20;offers[0].cost[6]=10;
    offers[6].creature=12;offers[6].available=4;offers[6].cost[6]=100;offers[6].cost[5]=2;
    long resources[]={0,0,0,0,0,5,350};auto plan=planRecruitment(a,resources,offers);
    assert(plan.counts[6]==2 && plan.counts[0]==15 && plan.remaining[6]==0 && plan.remaining[5]==1);
    assert(resources[6]==350 && a.getCreatureTotal()==1); // Preview never spends anything.
    for(int i=0;i<7;++i){a.m_armies[i]=i;a.m_numTroops[i]=1;}
    plan=planRecruitment(a,resources,offers);assert(plan.counts[6]==0 && plan.counts[0]==20);
    resources[6]=0;plan=planRecruitment(a,resources,offers);assert(plan.total==0);
    offers[0].cost[6]=0;plan=planRecruitment(a,resources,offers);assert(plan.counts[0]==20 && plan.remaining[6]==0);
    assert(actionForModifiers(true,true,false)==Singles && actionForModifiers(true,true,true)==TransferAll);
    puts("{\"passed\":true,\"checks\":[\"single/fill/gather/balance\",\"keep last creature\",\"full destination\",\"overflow\",\"shared recruitment budget\",\"population/slot limits\",\"free creatures\",\"non-mutating preview\"]}");
}
