#!/usr/bin/env python3
"""Prepare and freeze the candidate boot over the verified 0360 root."""

import argparse
from functools import partial
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from frame361_scope import (BASE, BUILD_BATCH_BYTES, CORE, CORE_BYTES, DOC, HEADER, MAIN,
    P360, PATCH, REF360, RESERVE, SAVED_SLOTS, SUCCESS, WORK, check_baseline,
    expected_plan, load, require, sha, signed_pair)

shared = import_module('prepare-frame349')
runner = import_module('run-frame361-trial')
save = shared.stage.save
REFERENCE = REF360/'restored-capture/result.json'
CLEANUP = MAIN/'research/tmp/0361-storage-retirement'
MAX_COMPRESSED_METADATA = 14_000_000


def check_budget():
    budget = load(BASE/'build-storage-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==BUILD_BATCH_BYTES and
            budget['current_accounted_bytes']+BUILD_BATCH_BYTES<=budget['limit_bytes'],
            '0361 whole preparation and runtime batch not admitted')


def capture():
    check_budget()
    current = check_baseline()
    slots = BASE/'slot-capture'
    if not slots.exists():
        subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
            '--baseline',str(REFERENCE),'--out',str(slots),'--reuse-data-from',str(SAVED_SLOTS)],
            check=True,capture_output=True,timeout=300)
    snapshot = BASE/'metadata-snapshot'
    meta = (load(snapshot/'result.json') if snapshot.exists() else
        import_module('capture-core342-metadata').capture(snapshot,HEADER,trial='0361',
            maximum_compressed_bytes=MAX_COMPRESSED_METADATA))
    require(meta['root_header_sha256']==HEADER and meta['compressed_bytes']<=MAX_COMPRESSED_METADATA and
            not (meta['device_writes'] or meta['device_boots']), '0361 read-only metadata differs')
    return dict(files=len(current['files']),metadata_bytes=meta['compressed_bytes'],
                log_bytes=current['combined_log_bytes'],device_writes=0)


def delta():
    check_budget()
    receipt,signed = signed_pair()
    candidate = signed['variants']['candidate']
    subprocess.run(['codesign','--verify','--strict',candidate['binary']],
                   check=True,capture_output=True,timeout=60)
    core = dict(state='0361-exact-ARM64-Core-signed',
        binary=candidate['binary'],binary_sha256=CORE,bytes=CORE_BYTES,sdk=candidate['sdk'],
        signature_verified=True,input_pins={str(receipt):sha(receipt)},device_commands=0)
    for name,value in (('core-native',core),('edr-native',load(P360/'edr-native/result.json'))):
        path = BASE/name/'result.json'
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            require(load(path)==value,'existing signed receipt differs: '+name)
        else:
            save(path,value)
    return shared.stage.delta(BASE,P360,trial='0361',header=HEADER,baseline=REFERENCE,core_logical=CORE_BYTES)


def model():
    check_budget()
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0361')
    return dict(checks=len(result['checks']),failure_points=result['all_restore_partial_write_points'],
                maximum_actual_model_restore_bytes=result['maximum_actual_model_restore_bytes'],device_writes=0)


def host():
    check_budget()
    plan = expected_plan()
    out = BASE/'frame-host'
    out.mkdir()
    try:
        runner.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                             static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'wrong early frame gate')
    else:
        raise ValueError('0361 frame analysis before independent restore')
    fixture = import_module('check-core342-pipeline')
    control = []
    with TemporaryDirectory(prefix='0361-flow-',dir=BASE) as temporary:
        for case in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                     'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
            fixture.control_fixture(Path(temporary),plan,case,control)

    collector = runner.scorer.prior
    with TemporaryDirectory(prefix='0361-host-replay-',dir=BASE) as temporary:
        path = Path(temporary)
        for filename in ('kernel.log','core-wait-execution-analysis.json','kernel-IO-identity-analysis.json',
                         'kernel-IO-analysis.json','independent-restore.json'):
            (path/filename).symlink_to(REF360/filename)
        before = load(REF360/'fresh-before/result.json')
        archived = load(REF360/'result.json')
        result = {key:archived[key] for key in ('restored','independent_restore_verified','static_root_comparison_passed')}

        def qualified_archived_core(_execution,_plan,result,_before,_code):
            result['state'] = collector.timeline.CORE_PASSED

        replay = partial(collector.collect_after_restore,core_analyzer=qualified_archived_core)
        with patch.object(collector,'collect_after_restore',replay):
            runner.after_restore(path,plan,result,before,0)
        require(result['state']==SUCCESS and result['active_surface_reservations']==111 and
                result['strict_new_frame_rate_bounds']==archived['strict_new_frame_rate_bounds'] and
                result['recording_comparison']['0360']==result['recording_comparison']['0361'] and
                result['recording_comparison']['0361']['matched_submissions']==722,
                '0361 replay differs from the restored 0360 records')
    summary = dict(state='0361-archived-replay-and-control-flow-passed',control_scenarios=control,
                   pacing_reference_reproduced=True,matched_recording_submissions=722,device_commands=0)
    save(out/'result.json',summary)
    return dict(replay=True,control_scenarios=len(control),matched_submissions=722,device_commands=0)


def storage(plan):
    previous = load(P360/'storage-bound-360.json')
    total = sum(previous['components'].values())
    require(total==182_106_272 and total<=RESERVE and previous['new_log_data_stored_once'],
            '0361 runtime output and rollback reservation differs')
    return dict(previous,state='bounded0361-runtime-batch',worst_case_bytes=total,
        reserve_bytes=RESERVE,fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def criteria(plan):
    check_budget()
    original = load(P360/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','install_plan_sha256','parent_trial_plan_sha256',
               'owned_core_sha256','owned_core_logical_bytes','unchanged_0342_Core_and_frontend',
               'new_kernel_builds','new_boot_images','optimization','performance_comparison',
               'log_capture','matched_Core_control'}
    require({k for k in original.keys()|plan.keys() if original.get(k)!=plan.get(k)}<=allowed and
            original['frame_capture']==plan['frame_capture'] and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442 and
            plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            '0361 adds an effect outside this Core-only installation')
    host,rollback,slots = (load(BASE/name) for name in ('frame-host/result.json','restore-model/result.json',
                                                         'slot-capture/result.json'))
    require(host['state']=='0361-archived-replay-and-control-flow-passed' and len(host['control_scenarios'])==9 and
            host['matched_recording_submissions']==722 and rollback['all_model_IO_writes_memory_only'] and
            len(rollback['checks'])==47 and rollback['all_restore_partial_write_points']==17 and
            rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            slots['baseline_sha256']==sha(REFERENCE) and len(slots['reused_original_data'])==6 and
            not (slots['device_writes'] or slots['device_boots']), '0361 restore or capture evidence is incomplete')
    for name,old in slots['reused_original_data'].items():
        expected = SAVED_SLOTS/(name+'-old-data.bin')
        require(Path(old)==expected and (BASE/'slot-capture'/expected.name).resolve()==expected,
                '0361 original slot archive differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P360,HEADER,plan)


def pins():
    core_receipt,signed = signed_pair()
    artifacts = (P360/'native-kernel/build-manifest.json',P360/'frame360-image.json',BASE/'edr-native/result.json',
                 BASE/'core-native/result.json',BASE/'frame-host/result.json',BASE/'restore-model/result.json')
    extra = [Path(__file__),core_receipt,Path(signed['variants']['reference']['binary']),
             BASE/'draw-checks/result.json',BASE/'producer-audit.json',P360/'slot-delta/install-plan.json',
             REF360/'frame-pacing-0358-0359-0360.json',REF360/'kernel-IO-analysis.json',
             CLEANUP/'verified-retirement-manifest.json',CLEANUP/'retirement-complete.json']
    extra.extend(Path(name) for name in load(BASE/'slot-capture/result.json')['reused_original_data'].values())
    return shared.pins(base=BASE,prior=P360,doc=DOC,patch=PATCH,reference=REF360,
                       trial='0361',extra=extra,artifacts=artifacts)


def freeze():
    return shared.freeze(base=BASE,prior=P360,expected=expected_plan,validate=criteria,
                        storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                        storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (capture,delta,model,host,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
