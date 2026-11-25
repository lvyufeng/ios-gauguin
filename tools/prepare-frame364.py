#!/usr/bin/env python3
"""Stage, replay, freeze and review the matched 0364 capture on restored 0363."""

import argparse
from functools import partial
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from frame364_scope import (BASE, DOC, HEADER, LOG_SUFFIX, MAIN, METADATA_CAP, P363, PATCH,
    REF363, REFERENCE, REPORT_BYTES, RESERVE, SAVED_SLOTS, SUCCESS, WORK, check_archive, check_baseline,
    check_budget, expected_plan, load, require, sha)

shared = import_module('prepare-frame349')
save = shared.stage.save
TRIAL = '0364'


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
        import_module('capture-core342-metadata').capture(snapshot,HEADER,trial=TRIAL,
            maximum_compressed_bytes=METADATA_CAP))
    require(meta['root_header_sha256']==HEADER and meta['compressed_bytes']<=METADATA_CAP and
            not (meta['device_writes'] or meta['device_boots']), '0364 read-only metadata differs')
    return dict(files=len(current['files']),metadata_bytes=meta['compressed_bytes'],
                log_bytes=current['combined_log_bytes'],device_writes=0)


def delta():
    check_budget()
    for directory in ('core-native','edr-native'):
        receipt = Path(directory)/'result.json'
        (BASE/directory).mkdir(exist_ok=True)
        if not (BASE/receipt).exists():
            shutil.copyfile(P363/receipt,BASE/receipt)
        require(sha(BASE/receipt)==sha(P363/receipt),'0363 signed input receipt differs')
    result = shared.stage.delta(BASE,P363,trial=TRIAL,header=HEADER,baseline=REFERENCE)
    expected_plan()
    return result


def model():
    check_budget()
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(result['checks']),failure_points=result['all_restore_partial_write_points'],
                maximum_actual_model_restore_bytes=result['maximum_actual_model_restore_bytes'],device_writes=0)


def host():
    check_budget()
    archive = check_archive()
    runner = import_module('run-frame364-trial')
    from frame364_analysis import kernel, measure

    out = BASE/'frame-host'
    out.mkdir()
    reference = measure(REF363)
    slow = reference['slow_drag']
    front = reference['frontend']
    cases = slow['identity']['repeats']
    stages = [r['next_certified_copy']['stage'] for r in cases]
    require(slow['scans']=={'changed':74,'repeated':3,'unknown':0} and
            slow['identity']['complete_IO_submits']==112 and
            sum(bool(row['certified_copy'] and row['certified_copy']['core']) for row in slow['identity']['frames'])==74 and
            slow['first_through_last_changed']['swaps']==74 and
            [r['frame'] for r in cases]==[15736,15741,15750] and
            [r['next_certified_copy']['native_fence'] for r in cases]==[939,944,952] and
            stages==['issued_awaiting_observed_GPU_completion','submit_runtime_issue',
                     'issued_awaiting_observed_GPU_completion'] and
            all(r['preblank_probe']['result']=='lock_busy' for r in cases) and
            cases[0]['accepted_candidates'][1]['stage']=='Core_commit_queue' and
            cases[1]['accepted_candidates'][0]['stage']=='no_writer_claim_observed' and
            front['all_strokes']['scans']==61 and front['warm_strokes_3_to_13']['with_return']==24 and
            front['warm_strokes_3_to_13']['visible_by_cutoff_in_slack_model']==1,
            'archived 0363 targeted timing differs')
    core = load(REF363/'core-wait-execution-analysis.json')
    decoded = load(REF363/'kernel-IO-analysis.json')
    bounds = tuple(slow['identity']['IO_join_bounds_us'])
    legacy = kernel.join(decoded,core,bounds)
    require(legacy['errors']=={'program_new_BO_or_slab_reuse_not_observed_in_full_script':1},
            'warm-window exemption changed the full-script qualification')
    token = cases[1]['next_certified_copy']['kernel_token']
    damaged = dict(decoded,rows=[r for r in decoded['rows'] if r['token']!=token])
    rejected = kernel.join(damaged,core,bounds,require_program_activity=False)
    require(not rejected['coverage_qualified'] and rejected['errors'].get('missing_or_ambiguous_submit_identity')==1,
            'slow-drag exact join accepted missing IO identity')
    save(out/'archived-0363-deadlines.json',reference)

    plan = expected_plan()
    keys = ('restored','independent_restore_verified','static_root_comparison_passed')
    try:
        runner.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                             static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'wrong 0364 readback gate')
    else:
        raise ValueError('0364 analysis accepted an unrestored capture')
    with TemporaryDirectory(prefix='0364-host-replay-',dir=BASE) as temporary:
        folder = Path(temporary)
        for name in ('kernel.log','kernel.log.bin','core-wait-execution-analysis.json',
                     'kernel-IO-identity-analysis.json','kernel-IO-analysis.json','independent-restore.json',
                     'springboard-new.log'):
            (folder/name).symlink_to(REF363/name)

        def archived_core(_path,_plan,result,_before,_code):
            result['state'] = runner.scorer.prior.timeline.CORE_PASSED

        verdict = {key:archive[key] for key in keys}
        collection = partial(runner.scorer.prior.collect_after_restore,core_analyzer=archived_core)
        with patch.object(runner.scorer.prior,'collect_after_restore',collection):
            runner.after_restore(folder,plan,verdict,load(REF363/'fresh-before/result.json'),0)
        require(verdict['state']==SUCCESS and verdict['frame_trace_complete'] and
                verdict['strict_new_frame_rate_bounds']==archive['strict_new_frame_rate_bounds'] and
                verdict['slow_drag_joined_submissions']==112 and
                not verdict['sustained_motion_steady_60_qualified'] and
                (folder/'present-alignment-0363-0364.json').is_file(), '0364 full after-restore replay differs')
        replay = load(folder/'motion-identity-0363-0364.json')
        require(replay['reference_0363']==replay['current_0364'] and
                len(replay['slow_drag_alignment_by_scan_ordinal'])==77,'self-comparison changed identical wire data')
    report = dict(state='0364-archived-identities-and-after-readback-replay-qualified',
        input_pins={str(out/'archived-0363-deadlines.json'):sha(out/'archived-0363-deadlines.json')},
        matched_slow_submits=112,matched_certified_copies=74,repeat_stages=stages,missing_IO_rejected=True,
        restoration_gate_checked=True,all_13_and_slow_scan_ordinals_checked=True,device_commands=0)
    save(out/'result.json',report)
    return report


def storage(plan):
    previous = load(P363/'storage-bound-363.json')
    components = dict(previous['components'])
    components.pop('SDK_and_motion_comparison')
    components['matched_producer_and_motion_comparison'] = REPORT_BYTES
    measured = plan['log_capture']['measured_baseline_bytes']
    require(previous['new_log_data_stored_once'] and
            sum(components.values())==previous['worst_case_bytes']<=RESERVE and
            plan['log_capture']['max_combined_log_bytes']==measured+LOG_SUFFIX,
            '0364 storage reservation does not cover bounded results and verified suffixes')
    return dict(previous,state='bounded0364-runtime-batch',components=components,
                fresh_log_bytes=measured,log_cap_bytes=measured+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    prior = load(P363/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','install_plan_sha256','parent_trial_plan_sha256',
        'new_kernel_builds','new_boot_images','optimization','performance_comparison','log_capture'}
    require({key for key in plan.keys()|prior.keys() if plan.get(key)!=prior.get(key)}<=allowed,
            '0364 broadens the frozen destructive or volatile scope')
    install = load(BASE/'slot-delta/install-plan.json')
    previous_install = load(P363/'slot-delta/install-plan.json')
    require(all(row['new_file_sha256']==previous_install['rows'][name]['new_file_sha256'] and
                row['new_logical']==previous_install['rows'][name]['new_logical']
                for name,row in install['rows'].items()), '0364 candidate file differs from 0363')
    host,model,slots,meta = (load(BASE/name) for name in ('frame-host/result.json',
        'restore-model/result.json','slot-capture/result.json','metadata-snapshot/result.json'))
    require(host['state']=='0364-archived-identities-and-after-readback-replay-qualified' and
            host['matched_certified_copies']==74 and host['matched_slow_submits']==112 and
            host['restoration_gate_checked'] and host['missing_IO_rejected'] and
            model['all_model_IO_writes_memory_only'] and len(model['checks'])==47 and
            model['all_restore_partial_write_points']==17 and
            model['maximum_actual_model_restore_bytes']<=plan['maximum_restore_userdata_bytes'] and
            model['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            slots['baseline_sha256']==sha(REFERENCE) and len(slots['reused_original_data'])==6 and
            meta['root_header_sha256']==HEADER and meta['compressed_bytes']<=METADATA_CAP and
            not any(r['device_writes'] or r['device_boots'] for r in (slots,meta)),
            '0364 archived timing, fresh allocation or restore proof differs')
    for name,path in slots['reused_original_data'].items():
        original = SAVED_SLOTS/(name+'-old-data.bin')
        require(Path(path)==original and (BASE/'slot-capture'/original.name).resolve()==original,
                '0364 rollback data differs from archived original')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P363,HEADER,plan)


def pins():
    artifacts = (P363/'native-kernel/build-manifest.json',P363/'frame363-image.json',
        BASE/'core-native/result.json',BASE/'edr-native/result.json',BASE/'frame-host/result.json',
        BASE/'restore-model/result.json')
    extra = [P363/'slot-delta/install-plan.json',P363/'gate-start-host.json',
        REF363/'frame-pacing-0361-0363.json',REF363/'kernel-IO-analysis.json',REF363/'springboard-new.log',
        MAIN/'research/tmp/0364-storage-retirement/verified-retirement-manifest.json',
        MAIN/'research/tmp/0364-storage-retirement/retirement-complete.json']
    extra.extend(Path(path) for path in load(BASE/'slot-capture/result.json')['reused_original_data'].values())
    return shared.pins(base=BASE,prior=P363,doc=DOC,patch=PATCH,reference=REF363,trial=TRIAL,
                       extra=extra,artifacts=artifacts)


def freeze():
    return shared.freeze(base=BASE,prior=P363,expected=expected_plan,validate=criteria,
                         storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (capture,delta,model,host,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
