#!/usr/bin/env python3
"""Read-only actual-root overlay and fault model for eight-range installation."""

import hashlib
import importlib.util
import json
from pathlib import Path


WORK = Path(__file__).resolve().parents[1]
BASE = WORK/'research/tmp/sb-spawn-314'


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
    denied.model_only=False
    try:INSTALL.preflight(plan_dir,capture_dir,approval,denied,HFS,Remote)
    except ValueError:pass
    else:raise AssertionError('fixture approval reached non-model IO')
    assert denied.reads==denied.writes==0
    success=ModelIO(base,[])
    result=INSTALL.install(plan_dir,capture_dir,approval,success,HFS,Remote,lambda _row:None)
    assert result['state']=='install-applied-and-HFSX-verified'
    for name,row in plan['rows'].items():
        data=success.read(row['data_block']*4096,row['data_blocks']*4096)
        cat=success.read(row['catalog_block']*4096,4096)
        assert hashlib.sha256(data).hexdigest()==row['new_data_sha256']
        assert hashlib.sha256(cat).hexdigest()==row['new_catalog_sha256']
    for fail_at in range(1,9):
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
    receipt={'state':'passed-readonly-eight-range-install-model',
             'base_plan_sha256':approval['plan_sha256'],
             'installed_HFSX_files':4,'install_bytes':plan['install_write_bytes'],
             'failure_on_write':list(range(1,9)),
             'rollback_verified':True,'rollback_failure_reported':True,
             'fixture_rejected_on_non_model':True,
             'device_writes':0,'device_boots':0}
    out=BASE/'install-model-review.json'
    assert base.unchanged(), 'live root changed during read-only model'
    receipt['partial_write_failure_tested'] = True
    receipt['input_pins'] = {str(p.resolve()):sha(p) for p in [Path(__file__), *sorted((WORK/'tools').glob('*sb-cadence*.py')), WORK/'tests/test_sb_cadence_restore_model.py']}
    assert not out.exists()
    with out.open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
