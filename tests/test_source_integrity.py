"""Offline regression tests for b1r6 Windows Git checkout line-ending handling."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_verifier', ROOT / 'scripts/verify-source-content.py')
source_verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_verifier)


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True).stdout.decode().strip()


class SourceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'upstream'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        git(self.repo, 'config', 'user.email', 'ci@example.invalid')
        git(self.repo, 'config', 'user.name', 'Fixture CI')
        self.manifest = self.repo / source_verifier.MANIFEST
        self.manifest.parent.mkdir(parents=True)
        self.document = {'release': 'windows-engine-20261116-4', 'chromium': '157.0.8103.38',
                         'x64': {'asset': 'ardia-engine-win-x64.zip', 'sha256': 'f'*64}}
        self.raw = (json.dumps(self.document, indent=2) + '\n').encode('utf-8')
        self.manifest.write_bytes(self.raw)
        self.lockfile = self.repo / 'pnpm-lock.yaml'
        self.lock_raw = b'lockfileVersion: 9.0\npackages:\n  test: value\n'
        self.lockfile.write_bytes(self.lock_raw)
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'verified fixture')
        self.identity_path = self.base / 'identity.json'
        self.identity = {
            'engine_manifest_sha256': hashlib.sha256(self.raw).hexdigest(),
            'engine_manifest_blob_sha': git(self.repo, 'rev-parse', 'HEAD:' + source_verifier.MANIFEST),
            'engine_release': self.document['release'],
            'engine_asset': self.document['x64']['asset'],
            'engine_sha256': 'f'*64,
            'engine_chromium': self.document['chromium'],
        }
        self.save_identity()

    def save_identity(self):
        self.identity_path.write_text(json.dumps(self.identity), encoding='utf-8')

    def test_exact_checkout_passes_and_pins_git_lockfile_hash(self):
        verified = source_verifier.verify(self.repo, self.identity_path)
        self.assertEqual(verified['lockfile_sha256'], hashlib.sha256(self.lock_raw).hexdigest())
        self.assertEqual(verified['source_manifest_checkout'], 'byte-identical')
        self.assertEqual(verified['source_lockfile_checkout'], 'byte-identical')

    def test_crlf_only_checkout_passes_but_hashes_original_git_blob(self):
        self.manifest.write_bytes(self.raw.replace(b'\n', b'\r\n'))
        self.lockfile.write_bytes(self.lock_raw.replace(b'\n', b'\r\n'))
        self.assertNotEqual(hashlib.sha256(self.raw).hexdigest(), hashlib.sha256(self.manifest.read_bytes()).hexdigest())
        verified = source_verifier.verify(self.repo, self.identity_path)
        self.assertEqual(verified['source_manifest_checkout'], 'line-ending-only')
        self.assertEqual(verified['source_lockfile_checkout'], 'line-ending-only')
        self.assertEqual(verified['lockfile_sha256'], hashlib.sha256(self.lock_raw).hexdigest())

    def test_worktree_manifest_tampering_still_blocked(self):
        self.manifest.write_bytes(self.raw.replace(b'windows-engine-20261116-4', b'windows-engine-20261116-2'))
        with self.assertRaisesRegex(source_verifier.VerificationError, 'beyond line endings'):
            source_verifier.verify(self.repo, self.identity_path)

    def test_worktree_lockfile_tampering_still_blocked(self):
        self.lockfile.write_bytes(self.lock_raw + b'altered: true\n')
        with self.assertRaisesRegex(source_verifier.VerificationError, 'beyond line endings'):
            source_verifier.verify(self.repo, self.identity_path)

    def test_mismatched_preflight_sha_still_blocked(self):
        self.identity['engine_manifest_sha256'] = '0'*64
        self.save_identity()
        with self.assertRaisesRegex(source_verifier.VerificationError, 'differs from preflight'):
            source_verifier.verify(self.repo, self.identity_path)

    def test_mismatched_git_blob_identity_still_blocked(self):
        self.identity['engine_manifest_blob_sha'] = '0'*40
        self.save_identity()
        with self.assertRaisesRegex(source_verifier.VerificationError, 'Git blob object differs'):
            source_verifier.verify(self.repo, self.identity_path)

    def test_mismatched_engine_metadata_still_blocked(self):
        self.identity['engine_chromium'] = '0.0.0.0'
        self.save_identity()
        with self.assertRaisesRegex(source_verifier.VerificationError, 'engine identity'):
            source_verifier.verify(self.repo, self.identity_path)

    def test_missing_manifest_worktree_blocked(self):
        self.manifest.unlink()
        with self.assertRaisesRegex(source_verifier.VerificationError, 'missing/unreadable'):
            source_verifier.verify(self.repo, self.identity_path)

    def test_missing_preflight_digest_blocked(self):
        self.identity.pop('engine_manifest_sha256')
        self.save_identity()
        with self.assertRaisesRegex(source_verifier.VerificationError, 'valid engine manifest'):
            source_verifier.verify(self.repo, self.identity_path)


if __name__ == '__main__':
    unittest.main()
