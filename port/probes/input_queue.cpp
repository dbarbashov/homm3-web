#include "inputmgr.h"
#include "winmgr.h"
#include "kbwin.h"
#include <SDL.h>
#include <cassert>
#include <cstdio>

static void move(int x,int y=20){mouseMessageHandler(nullptr,WM_MOUSEMOVE,0,(y<<16)|x);}
static int count(){return (g_inputManager->m_tail-g_inputManager->m_head+64)%64;}
static message& at(int n){return g_inputManager->m_buffer[(g_inputManager->m_head+n)%64];}
static void reset(int offset=0){g_inputManager->m_head=g_inputManager->m_tail=offset;}
int main(){
    SDL_Init(SDL_INIT_EVENTS);
    g_inputManager=new inputManager;g_inputManager->open(1);
    g_windowManager=new heroWindowManager;
    for(int offset:{0,62,63}){
        reset(offset);
        for(int i=0;i<1000;++i)move(i);
        assert(count()==1 && at(0).m_id==MESSAGE_MOUSE_MOVE && at(0).m_mouseX==999);
        // A mouse press/release cannot disappear behind later motion.
        mouseMessageHandler(nullptr,WM_LBUTTONDOWN,0,(20<<16)|999);
        for(int i=0;i<1000;++i)move(i);
        mouseMessageHandler(nullptr,WM_LBUTTONUP,0,(20<<16)|999);
        move(10);
        assert(count()==5);
        assert(at(1).m_id==MESSAGE_LEFT_BUTTON_DOWN && at(3).m_id==MESSAGE_LEFT_BUTTON_UP);
        assert(at(0).m_mouseX==999 && at(2).m_mouseX==999 && at(4).m_mouseX==10);
        // Keys and modifier changes delimit motion, including drag modifiers.
        reset(offset);move(1);
        keyboardMessageHandler(nullptr,WM_KEYDOWN,0,30<<16);move(2);
        keyboardMessageHandler(nullptr,WM_KEYUP,0,30<<16);move(3);
        assert(count()==5 && at(1).m_id==MESSAGE_KEY_DOWN && at(3).m_id==MESSAGE_KEY_UP);
        SDL_SetModState(KMOD_SHIFT);move(4);move(5);SDL_SetModState(KMOD_NONE);move(6);
        assert(count()==7 && at(4).m_mouseX==3 && at(5).m_mouseX==5 && at(6).m_mouseX==6);
        assert(at(5).m_qualifier!=at(6).m_qualifier);
        reset(offset);move(10);g_inputManager->m_head=g_inputManager->m_tail;move(20);
        assert(count()==1 && at(0).m_mouseX==20);
    }
    puts("{\"passed\":true,\"checks\":[\"1000 motions retain latest position\",\"mouse press/release boundaries\",\"key boundaries\",\"modifier boundaries\",\"ring wrap and consumed queue\"]}");
    SDL_Quit();
}
