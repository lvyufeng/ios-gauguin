#!/usr/bin/env python3
"""Check ordered replay, error propagation and explicit source targeting."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / 'tools/xnu-patches.py'


class PatchSeriesTests(unittest.TestCase):
    def setUp(self):
        # Exercise an exported source directory inside the enclosing git repo.
        scratch = ROOT / 'research/tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='series-test-', dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / 'xnu'
        (self.source / 'bsd/conf').mkdir(parents=True)
        (self.source / 'bsd/conf/files').write_text('')
        self.series = self.directory / 'series'
        (self.directory / 'first.patch').write_text(
            '--- /dev/null\n+++ b/probe\n@@ -0,0 +1 @@\n+first\n')
        (self.directory / 'second.patch').write_text(
            '--- a/probe\n+++ b/probe\n@@ -1 +1 @@\n-first\n+second\n')

    def apply(self):
        return subprocess.run(
            [sys.executable, str(TOOL), '--series', str(self.series),
             'apply', str(self.source)], capture_output=True, text=True)

    def test_dependent_patches_apply_in_order(self):
        self.series.write_text('# selected patches\nfirst.patch\n\nsecond.patch\n')
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.source / 'probe').read_text(), 'second\n')
        self.assertIn('Applied 2 patches', result.stdout)

    def test_conflict_stops_replay(self):
        (self.directory / 'bad.patch').write_text(
            '--- a/probe\n+++ b/probe\n@@ -1 +1 @@\n-absent\n+bad\n')
        self.series.write_text('first.patch\nbad.patch\nsecond.patch\n')
        result = self.apply()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.source / 'probe').read_text(), 'first\n')
        self.assertNotIn('Applying second.patch', result.stdout)

    def test_invalid_manifest_is_rejected_before_writes(self):
        for text in ('first.patch\nfirst.patch\n', 'first.patch\nmissing.patch\n',
                     '../outside.patch\n', '# no patches\n'):
            with self.subTest(text=text):
                self.series.write_text(text)
                result = self.apply()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.source / 'probe').exists())

    def test_watchdog_sync_uses_the_explicit_tree(self):
        target = self.source / 'bsd/dev/sweet_init_watchdog.h'
        target.parent.mkdir()
        result = subprocess.run(
            ['bash', str(ROOT / 'deps/sync-watchdog.sh'), str(self.source)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_bytes(), (ROOT / 'xnu/sweet_init_watchdog.h').read_bytes())


if __name__ == '__main__':
    unittest.main()
