"""A corrupt or mismatched runtime must never replace an installed client."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('engine_client', Path(__file__).resolve().parents[1] / 'scripts/engine-client.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        (self.root / 'engine.lock.json').write_text(json.dumps({'commit': 'a' * 40}))
        self.destination = self.root / 'web/port'
        self.destination.mkdir(parents=True)
        for name in ('game.js', 'game.wasm'):
            (self.destination / name).write_bytes(b'previous runtime')
            (self.bundle / name).write_bytes(b'new runtime ' + name.encode())
        self.manifest = {'schema': 1, 'engineRevision': 'a' * 40, 'artifacts': {
            name: hashlib.sha256((self.bundle / name).read_bytes()).hexdigest()
            for name in ('game.js', 'game.wasm')}}

    def install(self):
        (self.bundle / 'engine-build.json').write_text(json.dumps(self.manifest))
        with patch.object(installer, 'ROOT', self.root), patch.object(sys, 'argv', ['engine-client.py', 'install', '--from-dir', str(self.bundle)]):
            installer.main()

    def assert_previous_preserved(self):
        for name in ('game.js', 'game.wasm'):
            self.assertEqual((self.destination / name).read_bytes(), b'previous runtime')

    def test_matching_bundle_installs_only_runtime(self):
        (self.bundle / 'private.cpp').write_text('must not be exported')
        self.install()
        self.assertEqual(sorted(p.name for p in self.destination.iterdir()), ['engine-build.json', 'game.js', 'game.wasm'])
        self.assertEqual((self.destination / 'game.wasm').read_bytes(), b'new runtime game.wasm')

    def test_wrong_revision_preserves_previous_install(self):
        self.manifest['engineRevision'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'revision'):
            self.install()
        self.assert_previous_preserved()

    def test_corruption_preserves_previous_install(self):
        (self.bundle / 'game.wasm').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.install()
        self.assert_previous_preserved()

    def test_unexpected_manifest_member_is_rejected(self):
        self.manifest['artifacts']['../private.cpp'] = 'c' * 64
        with self.assertRaisesRegex(ValueError, 'hashes'):
            self.install()
        self.assert_previous_preserved()


if __name__ == '__main__':
    unittest.main()
