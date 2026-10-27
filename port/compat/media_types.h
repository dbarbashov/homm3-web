#pragma once
#include "windows.h"
// Opaque third-party handles at the portable sound service boundary.
struct _DIG_DRIVER;
class ds_memsample;
struct _STREAM;
using HDIGDRIVER=_DIG_DRIVER*;
using HSAMPLE=ds_memsample*;
using HSTREAM=_STREAM*;
struct WAVEFORMAT { WORD wFormatTag,nChannels; DWORD nSamplesPerSec,nAvgBytesPerSec; WORD nBlockAlign; };
struct PCMWAVEFORMAT { WAVEFORMAT wf; WORD wBitsPerSample; };
extern "C" int AIL_stream_status(HSTREAM);
struct BINK;
extern "C" int BinkPause(BINK*,int);
