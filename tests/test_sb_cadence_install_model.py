#!/usr/bin/env python3
"""Read-only actual-root overlay and fault model for eleven-range installation."""

import hashlib
import importlib.util
import json
import copy
import tempfile
import struct
from pathlib import Path


WORK = Path(__file__).resolve().parents[1]
BASE = WORK/'research/tmp/queue-loss-337'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RESTORE_TEST=load('restore_test',WORK/'tests/test_sb_cadence_restore_model.py')
INSTALL=load('sb_install',WORK/'tools/sb-cadence-slot-install-io.py')
RecoveryIO,HFS,Remote,ModelIO=(RESTORE_TEST.RecoveryIO,RESTORE_TEST.HFS,
                                RESTORE_TEST.Remote,RESTORE_TEST.ModelIO)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    base=RESTORE_TEST.ReadonlyCache(RecoveryIO())
    ident=base.identity()
    assert ident['state']=='recovery' and ident['product']=='gauguin'
    assert ident['unmounted'] and ident['no_holders']
    plan_dir=BASE/'slot-delta'
    capture_dir=BASE/'slot-capture'
    plan=json.loads((plan_dir/'install-plan.json').read_bytes())
    approval={'approved':True,'one_shot':True,'allow_install':True,
              'allow_rollback':True,'fixture_only':True,
              'plan_sha256':sha(plan_dir/'install-plan.json')}
    denied=ModelIO(base,[])
    try:INSTALL.preflight(plan_dir,capture_dir,{**approval,'plan_sha256':'bad'},denied,HFS,Remote)
    except ValueError:pass
    else:raise AssertionError('mismatched approval accepted')
    assert denied.reads==denied.writes==0
    # Both entries share one leaf. Reject a forgotten second length update and
    # a mutation outside either owned field, even with internally updated hashes.
    for mutation in ('omitted-admission-field','unrelated-byte'):
        with tempfile.TemporaryDirectory(prefix='install-negative-',dir=BASE) as temp:
            altered=Path(temp);changed=copy.deepcopy(plan)
            for path in plan_dir.glob('*.bin'):(altered/path.name).write_bytes(path.read_bytes())
            cat=bytearray((altered/'eagl-new-catalog.bin').read_bytes())
            if mutation=='omitted-admission-field':
                row=changed['rows']['admission'];at=row['catalog_offset']
                cat[at:at+8]=struct.pack('>Q',row['old_logical'])
            else:cat[0]^=1
            digest=hashlib.sha256(cat).hexdigest()
            for name in ('eagl','admission'):
                (altered/(name+'-new-catalog.bin')).write_bytes(cat)
                changed['rows'][name]['new_catalog_sha256']=digest
            (altered/'install-plan.json').write_text(json.dumps(changed))
            bad=ModelIO(base,[])
            try:INSTALL.preflight(altered,capture_dir,{**approval,'plan_sha256':sha(altered/'install-plan.json')},bad,HFS,Remote)
            except ValueError:pass
            else:raise AssertionError('invalid shared catalog mutation accepted')
            assert bad.writes==0
    # The core length may change only at its owned field, even if a forged
    # plan updates the image hash.
    with tempfile.TemporaryDirectory(prefix='core-catalog-negative-',dir=BASE) as temp:
        altered=Path(temp);changed=copy.deepcopy(plan)
        for path in plan_dir.glob('*.bin'):(altered/path.name).write_bytes(path.read_bytes())
        cat=bytearray((altered/'core-new-catalog.bin').read_bytes());cat[0]^=1
        (altered/'core-new-catalog.bin').write_bytes(cat)
        changed['rows']['core']['new_catalog_sha256']=hashlib.sha256(cat).hexdigest()
        (altered/'install-plan.json').write_text(json.dumps(changed))
        bad=ModelIO(base,[])
        try:INSTALL.preflight(altered,capture_dir,{**approval,'plan_sha256':sha(altered/'install-plan.json')},bad,HFS,Remote)
        except ValueError:pass
        else:raise AssertionError('unrelated core catalog mutation accepted')
        assert bad.writes==0
    denied.model_only=False
    try:INSTALL.preflight(plan_dir,capture_dir,approval,denied,HFS,Remote)
    except ValueError:pass
    else:raise AssertionError('fixture approval reached non-model IO')
    assert denied.reads==denied.writes==0
    success=ModelIO(base,[])
    result=INSTALL.install(plan_dir,capture_dir,approval,success,HFS,Remote,lambda _row:None)
    assert result['state']=='install-applied-and-HFSX-verified'
    core=plan['rows']['core']
    assert core['old_logical']==8407792 and core['new_logical']==8391360
    assert any(start==core['catalog_block']*4096 for start,_bytes in success.overlays)
    for name,row in plan['rows'].items():
        data=success.read(row['data_block']*4096,row['data_blocks']*4096)
        cat=success.read(row['catalog_block']*4096,4096)
        assert hashlib.sha256(data).hexdigest()==row['new_data_sha256']
        assert hashlib.sha256(cat).hexdigest()==row['new_catalog_sha256']
    for fail_at in range(1,plan['changed_ranges']+1):
        failure=ModelIO(base,[])
        failure.fail_write_numbers={fail_at}
        result=INSTALL.install(plan_dir,capture_dir,approval,failure,HFS,Remote,lambda _row:None)
        assert result['state']=='install-failed-rollback-verified'
        assert failure.writes==2*fail_at
        for name,row in plan['rows'].items():
            assert hashlib.sha256(failure.read(row['data_block']*4096,row['data_blocks']*4096)).hexdigest()==row['old_data_sha256']
            assert hashlib.sha256(failure.read(row['catalog_block']*4096,4096)).hexdigest()==row['old_catalog_sha256']
    broken=ModelIO(base,[])
    broken.fail_write_numbers={2,3}
    result=INSTALL.install(plan_dir,capture_dir,approval,broken,HFS,Remote,lambda _row:None)
    assert result['state']=='install-failed-rollback-incomplete' and result['rollback_failures']
    receipt={'state':'passed-readonly-eleven-range-install-model',
             'base_plan_sha256':approval['plan_sha256'],
             'installed_HFSX_files':6,'install_bytes':plan['install_write_bytes'],
             'failure_on_write':list(range(1,plan['changed_ranges']+1)),
             'rollback_verified':True,'rollback_failure_reported':True,
             'fixture_rejected_on_non_model':True,
             'shared_catalog_missing_field_and_unrelated_byte_rejected':True,
             'unrelated_core_catalog_mutation_rejected':True,'changed_core_catalog_written':True,
             'device_writes':0,'device_boots':0}
    out=BASE/'install-model-review.json'
    assert base.unchanged(), 'live root changed during read-only model'
    receipt['partial_write_failure_tested'] = True
    receipt['input_pins'] = {str(p.resolve()):sha(p) for p in [Path(__file__), WORK/'tools/sb-cadence-slot-install-io.py', WORK/'tools/build-sb-cadence-restore.py', WORK/'tools/sb-cadence-slot-restore-io.py', WORK/'tests/test_sb_cadence_restore_model.py', *[Path(__import__(cls.__module__).__file__) for cls in (RecoveryIO,HFS,Remote)]]}
    assert not out.exists()
    with out.open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
