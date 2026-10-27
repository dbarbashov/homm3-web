#pragma once
#include "windows.h"
// Fixed-width descriptor used by the shared RGB conversion helper.
struct DDPIXELFORMAT { DWORD dwSize,dwFlags,dwFourCC,dwRGBBitCount,dwRBitMask,dwGBitMask,dwBBitMask,dwRGBAlphaBitMask; };
struct IDirectDrawSurface;
