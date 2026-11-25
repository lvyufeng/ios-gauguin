#!/usr/bin/env python3
"""Stage, qualify and freeze 0360 without mutating the device."""

import argparse
from functools import partial
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from frame360_scope import (BASE, DOC, HEADER, KERNEL, LOG_SUFFIX, MAIN, METADATA_BYTES,
    P358, P359, PATCH, PREPARATION_BYTES, REF358, REF359, RESERVE, SUCCESS, WORK,
    check_baseline, expected_plan, load, require, sha)

shared = import_module('prepare-frame349')
runner = import_module('run-frame360-trial')
save = shared.stage.save
REFERENCE = REF359/'restored-capture/result.json'
ADMISSION = BASE/'build-storage-admission.json'


def admission():
    total = PREPARATION_BYTES+RESERVE
    budget = json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
        '--planned-bytes',str(total)],text=True,timeout=600))
    require(budget['admitted'] and budget['planned_batch_bytes']==total,
            'total prepared and runtime storage unavailable')
    save(ADMISSION,budget)
    return budget


def check_admission():
    budget = load(ADMISSION)
    require(budget['admitted'] and budget['planned_batch_bytes']==PREPARATION_BYTES+RESERVE and
            budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'],
            'complete preparation and trial budget missing')


def package():
    check_admission()
    return shared.package(base=BASE,prior=P358,trial='0360',patch=PATCH,mode=9,
        signed_edr_reference=P358/'edr-native/result.json')


def capture():
    check_admission()
    reference = load(REFERENCE)
    fresh = BASE/'current-root-capture'
    if not fresh.exists():
        profile = load(P359/'capture-profile.json')
        profile.update(out=str(fresh),phase='before-boot',expected_header_sha256=HEADER,
                       max_combined_log_bytes=reference['combined_log_bytes']+LOG_SUFFIX)
        import_module('capture-core342-root').capture(profile,save_files=False)
    current = check_baseline()
    slots = BASE/'slot-capture'
    if not slots.exists():
        subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
            '--baseline',str(REFERENCE),'--out',str(slots),'--reuse-data-from',str(P359/'slot-capture')],
            check=True,capture_output=True,timeout=300)
    snapshot = BASE/'metadata-snapshot'
    metadata = (load(snapshot/'result.json') if snapshot.exists() else
        import_module('capture-core342-metadata').capture(snapshot,HEADER,trial='0360',
            maximum_compressed_bytes=METADATA_BYTES))
    require(metadata['state']=='readonly0360-complete-special-metadata-overlay' and
            metadata['root_header_sha256']==HEADER and metadata['compressed_bytes']<=METADATA_BYTES and
            not (metadata['device_writes'] or metadata['device_boots']), 'live 0360 metadata differs')
    return dict(metadata_bytes=metadata['compressed_bytes'],log_bytes=current['combined_log_bytes'],device_writes=0)


def delta():
    check_admission()
    return shared.stage.delta(BASE,P358,trial='0360',header=HEADER,baseline=REFERENCE,core_logical=7_992_224)


def model():
    check_admission()
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0360')
    return dict(checks=len(result['checks']), failure_points=result['all_restore_partial_write_points'],
                maximum_actual_model_restore_bytes=result['maximum_actual_model_restore_bytes'],device_writes=0)


def controls():
    plan = expected_plan()
    out = BASE/'frame-host'
    try:
        runner.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                             static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'wrong early capture failure')
    else:
        raise ValueError('0360 frame analysis before independent restore')

    fixture = import_module('check-core342-pipeline')
    scenarios = []
    with TemporaryDirectory(prefix='0360-flow-',dir=out) as temporary:
        for name in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                     'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
            fixture.control_fixture(Path(temporary),plan,name,scenarios)
    receipt = dict(scenarios=scenarios,analysis_requires_independent_readback=True,device_commands=0)
    save(out/'control-models.json',receipt)
    return dict(scenarios=len(scenarios),device_commands=0)


def replay():
    # Exercise the real display collector against qualified 0358 inputs.
    # The only modeled wire field is one read reservation flag.
    raw = import_module('check-frame360').check_decoder(REF358)
    archive = load(REF358/'result.json')
    plan = expected_plan() | dict(kernel_banner=load(P358/'trial-plan.json')['kernel_banner'])
    before = load(REF358/'fresh-before/result.json')
    result = {key:archive[key] for key in ('restored','independent_restore_verified','static_root_comparison_passed')}
    with TemporaryDirectory(prefix='0360-display-replay-',dir=BASE) as temporary:
        path = Path(temporary)
        for filename in ('core-wait-execution-analysis.json','kernel-IO-identity-analysis.json',
                         'kernel-IO-analysis.json','independent-restore.json'):
            (path/filename).symlink_to(REF358/filename)
        (path/'kernel.log').write_text(raw)

        def reuse_verified_core(_execution,_plan,state,_before,_code):
            state['state'] = runner.prior.timeline.CORE_PASSED

        collect = partial(runner.prior.collect_after_restore,core_analyzer=reuse_verified_core)
        with patch.object(runner.prior,'collect_after_restore',collect):
            runner.after_restore(path,plan,result,before,0)
        require(result['state']==SUCCESS and result['active_surface_reservations']==1 and
                result['strict_new_frame_rate_bounds']==archive['strict_new_frame_rate_bounds'] and
                result['active_read_guards_crossing_deadline']==9 and
                not result['stable_60_fps_observed'], '0360 restored replay or reservation join differs')
    receipt = dict(state='0360-restored-display-replay-passed',modeled_reservation_receipts=1,
                   reference_pacing_unchanged=True,device_commands=0)
    save(BASE/'frame-host/restored-display-replay.json',receipt)
    return receipt


def storage(plan):
    bound = load(P358/'storage-bound-358.json')
    components = bound['components'] | dict(pacing_comparison=runner.PACING_BYTES)
    total = sum(components.values())
    require(bound['new_log_data_stored_once'] and total==182_106_272 and total<=RESERVE and
            plan['storage_reserve_bytes']==RESERVE and plan['log_capture']['maximum_suffix_bytes']==LOG_SUFFIX and
            plan['log_capture']['max_combined_log_bytes']-plan['log_capture']['measured_baseline_bytes']==LOG_SUFFIX,
            'runtime capture and recovery budget exceeds the reservation')
    return dict(bound,state='bounded0360-runtime-batch',components=components,worst_case_bytes=total,
        reserve_bytes=RESERVE,fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def criteria(plan):
    check_admission()
    original = load(P358/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','kernel_banner','kernel_identity','EDR_helper_sha256',
               'root_header_sha256','install_plan_sha256','storage_reserve_bytes','misc_before_sha256',
               'parent_trial_plan_sha256','read_reservation','optimization','performance_comparison','log_capture'}
    require({key for key in original.keys()|plan.keys() if original.get(key)!=plan.get(key)}<=allowed and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442 and
            plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            '0360 adds a device effect outside the reviewed scope')
    host,controls_data,replay_data,rollback,slots,metadata = (load(BASE/name) for name in (
        'frame-host/result.json','frame-host/control-models.json','frame-host/restored-display-replay.json',
        'restore-model/result.json','slot-capture/result.json','metadata-snapshot/result.json'))
    require(host['state']=='0360-host-verified' and host['kernel_sha256']==KERNEL and
            host['read_guard_concurrency_and_lifetime'] and host['exact_writer_decoder'] and
            [t['active_read_guards_crossing_deadline'] for t in host['trials']]==[9,25] and
            len(controls_data['scenarios'])==9 and controls_data['analysis_requires_independent_readback'] and
            replay_data['state']=='0360-restored-display-replay-passed' and
            rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            slots['baseline_sha256']==sha(REFERENCE) and len(slots['reused_original_data'])==6 and
            metadata['root_header_sha256']==HEADER and metadata['compressed_bytes']<=METADATA_BYTES,
            '0360 concurrency, CRC or restore models are incomplete')
    for name, saved in slots['reused_original_data'].items():
        expected = P359/'slot-capture'/(name+'-old-data.bin')
        require(Path(saved)==expected and (BASE/'slot-capture'/expected.name).resolve()==expected,
                '0360 original data archive path differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P358,HEADER,plan)


def pins():
    extra = [Path(__file__),WORK/'tests/fixtures/dpu360_read.cpp',
             BASE/'frame-host/control-models.json',BASE/'frame-host/restored-display-replay.json',
             P358/'trial-plan.json',P358/'storage-bound-358.json',P358/'slot-delta/install-plan.json',
             P359/'slot-capture/result.json']
    extra.extend(REF358/name for name in ('kernel.log','frame-scanout-analysis.json','result.json','independent-restore.json'))
    extra.extend(Path(p) for p in load(BASE/'slot-capture/result.json')['reused_original_data'].values())
    return shared.pins(base=BASE,prior=P359,doc=DOC,patch=PATCH,reference=REF359,trial='0360',extra=extra)


def freeze():
    return shared.freeze(base=BASE,prior=P359,expected=expected_plan,validate=criteria,
                        storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                        storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (admission,package,capture,delta,model,controls,replay,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
