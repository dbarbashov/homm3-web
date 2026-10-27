#pragma once
class Bitmap16Bit;
namespace Port {
void cursorInside(bool inside);
bool cursorNeedsRedraw(int offsetX,int offsetY);
void drawCursor(Bitmap16Bit& target,int offsetX=0,int offsetY=0);
}
