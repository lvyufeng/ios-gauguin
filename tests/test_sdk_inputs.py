#!/usr/bin/env python3
"""Verify SDK pinning and staging without downloading or embedding Apple files."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('xnu_stage_sdk', ROOT / 'tools/xnu-stage-sdk.py')
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)


class SDKInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='sdk-input-test-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / 'xnu'
        (self.source / 'bsd/conf').mkdir(parents=True)
        (self.source / 'bsd/conf/files').write_text('')
        for name in sdk.TARGETS:
            (self.source / name).parent.mkdir(parents=True, exist_ok=True)
        self.data = b'/* synthetic SDK fixture */\n#define TEST_TARGET 1\n'
        self.header = self.directory / 'fixture.h'
        self.header.write_bytes(self.data)
        self.cache = self.directory / 'cache'
        digest = patch.object(sdk, 'HEADER_SHA256', hashlib.sha256(self.data).hexdigest())
        digest.start()
        self.addCleanup(digest.stop)

    def test_explicit_verified_header_is_idempotent(self):
        with patch.object(sdk.urllib.request, 'urlopen') as download:
            sdk.stage(self.source, self.header)
            times = [(self.source / name).stat().st_mtime_ns for name in sdk.TARGETS]
            sdk.stage(self.source, self.header)
            download.assert_not_called()
        for name, stamp in zip(sdk.TARGETS, times):
            self.assertEqual((self.source / name).read_bytes(), self.data)
            self.assertEqual((self.source / name).stat().st_mtime_ns, stamp)

    def test_bad_header_preserves_existing_destinations(self):
        self.header.write_bytes(b'wrong header')
        for name in sdk.TARGETS:
            (self.source / name).write_bytes(b'existing')
        with self.assertRaises(ValueError):
            sdk.stage(self.source, self.header)
        for name in sdk.TARGETS:
            self.assertEqual((self.source / name).read_bytes(), b'existing')

    def test_verified_download_is_cached(self):
        with patch.object(sdk.urllib.request, 'urlopen', return_value=io.BytesIO(self.data)) as download:
            sdk.stage(self.source, cache=self.cache)
            sdk.stage(self.source, cache=self.cache)
            download.assert_called_once_with(sdk.HEADER_URL, timeout=30)
        self.assertEqual((self.cache / 'TargetConditionals.h').read_bytes(), self.data)

    def test_failed_download_digest_leaves_no_cached_header(self):
        with patch.object(sdk.urllib.request, 'urlopen', return_value=io.BytesIO(b'wrong')):
            with self.assertRaises(ValueError):
                sdk.stage(self.source, cache=self.cache)
        self.assertFalse((self.cache / 'TargetConditionals.h').exists())
        self.assertEqual(list(self.cache.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
