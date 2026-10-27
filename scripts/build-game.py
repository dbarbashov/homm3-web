"""Build the recovered game integration target separately from the stable menu."""
from pathlib import Path
import argparse,json,subprocess,shlex,sys
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--target',choices=['native','web'],default='native')
p.add_argument('--no-compile',action='store_true')
p.add_argument('--probe',action='store_true')
a=p.parse_args()
if a.probe and a.target != "native":p.error("The map probe is a native command-line target")
m=json.loads((ROOT/'port/game-sources.json').read_text())
if not a.no_compile:
    subprocess.run([sys.executable,'scripts/prepare-port.py'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'scripts/compile-port.py','--target',a.target,*m['core']],cwd=ROOT,check=True)
compiler='clang++' if a.target=='native' else str(ROOT/'.local/emsdk/upstream/emscripten/em++')
flags=['-std=c++14','-DHOMM3_PORT','-DHOMM3_FULL_GAME','-include','port/compat/prefix.h','-Iport/compat','-Ibuild/portable-source/include','-O1','-g','-Wno-writable-strings','-Wno-deprecated-declarations']
if a.target=='native':
    flags+=shlex.split(subprocess.check_output(['sdl2-config','--cflags','--libs'],text=True))+['-Wl,-dead_strip','-lz']
    output='build/game-probe' if a.probe else 'build/homm3-game'
else:
    flags+=['-lidbfs.js','-sUSE_ZLIB=1','-sUSE_SDL=2','-fexceptions','-sASYNCIFY=1','-sASYNCIFY_STACK_SIZE=1048576','-sALLOW_MEMORY_GROWTH=1','-sINITIAL_MEMORY=268435456','-sSTACK_SIZE=8388608','-sFORCE_FILESYSTEM=1','-sEXPORTED_RUNTIME_METHODS=["FS","IDBFS","callMain"]','-sINVOKE_RUN=0','-sEXIT_RUNTIME=0','-sENVIRONMENT=web']
    output='web/port/game.js'
source='port/probes/game.cpp' if a.probe else 'port/game_main.cpp'
args=[compiler,*flags,source,*[f'build/cpp-{a.target}/{u}.o' for u in m['core']],*[f'port/platform/{u}.cpp' for u in m['platform']],*[f'port/frontend/{u}.cpp' for u in m['frontend']],'-o',output]
r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
(ROOT/f'build/link-game-{a.target}.log').write_text(r.stdout+r.stderr)
print(r.stdout+r.stderr if r.returncode else 'Built '+output)
raise SystemExit(r.returncode)
