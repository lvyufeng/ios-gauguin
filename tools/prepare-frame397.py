#!/usr/bin/env python3
"""Freeze one bounded 60 Hz boot for the completed resident-buffer allocation path."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

previous = import_module('prepare-frame393')
check = import_module('check-frame397')
BASE, P393, P394, IMAGE = check.BASE, check.P393, check.P394, check.IMAGE
LAST = P393/'execution'
KERNEL = BASE/'native-kernel/build-manifest.json'
OFFLINE = BASE/'offline.json'
DOC = WORK/'docs/gauguin-frame-397-resident-buffer-overlap-20261123.md'
BATCH, RESERVE, shared, save = previous.BATCH, previous.RESERVE, previous.shared, previous.save
TRIAL = '0397'
FLAGS = (*[flag for flag in previous.FLAGS if not flag.startswith('allow_0393')],
         'allow_0397_one_bounded_60Hz_temporary_boot_with_completed_resident_BO_reuse')
SUCCESS = '0397-resident-BO-overlap-physically-measured-root-restored'


def admitted():
    budget = load(BASE/'live-batch-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==BATCH and
        budget['current_accounted_bytes']+BATCH<=budget['limit_bytes'], '0397 full batch exceeds storage')


def recovery_parent():
    return P394 if (P394/'execution').exists() else P393


def baseline(*, fresh=True):
    control = load(LAST/'result.json')
    require(control['DPU_independent_physical_FPS_qualified'] and control['restored'] and
        control['independent_restore_verified'] and not control['stable_60_fps_observed'], '0393 physical control is unavailable or already stable')
    recovery = recovery_parent()
    end, proof, restored = (load(recovery/'execution'/path) for path in (
        'result.json', 'independent-restore.json', 'restored-capture/result.json'))
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed'] and
        proof['install_plan_sha256']==load(recovery/'trial-plan.json')['install_plan_sha256'] and
        proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'] and
        proof['root_header_sha256']==restored['root_header_sha256'] and not end.get('stable_60_fps_observed',False),
        '0397 requires the current independently restored root and unfinished stable 60 fps')
    if not fresh:
        return restored
    now = load(BASE/'current-root-capture/result.json')
    require(not now['device_writes'] and len(now['files'])==31 and all(now[key]==restored[key] for key in (
        'root_header_sha256', 'combined_log_bytes', 'files', 'directories')), 'fresh recovery and last verified root differ')
    return now


def capture():
    admitted()
    return previous.previous.capture_from(BASE,recovery_parent(),TRIAL,baseline)


def delta():
    live = baseline()
    for kind in ('core','c4'):
        target = BASE/(kind+'-native/result.json')
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(P393/(kind+'-native/result.json'),target)
    return shared.stage.delta(BASE,P393,trial=TRIAL,header=live['root_header_sha256'],
        baseline=recovery_parent()/'execution/restored-capture/result.json',core_logical=7_975_712)


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    live = baseline()
    parent_path = P393/'trial-plan.json'
    parent = load(parent_path)
    old_log_bytes = load(recovery_parent()/'trial-plan.json')['log_capture']['measured_baseline_bytes']
    install_path = BASE/'slot-delta/install-plan.json'
    helper_path = BASE/'edr-native/result.json'
    install, image, native, helper, offline = (load(p) for p in (install_path,IMAGE,KERNEL,helper_path,OFFLINE))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    require(offline['exact_cases']==25 and offline['ASan_UBSan'] and not offline['device_commands'] and
        native['baseline_reproduced_except_uuid'] and native['inputs_unchanged'] and
        native['input_pins'][str(check.PATCH)]==offline['patch_sha256']==sha(check.PATCH) and
        len(native['object_replacements'])==1 and all(Path(p).stem=='GauguinGPU' for p in native['object_replacements'].values()) and
        sha(image['image'])==image['image_sha256'] and sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
        image['command']==parent['boot_command'] and image['command'].split().count('sweetgpumap=1')==1 and
        image['build_identity']==native['identity']==helper['kernel_identity'] and helper['matching_0393_machine_code'] and
        sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
        install['core_sha256']==parent['owned_core_sha256'] and install['trial']==TRIAL and
        install['root_header_sha256']==header and install['changed_ranges']==12 and
        sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
        parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
        parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
        parent['sustained_motion']['normal_reports']==162, '0397 eligible allocator, timing or restoration scope differs')
    return dict(parent,state='prepared-frame397-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=native['identity'],kernel_banner=native['kernel_banner'],EDR_helper_sha256=helper['binary_sha256'],
        signed_native_EDR_scope_sha256=sha(helper_path),
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={key:live['files'][key]['bytes'] for key in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-old_log_bytes),
        optimization='Return only a completed resident ordinary BO while unrelated GPU work is pending.',
        performance_comparison='Compare 0393/0397 allocation waits, native GPU stages, first response and physical frame repeats.')


def criteria(plan):
    admitted()
    parent = load(P393/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256',
        'signed_native_EDR_scope_sha256','log_capture','optimization','performance_comparison'}
    require({k for k in parent.keys() | plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0397 effect scope differs')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P393,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
         =={'admission'},'0397 affected userspace outside the signed kernel admission')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
        proof['all_restore_partial_write_points']==17,'0397 rollback model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P393,plan['root_header_sha256'],plan)


def storage(plan):
    prior = load(P393/'storage-bound-393.json')
    require(prior['worst_case_bytes']<=RESERVE,'0397 runtime exceeds reserve')
    return dict(prior,state='bounded0397-resident-BO-overlap-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    scripts = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    recovery = recovery_parent()
    parent = load(P393/'trial-plan.json')
    files = [*(WORK/path for path in scripts), DOC,check.PATCH,check.FIXTURE,OFFLINE,IMAGE,KERNEL,
        MAIN/'tools/storage-budget.py',BASE/'live-batch-admission.json',BASE/'rebuild-admission.json',BASE/'package-admission.json',
        BASE/'current-root-capture/result.json',Path(parent['observer_helper']), P393/'ready.json',P393/'trial-plan.json',
        P393/'storage-bound-393.json',recovery/'trial-plan.json',recovery/'capture-profile.json',
        *(recovery/'execution'/path for path in ('result.json','independent-restore.json','restored-capture/result.json')),
        *(LAST/path for path in ('result.json','independent-restore.json','scanout-comparison-0395-0393.json',
            'kernel.log','kernel.log.bin','page-flip-latches.json','kernel-IO-analysis.json'))]
    result = previous.previous.scoped_pins(BASE,files,KERNEL,IMAGE)
    for name,digest in load(OFFLINE)['input_pins'].items():
        require(sha(name)==digest and result.setdefault(name,digest)==digest,'0397 offline inputs changed')
    return result


def freeze():
    return shared.freeze(base=BASE,prior=recovery_parent(),expected=expected_plan,validate=criteria,storage_bound=storage,
        pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
        preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {f.__name__:f for f in (capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=actions)
    print(json.dumps(actions[parser.parse_args().step](),indent=2))
