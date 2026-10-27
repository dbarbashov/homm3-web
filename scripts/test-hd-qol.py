"""HD army conservation and recruitment budget regression."""
from pathlib import Path
import subprocess, shlex, os
ROOT=Path(__file__).resolve().parents[1]
objects=sorted((ROOT/'build/cmake-game-native/CMakeFiles/homm3-port.dir').rglob('*.o'))
objects=[str(p) for p in objects if p.name!='game_main.cpp.o']
flags=shlex.split(subprocess.check_output(['sdl2-config','--cflags','--libs'],text=True))
subprocess.run(['clang++','-std=c++14','-DHOMM3_PORT','-DHOMM3_FULL_GAME','-include','port/compat/prefix.h','-Iport/compat','-Ibuild/portable-source/include','-Wno-writable-strings','-Wno-deprecated-declarations',*flags,'-Wl,-dead_strip','port/probes/hd_qol.cpp',*objects,*[str(ROOT/'build/ffmpeg-native/install/lib'/('lib'+n+'.a')) for n in ['avformat','avcodec','swscale','swresample','avutil']],'-lz','-o','build/hd-qol-probe'],cwd=ROOT,check=True)
run=subprocess.run([str(ROOT/'build/hd-qol-probe'),str(ROOT/'.local/runtime')],cwd=ROOT,env={**os.environ,'SDL_VIDEODRIVER':'dummy','SDL_RENDER_DRIVER':'software','SDL_AUDIODRIVER':'dummy'},text=True,capture_output=True,timeout=30)
print(run.stdout,run.stderr)
(ROOT/'test-results/hd-qol-native.json').write_text(run.stdout)
raise SystemExit(run.returncode)
