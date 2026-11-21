"""Fixture-based checks of SHA-256-to-official-Windows-asset lookup.

No actual GitHub downloads or Windows graphical tests are performed.
"""
import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import release, data_layout, launcher_options

COMMIT='e4e0893'+'e'*33
LOCK='f'*40

def asset(tag,version,digest,arch='x64',id=5):
    name=('Ardia-Setup-'+arch+'.exe') if tag=='windows-alpha' else 'Ardia-'+version+'-windows-'+arch+'-setup.exe'
    return {'name':name,'size':30000000,'id':id,'digest':('sha256:'+digest) if digest else None,
            'browser_download_url':f'https://github.com/ardia-browser/ardia/releases/download/{tag}/{name}'}

def rel(tag,prerelease,assets,body=''):
    return {'tag_name':tag,'draft':False,'prerelease':prerelease,'assets':assets,'body':body}

class ExactHashDiscovery(TestCase):
    def fixtures(self,root):
        root=Path(root);o=root/'opts.json';l=root/'layout.json';identity=root/'id.json'
        o.write_text(json.dumps(launcher_options.manifest_for(launcher_options.DEFAULTS)))
        l.write_text(json.dumps(data_layout.manifest_for(True)))
        return o,l,identity
    def run_with(self,releases,channel,hash,tag='',version='',asset_id=''):
        with TemporaryDirectory() as temp:
            opts,lay,identity=self.fixtures(temp)
            def japi(endpoint,token):
                if endpoint.startswith('/releases?per_page='):
                    return releases if endpoint.endswith('page=1') else []
                if endpoint.startswith('/releases/tags/'):
                    t=endpoint.split('/')[-1]
                    return next(r for r in releases if r['tag_name']==t)
                if endpoint.startswith('/commits/'):
                    return {'sha':COMMIT}
                if endpoint.startswith('/contents/pnpm-lock.yaml?'):
                    return {'sha':LOCK}
                raise AssertionError(endpoint)
            with patch.object(release,'japi',side_effect=japi):
                release.resolve(argparse.Namespace(channel=channel,arch='x64',version=version,
                    release_tag=tag,expected_setup_sha256=hash,expected_app_sha256='',
                    expected_asset_id=asset_id,launcher_options=str(opts),data_layout=str(lay),identity=str(identity)))
            return json.loads(identity.read_text())
    def test_setup_hash_finds_stable_asset_not_newest(self):
        rs=[rel('v0.2.48',False,[asset('v0.2.48','0.2.48','b'*64)]),
            rel('v0.2.47',False,[asset('v0.2.47','0.2.47','a'*64)])]
        m=self.run_with(rs,'stable','a'*64)
        self.assertEqual(m['release_tag'],'v0.2.47')
        self.assertEqual(m['expected_setup_sha256'],'a'*64)
        self.assertTrue(m['installer_sha_lookup_used'])
    def test_setup_hash_finds_rolling_alpha(self):
        body='Ardia 0.2.47 for Windows, build 7929 (commit `e4e0893`).'
        rs=[rel('windows-alpha',True,[asset('windows-alpha','0.2.47','a'*64)],body),
            rel('v0.2.47-nightly.9',True,[asset('v0.2.47-nightly.9','0.2.47-nightly.9','b'*64)])]
        m=self.run_with(rs,'prerelease','a'*64)
        self.assertEqual(m['build'],7929)
        self.assertEqual(m['release_tag'],'windows-alpha')
        self.assertTrue(m['installer_sha_lookup_used'])
    def test_no_stable_fallback_to_prerelease(self):
        rs=[rel('windows-alpha',True,[asset('windows-alpha','0.2.47','a'*64)])]
        with self.assertRaisesRegex(RuntimeError,'No matching official stable'):
            self.run_with(rs,'stable','a'*64)
    def test_no_digest_not_assumed_to_match(self):
        rs=[rel('v0.2.47',False,[asset('v0.2.47','0.2.47',None)])]
        with self.assertRaisesRegex(RuntimeError,'No matching official'):
            self.run_with(rs,'stable','a'*64)
    def test_different_checksum_not_silently_substituted(self):
        rs=[rel('v0.2.47',False,[asset('v0.2.47','0.2.47','b'*64)])]
        with self.assertRaisesRegex(RuntimeError,'No matching official'):
            self.run_with(rs,'stable','a'*64)
    def test_identical_hash_on_multiple_releases_requires_disambiguation(self):
        rs=[rel('v0.2.47',False,[asset('v0.2.47','0.2.47','a'*64)]),
            rel('v0.2.46',False,[asset('v0.2.46','0.2.46','a'*64)])]
        with self.assertRaisesRegex(RuntimeError,'matches multiple releases'):
            self.run_with(rs,'stable','a'*64)
    def test_explicit_tag_never_redirected_by_sha(self):
        rs=[rel('v0.2.47',False,[asset('v0.2.47','0.2.47','a'*64)]),
            rel('v0.2.46',False,[asset('v0.2.46','0.2.46','b'*64)])]
        with self.assertRaisesRegex(RuntimeError,'differs from official'):
            self.run_with(rs,'stable','b'*64,tag='v0.2.47')
    def test_requested_version_is_strict_constraint(self):
        rs=[rel('v0.2.47',False,[asset('v0.2.47','0.2.47','a'*64)]),
            rel('v0.2.46',False,[asset('v0.2.46','0.2.46','b'*64)])]
        with self.assertRaisesRegex(RuntimeError,'differs from official'):
            self.run_with(rs,'stable','b'*64,version='0.2.47')
    def test_matching_expected_asset_id(self):
        rs=[rel('v0.2.47',False,[asset('v0.2.47','0.2.47','a'*64,id=12345)])]
        m=self.run_with(rs,'stable','a'*64,asset_id='12345')
        self.assertEqual(m['asset_id'],12345)
    def test_wrong_asset_id_rejected(self):
        rs=[rel('v0.2.47',False,[asset('v0.2.47','0.2.47','a'*64,id=12345)])]
        with self.assertRaisesRegex(RuntimeError,'asset ID differs'):
            self.run_with(rs,'stable','a'*64,asset_id='12346')
