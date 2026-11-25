#!/usr/bin/env python3
"""Freeze a repeat or a single DPU work-duration change after 0407 is measured."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX,MAIN,WORK,load,require,sha

check = import_module('check-frame408-dispatch')
prior = import_module('prepare-frame407')
BASE,P407 = check.BASE,check.P407
LAST = P407/'execution'
CONTROL = LAST/'scanout-comparison-0404-0407.json'
P404 = prior.P404
BEST_CONTROL = prior.CONTROL
CHOICE = BASE/'work-duration-selection.json'
HOST = BASE/'offline-1401.json'
IMAGE = BASE/'frame408-image.json'
DOC = WORK/'docs/gauguin-frame-408-dpu-work-duration-20261124.md'
TRIAL = '0408'
BATCH,RESERVE,shared,save = prior.BATCH,prior.RESERVE,prior.shared,prior.save
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0407')],
         'allow_0408_one_bounded_60Hz_temporary_boot_with_reviewed_compositor_work_duration')
SUCCESS = '0408-DPU-work-duration-physically-measured-root-restored'


def budget(name,planned):
    proof = load(BASE/name)
    require(proof['admitted'] and proof['planned_batch_bytes']==planned and
            proof['current_accounted_bytes']+planned<=proof['limit_bytes'],'0408 batch exceeds storage')


def decision():
    selection = load(CHOICE)
    result = load(LAST/'result.json')
    work = selection['work_duration_us']
    require(result['DPU_independent_physical_FPS_qualified'] and result['independent_restore_verified'] and
            selection['terminal_sha256']==sha(LAST/'result.json') and
            selection['comparison_sha256']==sha(CONTROL) and
            (work==0)==result['stable_60_fps_observed'], '0408 decision differs from restored physical evidence')
    if work:
        require(work==load(HOST)['work_us'] and selection['physical_control_sha256']==sha(BEST_CONTROL) and
                selection['reference_stock_khz']==1_401_600,'0408 staged duration or stock control differs')
    return work


def baseline(*,fresh=True):
    terminal,proof,restored = (load(LAST/name) for name in (
        'result.json','independent-restore.json','restored-capture/result.json'))
    require(terminal['trial']=='0407' and terminal['boot_attempts']==1 and terminal['restored'] and
            terminal['independent_restore_verified'] and terminal['static_root_comparison_passed'] and
            proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and
            proof['misc_original_4096_bytes_match'] and proof['root_header_sha256']==restored['root_header_sha256'] and
            proof['install_plan_sha256']==load(P407/'trial-plan.json')['install_plan_sha256'],
            '0407 independent restoration differs')
    if not fresh:
        return restored
    live = load(BASE/'current-root-capture/result.json')
    require(not live['device_writes'] and len(live['files'])==31 and all(live[k]==restored[k] for k in (
        'root_header_sha256','combined_log_bytes','files','directories')), '0408 recovery root differs')
    return live


def kernel_manifest(work):
    path = BASE/'native-kernel-1401/build-manifest.json' if work else check.CONTROL
    kernel = load(path)
    require(kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            sha(kernel['kernel'])==kernel['kernel_sha256'],'0408 kernel differs')
    if work:
        host = load(HOST)
        require({Path(p).stem for p in kernel['object_replacements'].values()}==
                    {'SweetFramebuffer','gauguin_ui_trace_board'} and host['stock_target_khz']==1_401_600 and
                kernel['input_pins'][str(check.PATCH)]==host['patch_sha256']==sha(check.PATCH) and
                kernel['input_pins'][str(check.STOCK_PATCH)]==host['stock_patch_sha256']==sha(check.STOCK_PATCH),
                '0408 candidate changed units outside DPU work and the verified stock point')
    return path,kernel


def package():
    work = decision()
    budget('complete-batch-admission.json',BATCH+60_000_000 if work else BATCH)
    baseline(fresh=False)
    kernel_path,kernel = kernel_manifest(work)
    parent = load(P407/'trial-plan.json')
    donor = P407/'edr-native/result.json'
    old = load(donor)
    if work:
        pack = import_module('package-frame344')
        setup = import_module('prepare-frame393')
        image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
            frame_capture_mode=9,scripted_motion=True,private_scanout_shim=setup.previous.previous.previous.prior388.SHIM,
            command_profile=setup.previous.command_profile)
        control,candidate = (pack.parts(Path(p).read_bytes()) for p in (parent['image'],image['image']))
        require(control[0][:16]==candidate[0][:16] and control[0][20:]==candidate[0][20:] and
                control[1]==candidate[1] and control[3]==candidate[3] and image['command']==parent['boot_command'],
                '0408 wrapper or physical DPU mode differs')
        helper = pack.edr(image,base=BASE,trial=TRIAL,
            signed_reference=prior.prior.prior.previous.check.placement.P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
        words = import_module('check-frame395-edr').native_words
        require(sha(old['binary'])==old['binary_sha256'] and words(helper['binary'])==words(old['binary']),
                '0408 signed GPU point differs')
        helper['matching_0407_machine_code'] = True
        helper['input_pins'].update({str(donor):sha(donor),old['binary']:old['binary_sha256']})
    else:
        image,helper = load(P407/'frame407-image.json'),old
        (BASE/'edr-native').mkdir()
    image['kernel_manifest'] = str(kernel_path)
    save(BASE/'edr-native/result.json',helper)
    save(IMAGE,image)
    for kind in ('core','c4'):
        receipt = BASE/f'{kind}-native/result.json'
        receipt.parent.mkdir()
        shutil.copyfile(P407/f'{kind}-native/result.json',receipt)
    return {k:image[k] for k in ('image_sha256','image_bytes','build_identity')}


def capture():
    budget('live-batch-admission.json',BATCH)
    return prior.prior.prior.previous.capture_tools.capture_from(BASE,P407,TRIAL,baseline)


def delta():
    return shared.stage.delta(BASE,P407,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    live,work = baseline(),decision()
    _,kernel = kernel_manifest(work)
    parent_path = P407/'trial-plan.json'
    parent = load(parent_path)
    install_path,helper_path = BASE/'slot-delta/install-plan.json',BASE/'edr-native/result.json'
    install,helper,image = map(load,(install_path,helper_path,IMAGE))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    require(kernel['kernel_sha256']==image['kernel_sha256'] and sha(image['image'])==image['image_sha256'] and
            image['build_identity']==kernel['identity']==helper['kernel_identity'] and
            image['command']==parent['boot_command'] and
            (helper['matching_0407_machine_code'] if work else parent['image_sha256']==image['image_sha256']) and
            sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
            install['core_sha256']==parent['owned_core_sha256'] and install['C4_sha256']==parent['C4_sha256'] and
            install['rows']['core']['new_logical']==parent['owned_core_logical_bytes'] and
            install['rows']['c4']['new_logical']==parent['C4_logical_bytes'] and
            install['trial']==TRIAL and install['root_header_sha256']==header and install['changed_ranges']==12 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
            parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
            parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
            parent['sustained_motion']['normal_reports']==162,'0408 exact timing or recovery scope differs')
    return dict(parent,state='prepared-frame408-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=helper['binary_sha256'],
        signed_native_EDR_scope_sha256=sha(helper_path),work_duration_us=work,
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={k:live['files'][k]['bytes'] for k in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-parent['log_capture']['measured_baseline_bytes']),
        optimization=f'Use a {work} us compositor budget on the same DPU cadence.' if work else 'Repeat the exact 0407 profile.',
        performance_comparison='Align warm and drag scans against 0407 after verified restoration.')


def criteria(plan):
    budget('complete-batch-admission.json',BATCH+60_000_000 if plan['work_duration_us'] else BATCH)
    budget('live-batch-admission.json',BATCH)
    parent = load(P407/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'log_capture','optimization','performance_comparison','work_duration_us'}
    require({k for k in parent.keys()|plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0408 scope differs')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P407,BASE))
    changes = {'admission'} if plan['work_duration_us'] else set()
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
            ==changes,'0408 userspace differs beyond reviewed kernel identity')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0408 recovery model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P407,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P407/'storage-bound-407.json')
    require(old['worst_case_bytes']<=RESERVE,'0408 runtime exceeds reserve')
    return dict(old,state='bounded0408-DPU-work-duration-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    parent = load(P407/'trial-plan.json')
    work = decision()
    kernel,_ = kernel_manifest(work)
    paths = [*(WORK/p for p in tracked),DOC,kernel,IMAGE,CONTROL,CHOICE,MAIN/'tools/storage-budget.py',
        BASE/'complete-batch-admission.json',BASE/'live-batch-admission.json',BASE/'current-root-capture/result.json',
        Path(parent['observer_helper']),*(P407/p for p in ('ready.json','storage-bound-407.json','trial-plan.json',
            'capture-profile.json','core-native/result.json','c4-native/result.json','edr-native/result.json')),
        *(LAST/p for p in ('result.json','independent-restore.json','restored-capture/result.json',
                           'kernel.log','kernel.log.bin','page-flip-latches.json'))]
    if work:
        paths += [HOST,check.PATCH,check.STOCK_PATCH,BASE/'native-stock-1401-admission.json',BEST_CONTROL,
            P404/'trial-plan.json',*(P404/'execution'/p for p in ('result.json','independent-restore.json',
                'kernel.log','kernel.log.bin','page-flip-latches.json'))]
    retirement = BASE/'retired-exact-generated-install-archives.json'
    if retirement.is_file():
        paths.append(retirement)
    bindings = prior.prior.prior.previous.capture_tools.scoped_pins(BASE,paths,kernel,IMAGE)
    if work:
        for path,digest in load(HOST)['input_pins'].items():
            require(sha(path)==digest and bindings.setdefault(path,digest)==digest,'0408 work proof input differs')
    return bindings


def freeze():
    return shared.freeze(base=BASE,prior=P407,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
