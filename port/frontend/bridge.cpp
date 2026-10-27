#include "frontend_bridge.h"
#include "../platform/sdl_backend.h"
#include "bitmap16.h"
#include "wingraph.h"
#include "winmgr.h"
#include "window.h"
#include "widget.h"
#include "message.h"
#include "inputmgr.h"
#ifdef HOMM3_FULL_GAME
#include "advmgr.h"
#endif
#include <vector>
#include <cstdio>
#include <cstring>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace {
struct Context {heroWindow* window;int (*handler)(message&);const char* screen;bool ready;};
std::vector<Context> dialogs;
bool loadMode=false;
void publishState(const Context& context){
    int highlighted=-1;
    for(widget* w=context.window->m_headWidget;w;w=w->m_nextWidget)
        if(w->m_status&widget::WIDGET_HIGHLIGHTED)highlighted=w->m_id;
#ifdef __EMSCRIPTEN__
    unsigned hash=Port::frameHash();
    EM_ASM({if(window.homm3PortDiagnostics){window.homm3PortDiagnostics.hovered=$0;window.homm3PortDiagnostics.framebufferFNV1a=($1>>>0).toString(16).padStart(8,'0');}},highlighted,hash);
#endif
}
int dispatch(message& msg){
    Context context=dialogs.back();
    if(!context.ready){
        dialogs.back().ready=true;
        Port::present();
        // doDialog has now flushed input. Re-evaluate the stationary pointer
        // through the original handler when a menu is reopened with a hotkey.
        g_inputManager->forceMouseMove();
        Port::notifyScreen(context.screen);
    }
    if(Port::shouldQuit()){
        msg.m_id=MESSAGE_WIDGET;msg.m_codeX=widget::WIDGET_END_DIALOG;
        g_windowManager->m_dialogReturn=-1;
        return MESSAGE_DISPATCH_FORWARD;
    }
    const bool changed=msg.m_id!=MESSAGE_NONE || !context.ready;
    int result=context.handler(msg); // The original menu handler owns hover and commands.
    if(changed)publishState(context);
    if(result==MESSAGE_DISPATCH_FORWARD && msg.m_id==MESSAGE_WIDGET && msg.m_codeX==widget::WIDGET_END_DIALOG)
        Port::announceCommand(g_windowManager->m_dialogReturn,context.screen);
    return result;
}
}
namespace Port {
unsigned frameHash(){
    unsigned h=2166136261u;const auto* p=reinterpret_cast<const unsigned char*>(g_initWin.GetMap(0,0));
    for(int i=0;i<g_initWin.GetPitch()*g_initWin.GetHeight();++i)h=(h^p[i])*16777619u;return h;
}
void notifySnapshot(const char* screen){
    printf("{\"ready\":true,\"engine\":\"homm3-decomp-cpp\",\"screen\":\"%s\",\"framebufferFNV1a\":\"%08x\"}\n",screen,frameHash());fflush(stdout);
}
void notifyScreen(const char* screen){
    notifySnapshot(screen);
#ifdef __EMSCRIPTEN__
    const unsigned hash=frameHash();
    EM_ASM({
        var d=window.homm3PortDiagnostics;
        if(!d)d=window.homm3PortDiagnostics=({ready:true,engine:'homm3-decomp-cpp',commands:[],transitions:[]});
        d.screen=UTF8ToString($0);d.hovered=-1;d.framebufferFNV1a=($1>>>0).toString(16).padStart(8,'0');
        d.transitions.push(d.screen);
        window.dispatchEvent(new Event('homm3-ready'));
    },screen,hash);
#endif
}
void setGameTypeMode(bool load){loadMode=load;}
int runDialog(heroWindow* window,int (*handler)(message&),int fade,const char* screen){
    if(!strcmp(screen,"game-type"))screen=loadMode?"load":"new";
    dialogs.push_back({window,handler,screen,false});
    try{g_windowManager->doDialog(window,dispatch,fade);}catch(...){dialogs.pop_back();throw;}
    dialogs.pop_back();
    if(!dialogs.empty()){notifyScreen(dialogs.back().screen);publishState(dialogs.back());}
#ifdef HOMM3_FULL_GAME
    else if(g_advManager && g_advManager->m_status==1)notifyScreen("adventure");
#endif
    return g_windowManager->m_dialogReturn;
}
int runDialogDraw(heroWindow* window,int (*handler)(message&),int (*draw)(message&),int fade,const char* screen){
    dialogs.push_back({window,handler,screen,false});
    try{g_windowManager->doDialogDraw(window,dispatch,draw,fade);}catch(...){dialogs.pop_back();throw;}
    dialogs.pop_back();
    if(!dialogs.empty()){notifyScreen(dialogs.back().screen);publishState(dialogs.back());}
#ifdef HOMM3_FULL_GAME
    else if(g_advManager && g_advManager->m_status==1)notifyScreen("adventure");
#endif
    return g_windowManager->m_dialogReturn;
}

}
