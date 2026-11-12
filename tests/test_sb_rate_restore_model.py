#!/usr/bin/env python3
"""Read-only real-HFSX overlay plus fault-injected restoration model."""

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path


MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
BASE = WORK/'research/tmp/sb-rate-20261112'
sys.path[:0] = [str(MAIN/'research/tmp/dsh-0175'),
                str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112')]
from write_root_delta175v2 import RecoveryIO
from local_hfs175v3 import HFS
from metal_ca_c5_delta import Remote


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name,WORK/'tools'/filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RESTORE = load('sb_restore','build-sb-rate-restore.py')
IO_CORE = load('sb_restore_io','sb-rate-slot-restore-io.py')


class ModelIO:
    model_only = True
    def __init__(self, base, overlays):
        self.base = base
        self.overlays = list(overlays)
        self.reads = self.writes = 0
        self.fail_write_numbers = set()

    def identity(self):
        return self.base.identity()

    def read(self, offset, length):
        self.reads += 1
        raw = bytearray(self.base.read(offset,length))
        for start, image in self.overlays:
            lo,hi = max(offset,start),min(offset+length,start+len(image))
            if lo < hi:
                raw[lo-offset:hi-offset] = image[lo-start:hi-start]
        return bytes(raw)

    def write(self, offset, image):
        self.writes += 1
        if self.writes in self.fail_write_numbers:
            raise OSError('model write failure')
        assert offset%4096 == len(image)%4096 == 0
        self.overlays.append((offset,bytes(image)))

    def sync(self):
        pass


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    base = RecoveryIO()
    ident = base.identity()
    assert ident['state'] == 'recovery' and ident['product'] == 'gauguin'
    assert ident['unmounted'] and ident['no_holders']
    plan_dir = BASE/'slot-delta-v2'
    capture_dir = BASE/'slot-capture-v2'
    plan = json.loads((plan_dir/'install-plan.json').read_bytes())
    initial = []
    for name,row in plan['rows'].items():
        data = (plan_dir/(name+'-new-data.bin')).read_bytes()
        cat = bytearray((plan_dir/(name+'-new-catalog.bin')).read_bytes())
        if name == 'job':
            # HFSPlusCatalogFile.reserved1 is 84 bytes before this fork's
            # logicalSize. It is parser-ignored, unlike an arbitrary block byte.
            cat[row['catalog_offset']-84] ^= 1
        initial.extend([(row['data_block']*4096,data),(row['catalog_block']*4096,bytes(cat))])
    model = ModelIO(base,initial)
    with tempfile.TemporaryDirectory(prefix='sb-rate-restore-model-',dir=BASE) as temp:
        bundle = Path(temp)/'bundle'
        dynamic = RESTORE.prepare(plan_dir,capture_dir,model,HFS,Remote,bundle)
        assert dynamic['state'] == 'prepared-dynamic-SpringBoard-slot-restoration'
        assert dynamic['write_bytes'] == plan['install_write_bytes']
        approval = {'approved':True,'one_shot':True,'allow_restore':True,
                    'allow_rollback':True,'fixture_only':True,
                    'plan_sha256':sha(plan_dir/'install-plan.json')}
        denied = ModelIO(base,initial)
        try:
            IO_CORE.restore_rows(plan_dir,bundle,{**approval,'plan_sha256':'bad'},denied)
        except ValueError:
            pass
        else:
            raise AssertionError('mismatched approval accepted')
        assert denied.reads == denied.writes == 0
        denied.model_only = False
        try:
            IO_CORE.restore_rows(plan_dir,bundle,approval,denied)
        except ValueError:
            pass
        else:
            raise AssertionError('fixture approval reached non-model IO')
        assert denied.reads == denied.writes == 0
        for fail_at in range(1,7):
            failure = ModelIO(base,initial)
            failure.fail_write_numbers = {fail_at}
            result = IO_CORE.restore(plan_dir,bundle,approval,failure,lambda _row:None)
            assert result['state'] == 'restore-failed-rollback-verified'
            assert failure.writes == 2*fail_at
            for start,image in initial:
                assert failure.read(start,len(image)) == image
        broken = ModelIO(base,initial)
        broken.fail_write_numbers = {2,3}
        result = IO_CORE.restore(plan_dir,bundle,approval,broken,lambda _row:None)
        assert result['state'] == 'restore-failed-rollback-incomplete'
        assert result['rollback_failures'] and broken.writes == 4
        success = ModelIO(base,initial)
        result = IO_CORE.restore(plan_dir,bundle,approval,success,lambda _row:None)
        assert result['state'] == 'restore-applied-and-readback-verified'
        hfs = HFS(stream=Remote(success),size=17179869184)
        try:
            for name,row in plan['rows'].items():
                file = hfs.paths[row['path']]
                assert file['data']['logical'] == row['old_logical']
                assert hashlib.sha256(hfs.content(row['path'])).hexdigest() == row['old_file_sha256']
        finally:
            hfs.close()
        job = plan['rows']['job']
        preserved = success.read(job['catalog_block']*4096,4096)
        assert preserved[job['catalog_offset']-84] == initial[3][1][job['catalog_offset']-84]
        receipt = {'state':'passed-readonly-dynamic-restore-model',
                   'base_plan_sha256':approval['plan_sha256'],
                   'dynamic_range_count':len(dynamic['ranges']),
                   'dynamic_write_bytes':dynamic['write_bytes'],
                   'failure_on_each_write':list(range(1,7)),
                   'rollback_verified':True,'rollback_failure_reported':True,
                   'unrelated_catalog_byte_preserved':True,
                   'restored_HFSX_files':3,'device_writes':0,'device_boots':0}
    out = BASE/'restore-model-review-v3.json'
    assert not out.exists()
    with out.open('x') as stream:
        json.dump(receipt,stream,indent=2);stream.write('\n')
    print(json.dumps(receipt,indent=2))


if __name__ == '__main__':
    main()
