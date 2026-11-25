#!/usr/bin/env python3
"""Freeze the bounded idle performance-core experiment after 0397 restoration."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

check = import_module('check-frame398')
previous = import_module('prepare-frame397')
BASE,P397,IMAGE = check.BASE,check.P397,check.IMAGE
LAST = P397/'execution'
KERNEL = BASE/'native-kernel/build-manifest.json'
OFFLINE = BASE/'offline.json'
ORIGINAL = BASE/'scheduler-control-text.json'
DOC = WORK/'docs/gauguin-frame-398-performance-core-scheduler-20261123.md'
BATCH,RESERVE,shared,save = previous.BATCH,previous.RESERVE,previous.shared,previous.save
TRIAL = '0398'
FLAGS = (*[flag for flag in previous.FLAGS if not flag.startswith('allow_0397')],
    'allow_0398_one_bounded_60Hz_temporary_boot_with_idle_performance_core_preference')
SUCCESS = '0398-idle-performance-core-physically-measured-root-restored'


def admitted():
    whole = load(BASE/'complete-batch-admission.json')
    budget = load(BASE/'live-batch-admission.json')
    require(whole['admitted'] and whole['planned_batch_bytes']==BATCH+60_000_000 and
        whole['current_accounted_bytes']+whole['planned_batch_bytes']<=whole['limit_bytes'] and
        budget['admitted'] and budget['planned_batch_bytes']==BATCH and
        budget['current_accounted_bytes']+BATCH<=budget['limit_bytes'],'0398 full batch exceeds storage')


def baseline(*,fresh=True):
    end,proof,back = (load(LAST/p) for p in ('result.json','independent-restore.json','restored-capture/result.json'))
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed'] and
        end['DPU_independent_physical_FPS_qualified'] and not end['stable_60_fps_observed'] and
        proof['install_plan_sha256']==load(P397/'trial-plan.json')['install_plan_sha256'] and
        proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'] and
        proof['root_header_sha256']==back['root_header_sha256'],'0397 must be physically measured and independently restored')
    if not fresh:
        return back
    live = load(BASE/'current-root-capture/result.json')
    require(not live['device_writes'] and len(live['files'])==31 and all(live[k]==back[k] for k in (
        'root_header_sha256','combined_log_bytes','files','directories')),'0398 recovery root differs from 0397')
    return live


def capture():
    admitted()
    return previous.previous.previous.capture_from(BASE,P397,TRIAL,baseline)


def delta():
    for kind in ('core','c4'):
        destination = BASE/(kind+'-native/result.json')
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(P397/(kind+'-native/result.json'),destination)
    return shared.stage.delta(BASE,P397,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=7_975_712)


def model():
    r = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(r['checks']),failure_points=r['all_restore_partial_write_points'])


def expected_plan():
    live = baseline()
    parent_path = P397/'trial-plan.json'
    parent = load(parent_path)
    path = BASE/'slot-delta/install-plan.json'
    helper_path = BASE/'edr-native/result.json'
    install, image, native, helper, host, original = (load(p) for p in (path,IMAGE,KERNEL,helper_path,OFFLINE,ORIGINAL))
    header,size = (live[k] for k in ('root_header_sha256','combined_log_bytes'))
    require(host['ASan_UBSan'] and original['exact_ARM64_text'] and original['bytes']==54732 and
        not (host['device_commands'] or original['device_commands']) and native['inputs_unchanged'] and
        native['baseline_reproduced_except_uuid'] and native['input_pins'][str(check.PATCH)]==host['patch_sha256']==sha(check.PATCH) and
        {Path(p).stem for p in native['object_replacements'].values()}=={'GauguinGPU','sched_prim'} and
        sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and sha(image['image'])==image['image_sha256'] and
        image['build_identity']==native['identity']==helper['kernel_identity'] and image['command']==parent['boot_command'] and
        helper['matching_0397_machine_code'] and sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
        install['core_sha256']==parent['owned_core_sha256'] and install['trial']==TRIAL and
        install['root_header_sha256']==header and install['changed_ranges']==12 and
        sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
        parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
        parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
        parent['sustained_motion']['normal_reports']==162,'0398 candidate, display timing or restore scope differs')
    return dict(parent,state='prepared-frame398-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(path),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=helper['binary_sha256'],signed_native_EDR_scope_sha256=sha(helper_path),
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={k:live['files'][k]['bytes'] for k in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-parent['log_capture']['measured_baseline_bytes']),
        optimization='Prefer an idle recommended performance CPU for the observed compositor recorder.',
        performance_comparison='Compare 0397 and 0398 CPU placement, recorder timing and actual per-vblank content.')


def criteria(plan):
    admitted()
    parent = load(P397/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'log_capture','optimization','performance_comparison'}
    require({k for k in parent.keys() | plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0398 effect scope differs')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P397,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
        =={'admission'},'0398 altered userspace beyond the signed new-kernel admission')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
        proof['all_restore_partial_write_points']==17,'0398 restore model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P397,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P397/'storage-bound-397.json')
    require(old['worst_case_bytes']<=RESERVE,'0398 runtime exceeds reserve')
    return dict(old,state='bounded0398-idle-core-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    parent = load(P397/'trial-plan.json')
    files = [*(WORK/p for p in tracked), DOC,OFFLINE,ORIGINAL,KERNEL,IMAGE,check.PATCH,check.FIXTURE,check.FDT,
        MAIN/'tools/storage-budget.py',BASE/'complete-batch-admission.json',BASE/'live-batch-admission.json',
        BASE/'scheduler-recipe.json',
        BASE/'current-root-capture/result.json',Path(parent['observer_helper']),P397/'ready.json',P397/'trial-plan.json',
        P397/'capture-profile.json',P397/'storage-bound-397.json',*(LAST/p for p in ('result.json','independent-restore.json',
        'restored-capture/result.json','scanout-comparison-0393-0397.json','kernel.log','kernel.log.bin','page-flip-latches.json'))]
    pins = previous.previous.previous.scoped_pins(BASE,files,KERNEL,IMAGE)
    for origin in (OFFLINE,BASE/'scheduler-recipe.json'):
        for path,digest in load(origin)['input_pins'].items():
            require(sha(path)==digest and pins.setdefault(path,digest)==digest,'0398 compiler or stock DT evidence changed')
    return pins


def freeze():
    return shared.freeze(base=BASE,prior=P397,expected=expected_plan,validate=criteria,storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {f.__name__:f for f in (capture,delta,model,freeze,review)}
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=actions)
    print(json.dumps(actions[parser.parse_args().step](),indent=2))
