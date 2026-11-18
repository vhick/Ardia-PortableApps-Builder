"""Fully offline fixtures for official Windows engine/setup provenance. No GitHub API needed."""
import base64
import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ardia_resolver_b1r4', ROOT / 'scripts/resolve.py')
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


def release(tag, *, stable=False):
    version = tag.removeprefix('v')
    name=f'Ardia-{version}-windows-x64-setup.exe'
    return {'tag_name': tag, 'draft': False, 'prerelease': not stable,
            'assets': [{'name': name,'id': 43210,
                        'size': 80_000_000, 'state': 'uploaded',
                        'digest': 'sha256:' + 'a'*64,
                        'browser_download_url': 'https://github.com/ardia-browser/ardia/releases/download/' + tag + '/' + name}]}


def prebuilt(engine_name, sha='a'*64):
    raw = json.dumps({'release': engine_name, 'chromium': '157.0.8103.38',
                      'x64': {'asset': 'ardia-engine-win-x64.zip', 'sha256': sha}}).encode('utf8')
    return {'type':'file', 'encoding':'base64','content':base64.b64encode(raw).decode('ascii'),
            'sha': '1'*40}


def engine(name, sha='a'*64, *, state='uploaded'):
    return {'tag_name': name, 'draft': False,
            'assets':[{'name':'ardia-engine-win-x64.zip','size':400_000_000,
                       'state':state, 'digest':'sha256:'+sha}]}


class EnginePreflightTests(unittest.TestCase):
    def test_404_missing_engine_falls_back_to_older_exact_tag(self):
        newer, older = release('v0.2.47-nightly.5'), release('v0.2.47-nightly.4')
        mapping = {
            '/commits/v0.2.47-nightly.5': {'sha':'a'*40},
            '/commits/v0.2.47-nightly.4': {'sha':'b'*40},
            '/contents/scripts/windows/engine/prebuilt.json?ref='+'a'*40: prebuilt('windows-engine-20261116-4'),
            '/contents/scripts/windows/engine/prebuilt.json?ref='+'b'*40: prebuilt('windows-engine-20261116-2','b'*64),
            '/releases/tags/windows-engine-20261116-4': None,
            '/releases/tags/windows-engine-20261116-2': engine('windows-engine-20261116-2','b'*64),
        }
        with patch.object(resolver,'api',side_effect=lambda path,allow_404=False:mapping[path]):
            selected, sha, manifest, asset, skipped = resolver.choose([newer,older],'nightly','')
        self.assertEqual(selected['tag_name'],newer['tag_name'])
        self.assertEqual(sha,'a'*40)
        self.assertEqual(manifest['release'],'windows-engine-20261116-4')
        self.assertEqual(asset['size'],80_000_000)
        self.assertEqual(asset['method'],'official_setup')
        self.assertEqual(skipped[0][0],newer['tag_name'])

    def test_no_engine_returns_no_candidate(self):
        r = release('v0.2.47-nightly.5')
        mapping = {'/commits/v0.2.47-nightly.5': {'sha':'a'*40},
                   '/contents/scripts/windows/engine/prebuilt.json?ref='+'a'*40: prebuilt('windows-engine-20261116-4'),
                   '/releases/tags/windows-engine-20261116-4': None}
        with patch.object(resolver,'api',side_effect=lambda path,allow_404=False:mapping[path]):
            selected, _, _, _, notes = resolver.choose([r],'nightly','')
        self.assertEqual(selected['tag_name'], r['tag_name'])
        self.assertIn('OFFICIAL SETUP', notes[0][1].upper())

    def test_missing_matching_asset_skips_candidate(self):
        m = {'release': 'windows-engine-20261116-4', 'asset':'ardia-engine-win-x64.zip','sha256':'a'*64}
        with patch.object(resolver,'api',return_value={'tag_name':m['release'],'assets':[]}):
            found, problem = resolver.check_engine(m,cache={})
        self.assertIsNone(found)
        self.assertIn('no uploaded',problem)

    def test_engine_digest_mismatch_not_accepted(self):
        m = {'release':'windows-engine-20261116-4','asset':'ardia-engine-win-x64.zip','sha256':'a'*64}
        with patch.object(resolver,'api',return_value=engine(m['release'],'b'*64)):
            with self.assertRaisesRegex(RuntimeError,'digest conflicts'):
                resolver.check_engine(m,cache={})

    def test_manifest_requires_valid_paths_and_pinned_sha256(self):
        with patch.object(resolver,'api',return_value=prebuilt('windows-engine-20261116-4','b'*64)):
            info=resolver.manifest_for_commit('a'*40)
        self.assertEqual(info['sha256'],'b'*64)
        self.assertEqual(len(info['manifest_sha256']),64)
        for bad in ('../evil.zip','ardia-engine-win-arm64.zip'):
            with self.subTest(bad=bad):
                doc={'release':'windows-engine-20261116-4','x64':{'asset':bad,'sha256':'a'*64}}
                obj={'type':'file','encoding':'base64','content':base64.b64encode(json.dumps(doc).encode()).decode()}
                with patch.object(resolver,'api',return_value=obj):
                    with self.assertRaises(RuntimeError):resolver.manifest_for_commit('a'*40)

    def test_permission_error_is_not_fallback(self):
        r=release('v0.2.47-nightly.5')
        def blocked(path,allow_404=False):
            if path.startswith('/releases/tags/'):
                raise RuntimeError('GitHub API HTTP 403: rate limit exceeded')
            if path.startswith('/commits/'):return {'sha':'a'*40}
            return prebuilt('windows-engine-20261116-4')
        with patch.object(resolver,'api',side_effect=blocked):
            with self.assertRaisesRegex(RuntimeError,'HTTP 403'):
                resolver.choose([r],'nightly','')

    def test_404_is_only_ignored_when_explicitly_allowed(self):
        error=urllib.error.HTTPError('https://api.github.com/test',404,'Not found',{},None)
        with patch.object(resolver.urllib.request,'urlopen',side_effect=error):
            self.assertIsNone(resolver.api('/releases/tags/absent',allow_404=True))
        error2=urllib.error.HTTPError('https://api.github.com/test',403,'Forbidden',{},None)
        with patch.object(resolver.urllib.request,'urlopen',side_effect=error2):
            with self.assertRaisesRegex(RuntimeError,'HTTP 403'):
                resolver.api('/releases/tags/absent',allow_404=True)

    def test_auto_stable_first_then_nightly(self):
        st=release('v0.2.46',stable=True)
        nightly=release('v0.2.47-nightly.5')
        self.assertEqual(resolver.candidate_order([nightly,st],'auto'),[st,nightly])
        self.assertEqual(resolver.candidate_order([st,nightly],'nightly'),[nightly,st])

    def test_explicit_requested_does_not_select_older_release(self):
        rnew=release('v0.2.47-nightly.5')
        rold=release('v0.2.47-nightly.4')
        def fake(path,allow_404=False):
            if path.startswith('/releases?'):return [rnew,rold]
            if path.startswith('/commits/'):return {'sha':'a'*40}
            if path.startswith('/contents/'):return prebuilt('windows-engine-20261116-4')
            if path.startswith('/releases/tags/'):return None
            raise AssertionError(path)
        with patch.object(resolver,'api',side_effect=fake):
            selected, _, _, meta, _ = resolver.resolve('nightly','v0.2.47-nightly.5')
        self.assertEqual(selected['tag_name'],'v0.2.47-nightly.5')
        self.assertEqual(meta['method'],'official_setup')

    def test_reject_release_with_setup_asset_but_no_engine_manifest(self):
        r = release('v0.2.47-nightly.5')
        def fake(path,allow_404=False):
            if path.startswith('/commits/'):return {'sha':'a'*40}
            return None
        with patch.object(resolver,'api',side_effect=fake):
            selection=resolver.choose([r],'nightly','')
        self.assertIsNone(selection[0])
        self.assertIn('prebuilt.json',selection[-1][0][1])


    def test_official_setup_requires_published_sha256_and_exact_url(self):
        good=release('v0.2.47-nightly.5')
        selected,reason=resolver.check_setup(good)
        self.assertEqual(selected['method'],'official_setup')
        self.assertIsNone(reason)
        for attribute,invalid in (('digest',None),('browser_download_url','https://evil.invalid/x'),('id',None)):
            with self.subTest(attribute=attribute):
                obj=release('v0.2.47-nightly.5')
                obj['assets'][0][attribute]=invalid
                item,reason=resolver.check_setup(obj)
                self.assertIsNone(item)
                self.assertIsNotNone(reason)

    def test_matching_public_engine_preferred_to_official_setup(self):
        newer=release('v0.2.47-nightly.5')
        mapping={
            '/commits/v0.2.47-nightly.5': {'sha':'a'*40},
            '/contents/scripts/windows/engine/prebuilt.json?ref='+'a'*40: prebuilt('windows-engine-20261116-4'),
            '/releases/tags/windows-engine-20261116-4': engine('windows-engine-20261116-4')}
        with patch.object(resolver,'api',side_effect=lambda path,allow_404=False:mapping[path]):
            selected,sha,manifest,asset,notes=resolver.choose([newer],'nightly','')
        self.assertEqual(asset['method'],'prebuilt_engine')
        self.assertEqual(asset['size'],400_000_000)
        self.assertFalse(notes)

    def test_missing_engine_and_missing_setup_digest_skip_candidate(self):
        r=release('v0.2.47-nightly.5')
        r['assets'][0]['digest']=None
        mapping={'/commits/v0.2.47-nightly.5': {'sha':'a'*40},
                 '/contents/scripts/windows/engine/prebuilt.json?ref='+'a'*40: prebuilt('windows-engine-20261116-4'),
                 '/releases/tags/windows-engine-20261116-4': None}
        with patch.object(resolver,'api',side_effect=lambda path,allow_404=False:mapping[path]):
            selected,_,_,_,reasons=resolver.choose([r],'nightly','')
        self.assertIsNone(selected)
        self.assertIn('SHA-256',reasons[0][1])


if __name__ == '__main__':
    unittest.main()
