#pragma once
struct message;
class armyGroup;
namespace Port { namespace Fast {
// Inline storage keeps guards available to the separately linked menu target.
struct State { bool active=false; bool running=false; bool drawing=false; bool ready=false; bool waiting=false; bool halted=false; };
inline State& state(){ static State value; return value; }
inline bool enabled(){return state().active;}
inline bool executing(){return state().active && state().running;}
inline bool blocksInput(){return executing() || (enabled() && (state().waiting || state().halted));}
inline bool nativeUI(){return enabled() && !executing();}
bool request(int op,int id=0,int a=0,int b=0);
void tick();
void unavailable();
const char* waitingText();
void readOnlyView(bool enter);
struct ReadOnly { bool active; explicit ReadOnly(bool value):active(value){if(active)readOnlyView(true);} ~ReadOnly(){if(active)readOnlyView(false);} };
bool requestRecruit(armyGroup* army,short* available,int creature,int count);
void begin();
int adventureMain(message& msg);
} }
