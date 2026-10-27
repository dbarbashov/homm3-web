#pragma once
class TAdventureMapWindow;
class Bitmap816;
class heroWindow;
namespace Port { namespace HD {
int width();
int height();
int mapRight();
int mapHeight();
int centerX();
int centerY();
bool adventureVisible();
// Window lifetime, rather than manager/dialog flags, owns presentation geometry.
bool isAdventureWindow(const heroWindow* window);
void windowOpening(heroWindow* window, bool adventure);
void windowClosing(heroWindow* window);
void windowClosed(heroWindow* window);
bool hasAdventureBackdrop();
int overlayOffsetX();
int overlayOffsetY();
void resizeAdventure();
void layoutAdventure(TAdventureMapWindow* window,int dx,int dy);
void drawAdventureFrame(Bitmap816* bitmap);
} }
