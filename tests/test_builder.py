"""Controlled safety and metadata fixture tests. Not a claim of browser runtime portability."""
import importlib.util
import json
import os
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release', ROOT / 'scripts' / 'release.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class BuilderTests(unittest.TestCase):
    def test_semver_prerelease_pattern(self):
        import re
        p = r'0\.(\d+)\.(\d+)-nightly\.(\d+)'
        self.assertEqual(re.fullmatch(p, '0.2.47-nightly.7').groups(), ('2','47','7'))
        self.assertIsNone(re.fullmatch(p, '0.2.47'))
    def test_pe_rejects_nonexecutable(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d,'not.exe'); p.write_bytes(b'hello')
            with self.assertRaises(RuntimeError): r.pe_machine(p)
    def test_fingerprint(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d,'x'); p.write_bytes(b'abc')
            self.assertEqual(r.sha256(p), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
    def test_unverified_installer_cannot_run_outside_runner(self):
        # GitHub's Windows CI itself sets GITHUB_ACTIONS/RUNNER_OS. Remove them
        # deliberately so this test checks a *non-runner* environment on every OS.
        import argparse
        forbidden = ('GITHUB_ACTIONS', 'RUNNER_OS', 'RUNNER_ENVIRONMENT', 'RUNNER_TEMP')
        fixture = {k: v for k, v in os.environ.items() if k not in forbidden}
        with patch.dict(os.environ, fixture, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'GitHub-hosted Windows runner'):
                r.install_in_isolated_ci(argparse.Namespace(identity='dummy',installer='dummy',out='dummy'))

    def test_installer_denies_self_hosted_runner_before_reading_files(self):
        import argparse
        with patch.dict(os.environ, {
                'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'Windows',
                'RUNNER_ENVIRONMENT': 'self-hosted', 'RUNNER_TEMP': 'C:/_temp'}):
            with self.assertRaisesRegex(RuntimeError, 'GitHub-hosted Windows runner'):
                r.install_in_isolated_ci(argparse.Namespace(identity='dummy',installer='dummy',out='dummy'))

    def test_installer_denies_missing_hosted_marker(self):
        import argparse
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'Windows',
                                    'RUNNER_ENVIRONMENT': '', 'RUNNER_TEMP': 'C:/_temp'}):
            with self.assertRaisesRegex(RuntimeError, 'GitHub-hosted Windows runner'):
                r.install_in_isolated_ci(argparse.Namespace(identity='dummy',installer='dummy',out='dummy'))
    def test_refuse_zip_traversal_before_extracting(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); zfile=d/'ArdiaPortable_fixture.zip'
            with zipfile.ZipFile(zfile,'w') as z:
                z.writestr('ArdiaPortable/../escape.txt', 'test')
            import hashlib
            digest = r.sha256(zfile)
            sums = d/'SHA256SUMS.txt'; sums.write_text(f'{digest}  {zfile.name}\n', encoding='utf-8')
            p=subprocess.run([sys.executable, str(ROOT/'scripts/verify-existing-zip.py'), '--zip',str(zfile), '--sums',str(sums),'--out',str(d/'work')],capture_output=True,text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertFalse((d/'escape.txt').exists())
    def test_zip_preserves_nested_empty_directories(self):
        import argparse
        with tempfile.TemporaryDirectory() as d:
            root=Path(d,'ArdiaPortable'); (root/'Data/Profile/Empty/Inner').mkdir(parents=True)
            (root/'README.txt').write_text('fixture')
            out=Path(d,'out.zip')
            r.makezip(argparse.Namespace(root=str(root),out=str(out)))
            with zipfile.ZipFile(out) as z:
                self.assertIn('ArdiaPortable/Data/Profile/Empty/Inner/',z.namelist())
    def test_action_refs_pinned(self):
        wf=(ROOT/'.github/workflows/build.yml').read_text()
        self.assertIn('vhick/Portable-Package-Builder@v1.0.0', wf)
        self.assertIn('vhick/portable-release-publisher@v1.1.1', wf)
        self.assertIn("engine: custom-nsis", wf)
    def test_no_source_binary_committed(self):
        self.assertFalse(list((ROOT/'launcher').glob('*.exe')))
        self.assertFalse(list(ROOT.glob('*.paf.exe')))
    def test_upstream_not_force_claimed_signed(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8').lower()
        self.assertIn('unsigned',readme)

if __name__ == '__main__': unittest.main()
