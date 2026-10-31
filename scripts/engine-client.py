#!/usr/bin/env python3
"""Build from the public engine checkout, or install a verified runtime bundle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('game.js', 'game.wasm')


def verify_bundle(directory, revision):
    manifest = json.loads((directory / 'engine-build.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('engineRevision') != revision:
        raise ValueError('Engine bundle revision differs from engine.lock.json')
    if set(manifest.get('artifacts', {})) != set(NAMES):
        raise ValueError('Bundle must contain hashes for game.js and game.wasm')
    for name in NAMES:
        actual = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if actual != manifest['artifacts'][name]:
            raise ValueError('Engine artifact checksum mismatch: ' + name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build')
    build.add_argument('--engine', type=Path, default=Path(os.environ.get('HOMM3_ENGINE_ROOT', ROOT.parent / 'homm3-engine')))
    build.add_argument('--cmake', default=os.environ.get('CMAKE', 'cmake'))
    build.add_argument('--jobs', type=int, default=5)
    install = sub.add_parser('install')
    install.add_argument('--from-dir', type=Path, required=True)
    sub.add_parser('verify')
    a = p.parse_args()
    lock = json.loads((ROOT / 'engine.lock.json').read_text())
    revision = lock['commit']
    if a.command == 'verify':
        verify_bundle(ROOT / 'web/port', revision)
        print('Verified browser engine ' + revision)
        return
    with tempfile.TemporaryDirectory(prefix='homm3-client-') as temporary:
        source = Path(temporary)
        if a.command == 'build':
            engine = a.engine.resolve()
            if not (engine / 'scripts/build-client.py').is_file():
                p.error('Engine checkout required (https://github.com/dbarbashov/homm3-engine). Set HOMM3_ENGINE_ROOT, or use engine:install with a trusted bundle.')
            actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=engine, text=True).strip()
            if actual != revision:
                p.error('Engine revision differs from engine.lock.json; checkout ' + revision)
            dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=engine, text=True)
            if dirty:
                p.error('Engine checkout has uncommitted source changes; commit them and update both locks')
            subprocess.run([sys.executable, str(engine / 'scripts/build-client.py'), '--output', str(source),
                            '--cmake', a.cmake, '--jobs', str(a.jobs)], check=True)
        else:
            source = a.from_dir.resolve()
        verify_bundle(source, revision)
        destination = ROOT / 'web/port'
        destination.mkdir(parents=True, exist_ok=True)
        for name in (*NAMES, 'engine-build.json'):
            shutil.copy2(source / name, destination / name)
    print('Installed browser engine ' + revision)


if __name__ == '__main__':
    main()
