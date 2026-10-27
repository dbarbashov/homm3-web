"""Compile the unmodified upstream format readers and our browser adapter."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'upstream/homm3-decomp'
lock = json.loads((ROOT / 'upstream.lock.json').read_text())
if not UPSTREAM.exists():
    subprocess.run(['git', 'clone', '--branch', lock['branch'], lock['repository'], str(UPSTREAM)], check=True)
    subprocess.run(['git', '-C', str(UPSTREAM), 'checkout', lock['commit']], check=True)
actual = subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], text=True).strip()
if actual != lock['commit']:
    raise SystemExit(f'Upstream revision mismatch: {actual}; expected {lock["commit"]}')
build = ROOT / 'build'
build.mkdir(exist_ok=True)
common = ['rustc', '--edition=2021', '--target', 'wasm32-unknown-unknown', '-C', 'opt-level=2', '-C', 'panic=abort']
externs = []
for crate in ['homm3-map', 'homm3-def']:
    name = crate.replace('-', '_')
    out = build / f'lib{name}.rlib'
    subprocess.run(common + ['--crate-name', name, '--crate-type', 'rlib', str(UPSTREAM / 'tools' / crate / 'src/lib.rs'), '-o', str(out)], check=True)
    externs += ['--extern', f'{name}={out}']
subprocess.run(common + ['--crate-type', 'cdylib', str(ROOT / 'engine/lib.rs'), *externs, '-o', str(ROOT / 'web/engine.wasm')], check=True)
print('Built web/engine.wasm from pinned upstream parsers; no game assets bundled.')
