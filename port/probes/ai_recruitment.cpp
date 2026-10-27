// Regress the AI's real valuation and recruitment paths for free and paid stacks.
#include "game.h"
#include "ai_player.h"
#include "creaturetype.h"
#include "recruit.h"
#include "resourcemanager.h"
#include "kb.h"
#include <cstdio>
#include <stdexcept>
#include <unistd.h>
bool portableLoadGameData();
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
int main(int argc,char** argv){
    try {
        require(argc==2 && chdir(argv[1])==0,"runtime directory");
        initMainClasses();
        ResourceManager::SetPath("data/");ResourceManager::SetPixelFormat(0xf800,0x07e0,0x001f);
        int error=0;require(ResourceManager::Open(true,true,&error),"original resources");
        require(portableLoadGameData(),"game tables");
        for(bool free: {true,false}){
            const TCreatureType type=CREATURE_PIKEMAN;
            armyGroup army;army.add(type,1,-1);
            short available=14;
            int price[NUM_RESOURCES];getMonsterCost(type,price);
            long funds[NUM_RESOURCES];
            for(int i=0;i<NUM_RESOURCES;++i)funds[i]=free?0:price[i]*3;
            type_AI_creature_purchaser estimate(0,type,&available,free);
            require(estimate.getPurchaseValue(&army,0,nullptr,funds,0)>0,"positive recruit value");
            require(available==14 && army.getCreatureTotal()==1,"valuation changed real army/population");
            for(int i=0;i<NUM_RESOURCES;++i)require(funds[i]==(free?0:price[i]*3),"valuation spent funds");
            type_AI_creature_purchaser purchase(0,type,&available,free);
            purchase.doPurchase(&army,0,nullptr,funds,false,0);
            require(available==(free?0:11),"wrong remaining population");
            require(army.getCreatureTotal()==(free?15:4),"wrong recruited quantity");
            for(int i=0;i<NUM_RESOURCES;++i)require(funds[i]==0,"wrong purchase cost");
            type_AI_creature_purchaser exhausted(0,type,&available,free);
            require(exhausted.getPurchaseValue(&army,0,nullptr,funds,0)==0,"exhausted offer remains valuable");
        }
        puts("{\"passed\":true,\"freeRecruitment\":true,\"paidRecruitment\":true,\"valuationPreservesState\":true}");
        return 0;
    }catch(const std::exception& e){fprintf(stderr,"AI recruitment regression: %s\n",e.what());return 1;}
}
