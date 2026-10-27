#pragma once
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace Port {
// Opt-in, bounded timing markers. The probe creates the array before startup.
inline void traceCombat(const char* phase,int side,int slot){
#ifdef __EMSCRIPTEN__
    EM_ASM({const events=window.homm3CombatTrace;if(Array.isArray(events)){events.push({phase:UTF8ToString($0),side:$1,slot:$2,at:performance.now()});if(events.length>256)events.shift();}},phase,side,slot);
#else
    (void)phase;(void)side;(void)slot;
#endif
}
}
