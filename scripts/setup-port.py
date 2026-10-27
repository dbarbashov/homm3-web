"""Install the pinned local Emscripten SDK without changing shell startup files."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[1]
lock=json.loads((ROOT/'port/toolchain.lock.json').read_text())
sdk=ROOT/'.local/emsdk'
if not sdk.exists():
    subprocess.run(['git','clone','https://github.com/emscripten-core/emsdk.git',str(sdk)],check=True)
    subprocess.run(['git','-C',str(sdk),'checkout',lock['emsdkCommit']],check=True)
for action in ['install','activate']:
    subprocess.run([str(sdk/'emsdk'),action,lock['emscripten']],cwd=sdk,check=True)
print('Local SDK ready. Native builds also need clang++, SDL2, zlib and Python 3.')
