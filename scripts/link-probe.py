from pathlib import Path
import argparse,subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--target',choices=['native','web'],default='native');args=p.parse_args()
units='lodfile resource resourcemanager palette csprite cspriteframe csequence bitmap16 bitmap816 bitmap24 font textresource gamecontext'.split()
compiler='clang++' if args.target=='native' else str(ROOT/'.local/emsdk/upstream/emscripten/em++')
flags=['-std=c++14','-DHOMM3_PORT','-include','port/compat/prefix.h','-Iport/compat','-Ibuild/portable-source/include','-O1']
if args.target=='native':flags+=['-Wl,-dead_strip','-lz']
else:flags+=['-sUSE_ZLIB=1','-fexceptions','-sALLOW_MEMORY_GROWTH=1','-sENVIRONMENT=node','-sNODERAWFS=1']
output=ROOT/'build'/('resource-probe' if args.target=='native' else 'resource-probe.cjs')
sources=['port/resource_probe.cpp',*[f'port/platform/{name}.cpp' for name in ['files','pcx','archive_state']]]
cmd=[compiler,*flags,*sources,*[str(ROOT/'build'/f'cpp-{args.target}'/f'{u}.o') for u in units],'-o',str(output)]
r=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(ROOT/'build'/f'link-{args.target}.log').write_text(r.stdout)
print(r.stdout if r.returncode else f'Built: {output}');raise SystemExit(r.returncode)
