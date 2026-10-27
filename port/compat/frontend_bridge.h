#pragma once
class heroWindow;
class message;
namespace Port {
int runDialog(heroWindow* window,int (*handler)(message&),int fade,const char* screen);
int runDialogDraw(heroWindow*,int (*)(message&),int (*)(message&),int,const char*);
void notifySnapshot(const char* screen);
void notifyScreen(const char* screen);
unsigned frameHash();
void setGameTypeMode(bool load);
}
