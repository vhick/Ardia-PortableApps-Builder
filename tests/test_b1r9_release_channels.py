"""Offline regression tests for real stable/prerelease channel isolation.

These fixtures do not claim live GitHub downloads or a compiled browser.
"""
import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import release
import launcher_options
import data_layout

COMMIT = 'e4e0893' + 'e' * 33
LOCK = 'f' * 40


def asset(tag='v0.2.47', version='0.2.47', arch='x64', name=None):
    name = name or f'Ardia-{version}-windows-{arch}-setup.exe'
    return {'name': name, 'size': 38000000, 'id': 42,
            'browser_download_url': f'https://github.com/ardia-browser/ardia/releases/download/{tag}/{name}',
            'digest': 'sha256:' + 'a' * 64}


class ReleaseChannelTests(TestCase):
    def setup_files(self, temp):
        temp = Path(temp)
        f = temp / 'flags.json'
        l = temp / 'layout.json'
        f.write_text(json.dumps(launcher_options.manifest_for(launcher_options.DEFAULTS)), encoding='utf-8')
        l.write_text(json.dumps(data_layout.manifest_for(True)), encoding='utf-8')
        return f, l

    def run_resolver(self, temp, api, channel, version='', arch='x64'):
        f, l = self.setup_files(temp)
        identity = Path(temp) / 'id.json'
        with patch.object(release, 'japi', side_effect=api):
            release.resolve(argparse.Namespace(
                arch=arch, channel=channel, version=version,
                launcher_options=str(f), data_layout=str(l), identity=str(identity)))
        return json.loads(identity.read_text(encoding='utf-8'))

    def stable_api(self, *assets, release_version='0.2.47', prerelease=False, draft=False):
        def api(endpoint, token):
            record = {'tag_name': 'v' + release_version, 'draft': draft,
                      'prerelease': prerelease, 'assets': list(assets)}
            if endpoint == f'/releases/tags/v{release_version}': return record
            if endpoint == '/releases?per_page=100&page=1': return [record]
            if endpoint == '/commits/v' + release_version:
                return {'sha': COMMIT}
            if endpoint.startswith('/contents/pnpm-lock.yaml?ref='):
                return {'sha': LOCK}
            raise AssertionError('Wrong endpoint ' + endpoint)
        return api

    def alpha_api(self, version='0.2.47', arch='x64', prerelease=True):
        body = f'Ardia {version} for Windows, build 7929 (commit `e4e0893`).'
        def api(endpoint, token):
            if endpoint == '/releases/tags/windows-alpha':
                return {'tag_name': 'windows-alpha', 'prerelease': prerelease,
                        'draft': False, 'body': body,
                        'assets': [asset('windows-alpha', version, arch,
                                         name=f'Ardia-Setup-{arch}.exe')]}
            if endpoint == '/commits/v' + version: return {'sha': COMMIT}
            if endpoint.startswith('/contents/pnpm-lock.yaml?ref='):
                return {'sha': LOCK}
            raise AssertionError('Wrong endpoint ' + endpoint)
        return api

    def test_stable_exactly_classified_and_uses_stable_asset(self):
        with TemporaryDirectory() as d:
            meta = self.run_resolver(d, self.stable_api(asset()), 'stable', version='0.2.47')
            self.assertEqual(meta['release_channel'], 'stable')
            self.assertEqual(meta['release_tag'], 'v0.2.47')
            self.assertFalse(meta['github_release_is_prerelease'])
            self.assertEqual(meta['source_commit'], COMMIT)
            self.assertEqual(meta['asset_name'], 'Ardia-0.2.47-windows-x64-setup.exe')
            self.assertIn('portable-ardia-stable-0.2.47', meta['release_tag_for_builder'])
            self.assertIn('b1r11', meta['release_tag_for_builder'])

    def test_stable_latest_without_requested_version_uses_releases_latest(self):
        with TemporaryDirectory() as d:
            m = self.run_resolver(d, self.stable_api(asset()), 'stable')
            self.assertEqual(m['version'], '0.2.47')

    def test_stable_does_not_fall_back_to_windows_alpha_if_no_windows_assets(self):
        with TemporaryDirectory() as d:
            api = self.stable_api({'name': 'Ardia-0.2.47-macos-arm64.dmg', 'size': 2000000, 'id': 9})
            with self.assertRaisesRegex(RuntimeError, 'No published non-prerelease Ardia release'):
                self.run_resolver(d, api, 'stable')

    def test_stable_refuses_gitHub_prerelease_or_draft(self):
        for draft, pre in ((False, True), (True, False)):
            with self.subTest(draft=draft, prerelease=pre), TemporaryDirectory() as d:
                with self.assertRaisesRegex(RuntimeError, 'draft or prerelease'):
                    self.run_resolver(d, self.stable_api(asset(), draft=draft, prerelease=pre), 'stable', '0.2.47')

    def test_stable_does_not_accept_nightly_version_as_stable(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError, 'Stable channel requires'):
                self.run_resolver(d, self.stable_api(asset()), 'stable', '0.2.47-nightly.7')

    def test_latest_stable_with_windows_asset_uses_numeric_versions(self):
        with TemporaryDirectory() as d:
            def fake_api(endpoint, token):
                if endpoint == '/releases?per_page=100&page=1':
                    return [
                        {'tag_name': 'v0.2.9', 'draft': False, 'prerelease': False,
                         'assets': [asset('v0.2.9', '0.2.9')]},
                        {'tag_name': 'v0.2.47', 'draft': False, 'prerelease': False,
                         'assets': [{'name': 'Mac.dmg', 'size': 2500000}]},
                        {'tag_name': 'v0.2.10', 'draft': False, 'prerelease': False,
                         'assets': [asset('v0.2.10', '0.2.10')]},
                        {'tag_name': 'v0.2.48-nightly.1', 'draft': False, 'prerelease': True,
                         'assets': [asset('v0.2.48-nightly.1', '0.2.48-nightly.1')]},
                    ]
                if endpoint == '/commits/v0.2.10': return {'sha': COMMIT}
                if endpoint.startswith('/contents/pnpm-lock.yaml?ref='): return {'sha': LOCK}
                raise AssertionError(endpoint)
            metadata = self.run_resolver(d, fake_api, 'stable')
            self.assertEqual(metadata['version'], '0.2.10')

    def test_stable_source_and_asset_must_match_official_version_tag(self):
        with TemporaryDirectory() as d:
            evil = asset('windows-alpha')
            with self.assertRaisesRegex(RuntimeError, 'official release'):
                self.run_resolver(d, self.stable_api(evil), 'stable', '0.2.47')

    def test_prerelease_accepts_upstream_alpha_with_stable_looking_version(self):
        with TemporaryDirectory() as d:
            meta = self.run_resolver(d, self.alpha_api(), 'prerelease')
            self.assertEqual(meta['version'], '0.2.47')
            self.assertEqual(meta['release_tag'], 'windows-alpha')
            self.assertTrue(meta['github_release_is_prerelease'])
            self.assertEqual(meta['release_channel'], 'prerelease')
            self.assertIn('portable-ardia-prerelease-', meta['release_tag_for_builder'])

    def test_prerelease_accepts_windows_alpha_with_nightly_version(self):
        with TemporaryDirectory() as d:
            meta = self.run_resolver(d, self.alpha_api(version='0.2.47-nightly.7'),
                                     'prerelease', version='0.2.47-nightly.7')
            self.assertEqual(meta['version'], '0.2.47-nightly.7')

    def test_windows_alpha_requires_prerelease_classification(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError, 'published prerelease'):
                self.run_resolver(d, self.alpha_api(prerelease=False), 'prerelease')

    def test_same_upstream_commit_gives_distinct_channel_release_tags(self):
        with TemporaryDirectory() as d:
            stable = self.run_resolver(d, self.stable_api(asset()), 'stable')
            alpha = self.run_resolver(d, self.alpha_api(), 'prerelease')
            self.assertNotEqual(stable['release_tag_for_builder'], alpha['release_tag_for_builder'])

    def test_stable_staging_appinfo_and_identity_validate_without_changing_layout(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            meta = self.run_resolver(d, self.stable_api(asset()), 'stable', version='0.2.47')
            source = root / 'upstream'
            source.mkdir()
            for filename in ('Ardia.exe', 'chrome.dll', 'Ardia.ico'):
                (source / filename).write_bytes(b'MZ' + bytes(60))
            launcher = root / 'ArdiaPortable.exe'
            launcher.write_bytes(b'MZ' + bytes(60))
            package = root / 'ArdiaPortable'
            with patch.object(release, 'pe_machine', return_value=0x8664), \
                 patch.object(release, 'fetch', side_effect=lambda url, path: Path(path).write_text('LICENSE NOTICE', encoding='utf-8')):
                release.stage(argparse.Namespace(identity=str(root/'id.json'),
                                                install=str(source), launcher=str(launcher), out=str(package)))
            for png in ('appicon_16.png', 'appicon_32.png'):
                (package / 'App/AppInfo' / png).write_bytes(b'png')
            appinfo = (package / 'App/AppInfo/appinfo.ini').read_text(encoding='utf-8')
            self.assertIn('PackageVersion=0.2.47.9999', appinfo)
            self.assertIn('DisplayVersion=0.2.47 (b1r11)', appinfo)
            self.assertIn('Windows stable release', appinfo)
            self.assertTrue((package / 'Data/Local/Ardia/User Data').is_dir())
            self.assertTrue((package / 'Data/Roaming/Ardia').is_dir())
            self.assertFalse((package / 'Data/Profile').exists())
            with patch.object(release, 'pe_machine', return_value=0x8664):
                release.validate(argparse.Namespace(identity=str(root/'id.json'), root=str(package)))
            meta = json.loads((root/'id.json').read_text(encoding='utf-8'))
            self.assertEqual(meta['release_channel'], 'stable')
            self.assertEqual(json.loads((package/'Other/Source/build-identity.json').read_text(encoding='utf-8'))['release_channel'], 'stable')

    def test_stable_package_validator_refuses_mislabeled_release_classification(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            meta = self.run_resolver(d, self.stable_api(asset()), 'stable', version='0.2.47')
            source = root/'upstream'; source.mkdir()
            for f in ('Ardia.exe', 'chrome.dll', 'Ardia.ico'):
                (source/f).write_bytes(b'MZ' + bytes(40))
            launcher = root/'launch.exe'; launcher.write_bytes(b'MZ' + bytes(40))
            package = root/'ArdiaPortable'
            with patch.object(release,'pe_machine',return_value=0x8664), \
                 patch.object(release,'fetch',side_effect=lambda url,path: Path(path).write_text('source')):
                release.stage(argparse.Namespace(identity=str(root/'id.json'),install=str(source),launcher=str(launcher),out=str(package)))
            for png in ('appicon_16.png','appicon_32.png'):
                (package/'App/AppInfo'/png).write_bytes(b'png')
            m = json.loads((root/'id.json').read_text())
            m['github_release_is_prerelease'] = True
            (root/'id.json').write_text(json.dumps(m))
            with patch.object(release,'pe_machine',return_value=0x8664):
                with self.assertRaisesRegex(RuntimeError,'prerelease flag differs'):
                    release.validate(argparse.Namespace(identity=str(root/'id.json'),root=str(package)))

    def test_package_version_numeric_ordering_prevents_stable_downgrade(self):
        self.assertEqual(release.portableapps_version('0.2.47'), '0.2.47.9999')
        self.assertEqual(release.portableapps_version('0.2.47','prerelease'), '0.2.47.9998')
        self.assertEqual(release.portableapps_version('0.2.47-nightly.7'), '0.2.47.7')
        self.assertEqual(release.portableapps_version('0.2.48'), '0.2.48.9999')
        with self.assertRaisesRegex(RuntimeError, 'exceeds'):
            release.portableapps_version('0.2.47-nightly.9999')

    def test_release_workflow_selects_stable_or_alpha_and_preserves_existing_options(self):
        w = (ROOT / '.github/workflows/build.yml').read_text(encoding='utf-8')
        self.assertIn('release_channel:', w)
        self.assertIn('options: [prerelease, stable]', w)
        self.assertIn('--channel $env:RELEASE_CHANNEL', w)
        self.assertIn('PKG_CHANNEL=$($m.release_channel)', w)
        self.assertIn('b1r11', w)
        self.assertIn('windows_style_data_folders:', w)
        self.assertIn('disable_encryption_win:', w)
        self.assertIn('default: false', w)
        self.assertIn('windows-2022', w)
        self.assertIn('vhick/Portable-Package-Builder@v1.0.0', w)
        self.assertIn('vhick/portable-release-publisher@v1.1.1', w)

    def test_offline_alpha_and_stable_release_asset_names_are_strict(self):
        with self.assertRaisesRegex(RuntimeError, 'No unique official Windows'):
            release.find_release_asset({'tag_name':'v0.2.47',
                                         'assets':[asset(name='Ardia-dummy-x64.exe')]},
                                        'x64','0.2.47','stable')
        with self.assertRaisesRegex(RuntimeError, 'No unique official Windows'):
            release.find_release_asset({'tag_name':'v0.2.47',
                                         'assets':[asset(), asset(name='Ardia-Setup-x64.exe')]},
                                        'x64','0.2.47','stable')

if __name__ == '__main__': main()
