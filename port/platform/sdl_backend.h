#pragma once
class Bitmap16Bit;
namespace Port {
struct ExitRequested {};
bool openDisplay();
void resizeDisplay(int width,int height);
void displaySize(int& width,int& height);
bool setFullscreen(bool enabled);
void closeDisplay();
bool shouldQuit();
void present();
void commitFrame(int x,int y,int width,int height);
const Bitmap16Bit& committedFrame();
const Bitmap16Bit& presentedFrame();
void announceCommand(int id,const char* screen);
}
