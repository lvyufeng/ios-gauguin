#!/usr/bin/env python3
"""Actual CPU staging logic with platform seams and inaccessible guard pages.

Only the DSB instruction is replaced; DT, ml_io_map_wcomb, ml_vtophys and the
SHA256 calls are seams in tests/fixtures/gauguin_pas_stage_host.c. The crypto
seam accepts only the exact synthetic6860-byte image; the production pin is
left untouched and is independently checked against the real firmware during
image qualification.

The A615ZapMDT descriptor and asset page fed to the C consumer are not written
by hand: the real packer (tools/mkpayload.py) is run on the synthetic MDT bytes
that the original C loop generates, and its emitted16-byte
/chosen/memory-map/A615ZapMDT property and last16384-byte payload segment are
passed to the fixture as files. Only ZAP_MDT_SHA256 is overridden for that one
packer call, because the real production pin is for the real firmware; the
real pin constant itself is asserted to remain unchanged.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shlex
import signal
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
XNU = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
SOURCE = Path(os.environ.get('PAS_STAGE_SOURCE', XNU / 'bsd/dev/gauguin_pas_stage.c'))
FIXTURE = HERE / 'fixtures/gauguin_pas_stage_host.c'
PAGE = 16384
RAW = 6860
# The exact bytes the fixture's independent synthetic loop generates and the
# ones the packer assets here are built from.
SYNTHETIC = bytes(i % 251 for i in range(RAW))
REAL_PIN = '6f2a0e35325097f98fded6123d755266cdbb44caa932be61251b65b5c516ac7b'
CC = shlex.split(os.environ.get('CC', 'cc')) + [
    '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O1', '-g',
    '-fsanitize=address,undefined', '-fno-omit-frame-pointer']


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def production_source():
    """The staging C with only the DSB and its includes replaced."""
    source = SOURCE.read_text()
    assert not re.search(r'smc #|ml_io_unmap|sweet_spmi|rpmh_write|write32|read32', source)
    assert source.count('ml_io_map_wcomb((vm_offset_t)pa') == 1
    assert not re.search(r'pmap_(enter|remove|protect|map)\b', source)
    # `dst[i]`, not `target[i]`: that decoy name also appears in fixture code.
    assert 'dst[i] = 0;' in source and 'dst[i] = image[i];' in source
    assert source.count('SHA256_Update(&') == 1
    assert 'SHA256_Update(&ctx, bytes, PST_BYTES);' in source
    barrier = '__asm__ volatile("dsb sy" ::: "memory");'
    assert source.count(barrier) == 1
    source = source.replace(barrier, 'fake_dsb();')
    return re.sub(r'^#include .*\n', '', source, flags=re.M)


class StagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.is_file():
            # An explicitly named source is a test failure, not an excuse to
            # pass; only an absent default tree may skip.
            if 'XNU_SOURCE' in os.environ or 'PAS_STAGE_SOURCE' in os.environ:
                raise FileNotFoundError(f'PAS staging source missing: {SOURCE}')
            raise unittest.SkipTest(f'PAS staging source missing: {SOURCE}')
        cls.fixture = FIXTURE.read_text()
        assert cls.fixture.count('@SOURCE@') == 1
        cls.temporary = tempfile.TemporaryDirectory(prefix='pas-staging-')
        cls.base = Path(cls.temporary.name)
        cls.kernel_path = cls.base / 'kernel'
        cls.adt_path = cls.base / 'tree'
        cls.mdt_path = cls.base / 'mdt'
        cls.mdt_path.write_bytes(SYNTHETIC)
        # Reuse the NVT asset fixtures' synthetic ARM64 kernel and ADT.
        cls.section = module('pas_staging_payload_fixtures', HERE / 'test_payload_nvt_asset.py')
        cls.kernel_path.write_bytes(cls.section.kernel())
        cls.adt_path.write_bytes(cls.section.adt.serialize(cls.section.tree()))
        cls.pack = module('pas_staging_packer', ROOT / 'tools/mkpayload.py')
        cls.pack_records = {name: getattr(cls.pack, name) for name in ('ZAP_MDT_SIZE', 'ZAP_MDT_SHA256')}
        assert cls.pack_records == {'ZAP_MDT_SIZE': RAW, 'ZAP_MDT_SHA256': REAL_PIN}
        warnings.simplefilter('ignore', ResourceWarning)
        digest = hashlib.sha256(SYNTHETIC).hexdigest()
        cls.pack.ZAP_MDT_SHA256 = digest
        try:
            cls.blob, cls.info = cls.pack.build(cls.kernel_path, cls.adt_path, '', zap_mdt_path=cls.mdt_path)
        finally:
            cls.pack.ZAP_MDT_SHA256 = REAL_PIN
        # The synthetic content is never what production accepts.
        cls.synthetic_digest = digest
        cls.check_emitted_layout()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    @classmethod
    def check_emitted_layout(cls):
        """Parse the real payload: ADT property16B and last segment16384B."""
        adt = cls.section.adt
        assert cls.pack.ZAP_MDT_SHA256 == REAL_PIN
        assert cls.synthetic_digest != REAL_PIN
        _, version, count = struct.unpack_from('<8sII', cls.blob)
        base, _, adt_off, adt_size, _, phys, _ = struct.unpack_from('<7Q', cls.blob, 0x10)
        assert version == 1
        root, consumed = adt.parse(cls.blob[adt_off:adt_off + adt_size])
        assert consumed == adt_size
        mmap = next(c for c in root.children if c.name == 'chosen').children[0]
        assert mmap.name == 'memory-map'
        property = mmap.prop('A615ZapMDT')
        assert len(property) == 16
        pa, length = struct.unpack('<2Q', property)
        assert length == PAGE
        va, size, offset, stored = struct.unpack_from('<4Q', cls.blob, cls.pack.SEG_TABLE + (count - 1) * 32)
        assert (size, stored) == (PAGE, PAGE)
        assert pa == phys + va - base
        segment = cls.blob[offset:offset + stored]
        assert len(segment) == PAGE
        assert segment[:RAW] == SYNTHETIC
        assert segment[RAW:] == bytes(PAGE - RAW)
        assert cls.info['zap_metadata']['size'] == RAW
        assert cls.info['zap_metadata']['reserved'] == PAGE
        cls.property, cls.segment, cls.asset_pa = property, segment, pa
        return property, segment

    def build(self, name, source, property, segment):
        directory = self.base / name
        directory.mkdir()
        (directory / 'descriptor.bin').write_bytes(property)
        (directory / 'page.bin').write_bytes(segment)
        source_path = directory / 'test.c'
        source_path.write_text(self.fixture.replace('@SOURCE@', source))
        binary = directory / 'test'
        subprocess.run(CC + [str(source_path), '-o', str(binary)], check=True, timeout=60,
                       capture_output=True, text=True)
        return binary, directory / 'descriptor.bin', directory / 'page.bin'

    def run_fixture(self, binary, descriptor, page, check=True):
        return subprocess.run([str(binary), str(descriptor), str(page)], check=check,
                              timeout=30, capture_output=True, text=True)

    def test_emitted_descriptor_is_reserved_page_and_raw_is_pinned(self):
        property, segment = self.check_emitted_layout()
        self.assertEqual(struct.unpack('<2Q', property)[1], PAGE)
        self.assertEqual(segment[:RAW], SYNTHETIC)
        self.assertEqual(self.pack_records, {'ZAP_MDT_SIZE': RAW, 'ZAP_MDT_SHA256': REAL_PIN})

    def test_fixed_consumer_stages_emitted_descriptor(self):
        binary, descriptor, page = self.build('fixed', production_source(), self.property, self.segment)
        result = self.run_fixture(binary, descriptor, page)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('guarded readback, translation/corruption failures and retention pass', result.stdout)

    def test_consumer_requiring_raw_length_rejects_reserved_page(self):
        """Runtime proof, not a source-text match: a consumer that requires the
        raw6860 length refuses the descriptor the real packer emits."""
        source = production_source()
        repaired = '!pa || reserved_bytes != PST_PAGE || '
        assert source.count(repaired) == 1 and '!= PST_BYTES' not in source
        mutated = source.replace(repaired, '!pa || reserved_bytes != PST_BYTES || ')
        # build() already compiled with -Werror, so a compile error cannot reach
        # here. The fixture's assert aborts, which Python reports as -SIGABRT;
        # that abort must be the first positive case, not an earlier check.
        binary, descriptor, page = self.build('raw_length', mutated, self.property, self.segment)
        result = self.run_fixture(binary, descriptor, page, check=False)
        self.assertEqual(-result.returncode, signal.SIGABRT)
        self.assertNotIn('complete metadata_bytes=', result.stdout)
        self.assertIn('mock.maps==1 && mock.hashes==2 && mock.translations==2 && '
                      'mock.barriers==1 && pst_mapping==(vm_offset_t)target', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)