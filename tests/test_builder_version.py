"""Regression tests for partial kit-copy failures and revision consistency."""
import importlib.util
import pathlib
import shutil
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('revision_checker', ROOT/'scripts/check-builder-revision.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

class KitRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        for relative in [
            'BUILDER_REVISION', '.github/workflows/build.yml', 'scripts/resolve.py',
            'scripts/stage.ps1', 'README.md', 'tests/test_local.py',
            'tests/test_msvc_preflight.py', 'docs/LOCAL_VERIFICATION.json',
        ]:
            target = self.root/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/relative, target)

    def test_current_kit_is_coherent(self):
        self.assertEqual(checker.check(self.root), [])

    def test_old_local_test_is_rejected(self):
        f = self.root/'tests/test_local.py'
        f.write_text(f.read_text(encoding='utf-8') + "\n# stale b1r7 test\n", encoding='utf-8')
        self.assertTrue(any('stale hardcoded version' in x for x in checker.check(self.root)))

    def test_old_installer_revision_is_rejected(self):
        f = self.root/'.github/workflows/build.yml'
        f.write_text(f.read_text(encoding='utf-8').replace('package-revision: b1r9', 'package-revision: b1r8'), encoding='utf-8')
        self.assertTrue(any('package-revision: b1r9' in x for x in checker.check(self.root)))

    def test_missing_hidden_workflow_is_rejected(self):
        (self.root/'.github/workflows/build.yml').unlink()
        self.assertTrue(any('.github/workflows/build.yml' in x for x in checker.check(self.root)))

if __name__ == '__main__':
    unittest.main()
