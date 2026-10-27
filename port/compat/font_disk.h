#pragma once
#include "font.h"
#include <cstdint>
// Original FNT files serialize the VC6 header, including obsolete pointer slots.
// These slots are not valid host pointers and are never used by the glyph renderer.
struct PortableFontDiskSpec {
    uint8_t first,last,depth;
    int8_t xspace,yspace;
    uint8_t height;
    int8_t baseyoffset,pad;
    uint32_t numpal,unusedPalPointers[5];
    font::TFontSpec::myABC abc[256];
    uint32_t offsets[256];
};
static_assert(sizeof(PortableFontDiskSpec)==0x1020,"FNT header disk layout");
inline font::TFontSpec decodeFontSpec(const PortableFontDiskSpec& disk){
    font::TFontSpec host{};
    host.first=disk.first;host.last=disk.last;host.depth=disk.depth;
    host.xspace=disk.xspace;host.yspace=disk.yspace;host.height=disk.height;
    host.baseyoffset=disk.baseyoffset;host.pad=disk.pad;host.numpal=disk.numpal;
    for(int i=0;i<256;++i){host.abc[i]=disk.abc[i];host.Offset[i]=disk.offsets[i];}
    return host;
}
