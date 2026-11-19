import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class MsvcIntegrationTests(unittest.TestCase):
    def test_hosted_runner_uses_documented_vs2022_image(self):
        w=(ROOT/'.github/workflows/build.yml').read_text(encoding='utf8')
        self.assertIn('runs-on: windows-2022',w)
        self.assertNotIn('runs-on: windows-latest',w)
    def test_compiler_probe_precedes_setup_download_and_build(self):
        w=(ROOT/'.github/workflows/build.yml').read_text(encoding='utf8')
        self.assertLess(w.index('Verify Windows x64 MSVC toolchain'),w.index('Download and SHA256-verify official'))
        self.assertLess(w.index('Verify Windows x64 MSVC toolchain'),w.index('Compile real Ardia Windows application'))
    def test_shared_vswhere_discovery_with_safe_fallback(self):
        s=(ROOT/'scripts/msvc-tools.ps1').read_text(encoding='utf8')
        self.assertIn("'Microsoft.VisualStudio.Component.VC.Tools.x86.x64'",s)
        self.assertIn("'-all', '-products', '*'",s)
        self.assertIn('vcvars64.bat',s)
        self.assertIn(r'bin\Hostx64\x64\cl.exe',s)
        self.assertIn('Find-ArdiaMsvcVcvars',s)
        self.assertIn('throw',s)
    def test_toolchain_scripts_reuse_shared_locator_and_check_exit(self):
        for name in ['verify-msvc.ps1','test-launch-flags.ps1','compile-launcher.ps1']:
            with self.subTest(script=name):
                s=(ROOT/'scripts'/name).read_text(encoding='utf8')
                self.assertIn('msvc-tools.ps1',s)
                self.assertIn('Find-ArdiaMsvcVcvars',s)
                self.assertIn('where.exe cl.exe',s)
                self.assertIn('Invoke-ArdiaMsvcBatch -Script $batch',s)
                self.assertNotIn('& cmd.exe /d /c',s)
                self.assertIn('$code',s)
    def test_batch_runner_uses_raw_process_arguments_with_double_wrapping(self):
        s=(ROOT/'scripts/msvc-tools.ps1').read_text(encoding='utf8')
        self.assertIn('function Invoke-ArdiaMsvcBatch',s)
        self.assertIn('[System.Diagnostics.ProcessStartInfo]::new()',s)
        self.assertIn("$start.Arguments = '/D /S /C \"\"' + $resolved + '\"\"'",s)
        self.assertIn('$process.WaitForExit()',s)
        self.assertIn('return [int]$process.ExitCode',s)
        self.assertIn('$start.UseShellExecute = $false',s)
    def test_spaced_path_batch_regression_before_toolchain(self):
        w=(ROOT/'.github/workflows/build.yml').read_text(encoding='utf8')
        self.assertLess(w.index('Verify CMD batch quoting with paths containing spaces'),w.index('Verify Windows x64 MSVC toolchain'))
        s=(ROOT/'scripts/test-msvc-batch-quoting.ps1').read_text(encoding='utf8')
        self.assertIn('Invoke-ArdiaMsvcBatch -Script $batch',s)
        self.assertIn('exit /b 42',s)
        self.assertIn('expected 42',s)
        self.assertIn('with spaces',s)
        preflight=(ROOT/'scripts/verify-msvc.ps1').read_text(encoding='utf8')
        self.assertIn('Ardia MSVC preflight with spaces',preflight)
        self.assertIn('Invoke-ArdiaMsvcBatch -Script $batch',preflight)
    def test_no_change_to_launcher_flags_or_profile(self):
        t=(ROOT/'launcher/ArdiaPortable.cpp').read_text(encoding='utf8')
        f=(ROOT/'launcher/ArdiaLaunchFlags.h').read_text(encoding='utf8')
        self.assertIn('ARDIA_DATA_DIR',t)
        for flag in ['--disable-ardia-update','--no-default-browser-check','--disable-logging','--disable-breakpad','--disable-machine-id','--disable-encryption-win']:
            self.assertIn(flag,f)
if __name__=='__main__':unittest.main()
