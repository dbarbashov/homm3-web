"""Native command ownership, economy, original combat and snapshot regressions.

Build the native CMake game first, as for the existing sidebar/AI probes.
--native-build, --video-root and --runtime can reuse a main checkout's build
when this script is run from an isolated worktree. Changed engine units and
platform boundary are always compiled from this checkout.
"""
from pathlib import Path
import argparse
import json
import os
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--native-build', type=Path, default=ROOT / 'build/cmake-game-native')
p.add_argument('--video-root', type=Path, default=ROOT / 'build/ffmpeg-native/install')
p.add_argument('--runtime', type=Path, default=Path(os.environ.get('HOMM3_RUNTIME', ROOT / '.local/runtime')))
a = p.parse_args()
changed = ['advmgr', 'events', 'kb', 'winmgr', 'exec', 'game', 'cursor', 'townmgr', 'recruit', 'hero', 'advspells']
object_root = a.native_build.resolve() / 'CMakeFiles/homm3-port.dir'
if not object_root.is_dir():
    p.error(f'Build the native game first; missing {object_root}')
if not a.runtime.is_dir():
    p.error(f'Original game assets are required: {a.runtime}')
subprocess.run([sys.executable, 'scripts/prepare-port.py'], cwd=ROOT, check=True)
subprocess.run([sys.executable, 'scripts/compile-port.py', '--target', 'native', *changed], cwd=ROOT, check=True)
exclude = {f'{name}.cpp.o' for name in [*changed, 'game_main', 'sdl_backend', 'fast_game', 'hd_qol']}
objects = [str(path) for path in sorted(object_root.rglob('*.o')) if path.name not in exclude]
objects += [str(ROOT / f'build/cpp-native/{name}.o') for name in changed]
flags = shlex.split(subprocess.check_output(['sdl2-config', '--cflags', '--libs'], text=True))
video = a.video_root.resolve()
command = ['clang++', '-std=c++14', '-DHOMM3_PORT', '-DHOMM3_FULL_GAME',
           '-include', 'port/compat/prefix.h', '-Iport/compat', '-Ibuild/portable-source/include',
           '-O1', '-Wno-writable-strings', '-Wno-deprecated-declarations', *flags,
           '-Wl,-dead_strip', 'port/probes/fast_game.cpp', 'port/platform/sdl_backend.cpp', 'port/platform/hd_qol.cpp', 'port/platform/cursor.cpp',
           *objects, '-I' + str(video / 'include'),
           *[str(video / f'lib/lib{name}.a') for name in ['avformat', 'avcodec', 'swscale', 'swresample', 'avutil']],
           '-lz', '-o', 'build/fast-bridge-probe']
compiled = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
(ROOT / 'build/fast-bridge-probe-build.log').write_text(compiled.stdout + compiled.stderr)
if compiled.returncode:
    print(compiled.stdout + compiled.stderr)
    raise SystemExit(compiled.returncode)
run = subprocess.run([str(ROOT / 'build/fast-bridge-probe'), str(a.runtime.resolve())], cwd=ROOT,
                     env={**os.environ, 'SDL_VIDEODRIVER': 'dummy', 'SDL_RENDER_DRIVER': 'software', 'SDL_AUDIODRIVER': 'dummy'},
                     text=True, capture_output=True, timeout=30)
print(run.stdout, run.stderr)
if run.returncode:
    raise SystemExit(run.returncode)
result = json.loads(run.stdout.strip().splitlines()[-1])
output = ROOT / 'test-results/fast-game'
output.mkdir(parents=True, exist_ok=True)
(output / 'native.json').write_text(json.dumps(result, indent=2) + '\n')
if not result.get('passed'):
    raise SystemExit('Native fast-game assertions failed')
