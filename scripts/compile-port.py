"""Compile real upstream translation units; keep diagnostics per unit/target."""
from pathlib import Path
import argparse, concurrent.futures, subprocess, json

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--target',choices=['native','web'],default='native')
parser.add_argument('--syntax',action='store_true')
parser.add_argument('--sanitize',action='store_true')
parser.add_argument('units',nargs='*',default=json.loads((ROOT/'port/sources.json').read_text())['core'])
args=parser.parse_args()
out=ROOT/'build'/(f'cpp-{args.target}'+('-asan' if args.sanitize else ''));out.mkdir(exist_ok=True,parents=True)
compiler='clang++' if args.target=='native' else str(ROOT/'.local/emsdk/upstream/emscripten/em++')
flags=['-std=c++14','-fms-extensions','-DHOMM3_PORT','-Wno-writable-strings','-Wno-ignored-attributes','-Wno-unknown-pragmas','-Wno-deprecated-declarations','-Wno-non-c-typedef-for-linkage','-Wno-invalid-constexpr','-Wno-unused-value','-Wno-out-of-line-declaration','-Wno-address-of-temporary','-Wno-dangling-else','-ferror-limit=50','-O1','-ffunction-sections','-fdata-sections','-include',str(ROOT/'port/compat/prefix.h')]
for inc in ['port/compat','build/portable-source/include']:
    flags+=['-I'+str(ROOT/inc)]
if args.sanitize:flags+=['-g','-fsanitize=address','-fno-omit-frame-pointer']
if args.target=='web':flags+=['-sUSE_ZLIB=1','-fexceptions']

def compile_unit(unit):
    source=ROOT/'build/portable-source/src'/f'{unit}.cpp'
    cmd=[compiler,*flags,*(['-fsyntax-only'] if args.syntax else ['-c']),str(source),'-o',str(out/f'{unit}.o')]
    run=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (out/f'{unit}.log').write_text(run.stdout)
    errors=[s for s in run.stdout.splitlines() if 'error:' in s]
    print(f'{unit}: '+('PASS' if not run.returncode else f'FAIL ({len(errors)}) '+ '\n  '.join(errors[:3])),flush=True)
    return {'unit':unit,'ok':run.returncode==0,'errors':errors,'command':cmd}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    results=list(pool.map(compile_unit,args.units))
(out/'compile-report.json').write_text(json.dumps(results,indent=2))
print(f'{sum(x["ok"] for x in results)}/{len(results)} translation units compile ({args.target})')
raise SystemExit(0 if all(x['ok'] for x in results) else 1)
