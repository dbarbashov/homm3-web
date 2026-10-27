#pragma once
class Bitmap16Bit;
namespace Port {
void cursorInside(bool inside);
void drawCursor(Bitmap16Bit& target,int offsetX=0,int offsetY=0);
}
