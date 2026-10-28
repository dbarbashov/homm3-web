#pragma once
struct message;
namespace Port { namespace Fast {
// Inline storage keeps guards available to the separately linked menu target.
struct State { bool active=false; bool running=false; };
inline State& state(){ static State value; return value; }
inline bool enabled(){return state().active;}
inline bool executing(){return state().active && state().running;}
inline bool blocksInput(){return enabled();}
void begin();
int adventureMain(message& msg);
} }
