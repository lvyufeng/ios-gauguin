#!/usr/bin/env python3
"""Freeze the verified F344 repair over the restored 0362 root."""

import argparse
from functools import partial
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from frame363_scope import (BASE, CONSOLE_RESERVE, CONTROL, CORE_BYTES, DOC, HEADER, LOG_SUFFIX,
    MAIN, METADATA_CAP, P361, P362, PATCH, REF361, REF362, REFERENCE, RESERVE, SAVED_SLOTS, SUCCESS,
    WORK, check_baseline, check_budget, expected_plan, load, require, sha, signed_pair)

shared = import_module('prepare-frame349')
save = shared.stage.save


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
        import_module('capture-core342-metadata').capture(snapshot,HEADER,trial='0363',
            maximum_compressed_bytes=METADATA_CAP))
    require(meta['root_header_sha256']==HEADER and meta['compressed_bytes']<=METADATA_CAP and
            not (meta['device_writes'] or meta['device_boots']), '0363 read-only metadata differs')
    return dict(files=len(current['files']),metadata_bytes=meta['compressed_bytes'],
                log_bytes=current['combined_log_bytes'],device_writes=0)


def delta():
    check_budget()
    receipt,pair = signed_pair(P361)
    core = pair['variants']['reference']
    subprocess.run(['codesign','--verify','--strict',core['binary']],check=True,capture_output=True,timeout=60)
    (BASE/'core-native').mkdir()
    save(BASE/'core-native/result.json',dict(state='0363-exact-SDK27.2-unmodified-Core-signed',
        binary=core['binary'],binary_sha256=CONTROL,bytes=CORE_BYTES,sdk='27.2',signature_verified=True,
        input_pins={str(receipt):sha(receipt)},device_commands=0))
    return shared.stage.delta(BASE,P362,trial='0363',header=HEADER,baseline=REFERENCE,core_logical=CORE_BYTES)


def model():
    check_budget()
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0363')
    return dict(checks=len(result['checks']),failure_points=result['all_restore_partial_write_points'],
                maximum_actual_model_restore_bytes=result['maximum_actual_model_restore_bytes'],device_writes=0)


def host():
    check_budget()
    plan = expected_plan()
    out = BASE/'frame-host'
    out.mkdir()
    old_check = import_module('check-frame362')
    runner = import_module('run-frame363-trial')
    baseline = import_module('run-frame362-trial').scorer
    archive = load(REF361/'result.json')
    ref_plan = load(P361/'trial-plan.json')
    proof_keys = ('restored','independent_restore_verified','static_root_comparison_passed')
    try:
        runner.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                             static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'wrong 0363 readback gate')
    else:
        raise ValueError('0363 analysis accepted an unrestored capture')
    workload = old_check.replay(out,plan,base=BASE)
    frame = load(REF361/'frame-scanout-analysis.json')
    raw = (REF361/'kernel.log').read_text()
    with TemporaryDirectory(prefix='0363-full-scorer-',dir=BASE) as temporary:
        folder = Path(temporary)
        for name in ('core-wait-execution-analysis.json','kernel-IO-identity-analysis.json',
                     'kernel-IO-analysis.json','independent-restore.json','springboard-new.log'):
            (folder/name).symlink_to(REF361/name)
        (folder/'kernel.log').write_text(old_check.modeled_motion(raw,frame))

        def archived_qualified_core(_path,_plan,result,_before,_code):
            result['state'] = baseline.prior.timeline.CORE_PASSED

        result = {key:archive[key] for key in proof_keys}
        replay = partial(baseline.prior.collect_after_restore,core_analyzer=archived_qualified_core)
        fixture_plan = dict(plan,kernel_banner=ref_plan['kernel_banner'])
        with patch.object(baseline.prior,'collect_after_restore',replay):
            runner.after_restore(folder,fixture_plan,result,load(REF361/'fresh-before/result.json'),0)
        require(result['state']==SUCCESS and result['frame_trace_complete'] and
                result['strict_new_frame_rate_bounds']==archive['strict_new_frame_rate_bounds'] and
                result['matched_original_stroke_core']['0363']['joined_submissions']==741 and
                result['expected_motion_benchmark'] and not result['stable_60_fps_observed'] and
                result['sustained_motion']['scans']['changed']==0 and
                (folder/'SDK27-0361-0363-comparison.json').is_file(),
                '0363 full after-restore replay differs')
    # Use intact F344 from 0361 to estimate the console contribution absent
    # in 0362. Periodic vblank/CRC rows are already in the 0361 contribution.
    frame_bytes = sum(len(line.encode())+1 for line in raw.splitlines()
                      if line.startswith(('SWEET F344','SWEET F345','SWEET F348',
                                          'SWEET F349','SWEET F350','SWEET F358','SWEET F357')))
    extra = workload['capture_headroom']
    require(frame_bytes+extra['modeled_extra_f344_bytes']+extra['motion_event_reserve_bytes']<=CONSOLE_RESERVE,
            'repaired frame capture exceeds measured console headroom')
    report = dict(state='0363-matched-13-and-sustained-replay-qualified',device_commands=0,
        passed_host_gate=sha(BASE/'gate-start-host.json'),workload=workload,
        measured_frame_console_bytes=frame_bytes,modeled_motion_actuation=True)
    save(out/'result.json',report)
    return report


def storage(plan):
    previous = load(P362/'storage-bound-362.json')
    measured = plan['log_capture']['measured_baseline_bytes']
    require(previous['reserve_bytes']==RESERVE and previous['new_log_data_stored_once'] and
            sum(previous['components'].values())==previous['worst_case_bytes']==186_106_272 and
            plan['log_capture']['max_combined_log_bytes']==measured+LOG_SUFFIX,
            '0363 runtime reserve differs from its same-scope predecessor')
    return dict(previous,state='bounded0363-runtime-batch',fresh_log_bytes=measured,log_cap_bytes=measured+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    previous = load(P362/'trial-plan.json')
    changed = {'state','trial','root_header_sha256','install_plan_sha256','parent_trial_plan_sha256',
        'image','image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256',
        'optimization','performance_comparison','log_capture'}
    require({k for k in plan.keys()|previous.keys() if plan.get(k)!=previous.get(k)}<=changed,
            '0363 adds a device effect outside the verified F344 gate')
    gate,host,rollback,slots,meta = (load(BASE/name) for name in ('gate-start-host.json',
        'frame-host/result.json','restore-model/result.json','slot-capture/result.json','metadata-snapshot/result.json'))
    require(gate['state']=='0363-packed-boot-and-capture-prepare-passed' and gate['boot_selector']==4 and
            gate['cases']==480 and gate['capture_transition_and_single_poll_start'] and
            host['state']=='0363-matched-13-and-sustained-replay-qualified' and
            host['passed_host_gate']==sha(BASE/'gate-start-host.json') and
            host['workload']['control_models']==9 and host['workload']['reference_no_swap_scans']==64 and
            rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and
            rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            slots['baseline_sha256']==sha(REFERENCE) and len(slots['reused_original_data'])==6 and
            meta['root_header_sha256']==HEADER and meta['compressed_bytes']<=METADATA_CAP and
            not any(r['device_writes'] or r['device_boots'] for r in (slots,meta)),
            '0363 capture start or fresh rollback model differs')
    for name,old in slots['reused_original_data'].items():
        expected = SAVED_SLOTS/(name+'-old-data.bin')
        require(Path(old)==expected and (BASE/'slot-capture'/expected.name).resolve()==expected,
                '0363 original slot archive differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P362,HEADER,plan)


def pins():
    cleanup = MAIN/'research/tmp/0363-storage-retirement'
    artifacts = tuple(BASE/name for name in ('native-kernel/build-manifest.json','frame363-image.json',
        'edr-native/result.json','core-native/result.json','frame-host/result.json','restore-model/result.json',
        'gate-start-host.json'))
    extras = [P362/'slot-delta/install-plan.json',REF362/'result.json',REF362/'independent-restore.json',
        REFERENCE,REF362/'kernel.log',REF361/'frame-pacing-0360-0361.json',
        REF361/'driver-copy-rate-comparison.json',REF361/'springboard-new.log',REF361/'kernel-IO-analysis.json',
        cleanup/'verified-retirement-manifest.json',cleanup/'retirement-complete.json']
    extras.extend(Path(path) for path in load(BASE/'slot-capture/result.json')['reused_original_data'].values())
    return shared.pins(base=BASE,prior=P362,doc=DOC,patch=PATCH,reference=REF361,trial='0363',
                       extra=extras,artifacts=artifacts)


def freeze():
    return shared.freeze(base=BASE,prior=P362,expected=expected_plan,validate=criteria,
                        storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                        storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (capture,delta,model,host,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
