"""Materialize a portable build tree, leaving the matching upstream pristine."""
from pathlib import Path
import json, shutil, subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'upstream/homm3-decomp'
DEST=ROOT/'build/portable-source'
lock=json.loads((ROOT/'upstream.lock.json').read_text())
if not SOURCE.exists():
    subprocess.run(['git','clone','--branch',lock['branch'],lock['repository'],str(SOURCE)],check=True)
    subprocess.run(['git','-C',str(SOURCE),'checkout',lock['commit']],check=True)
actual=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
if actual!=lock['commit']:raise SystemExit('Upstream revision differs from upstream.lock.json')
for directory in ['include','src']:
    shutil.copytree(SOURCE/directory,DEST/directory,dirs_exist_ok=True)

# Exact, reviewable portability patches follow. No recovered function is stubbed.
patch_dir=ROOT/'port/patches'
if patch_dir.exists():
    for patch in sorted(patch_dir.glob('*.patch')):
        subprocess.run(['patch','-p1','-i',str(patch)],cwd=DEST,check=True,stdout=subprocess.DEVNULL)
print(DEST)

# Recover platform-independent helpers from otherwise unported units.
# Their function bodies are kept verbatim; the surrounding Win32 backend is SDL.
def body(unit, signature):
    text=(DEST/'src'/f'{unit}.cpp').read_text();start=text.index(signature);brace=text.index('{',start)
    depth=1;i=brace+1
    while depth:
        if text[i]=='{':depth+=1
        elif text[i]=='}':depth-=1
        i+=1
    return text[start:i]+'\n'
helpers='#include "kb.h"\n#include "kbwin.h"\n#include "soundmgr.h"\n#include "palette.h"\n#include "winmm_thunks.h"\n'
for unit, signature in [('kbwin','unsigned long GameTime::get()'),('kbwin','void GameTime::delayTil('),('kbwin','void GameTime::delay(int'),('kbwin','void initVideo()'),('wingraph','void setPlayerPaletteColors(unsigned short*'),('wingraph','void setPlayerPaletteColors(TPalette24&')]:
    helpers+=f'\n// Original body extracted from {unit}.cpp\n'+body(unit,signature)
(DEST/'src/platform_helpers.cpp').write_text(helpers)

# Original layout algorithm for the text-only front-end dialog adapter.
# Windows SDK min/max macros accept the original mixed long/int operands.
helpers += '#include "font.h"\n#include <cstdarg>\n#define min(a,b) (((a)<(b))?(a):(b))\n#define max(a,b) (((a)>(b))?(a):(b))\n'
helpers += 'static const int g_dialogIconMaxRows=2, g_dialogIconRowSingle=1, g_dialogIconRowPair=2, g_dialogIconRowTriple=3, g_dialogIconRowQuad=4;\n'
helpers += body('kb','void calculateNormalDialogSize(')
helpers += body('misc','std::string formatString(')
(DEST/'src/portable_helpers.cpp').write_text(helpers)

# Cursor DEF names and per-frame hotspots recovered from the original backend.
mouse=(DEST/'src/mousemgr.cpp').read_text()
start=mouse.index('DATA(0x0067ff38)')
end=mouse.index('// E:',mouse.index('POINT g_mouseHotSpots',start))
(DEST/'include/port_cursor_tables.h').write_text('// Extracted verbatim from mousemgr.cpp.\n'+mouse[start:end])

# Platform-independent original sound/resource lifetime helpers, verbatim.
sound='#include "soundmgr.h"\n#include "sample.h"\n#include "prefs.h"\n#include "kb.h"\n'
for signature in ['int soundManager::convertVolume(', 'void soundManager::waitSample(', 'SAMPLE2 loadPlaySample(', 'void clearMemSample(', 'void waitEndSample(']:
    sound+=body('soundmgr',signature)
(DEST/'src/sound_helpers.cpp').write_text(sound)

# Original movie descriptor names/flags; media decoding is supplied by FFmpeg.
video=(SOURCE/'src/smackmgr.cpp').read_text()
start=video.index('DATA(0x006839c0) SVideoDescriptor g_videoDescriptors')
end=video.index('};',start)+2
(DEST/'include/port_video_descriptors.h').write_text(video[start:end]+'\n')
