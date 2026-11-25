#!/usr/bin/env python3
"""Synthetic parser fixtures are never device acceptance evidence."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'tools'))
from metal_frontend_log import P, expected_hashes, qualify_frontend_log
from test_gpu_service_log import trace

BUILD = '0123456789abcdef01234567'

def fixture():
    seed = 0x12345678
    lines = [P+f'begin build={BUILD} delay=90 scope=root-offscreen-objects-not-CA',
             P+'memory phase=before-delay active=128 inactive=128 hard=1 footprint=8388608',
             P+f'device=Adreno (hakios-metal, chip 0x6010900) seed={seed} maxBO=67108864 queueSlots=4',
             P+'memory phase=opened active=128 inactive=128 hard=1 footprint=16777216']
    for i, (phase, digest) in enumerate(expected_hashes(seed).items()):
        if i == 8:lines.append(P+'abandoned-slots count=80 PASS')
        lines.append(P+f'pixels phase={phase} words=4096 hash={digest} PASS')
    lines.extend([P+'surface id=7 width=64 height=64 stride=256 format=BGRA cases=3 PASS',
                  P+'memory phase=after-resource-release active=128 inactive=128 hard=1 footprint=16777216',
                  P+'ownership reacquired=1 closed=1 PASS',
                  P+f'RESULT PASS build={BUILD} seed={seed} jobs=83 words=339968 abandoned=80 teardown-requested=1 discovery=0 shader-pipelines=0 UI=0'])
    stderr = P+'admitted OS=20H392 methods=12 ivars=2 root-only no-discovery\n'
    stderr += 'HakiosMetal[gauguin-metal-frontend-probe 42]: refused: buffer length 67108865 outside 1..64MiB kernel cap\n'
    return '\n'.join(lines)+'\n', stderr, trace(83)

class FrontendEvidence(unittest.TestCase):
    def test_complete_fixture_has_limited_claim(self):
        result = qualify_frontend_log(*fixture(), build=BUILD)
        self.assertEqual(result['jobs'], 83)
        self.assertEqual(result['output_words'], 339968)
        self.assertEqual(result['finite_service']['unrecorded_successes'], 67)
        for key in ('device_discovery_qualified','shader_pipelines_qualified','desktop_qualified','high_refresh_qualified'):
            self.assertFalse(result[key])

    def test_reject_corrupt_missing_duplicate_and_unknown_records(self):
        out, err, native = fixture()
        pixel = next(x+'\n' for x in out.splitlines() if 'pixels phase=format-70-red ' in x)
        abandoned = P+'abandoned-slots count=80 PASS\n'
        mutations = [out.replace(pixel,''), out.replace(pixel,pixel*2),
            out.replace(pixel,'interleaved '+pixel), out.replace(pixel,pixel[:40]+'\n'),
            out.replace('words=4096','words=4095',1),
            out.replace('hash='+pixel.split('hash=')[1][:16],'hash=0000000000000000',1),
            out.replace('seed=305419896 maxBO','seed=305419897 maxBO'),
            out.replace('chip 0x6010900','chip 0x6030500'),
            out.replace('jobs=83','jobs=82'), out.replace('discovery=0','discovery=1'),
            out.replace(abandoned,''),out.replace(abandoned,abandoned*2),
            out.replace('reacquired=1','reacquired=0'),
            out.replace('footprint=8388608','footprint=134217729'),
            out.replace('hard=1','hard=0',1),
            out.replace(P+'RESULT PASS',P+'RESULT FAIL'),
            out+P+'unknown diagnostic\n']
        for changed in mutations:
            self.assertNotEqual(changed,out)
            with self.subTest(changed=changed[-120:]),self.assertRaises(ValueError):
                qualify_frontend_log(changed,err,native,build=BUILD)

    def test_reject_runtime_ABI_and_operation_refusals(self):
        out, err, native = fixture()
        for changed in (err.replace('methods=12','methods=11'), err*2,
                        err+'GAUGUIN METAL226 ABI rejected _MTLCommandQueue\n',
                        err+'HakiosMetal: refused: framebuffer fetch\n',
                        err.replace('67108865','67108866')):
            with self.assertRaises(ValueError):qualify_frontend_log(out,changed,native,build=BUILD)

    def test_reject_native_mismatch_competing_owner_and_fault(self):
        out, err, native = fixture()
        for changed in (trace(84),native+'SWEET GPU AUTH: compositor opened pid=57 root_fence=83\n',
                        native+'SWEET GPU USER: client closed after fault; fixture\n'):
            with self.assertRaises(ValueError):qualify_frontend_log(out,err,changed,build=BUILD)

    def test_identity_is_not_inferred_from_pass_string(self):
        with self.assertRaises(ValueError):qualify_frontend_log(*fixture(),build='f'*24)

if __name__=='__main__':unittest.main(verbosity=2)
