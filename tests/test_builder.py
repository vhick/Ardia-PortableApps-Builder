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
import launcher_options as opts

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
    def test_launcher_flags_defined_once_and_user_data_stays_prelaunch(self):
        main = (ROOT/'launcher/main.cpp').read_text(encoding='utf-8')
        flags = (ROOT/'launcher/launch_flags.h').read_text(encoding='utf-8')
        self.assertIn('ARDIA_PORTABLE_DEFAULT_FLAGS', main)
        self.assertIn('L" --user-data-dir=" + quote(profile)', main)
        self.assertIn('SetEnvironmentVariableW(L"ARDIA_DATA_DIR", profile.c_str())', main)
        self.assertLess(main.index('SetEnvironmentVariableW(L"ARDIA_DATA_DIR"'), main.index('CreateProcessW('))
        for sw in ('--disable-ardia-update', '--no-default-browser-check',
                   '--disable-logging', '--disable-breakpad', '--disable-machine-id'):
            self.assertIn('L" ' + sw + '"', flags) if sw != '--disable-ardia-update' else self.assertIn('L" ' + sw + '";', flags)
        self.assertEqual(flags.count('L" --no-default-browser-check"'), 1)
        self.assertNotIn('L" --disable-encryption-win"', flags)

    def test_default_option_manifest_matches_checked_workflow_defaults(self):
        import re
        source = (ROOT/'.github/workflows/build.yml').read_text(encoding='utf-8')
        block = source.split('    inputs:', 1)[1].split('permissions:', 1)[0]
        for key, _switch, default, _status in opts.FLAGS:
            pattern = (r'(?m)^      ' + re.escape(key) +
                       r':\n        description:.*\n        type: boolean\n        default: (true|false)$')
            m = re.search(pattern, block)
            self.assertIsNotNone(m, key)
            self.assertEqual(m.group(1), 'true' if default else 'false')
        self.assertEqual(block.count('        type: boolean'), 8)

    def test_flags_combinations_compile_to_exact_allowlisted_strings(self):
        for key, switch, default, _status in opts.FLAGS:
            selections = dict(opts.DEFAULTS)
            selections[key] = not default
            manifest = opts.manifest_for(selections)
            header = opts.header_for(manifest)
            self.assertEqual(switch in manifest['enabled_arguments'], not default)
            self.assertEqual(('L" ' + switch + '"') in header, not default)
            self.assertTrue(header.strip().endswith(';'))
            self.assertNotEqual(manifest['fingerprint'], opts.manifest_for(opts.DEFAULTS)['fingerprint'])

    def test_fully_disabled_options_have_valid_empty_cpp_literal(self):
        data = opts.manifest_for({key: False for key in opts.KEYS})
        self.assertEqual(data['enabled_arguments'], [])
        self.assertIn('    L"";', opts.header_for(data))

    def test_unsafe_input_never_becomes_a_compiler_flag(self):
        self.assertRaises(ValueError, opts.manifest_for, {'arbitrary': True})
        self.assertRaises(ValueError, opts.parse_bool, 'true --bad', 'disable_logging')
        self.assertRaises(ValueError, opts.manifest_for, {k: 'true' for k in opts.KEYS})

    def test_tampered_option_manifest_is_rejected(self):
        data = opts.manifest_for(opts.DEFAULTS)
        data['enabled_arguments'].append('--not-allowed')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            opts.validate_manifest(data)
        data = opts.manifest_for(opts.DEFAULTS)
        data['fingerprint'] = '0'*12
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            opts.validate_manifest(data)

    def test_environment_boolean_parsing_respects_gitHub_values(self):
        import copy
        env = {'ARDIA_OPT_DISABLE_BREAKPAD': 'false',
               'ARDIA_OPT_DISABLE_ENCRYPTION_WIN': 'true'}
        selected = opts.from_environment(env)
        self.assertFalse(selected['disable_breakpad'])
        self.assertTrue(selected['disable_encryption_win'])
        self.assertTrue(selected['no_default_browser_check'])

    def test_generated_header_and_manifest_share_identity(self):
        with tempfile.TemporaryDirectory() as t:
            manifest = Path(t)/'opts.json'
            header = Path(t)/'flags.h'
            env = dict(os.environ, ARDIA_OPT_DISABLE_ARDIA_UPDATE='false',
                       ARDIA_OPT_DISABLE_LOGGING='false')
            out = subprocess.run([sys.executable, str(ROOT/'scripts/launcher_options.py'),
                                  '--out', str(manifest), '--header', str(header)],
                                 env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            data = opts.load_manifest(manifest)
            self.assertNotIn('--disable-logging', data['enabled_arguments'])
            self.assertNotIn('L" --disable-logging"', header.read_text())
            self.assertEqual(header.read_text(), opts.header_for(data))

    def test_workflow_flags_are_generated_before_compilation(self):
        workflow = (ROOT/'.github/workflows/build.yml').read_text(encoding='utf-8')
        self.assertLess(workflow.index('python scripts/launcher_options.py'),
                        workflow.index('./scripts/build-launcher.ps1'))
        self.assertIn(' --launcher-options work/launcher-options.json', workflow)
        self.assertIn('b1r5_f$($env:PKG_OPTIONS_ID).zip', workflow)
        self.assertIn('package-revision: b1r5-f${{ env.PKG_OPTIONS_ID }}', workflow)
        self.assertIn('PKG_OPTIONS_ID=$($m.launcher_flags_fingerprint)', workflow)
        self.assertEqual(workflow.count('type: boolean'), 8)

    def test_packaging_only_reuses_existing_compiled_switches(self):
        text = (ROOT/'.github/workflows/package-only.yml').read_text()
        self.assertNotIn('ARDIA_OPT_', text)
        self.assertNotIn('launcher_options.py', text)
        self.assertIn('verify-existing-zip.py', text)

    def test_distinct_checkbox_combinations_create_distinct_release_tags(self):
        import argparse
        fake_commit = 'abcdef1234567890abcdef1234567890abcdef12'
        base = {'body': 'Ardia 0.2.47-nightly.7 for Windows, build 7661 (commit `abcdef1`)',
                'draft': False, 'prerelease': True,
                'assets': [{'name': 'Ardia-Setup-x64.exe', 'size': 32000000,
                            'browser_download_url': 'https://github.com/ardia-browser/ardia/releases/download/windows-alpha/Ardia-Setup-x64.exe',
                            'id': 123456}]}
        def fake_api(endpoint, token):
            if endpoint == '/releases/tags/windows-alpha': return base
            if endpoint == '/commits/abcdef1': return {'sha': fake_commit}
            if endpoint == '/commits/v0.2.47-nightly.7': return {'sha': fake_commit}
            if endpoint.startswith('/contents/pnpm-lock.yaml?ref='): return {'sha': 'f'*40}
            raise AssertionError('unexpected ' + endpoint)
        with tempfile.TemporaryDirectory() as d, patch.object(r, 'japi', side_effect=fake_api):
            results=[]
            for enable in (True, False):
                selections = dict(opts.DEFAULTS)
                selections['disable_logging'] = enable
                manifest = opts.manifest_for(selections)
                options_file = Path(d, 'flags.json')
                options_file.write_text(json.dumps(manifest), encoding='utf-8')
                identity_file = Path(d, 'identity.json')
                r.resolve(argparse.Namespace(launcher_options=str(options_file), identity=str(identity_file), arch='x64', version=''))
                identity = json.loads(identity_file.read_text(encoding='utf-8'))
                self.assertEqual(identity['launcher_options'], manifest)
                self.assertTrue(identity['release_tag_for_builder'].endswith('b1r5-f' + manifest['fingerprint']))
                results.append(identity['release_tag_for_builder'])
            self.assertNotEqual(results[0], results[1])

    def test_staged_manifest_must_match_identity(self):
        import argparse
        with tempfile.TemporaryDirectory() as d:
            root = Path(d,'ArdiaPortable')
            required=['ArdiaPortable.exe', 'App/AppInfo/appinfo.ini', 'App/AppInfo/appicon.ico',
                      'App/AppInfo/appicon_16.png', 'App/AppInfo/appicon_32.png',
                      'App/Ardia/Ardia.exe','App/Ardia/chrome.dll','Other/Source/LICENSE',
                      'Other/Source/NOTICE','Other/Source/build-identity.json']
            for rel in required:
                file = root/rel
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b'MZ')
            (root/'Data/Profile').mkdir(parents=True)
            (root/'App/AppInfo/appinfo.ini').write_text('[Details]\nAppID=ArdiaBrowserPortableCommunity\n[Control]\nStart=ArdiaPortable.exe\n')
            manifest = opts.manifest_for(opts.DEFAULTS)
            meta = {'arch': 'x64', 'package_revision': 'b1r5', 'launcher_options': manifest,
                    'launcher_flags_fingerprint': manifest['fingerprint'],
                    'upstream_app_exe_sha256': r.sha256(root/'App/Ardia/Ardia.exe'),
                    'launcher_sha256': r.sha256(root/'ArdiaPortable.exe')}
            identity = Path(d,'identity.json'); identity.write_text(json.dumps(meta))
            (root/'Other/Source/launcher-options.json').write_text(json.dumps(manifest))
            with patch.object(r,'pe_machine',return_value=0x8664):
                r.validate(argparse.Namespace(identity=str(identity),root=str(root)))
                broken = dict(manifest)
                broken['fingerprint']='b'*12
                (root/'Other/Source/launcher-options.json').write_text(json.dumps(broken))
                with self.assertRaisesRegex(ValueError, 'mismatch'):
                    r.validate(argparse.Namespace(identity=str(identity),root=str(root)))

    def test_compiled_binary_flag_fixture_verification(self):
        import verify_launcher_flags as verifier
        with tempfile.TemporaryDirectory() as d:
            selection = dict(opts.DEFAULTS)
            selection['disable_ardia_update'] = False
            selection['disable_machine_id'] = False
            manifest = opts.manifest_for(selection)
            flags_json = Path(d, 'flags.json')
            flags_json.write_text(json.dumps(manifest), encoding='utf-8')
            good = Path(d, 'launcher.exe')
            wide = ''.join(' ' + arg for arg in manifest['enabled_arguments']).encode('utf-16le')
            good.write_bytes(b'MZ' + bytes(200) + wide + bytes(12))
            verifier.check(good, flags_json)
            good.write_bytes(b'MZ' + bytes(200) + wide + ' --disable-machine-id'.encode('utf-16le'))
            with self.assertRaisesRegex(ValueError, 'disabled flag'):
                verifier.check(good, flags_json)
            good.write_bytes(b'MZ' + bytes(200) + b'no flags')
            with self.assertRaisesRegex(ValueError, 'selected UTF-16'):
                verifier.check(good, flags_json)

    def test_windows_workflow_pins_supported_toolchain(self):
        workflow = (ROOT/'.github/workflows/build.yml').read_text(encoding='utf-8')
        self.assertIn('runs-on: windows-2022', workflow)
        self.assertIn('./scripts/build-launcher.ps1 -Architecture $env:PKG_ARCH', workflow)
        self.assertNotIn('runs-on: windows-2025', workflow)
        # Flags/checkmarks remain active and are generated before compilation.
        self.assertLess(workflow.index('scripts/launcher_options.py'), workflow.index('./scripts/build-launcher.ps1'))

    def test_build_script_probes_real_msvc_before_cmake(self):
        build = (ROOT/'scripts/build-launcher.ps1').read_text(encoding='utf-8')
        for required in ("-all -prerelease", "'[17.0,18.0)'", "VC/Tools/MSVC", 
                         "bin/Hostx64/$hostTarget/cl.exe", "vcvarsall.bat", 
                         "Microsoft Visual Studio/2022/Enterprise", "Visual Studio 17 2022", 
                         "CMAKE_GENERATOR_INSTANCE:PATH", "-A $platform"):
            self.assertIn(required, build)
        self.assertLess(build.index('cl.exe'), build.index('cmake -S launcher'))
        self.assertNotIn('Visual Studio 18 2026', build)

    def test_workflow_uses_safe_architecture_choices_and_no_compiler_download(self):
        workflow = (ROOT/'.github/workflows/build.yml').read_text(encoding='utf-8')
        self.assertIn('options: [x64, arm64]', workflow)
        script = (ROOT/'scripts/build-launcher.ps1').read_text(encoding='utf-8')
        self.assertIn("[ValidateSet('x64', 'arm64')]", script)
        self.assertIn("if ($Architecture -eq 'arm64') { 'ARM64' } else { 'x64' }", script)
        self.assertNotIn('Invoke-WebRequest', script)
        self.assertNotIn('Install-Module', script)

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
