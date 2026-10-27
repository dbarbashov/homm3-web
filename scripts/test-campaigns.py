"""Native coverage of the original campaign loader, without shipping retail data."""
from pathlib import Path
import subprocess, shlex, os
ROOT=Path(__file__).resolve().parents[1]
objects=[str(p) for p in sorted((ROOT/'build/cmake-game-native/CMakeFiles/homm3-port.dir').rglob('*.o')) if p.name!='game_main.cpp.o']
flags=shlex.split(subprocess.check_output(['sdl2-config','--cflags','--libs'],text=True))
libs=[str(ROOT/'build/ffmpeg-native/install/lib'/('lib'+n+'.a')) for n in ['avformat','avcodec','swscale','swresample','avutil']]
subprocess.run(['clang++','-std=c++14','-DHOMM3_PORT','-DHOMM3_FULL_GAME','-include','port/compat/prefix.h','-Iport/compat','-Ibuild/portable-source/include','-Wno-writable-strings','-Wno-deprecated-declarations',*flags,'-Wl,-dead_strip','port/probes/campaigns.cpp',*objects,*libs,'-lz','-o','build/campaigns-probe'],cwd=ROOT,check=True)
run=subprocess.run([str(ROOT/'build/campaigns-probe'),str(ROOT/'.local/runtime')],cwd=ROOT,env={**os.environ,'SDL_VIDEODRIVER':'dummy','SDL_RENDER_DRIVER':'software','SDL_AUDIODRIVER':'dummy'},text=True,capture_output=True,timeout=120)
if run.returncode==0:
 for line in run.stdout.splitlines():
  if not line.startswith('SCENARIO '): continue
  _,campaign,scenario=line.split()
  check=subprocess.run([str(ROOT/'build/campaigns-probe'),str(ROOT/'.local/runtime'),campaign,scenario],cwd=ROOT,text=True,capture_output=True,timeout=30)
  if check.returncode: print(check.stdout,check.stderr);raise SystemExit(check.returncode)
 print('All embedded campaign maps loaded successfully')
print(run.stdout,run.stderr);(ROOT/'test-results/campaigns-native.log').write_text(run.stdout+run.stderr);raise SystemExit(run.returncode)
