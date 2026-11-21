"""b1r7 two-layout build fixtures. No Windows GUI or live browser runtime claims."""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import data_layout
import launcher_options
import release
import verify_launcher_flags


class DataLayoutChoiceTests(unittest.TestCase):
    def test_boolean_layouts_have_distinct_reproducible_identities(self):
        mirror = data_layout.manifest_for(True)
        legacy = data_layout.manifest_for(False)
        self.assertEqual(mirror['layout'], 'windows-appdata-mirror-v2')
        self.assertEqual(legacy['layout'], 'legacy-profile-v1')
        self.assertNotEqual(mirror['fingerprint'], legacy['fingerprint'])
        self.assertEqual(mirror, data_layout.manifest_for(True))
        self.assertRaises(ValueError, data_layout.manifest_for, 'false')
        self.assertRaises(ValueError, data_layout.parse_bool, 'true --host-path')

    def test_workflow_checkbox_is_true_and_build_time_only(self):
        wf = (ROOT / '.github/workflows/build.yml').read_text(encoding='utf-8')
        self.assertIn("      windows_style_data_folders:\n", wf)
        self.assertIn('ARDIA_WINDOWS_STYLE_DATA: ${{ inputs.windows_style_data_folders }}', wf)
        self.assertLess(wf.index('scripts/data_layout.py'), wf.index('scripts/build-launcher.ps1'))
        self.assertIn(' --data-layout work/data-layout.json', wf)
        self.assertIn('_d$($env:PKG_LAYOUT_ID).zip', wf)
        self.assertIn('b1r10-${{ env.PKG_CHANNEL }}-s${{ env.PKG_SOURCE_ID }}-f${{ env.PKG_OPTIONS_ID }}-d${{ env.PKG_LAYOUT_ID }}', wf)
        self.assertIn('-Layout $env:PKG_LAYOUT_NAME', wf)
        packaging = (ROOT / '.github/workflows/package-only.yml').read_text(encoding='utf-8')
        self.assertNotIn('windows_style_data_folders', packaging)
        self.assertNotIn('data_layout.py', packaging)

    def test_headers_compile_distinct_real_paths(self):
        m = data_layout.header_for(data_layout.manifest_for(True))
        l = data_layout.header_for(data_layout.manifest_for(False))
        self.assertIn('ARDIA_PORTABLE_WINDOWS_DATA_LAYOUT = true;', m)
        self.assertIn('ARDIA_PORTABLE_WINDOWS_DATA_LAYOUT = false;', l)
        self.assertIn('L"legacy-profile-v1"', l)
        self.assertIn('L"windows-appdata-mirror-v2"', m)
        cpp = (ROOT / 'launcher/main.cpp').read_text(encoding='utf-8')
        self.assertIn('#include "data_layout.h"', cpp)
        self.assertIn('const bool windowsMirror = ARDIA_PORTABLE_WINDOWS_DATA_LAYOUT;', cpp)
        self.assertIn('const bool useLegacy = !windowsMirror || legacyHasData;', cpp)
        self.assertIn('if (!windowsMirror && mirrorHasData)', cpp)
        self.assertIn('if (legacyHasData && mirrorHasData)', cpp)
        self.assertIn('SetEnvironmentVariableW(L"ARDIA_PORTABLE_DATA_LAYOUT", ARDIA_PORTABLE_LAYOUT_NAME)', cpp)
        self.assertIn('hasOtherContents(localArdia, L"User Data", mirrorAppState)', cpp)
        for destructive in ('DeleteFileW(', 'RemoveDirectoryW(', 'SHFileOperationW(', 'MoveFileExW('):
            self.assertNotIn(destructive, cpp)
        self.assertLess(cpp.index('ARDIA_PORTABLE_LAYOUT_NAME'), cpp.index('CreateProcessW('))

    def _stage(self, tmp, mirror):
        tmp = Path(tmp)
        origin = tmp / 'fake-aria-installer-extraction'
        origin.mkdir()
        for name in ['Ardia.exe', 'chrome.dll', 'Ardia.ico']:
            (origin / name).write_bytes(b'MZ' + bytes(512))
        exe = tmp / 'Launcher.exe'
        exe.write_bytes(b'MZ' + bytes(512))
        opts = launcher_options.manifest_for(launcher_options.DEFAULTS)
        layout = data_layout.manifest_for(mirror)
        identity = tmp / 'identity.json'
        identity.write_text(json.dumps({
            'arch': 'x64', 'version': '0.2.47-nightly.7', 'package_revision': 'b1r9',
            'release_channel': 'prerelease', 'release_tag': 'windows-alpha',
            'github_release_is_prerelease': True, 'asset_id': 900001,
            'portable_data_layout': layout['layout'], 'data_layout': layout,
            'data_layout_fingerprint': layout['fingerprint'],
            'launcher_options': opts, 'launcher_flags_fingerprint': opts['fingerprint'],
            'source_commit': 'a' * 40,
        }), encoding='utf-8')
        def fetch_fixture(url, path):
            Path(path).write_text('SOURCE NOTICE', encoding='utf-8')
        out = tmp / 'ArdiaPortable'
        with patch.object(release, 'pe_machine', return_value=0x8664), patch.object(release, 'fetch', side_effect=fetch_fixture):
            release.stage(argparse.Namespace(identity=str(identity),install=str(origin),launcher=str(exe),out=str(out)))
        for name in ('appicon_16.png', 'appicon_32.png'):
            (out / 'App/AppInfo' / name).write_bytes(b'png fixture')
        return out, identity, layout

    def test_both_layouts_stage_validate_and_zip_without_mixing(self):
        for mirror in (True, False):
            with self.subTest(windows_style=mirror), TemporaryDirectory() as d:
                root, identity, layout = self._stage(d, mirror)
                self.assertEqual(data_layout.load_manifest(root / 'Other/Source/data-layout.json'), layout)
                with patch.object(release, 'pe_machine', return_value=0x8664):
                    release.validate(argparse.Namespace(identity=str(identity),root=str(root)))
                zip_path = Path(d) / 'out.zip'
                release.makezip(argparse.Namespace(root=str(root),out=str(zip_path)))
                with zipfile.ZipFile(zip_path) as z:
                    self.assertIsNone(z.testzip())
                    names = z.namelist()
                    if mirror:
                        self.assertIn('ArdiaPortable/Data/Local/Ardia/User Data/', names)
                        self.assertIn('ArdiaPortable/Data/Roaming/Ardia/', names)
                        self.assertNotIn('ArdiaPortable/Data/Profile/', names)
                    else:
                        self.assertIn('ArdiaPortable/Data/Profile/', names)
                        self.assertNotIn('ArdiaPortable/Data/Local/Ardia/User Data/', names)
                        self.assertNotIn('ArdiaPortable/Data/Roaming/Ardia/', names)

    def test_selected_layouts_produce_different_release_tags(self):
        fake_commit = 'abcdef1234567890abcdef1234567890abcdef12'
        upstream = {'body': 'Ardia 0.2.47-nightly.7 for Windows, build 7661 (commit `abcdef1`)',
                    'draft': False, 'prerelease': True, 'tag_name': 'windows-alpha',
                    'assets': [{'name': 'Ardia-Setup-x64.exe', 'size': 32000000,
                                'browser_download_url': 'https://github.com/ardia-browser/ardia/releases/download/windows-alpha/Ardia-Setup-x64.exe',
                                'id': 123456}]}
        def github_fixture(endpoint, token):
            if endpoint == '/releases/tags/windows-alpha': return upstream
            if endpoint in ('/commits/abcdef1', '/commits/v0.2.47-nightly.7'): return {'sha': fake_commit}
            if endpoint.startswith('/contents/pnpm-lock.yaml?ref='): return {'sha': 'f'*40}
            raise AssertionError(endpoint)
        with TemporaryDirectory() as d, patch.object(release, 'japi', side_effect=github_fixture):
            tmp = Path(d)
            flagsfile = tmp/'flags.json'
            flagsfile.write_text(json.dumps(launcher_options.manifest_for(launcher_options.DEFAULTS)),encoding='utf-8')
            tags=[]
            for choice in (True,False):
                layout = data_layout.manifest_for(choice)
                layoutfile = tmp/'layout.json'
                layoutfile.write_text(json.dumps(layout),encoding='utf-8')
                identity=tmp/'identity.json'
                release.resolve(argparse.Namespace(identity=str(identity), arch='x64', version='',
                           launcher_options=str(flagsfile),data_layout=str(layoutfile)))
                metadata=json.loads(identity.read_text(encoding='utf-8'))
                self.assertEqual(metadata['portable_data_layout'], layout['layout'])
                self.assertEqual(metadata['data_layout_fingerprint'], layout['fingerprint'])
                tags.append(metadata['release_tag_for_builder'])
            self.assertNotEqual(tags[0],tags[1])

    def test_mismatched_or_tampered_layout_manifest_is_rejected(self):
        with TemporaryDirectory() as d:
            root, identity, layout = self._stage(d, False)
            file = root / 'Other/Source/data-layout.json'
            file.write_text(json.dumps(data_layout.manifest_for(True)),encoding='utf-8')
            with self.assertRaisesRegex((ValueError,RuntimeError), 'manifest|layout'):
                release.validate(argparse.Namespace(identity=str(identity),root=str(root)))
            file.write_text(json.dumps(layout),encoding='utf-8')
            (root / 'Data/Local/Ardia/User Data').mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, 'both data layout roots'):
                release.validate(argparse.Namespace(identity=str(identity),root=str(root)))

    def test_compiled_pe_layout_selection_is_verified_independently(self):
        with TemporaryDirectory() as d:
            base = Path(d)
            flags = launcher_options.manifest_for(launcher_options.DEFAULTS)
            flags_file = base/'flags.json';flags_file.write_text(json.dumps(flags),encoding='utf-8')
            layout = data_layout.manifest_for(False)
            layout_file = base/'layout.json';layout_file.write_text(json.dumps(layout),encoding='utf-8')
            exe = base/'launcher.exe'
            utf16flags = ''.join(' ' + x for x in flags['enabled_arguments']).encode('utf-16le')
            exe.write_bytes(b'MZ' + bytes(100) + utf16flags + bytes(20) + layout['layout'].encode('utf-16le'))
            verify_launcher_flags.check(exe, flags_file, layout_file)
            layout_file.write_text(json.dumps(data_layout.manifest_for(True)),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'selected UTF-16 data layout marker'):
                verify_launcher_flags.check(exe, flags_file, layout_file)

    def test_installer_preserves_selected_layout(self):
        script = (ROOT / 'scripts/test-installer.ps1').read_text(encoding='utf-8')
        for name in ('windows-appdata-mirror-v2', 'legacy-profile-v1', 'Data/Profile', 'Data/Local/Ardia/User Data', 'Empty/Nested/Leaves'):
            self.assertIn(name, script)
        self.assertIn("(Join-Path $dest 'Data') -PathType Container", script)
        self.assertIn('New-Item -Path $required -ItemType Directory -Force', script)
        self.assertIn('Reinstall removed selected layout directory', script)


if __name__ == '__main__':
    unittest.main()
