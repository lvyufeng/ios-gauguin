#!/usr/bin/env python3
"""Actual C4 block-writer controls against an in-memory recovery device."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from metal_ca_c4_delta import BLOCK, PARTITION_BYTES, Refused, install, restore, sha


class FakeIO:
    model_only = True
    def __init__(self, plan, header, data, catalog, fail_write=0, bad_readback=0):
        self.positions = {0: bytearray(header),
                          plan['data_start_block']*BLOCK: bytearray(data),
                          plan['catalog_start_block']*BLOCK: bytearray(catalog)}
        self.fail_write, self.bad_readback = fail_write, bad_readback
        self.writes = self.syncs = 0
        self.last_written = None
        self.bad_readback_used = False
    def identity(self):
        return dict(state='recovery', product='gauguin', partition_bytes=PARTITION_BYTES,
                    unmounted=True, no_holders=True)
    def read(self, offset, length):
        assert offset in self.positions and length == len(self.positions[offset])
        value = bytes(self.positions[offset])
        if self.bad_readback == self.writes and self.last_written == offset and not self.bad_readback_used:
            self.bad_readback_used = True
            return bytes([value[0]^1]) + value[1:]
        return value
    def write(self, offset, value):
        assert offset in self.positions and len(value) == len(self.positions[offset])
        self.writes += 1
        self.last_written = offset
        if self.writes == self.fail_write:
            self.positions[offset][:len(value)//2] = value[:len(value)//2]
            raise OSError('injected partial write')
        self.positions[offset][:] = value
    def sync(self): self.syncs += 1


class BombIO:
    model_only = True
    def __getattr__(self, name):
        raise AssertionError('unapproved plan accessed IO through ' + name)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    candidate = args.candidate.resolve()
    plan_file = candidate / 'install-plan.json'
    plan = json.loads(plan_file.read_text())
    plan_sha = hashlib.sha256(plan_file.read_bytes()).hexdigest()
    header = (candidate / 'header-before.bin').read_bytes()
    data_old, data_new = [(candidate / name).read_bytes() for name in ('desktop-old.bin','desktop-new.bin')]
    cat_old, cat_new = [(candidate / name).read_bytes() for name in ('catalog-old.bin','catalog-new.bin')]
    assert sha(header) == plan['root_header_sha256']
    consent = dict(approved=True, one_shot=True, allow_install=True, allow_restore=True,
                   allow_rollback=True, allow_misc_marker=True, allow_temporary_boot=True,
                   plan_sha256=plan_sha, fixture_only=True)
    cases = []
    def check(name, passed):
        assert passed, name
        cases.append(name)
    for field in ('approved','one_shot','allow_install','allow_restore','allow_rollback',
                  'allow_misc_marker','allow_temporary_boot'):
        bad = dict(consent);bad[field] = False
        try: install(plan,plan_sha,candidate,bad,BombIO(),lambda _:None)
        except Refused: check('approval-'+field,True)
        else: check('approval-'+field,False)
    bad = dict(consent);bad['plan_sha256']='0'*64
    try: install(plan,plan_sha,candidate,bad,BombIO(),lambda _:None)
    except Refused: check('approval-plan-hash',True)
    else: check('approval-plan-hash',False)
    actual = FakeIO(plan,header,data_old,cat_old)
    receipt = install(plan,plan_sha,candidate,consent,actual,lambda _:None)
    check('install-success',receipt['state']=='applied-and-readback-verified' and
          receipt['runs']==2 and receipt['bytes']==434176 and actual.writes==2 and
          bytes(actual.positions[plan['data_start_block']*BLOCK])==data_new and
          bytes(actual.positions[plan['catalog_start_block']*BLOCK])==cat_new)
    for name,where in [('stale-data',plan['data_start_block']*BLOCK),
                       ('stale-catalog',plan['catalog_start_block']*BLOCK),('stale-header',0)]:
        fake=FakeIO(plan,header,data_old,cat_old)
        fake.positions[where][0]^=1
        try: install(plan,plan_sha,candidate,consent,fake,lambda _:None)
        except Refused: check(name,fake.writes==0)
        else: check(name,False)
    for phase in (1,2):
        fake=FakeIO(plan,header,data_old,cat_old,fail_write=phase)
        receipt=install(plan,plan_sha,candidate,consent,fake,lambda _:None)
        check('install-partial-write-'+str(phase),
              receipt['state']=='write-failed-rollback-verified' and
              bytes(fake.positions[plan['data_start_block']*BLOCK])==data_old and
              bytes(fake.positions[plan['catalog_start_block']*BLOCK])==cat_old)
    for phase in (1,2):
        fake=FakeIO(plan,header,data_old,cat_old,bad_readback=phase)
        receipt=install(plan,plan_sha,candidate,consent,fake,lambda _:None)
        check('install-readback-'+str(phase),
              receipt['state']=='write-failed-rollback-verified' and
              bytes(fake.positions[plan['data_start_block']*BLOCK])==data_old and
              bytes(fake.positions[plan['catalog_start_block']*BLOCK])==cat_old)

    # Post-boot catalog bytes are intentionally different outside the eight-
    # byte logical-size field. The dynamic restore must retain that change.
    post_cat=bytearray(cat_new);post_cat[1000]^=1;post_cat=bytes(post_cat)
    target_cat=bytearray(post_cat)
    at=plan['catalog_field_offset']
    target_cat[at:at+8]=cat_old[at:at+8]
    target_cat=bytes(target_cat)
    assert target_cat != cat_old and target_cat[1000]==post_cat[1000]
    assert not args.out.exists()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    inputs=out/'restore-inputs';inputs.mkdir()
    for name,data in [('data-current.bin',data_new),('data-old.bin',data_old),
                      ('catalog-current.bin',post_cat),('catalog-old.bin',target_cat)]:
        (inputs/name).write_bytes(data)
    dynamic=dict(state='prepared-dynamic-owned-C4-restoration',base_plan_sha256=plan_sha,
                 root_header_sha256=sha(header),file_cnid=plan['file_cnid'],
                 data_start_block=plan['data_start_block'],data_blocks=105,
                 catalog_start_block=plan['catalog_start_block'],catalog_field_offset=at,
                 old_file_bytes=plan['old_file_bytes'],new_file_bytes=plan['new_file_bytes'],
                 data_current_sha256=sha(data_new),data_old_sha256=sha(data_old),
                 catalog_current_sha256=sha(post_cat),catalog_old_sha256=sha(target_cat))
    (inputs/'restore-plan.json').write_text(json.dumps(dynamic,indent=2)+'\n')
    fake=FakeIO(plan,header,data_new,post_cat)
    receipt=restore(plan,plan_sha,dynamic,inputs,candidate,consent,fake,lambda _:None)
    check('dynamic-restore-preserves-runtime-catalog',
          receipt['state']=='applied-and-readback-verified' and
          bytes(fake.positions[plan['data_start_block']*BLOCK])==data_old and
          bytes(fake.positions[plan['catalog_start_block']*BLOCK])==target_cat)
    for phase in (1,2):
        fake=FakeIO(plan,header,data_new,post_cat,fail_write=phase)
        receipt=restore(plan,plan_sha,dynamic,inputs,candidate,consent,fake,lambda _:None)
        check('restore-partial-write-'+str(phase),
              receipt['state']=='write-failed-rollback-verified' and
              bytes(fake.positions[plan['data_start_block']*BLOCK])==data_new and
              bytes(fake.positions[plan['catalog_start_block']*BLOCK])==post_cat)
    for phase in (1,2):
        fake=FakeIO(plan,header,data_new,post_cat,bad_readback=phase)
        receipt=restore(plan,plan_sha,dynamic,inputs,candidate,consent,fake,lambda _:None)
        check('restore-readback-'+str(phase),
              receipt['state']=='write-failed-rollback-verified' and
              bytes(fake.positions[plan['data_start_block']*BLOCK])==data_new and
              bytes(fake.positions[plan['catalog_start_block']*BLOCK])==post_cat)
    result=dict(state='C4-actual-range-writer-controls-passed',cases=cases,count=len(cases),
                plan_sha256=plan_sha,fixture_approval_only=True,device_commands=0)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))


if __name__=='__main__': main()
