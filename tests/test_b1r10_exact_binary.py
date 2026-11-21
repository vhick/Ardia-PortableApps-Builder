"""Offline b1r10 exact-official-binary tests (no live GitHub, no Windows GUI)."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import release, launcher_options, data_layout

COMMIT = 'e4e0893' + 'e' * 33
LOCK = 'f' * 40


def fake_asset(tag='v0.2.47', version='0.2.47', digest='a'*64, asset_id=42):
    name = f'Ardia-{version}-windows-x64-setup.exe'
    return {'name': name, 'size': 38000000, 'id': asset_id,
            'browser_download_url': f'https://github.com/ardia-browser/ardia/releases/download/{tag}/{name}',
            'digest': ('sha256:' + digest) if digest is not None else None}


def api_for(tag='v0.2.47', prerelease=False, installer_digest='a'*64, asset_id=42):
    version = tag[1:]
    def api(endpoint, token):
        if endpoint == '/releases/tags/'+tag:
            return {'tag_name':tag, 'draft':False, 'prerelease':prerelease,
                    'assets':[fake_asset(tag,version,installer_digest,asset_id)]}
        if endpoint == '/commits/'+tag: return {'sha': COMMIT}
        if endpoint.startswith('/contents/pnpm-lock.yaml?ref='): return {'sha':LOCK}
        raise AssertionError('Unexpected GitHub endpoint: '+endpoint)
    return api


class ExactBinaryTests(TestCase):
    def resolve_it(self, folder, api, *, channel='stable', tag='v0.2.47', setup='', app='', asset_id='', version=''):
        folder = Path(folder)
        flags = folder/'opts.json'; layout=folder/'layout.json'; identity=folder/'identity.json'
        flags.write_text(json.dumps(launcher_options.manifest_for(launcher_options.DEFAULTS)), encoding='utf-8')
        layout.write_text(json.dumps(data_layout.manifest_for(True)),encoding='utf-8')
        with patch.object(release,'japi',side_effect=api):
            release.resolve(argparse.Namespace(channel=channel, arch='x64', version=version,
                        release_tag=tag, expected_setup_sha256=setup, expected_app_sha256=app,
                        expected_asset_id=asset_id, launcher_options=str(flags),
                        data_layout=str(layout), identity=str(identity)))
        return json.loads(identity.read_text(encoding='utf-8'))

    def test_pin_exact_digest_and_app_hash_are_saved(self):
        with TemporaryDirectory() as d:
            meta=self.resolve_it(d,api_for(),setup='A'*64,app='b'*64,asset_id='42')
            self.assertEqual(meta['expected_setup_sha256'],'a'*64)
            self.assertEqual(meta['expected_app_sha256'],'b'*64)
            self.assertIn('haaaaaaaaaaaaaaaa-e'+ 'b'*12,meta['source_fingerprint'])
            self.assertIn(meta['source_fingerprint'],meta['release_tag_for_builder'])

    def test_mismatching_expected_sha_rejected_before_download(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'differs from official GitHub release asset digest'):
                self.resolve_it(d,api_for(),setup='b'*64)

    def test_invalid_sha_rejected_without_download(self):
        for digest in ('abcd','a'*63,'z'*64,'a'*64+'extra'):
            with self.subTest(digest=digest),TemporaryDirectory() as d:
                with self.assertRaisesRegex(RuntimeError,'64 hexadecimal'):
                    self.resolve_it(d,api_for(),setup=digest)

    def test_github_asset_id_change_rejected(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'asset ID differs'):
                self.resolve_it(d,api_for(),asset_id='43')

    def test_github_asset_id_requires_numeric(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'positive integer'):
                self.resolve_it(d,api_for(),asset_id='not-number')

    def test_exact_stable_tag_cannot_be_nightly(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'For Stable'):
                self.resolve_it(d,api_for(),tag='v0.2.47-nightly.9')

    def test_stable_tag_cannot_be_windows_alpha(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'For Stable'):
                self.resolve_it(d,api_for(),tag='windows-alpha')

    def test_version_must_match_exact_release_tag(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'does not match Requested version'):
                self.resolve_it(d,api_for(),tag='v0.2.47',version='0.2.46')

    def test_archived_versioned_prerelease_with_real_windows_asset(self):
        with TemporaryDirectory() as d:
            meta=self.resolve_it(d,api_for(tag='v0.2.47-nightly.9',prerelease=True),
                        channel='prerelease', tag='v0.2.47-nightly.9')
            self.assertEqual(meta['release_tag'],'v0.2.47-nightly.9')
            self.assertEqual(meta['version'],'0.2.47-nightly.9')
            self.assertIsNone(meta['build'])  # never fabricate Windows engine build number

    def test_versioned_prerelease_refuses_non_prerelease(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'exact published prerelease'):
                self.resolve_it(d,api_for(tag='v0.2.47-nightly.9',prerelease=False),
                           channel='prerelease',tag='v0.2.47-nightly.9')

    def test_without_api_digest_uses_asset_id_fingerprint(self):
        with TemporaryDirectory() as d:
            meta=self.resolve_it(d,api_for(installer_digest=None,asset_id=890))
            self.assertEqual(meta['source_fingerprint'],'a890')

    def test_with_explicit_sha_and_no_api_digest_is_pinned(self):
        with TemporaryDirectory() as d:
            meta=self.resolve_it(d,api_for(installer_digest=None),setup='c'*64)
            self.assertEqual(meta['source_fingerprint'],'h'+'c'*16)

    def test_release_tags_differ_for_replaced_rolling_asset(self):
        with TemporaryDirectory() as d:
            a=self.resolve_it(d,api_for(asset_id=42))
            b=self.resolve_it(d,api_for(asset_id=43, installer_digest='b'*64))
            self.assertNotEqual(a['release_tag_for_builder'],b['release_tag_for_builder'])

    def test_acquire_verifies_requested_hash_even_without_github_digest(self):
        with TemporaryDirectory() as d:
            d=Path(d)
            content=b'MZ'+b'fixture installer bytes'*10
            expected=hashlib.sha256(content).hexdigest()
            identity=d/'identity.json';dest=d/'setup.exe'
            identity.write_text(json.dumps({'asset_url':'https://github.com/ardia-browser/ardia/releases/download/windows-alpha/Ardia-Setup-x64.exe',
                'asset_size':len(content), 'asset_api_digest':'', 'expected_setup_sha256':'0'*64}))
            def fake_fetch(url,path,token): Path(path).write_bytes(content)
            with patch.object(release,'fetch',side_effect=fake_fetch),patch.object(release,'pe_machine',return_value=0x8664):
                with self.assertRaisesRegex(RuntimeError,'REQUIRED workflow checksum'):
                    release.acquire(argparse.Namespace(identity=str(identity),out=str(dest)))
                value=json.loads(identity.read_text())
                value['expected_setup_sha256']=expected
                identity.write_text(json.dumps(value))
                release.acquire(argparse.Namespace(identity=str(identity),out=str(dest)))
            value=json.loads(identity.read_text())
            self.assertEqual(value['download_sha256'],expected)

    def test_pinned_asset_id_is_rechecked_before_download(self):
        with TemporaryDirectory() as d:
            d=Path(d);ident=d/'identity.json'
            ident.write_text(json.dumps({'asset_id':42,'expected_asset_id':42,
                'asset_name':'Ardia-Setup-x64.exe','asset_size':555,
                'asset_url':'https://github.com/ardia-browser/ardia/releases/download/windows-alpha/Ardia-Setup-x64.exe',
                'asset_api_digest':''}))
            with patch.object(release,'japi',return_value={'id':43,'name':'Ardia-Setup-x64.exe','size':555,'digest':None}), \
                 patch.object(release,'fetch',side_effect=AssertionError('must never download')):
                with self.assertRaisesRegex(RuntimeError,'asset metadata changed'):
                    release.acquire(argparse.Namespace(identity=str(ident),out=str(d/'bad.exe')))

    def test_setup_sha_accepts_github_digest_prefix(self):
        with TemporaryDirectory() as d:
            meta=self.resolve_it(d,api_for(),setup='sha256:'+'A'*64)
            self.assertEqual(meta['expected_setup_sha256'],'a'*64)

    def test_staging_rejects_wrong_upstream_app_exe(self):
        with TemporaryDirectory() as d:
            d=Path(d);root=d/'installed';root.mkdir()
            for name in ('Ardia.exe','chrome.dll','Ardia.ico'): (root/name).write_bytes(b'MZ' + bytes(64))
            launch=d/'ArdiaPortable.exe';launch.write_bytes(b'MZ'+bytes(64))
            opts=launcher_options.manifest_for(launcher_options.DEFAULTS)
            layout=data_layout.manifest_for(True)
            ident=d/'id.json';ident.write_text(json.dumps({'arch':'x64','version':'0.2.47',
                'package_revision':release.REVISION,'release_channel':'stable',
                'expected_app_sha256':'0'*64,'launcher_options':opts,
                'launcher_flags_fingerprint':opts['fingerprint'],'data_layout':layout,
                'data_layout_fingerprint':layout['fingerprint'],
                'portable_data_layout':layout['layout'], 'source_commit':'a'*40}))
            with patch.object(release,'pe_machine',return_value=0x8664):
                with self.assertRaisesRegex(RuntimeError,'REQUIRED workflow checksum'):
                    release.stage(argparse.Namespace(identity=str(ident),install=str(root),
                        launcher=str(launch),out=str(d/'portable')))

    def test_workflow_exposes_all_pins_and_preserves_defaults(self):
        workflow=(ROOT/'.github/workflows/build.yml').read_text(encoding='utf-8')
        for field in ('exact_release_tag:','expected_asset_id:','expected_setup_sha256:',
                      'expected_ardia_exe_sha256:', 'windows_style_data_folders:',
                      'disable_encryption_win:'):
            self.assertIn(field,workflow)
        self.assertLess(workflow.index('python scripts/release.py acquire'),
                        workflow.index('python scripts/release.py install-ci'))
        self.assertIn('PKG_SOURCE_ID',workflow)
        self.assertIn('windows-2022',workflow)
        self.assertIn('vhick/Portable-Package-Builder@v1.0.0',workflow)
        self.assertIn('vhick/portable-release-publisher@v1.1.1',workflow)
        self.assertEqual(workflow.count('type: boolean'),9)
