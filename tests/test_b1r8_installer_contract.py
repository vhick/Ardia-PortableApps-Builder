"""Regression guards for b1r8 installer/Data contract.

Static tests only. They do NOT run NSIS, install Ardia, or launch Windows GUI.
"""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'scripts'))
import release
import launcher_options
import data_layout

class InstallerContractTests(unittest.TestCase):
    def test_installer_smoke_checks_root_before_seeding_layout(self):
        text = (ROOT/'scripts/test-installer.ps1').read_text(encoding='utf-8')
        self.assertIn('Join-Path $dest \'Data\'', text)
        self.assertIn('Pinned installer did not create the top-level Data folder', text)
        self.assertLess(text.index('Pinned installer did not create the top-level Data folder'),
                        text.index('New-Item -Path $required -ItemType Directory -Force'))
        self.assertIn('if (Test-Path -LiteralPath $required)', text)
        self.assertIn('Installer unexpectedly created layout subdirectories', text)

    def test_installer_checks_selected_compiled_manifest_on_both_installs(self):
        text = (ROOT/'scripts/test-installer.ps1').read_text(encoding='utf-8')
        self.assertIn('Other/Source/data-layout.json', text)
        self.assertIn('if ($manifest.layout -ne $Layout)', text)
        self.assertEqual(text.count('Install-Test'), 3) # definition and two calls
        self.assertIn('Data/Profile', text)
        self.assertIn('Data/Local/Ardia/User Data', text)
        self.assertIn('Data/Roaming/Ardia', text)

    def test_reinstall_check_is_non_destructive_to_fixture_data(self):
        text = (ROOT/'scripts/test-installer.ps1').read_text(encoding='utf-8')
        self.assertIn('Empty/Nested/Leaves', text)
        self.assertIn('profile-preservation-marker-ユニコード.txt', text)
        self.assertIn('Reinstall removed an empty nested Data directory', text)
        self.assertIn('Reinstall changed seeded user Data', text)
        for suspect in ('Remove-Item -Recurse', 'Remove-Item -Force', 'Format-Volume', 'cmd /c rd'):
            self.assertNotIn(suspect, text)

    def test_previous_b1r7_manifest_still_validates_for_package_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)/'ArdiaPortable'
            for path in ('ArdiaPortable.exe','App/Ardia/Ardia.exe','App/Ardia/chrome.dll',
                         'App/AppInfo/appinfo.ini','App/AppInfo/appicon.ico',
                         'App/AppInfo/appicon_16.png','App/AppInfo/appicon_32.png',
                         'Other/Source/LICENSE','Other/Source/NOTICE','Other/Source/build-identity.json'):
                file = root/path
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(b'MZ'+bytes(60))
            (root/'App/AppInfo/appinfo.ini').write_text('[Details]\nAppID=ArdiaBrowserPortableCommunity\n[Control]\nStart=ArdiaPortable.exe\n',encoding='utf-8')
            (root/'Data/Local/Ardia/User Data').mkdir(parents=True)
            (root/'Data/Roaming/Ardia').mkdir(parents=True)
            flags = launcher_options.manifest_for(launcher_options.DEFAULTS)
            layout = data_layout.manifest_for(True)
            (root/'Other/Source/launcher-options.json').write_text(json.dumps(flags),encoding='utf-8')
            (root/'Other/Source/data-layout.json').write_text(json.dumps(layout),encoding='utf-8')
            meta={'arch':'x64','package_revision':'b1r7','portable_data_layout':layout['layout'],
                  'data_layout':layout,'data_layout_fingerprint':layout['fingerprint'],
                  'launcher_options':flags,'launcher_flags_fingerprint':flags['fingerprint'],
                  'upstream_app_exe_sha256':release.sha256(root/'App/Ardia/Ardia.exe'),
                  'launcher_sha256':release.sha256(root/'ArdiaPortable.exe')}
            identity=Path(tmp)/'identity.json'
            identity.write_text(json.dumps(meta),encoding='utf-8')
            with patch.object(release,'pe_machine',return_value=0x8664):
                release.validate(argparse.Namespace(identity=str(identity),root=str(root)))
            # A tampered old manifest must not be exempted from verification.
            (root/'Other/Source/data-layout.json').write_text(json.dumps(data_layout.manifest_for(False)),encoding='utf-8')
            with self.assertRaises((RuntimeError,ValueError)):
                with patch.object(release,'pe_machine',return_value=0x8664):
                    release.validate(argparse.Namespace(identity=str(identity),root=str(root)))

if __name__ == '__main__': unittest.main()
