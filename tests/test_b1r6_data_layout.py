"""Static and fixture validation of v2 Windows-mirror data layout.

These tests intentionally do NOT claim browser runtime confinement or successful
Windows MSVC compilation. The launcher C++ is compiled in GitHub Actions.
"""
import argparse
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('release_v2', ROOT/'scripts/release.py')
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)


class WindowsMirrorTests(unittest.TestCase):
    def _fixture(self, workspace, legacy=False):
        dest=workspace/'ArdiaPortable'
        for x in ['ArdiaPortable.exe', 'App/Ardia/Ardia.exe', 'App/Ardia/chrome.dll',
                  'App/AppInfo/appicon.ico', 'App/AppInfo/appicon_16.png',
                  'App/AppInfo/appicon_32.png','Other/Source/LICENSE','Other/Source/NOTICE',
                  'Other/Source/build-identity.json']:
            p=dest/x; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b'MZ' + bytes(90))
        for x in (['Data/Profile'] if legacy else ['Data/Local/Ardia/User Data','Data/Roaming/Ardia']):
            (dest/x).mkdir(parents=True)
        (dest/'App/AppInfo/appinfo.ini').write_text('[Details]\nAppID=ArdiaBrowserPortableCommunity\n[Control]\nStart=ArdiaPortable.exe\n',encoding='utf-8')
        from sys import path
        path.insert(0,str(ROOT/'scripts'))
        import launcher_options as opts
        manifest=opts.manifest_for(opts.DEFAULTS)
        ident={'arch':'x64','package_revision':'b1r5' if legacy else 'b1r6',
               'portable_data_layout':'legacy-profile-v1' if legacy else 'windows-appdata-mirror-v2',
               'launcher_options':manifest, 'launcher_flags_fingerprint':manifest['fingerprint'],
               'upstream_app_exe_sha256':R.sha256(dest/'App/Ardia/Ardia.exe'),
               'launcher_sha256':R.sha256(dest/'ArdiaPortable.exe')}
        if not legacy: (dest/'Other/Source/launcher-options.json').write_text(json.dumps(manifest),encoding='utf-8')
        identity=workspace/'identity.json';identity.write_text(json.dumps(ident),encoding='utf-8')
        return dest,identity

    def test_fresh_staged_layout_matches_windows_folders(self):
        import launcher_options as opts
        with TemporaryDirectory() as temp:
            work=Path(temp); origin=work/'original'
            origin.mkdir()
            for name in ['Ardia.exe','chrome.dll','Ardia.ico']:
                (origin/name).write_bytes(b'MZ'+bytes(90))
            launcher=work/'root-launcher.exe';launcher.write_bytes(b'MZ'+bytes(90))
            ident=work/'identity.json'
            manifest=opts.manifest_for(opts.DEFAULTS)
            ident.write_text(json.dumps({'arch':'x64','package_revision':'b1r6',
                'portable_data_layout':'windows-appdata-mirror-v2',
                'version':'0.2.47-nightly.7', 'source_commit':'a'*40,
                'launcher_options':manifest,'launcher_flags_fingerprint':manifest['fingerprint']}),encoding='utf-8')
            def fake_fetch(url,out):
                Path(out).write_text('fixture attribution only',encoding='utf-8')
            with patch.object(R,'pe_machine',return_value=0x8664), patch.object(R,'fetch',side_effect=fake_fetch):
                R.stage(argparse.Namespace(identity=str(ident),install=str(origin),launcher=str(launcher),out=str(work/'ArdiaPortable')))
            out=work/'ArdiaPortable'
            self.assertTrue((out/'Data/Local/Ardia/User Data').is_dir())
            self.assertTrue((out/'Data/Roaming/Ardia').is_dir())
            self.assertFalse((out/'Data/Profile').exists())
            self.assertTrue((out/'Other/Source/UPGRADE-AND-LINKS.md').is_file())
            self.assertEqual(json.loads(ident.read_text())['portable_data_layout'],'windows-appdata-mirror-v2')
            for png in ('appicon_16.png','appicon_32.png'):
                (out/'App/AppInfo'/png).write_bytes(b'png-fixture')
            with patch.object(R,'pe_machine',return_value=0x8664):
                R.validate(argparse.Namespace(identity=str(ident),root=str(out)))
            zfile=work/'out.zip';R.makezip(argparse.Namespace(root=str(out),out=str(zfile)))
            with zipfile.ZipFile(zfile) as z:
                self.assertIn('ArdiaPortable/Data/Local/Ardia/User Data/',z.namelist())
                self.assertIn('ArdiaPortable/Data/Roaming/Ardia/',z.namelist())
                self.assertNotIn('ArdiaPortable/Data/Profile/',z.namelist())

    def test_v2_validation_refuses_missing_roaming_folder(self):
        with TemporaryDirectory() as temp:
            folder,ident=self._fixture(Path(temp))
            (folder/'Data/Roaming/Ardia').rmdir()
            with self.assertRaisesRegex(RuntimeError,'Data/Roaming/Ardia'):
                R.validate(argparse.Namespace(identity=str(ident),root=str(folder)))

    def test_older_zip_is_still_accepted_for_packaging_only(self):
        with TemporaryDirectory() as temp:
            folder,ident=self._fixture(Path(temp),legacy=True)
            with patch.object(R,'pe_machine',return_value=0x8664):
                R.validate(argparse.Namespace(identity=str(ident),root=str(folder)))

    def test_launcher_env_and_profile_paths_are_set_before_createprocess(self):
        source=(ROOT/'launcher/main.cpp').read_text(encoding='utf-8')
        for fragment in ('data + L"\\\\Local"', 'localRoot + L"\\\\Ardia"',
                         'localArdia + L"\\\\User Data"', 'data + L"\\\\Roaming"',
                         'roamingRoot + L"\\\\Ardia"',
                         'SetEnvironmentVariableW(L"ARDIA_DATA_DIR", ardiaData.c_str())',
                         'SetEnvironmentVariableW(L"LOCALAPPDATA", localRoot.c_str())',
                         'SetEnvironmentVariableW(L"APPDATA", roamingRoot.c_str())'):
            self.assertIn(fragment,source)
        start=source.index('CreateProcessW(')
        for env in ('ARDIA_DATA_DIR','LOCALAPPDATA','APPDATA'):
            self.assertLess(source.index('SetEnvironmentVariableW(L"'+env),start)
        self.assertIn('L" --user-data-dir=" + quote(profile)',source)
        self.assertNotIn('SHSetKnownFolderPath',source)

    def test_launcher_fails_closed_on_ambiguous_mixed_profiles_and_links(self):
        source=(ROOT/'launcher/main.cpp').read_text(encoding='utf-8')
        self.assertIn('if (legacyHasData && mirrorHasData)',source)
        self.assertIn('Refusing to merge them',source)
        self.assertIn('const bool useLegacy = !windowsMirror || legacyHasData',source)
        self.assertIn('useLegacy ? legacyProfile : newProfile',source)
        self.assertIn('FILE_ATTRIBUTE_REPARSE_POINT',source)
        self.assertIn('mkRealDir(newProfile)',source)
        self.assertNotIn('MoveFileExW(',source)
        self.assertNotIn('DeleteFileW(',source)
        self.assertNotIn('RemoveDirectoryW(',source)

    def test_optional_shared_profile_detects_other_ardia_process(self):
        source=(ROOT/'launcher/main.cpp').read_text(encoding='utf-8')
        self.assertIn('isReparseDir(hostLocal + L"\\\\Ardia")',source)
        self.assertIn('isReparseDir(hostRoaming + L"\\\\Ardia")',source)
        self.assertIn('sharedHostProfile && anotherArdiaRunning(app)',source)
        self.assertIn('Close all installed Ardia processes',source)

    def test_installer_preservation_test_points_to_new_layout(self):
        code=(ROOT/'scripts/test-installer.ps1').read_text(encoding='utf-8')
        self.assertIn("$profileRoot = Join-Path $dest 'Data/Local/Ardia/User Data'",code)
        self.assertIn("$required = Join-Path $dest 'Data/Roaming/Ardia'",code)
        self.assertIn("$empty = Join-Path $profileRoot 'Empty/Nested/Leaves'", code)
        self.assertIn("$required = Join-Path $dest 'Data/Profile'",code)

    def test_docs_link_host_to_portable_not_reverse(self):
        doc=(ROOT/'docs/UPGRADE-AND-LINKS.md').read_text(encoding='utf-8')
        self.assertIn('mklink /J "%LOCALAPPDATA%\\Ardia" "D:\\PortableApps\\ArdiaPortable\\Data\\Local\\Ardia"',doc)
        self.assertIn('mklink /J "%APPDATA%\\Ardia" "D:\\PortableApps\\ArdiaPortable\\Data\\Roaming\\Ardia"',doc)
        self.assertIn('Do not run them at the same time',doc)
        self.assertIn('Data\\Profile-b1r5-backup',doc)

if __name__ == '__main__': unittest.main()
