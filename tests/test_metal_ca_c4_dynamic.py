#!/usr/bin/env python3
"""Read-only virtual activation tests live HFSX restoration discovery."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'research/tmp/dsh-0175')]
from metal_ca_c4_delta import BLOCK, Refused, prepare_restore, sha
from local_hfs175v3 import HFS
from write_root_delta175v2 import RecoveryIO


class ModelIO:
    model_only = True
    def __init__(self, real, overlays):
        self.real, self.overlays = real, overlays
    def identity(self):
        return self.real.identity()
    def read(self, offset, count):
        raw = bytearray(self.real.read(offset, count))
        for start, replacement in self.overlays:
            lo, hi = max(offset, start), min(offset+count, start+len(replacement))
            if lo < hi:
                raw[lo-offset:hi-offset] = replacement[lo-start:hi-start]
        return bytes(raw)
    def write(self, *_):
        raise AssertionError('read-only model attempted a device write')
    def sync(self):
        raise AssertionError('read-only model attempted a device sync')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    candidate = args.candidate.resolve()
    raw = (candidate / 'install-plan.json').read_bytes()
    plan, pin = json.loads(raw), hashlib.sha256(raw).hexdigest()
    assert sha((candidate / 'header-before.bin').read_bytes()) == plan['root_header_sha256']
    new_data, new_cat = [(candidate / name).read_bytes()
                         for name in ('desktop-new.bin','catalog-new.bin')]
    real = RecoveryIO()
    assert real.identity()['state'] == 'recovery' and real.identity()['unmounted'] and real.identity()['no_holders']
    modeled = ModelIO(real, ((plan['data_start_block']*BLOCK,new_data),
                             (plan['catalog_start_block']*BLOCK,new_cat)))
    fixture = dict(approved=True,one_shot=True,allow_install=True,allow_restore=True,
                   allow_rollback=True,allow_misc_marker=True,allow_temporary_boot=True,
                   plan_sha256=pin,fixture_only=True)
    try:
        prepare_restore(plan,pin,candidate,fixture,ModelIO(real,()),
                        args.out.resolve()/'inactive-rejected',HFS)
    except Refused:
        assert not (args.out.resolve()/'inactive-rejected').exists()
    else:
        raise AssertionError('inactive old binary was accepted for restoration')
    dynamic = prepare_restore(plan,pin,candidate,fixture,modeled,args.out.resolve(),HFS)
    out = args.out.resolve()
    assert dynamic['catalog_start_block'] == plan['catalog_start_block']
    assert dynamic['catalog_field_offset'] == plan['catalog_field_offset']
    assert (out/'data-current.bin').read_bytes() == new_data
    assert (out/'data-old.bin').read_bytes() == (candidate/'desktop-old.bin').read_bytes()
    assert (out/'catalog-current.bin').read_bytes() == new_cat
    assert (out/'catalog-old.bin').read_bytes() == (candidate/'catalog-old.bin').read_bytes()
    result = dict(state='virtual-active-C4-dynamic-restoration-passed',
                  install_plan_sha256=pin,
                  restore_plan_sha256=hashlib.sha256((out/'restore-plan.json').read_bytes()).hexdigest(),
                  catalog_start_block=dynamic['catalog_start_block'],
                  catalog_field_offset=dynamic['catalog_field_offset'],
                  read_only_catalog_bytes=dynamic['read_only_catalog_bytes'],
                  fixture_approval_only=True,device_writes=0)
    (out/'model-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
