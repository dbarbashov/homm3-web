"""Round-trip lobby headers over dirty memory, with no original game assets needed."""
from pathlib import Path
import argparse
import json
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--video-root', type=Path, default=ROOT / 'build/ffmpeg-native/install')
a = p.parse_args()
manifest = json.loads((ROOT / 'port/game-sources.json').read_text())
# Constructor changes in game.h require every translation unit to agree; linking
# reused objects from another checkout can select an old inline constructor.
subprocess.run([sys.executable, 'scripts/prepare-port.py'], cwd=ROOT, check=True)
subprocess.run([sys.executable, 'scripts/compile-port.py', '--target', 'native', *manifest['core']], cwd=ROOT, check=True)
flags = shlex.split(subprocess.check_output(['sdl2-config', '--cflags', '--libs'], text=True))
video = a.video_root.resolve()
command = ['clang++', '-std=c++14', '-DHOMM3_PORT', '-DHOMM3_FULL_GAME',
           '-include', 'port/compat/prefix.h', '-Iport/compat', '-Ibuild/portable-source/include',
           '-O1', '-Wno-writable-strings', '-Wno-deprecated-declarations', *flags,
           '-Wl,-dead_strip', 'port/probes/network_headers.cpp',
           *[f'build/cpp-native/{unit}.o' for unit in manifest['core']],
           *[f'port/platform/{unit}.cpp' for unit in manifest['platform']],
           *[f'port/frontend/{unit}.cpp' for unit in manifest['frontend']],
           '-I' + str(video / 'include'),
           *[str(video / f'lib/lib{name}.a') for name in ['avformat', 'avcodec', 'swscale', 'swresample', 'avutil']],
           '-lz', '-o', 'build/network-headers-probe']
compiled = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
(ROOT / 'build/network-headers-probe-build.log').write_text(compiled.stdout + compiled.stderr)
if compiled.returncode:
    print(compiled.stdout + compiled.stderr)
    raise SystemExit(compiled.returncode)
run = subprocess.run([str(ROOT / 'build/network-headers-probe')], cwd=ROOT,
                     text=True, capture_output=True, timeout=30)
print(run.stdout, run.stderr)
run.check_returncode()
result = json.loads(run.stdout.strip().splitlines()[-1])
output = ROOT / 'test-results/network-startup'
output.mkdir(parents=True, exist_ok=True)
(output / 'native.json').write_text(json.dumps(result, indent=2) + '\n')
assert result.get('passed'), result
