"""Validate the native platform against frame and real retail-media contracts."""
from pathlib import Path
import subprocess, shlex, os
ROOT=Path(__file__).resolve().parents[1]
objects=sorted((ROOT/'build/cmake-game-native/CMakeFiles/homm3-port.dir').rglob('*.o'))
objects=[str(p) for p in objects if p.name!='game_main.cpp.o']
flags=shlex.split(subprocess.check_output(['sdl2-config','--cflags','--libs'],text=True))
subprocess.run(['clang++','-std=c++14','-DHOMM3_PORT','-DHOMM3_FULL_GAME','-include','port/compat/prefix.h','-Iport/compat','-Ibuild/portable-source/include','-Wno-writable-strings','-Wno-deprecated-declarations',*flags,'-Wl,-dead_strip','port/probes/preferences.cpp',*objects,*[str(ROOT/'build/ffmpeg-native/install/lib'/('lib'+n+'.a')) for n in ['avformat','avcodec','swscale','swresample','avutil']],'-lz','-o','build/preferences-probe'],cwd=ROOT,check=True)

import tempfile,json
with tempfile.TemporaryDirectory(prefix='homm3-prefs-') as directory:
    for action in ['defaults','write','read','write-slow','read-slow']:
        subprocess.run([str(ROOT/'build/preferences-probe'),directory,action],check=True,timeout=15)
    (Path(directory)/'preferences.dat').write_text('H3PREF1\ninvalid record\n')
    subprocess.run([str(ROOT/'build/preferences-probe'),directory,'defaults'],check=True,timeout=15)
(ROOT/'test-results/preferences-native.json').write_text(json.dumps({'passed':True,'freshProcessPersistence':True,'corruptFileDefaults':True}))
