import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
resolver=module('resolve')
class ResolveTests(unittest.TestCase):
    def test_sort_numeric(self):
        self.assertGreater(resolver.key({'tag_name':'v0.2.10-nightly.4'}),resolver.key({'tag_name':'v0.2.9-nightly.40'}))
    def test_reject_unversioned(self):
        self.assertIsNone(resolver.TAG.fullmatch('windows-alpha'))
    def test_only_specific_windows_asset(self):
        r={'tag_name':'v0.2.47-nightly.3','assets':[{'name':'Ardia-0.2.47-nightly.3-windows-x64-setup.exe','size':2300000}]}
        self.assertEqual(resolver.asset(r)['name'],r['assets'][0]['name'])
    def test_no_unverified_names(self):
        r={'tag_name':'v0.2.47-nightly.3','assets':[{'name':'Setup.exe','size':2300000}]}
        self.assertIsNone(resolver.asset(r))
class BuilderRevisionTests(unittest.TestCase):
    def test_kit_uses_b1r6_everywhere(self):
        files=['scripts/resolve.py','.github/workflows/build.yml','scripts/stage.ps1']
        for file in files:
            self.assertIn('b1r6',(ROOT/file).read_text(encoding='utf-8'),file)
    def test_launcher_arguments_are_wired(self):
        source=(ROOT/'launcher/ArdiaPortable.cpp').read_text(encoding='utf-8')
        self.assertIn('ardia_portable::BuildBrowserArguments(forwarded,useDefaultFlags)',source)
        self.assertIn('--portable-no-default-flags',source)
        self.assertIn('args+=L" "+q(flag)',source)
        self.assertIn('ARDIA_DATA_DIR',source)
    def test_post_checkout_manifest_hash_is_enforced(self):
        source=(ROOT/'scripts/verify-source-content.py').read_text(encoding='utf-8')
        wrapper=(ROOT/'scripts/verify-upstream.ps1').read_text(encoding='utf-8')
        self.assertIn('engine_manifest_sha256',source)
        self.assertIn('engine_sha256',source)
        self.assertIn('git_blob', source)
        self.assertIn('verify-source-content.py', wrapper)
        self.assertIn('$LASTEXITCODE -ne 0', wrapper)
        self.assertIn('engine_source', (ROOT/'scripts/resolve.py').read_text())
        self.assertIn('official_setup', (ROOT/'.github/workflows/build.yml').read_text())
        self.assertIn('downloaded_setup_sha256', (ROOT/'scripts/validate.py').read_text())
        self.assertIn('engine_release',source)
        workflow=(ROOT/'.github/workflows/build.yml').read_text(encoding='utf-8')
        self.assertLess(workflow.index('Preflight Windows release'),workflow.index('Install upstream pinned pnpm'))
        self.assertLess(workflow.index('Verify source SHA and lockfile identity'),workflow.index('Compile real Ardia Windows application'))
        self.assertIn('package-revision: b1r6',workflow)
    def test_packaged_source_includes_helper(self):
        self.assertIn('ArdiaLaunchFlags.h',(ROOT/'scripts/stage.ps1').read_text(encoding='utf-8'))
        self.assertIn('ArdiaLaunchFlags.h',(ROOT/'scripts/validate.py').read_text(encoding='utf-8'))
    def test_official_setup_is_reverified_before_compilation(self):
        workflow=(ROOT/'.github/workflows/build.yml').read_text(encoding='utf-8')
        self.assertLess(workflow.index('Download and SHA256-verify official'),workflow.index('Compile real Ardia Windows application'))
        self.assertIn('Get-FileHash', (ROOT/'scripts/download-official-setup.ps1').read_text())
        self.assertIn('engine_chromium', (ROOT/'scripts/engine-from-official-setup.ps1').read_text())
        self.assertIn('CompiledApp', (ROOT/'scripts/engine-from-official-setup.ps1').read_text())
if __name__=='__main__':unittest.main()
