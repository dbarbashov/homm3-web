"""Build one recovered C++ front end for native SDL or Emscripten/SDL."""
from pathlib import Path
import argparse,subprocess,sys,json,os,shlex,platform
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--target',choices=['native','web'],default='native');p.add_argument('--no-compile',action='store_true');p.add_argument('--sanitize',action='store_true');a=p.parse_args()
manifest=json.loads((ROOT/'port/sources.json').read_text())
units=manifest['core']
if not a.no_compile:
    subprocess.run([sys.executable,'scripts/prepare-port.py'],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'scripts/compile-port.py','--target',a.target,*(['--sanitize'] if a.sanitize else []),*units],cwd=ROOT,check=True)
compiler=os.environ.get('CXX','clang++') if a.target=='native' else str(ROOT/'.local/emsdk/upstream/emscripten/em++')
flags=['-std=c++14','-DHOMM3_PORT','-include','port/compat/prefix.h','-Iport/compat','-Ibuild/portable-source/include','-O1','-Wno-writable-strings','-ffunction-sections','-fdata-sections']
if a.sanitize:flags+=['-g','-fsanitize=address','-fno-omit-frame-pointer']
if a.target=='native':
    flags+=shlex.split(subprocess.check_output(['sdl2-config','--cflags','--libs'],text=True))
    flags+=['-Wl,-dead_strip' if platform.system()=='Darwin' else '-Wl,--gc-sections','-lz']
    output=ROOT/'build'/('homm3-port-asan' if a.sanitize else 'homm3-port')
else:
    flags+=['-sUSE_ZLIB=1','-sUSE_SDL=2','-fexceptions','-sASYNCIFY=1','-sALLOW_MEMORY_GROWTH=1','-sINITIAL_MEMORY=67108864','-sSTACK_SIZE=4194304','-sFORCE_FILESYSTEM=1','-sEXPORTED_RUNTIME_METHODS=["FS","callMain"]','-sINVOKE_RUN=0','-sEXIT_RUNTIME=0','-sENVIRONMENT=web']
    output=ROOT/'web/port/homm3.js';output.parent.mkdir(exist_ok=True,parents=True)
sources=['port/main.cpp',*[f'port/platform/{n}.cpp' for n in manifest['platform']],*[f'port/frontend/{n}.cpp' for n in manifest['frontend']]]
cmd=[compiler,*flags,*sources,*[str(ROOT/'build'/(f'cpp-{a.target}'+('-asan' if a.sanitize else ''))/f'{u}.o') for u in units],'-o',str(output)]
r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(ROOT/'build'/f'link-port-{a.target}.log').write_text(r.stdout)
print(r.stdout if r.returncode else f'Built: {output}');raise SystemExit(r.returncode)
