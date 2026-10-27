#pragma once
#include "hd_army.h"
#include <array>
class town;
namespace Port { namespace HD {
struct RecruitOffer { int creature=-1, available=0, populationSlot=0; std::array<int,7> cost{}; };
struct RecruitPlan {
    armyGroup army;
    std::array<long,7> remaining{}, spent{};
    std::array<int,7> counts{};
    int total=0;
};
inline RecruitPlan planRecruitment(const armyGroup& army,const long* resources,const std::array<RecruitOffer,7>& offers) {
    RecruitPlan plan;plan.army=army;std::copy(resources,resources+7,plan.remaining.begin());
    // Strongest creatures first; every offer shares one budget and seven slots.
    for(int i=6;i>=0;--i){const auto& offer=offers[i];
        if(offer.creature<0 || offer.available<=0)continue;
        int dest=destination(plan.army,offer.creature);if(dest<0)continue;
        int count=std::min(offer.available,INT_MAX-plan.army.m_numTroops[dest]);
        for(int r=0;r<7;++r)if(offer.cost[r]>0)count=std::min<long>(count,std::max(0L,plan.remaining[r])/offer.cost[r]);
        if(count<=0)continue;
        plan.army.m_armies[dest]=offer.creature;plan.army.m_numTroops[dest]+=count;
        for(int r=0;r<7;++r){long cost=long(count)*offer.cost[r];plan.remaining[r]-=cost;plan.spent[r]+=cost;}
        plan.counts[i]=count;plan.total+=count;
    }
    return plan;
}
void recruitAll(town* target,bool baseCreatures,bool skipConfirmation);
void recruitLevel(town* target,int level);
} }
