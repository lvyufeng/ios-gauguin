#!/usr/bin/env python3
"""Prepare the verified Android bus step or repeat the exact 0408 profile."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

check = import_module('check-frame409-bandwidth')
prior = import_module('prepare-frame408')
BASE,P408 = check.BASE,check.P408
LAST = P408/'execution'
COMPARISON = LAST/'scanout-comparison-0407-0408.json'
SELECTED = BASE/'frame409-image.json'
OFFLINE = BASE/'bandwidth-candidate'
CANDIDATE = OFFLINE/'image-receipt.json'
DOC = WORK/'docs/gauguin-frame-409-stock-bandwidth-20261124.md'
TRIAL = '0409'
BATCH,RESERVE,shared,save = prior.BATCH,prior.RESERVE,prior.shared,prior.save
capture_tools = import_module('prepare-frame392')
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0408')],
         'allow_0409_one_bounded_60Hz_temporary_boot_with_reviewed_Android_BW_step')
SUCCESS = '0409-stock-bandwidth-physically-measured-root-restored'


def budget(name,planned):
    proof = load(BASE/name)
    require(proof['admitted'] and proof['planned_batch_bytes']==planned and
            proof['current_accounted_bytes']+planned<=proof['limit_bytes'],'0409 batch exceeds storage')


def decision():
    terminal, measured = load(LAST/'result.json'), load(COMPARISON)
    reference = measured['measurements']['0408']['ca_phase']
    require(terminal['state']==prior.SUCCESS and terminal['independent_restore_verified'] and
            terminal['static_root_comparison_passed'] and terminal['DPU_independent_physical_FPS_qualified'] and
            terminal['comparison']==COMPARISON.name and
            terminal['stable_60_fps_observed']==measured['stable_60_fps_observed'] and
            reference['qualified'] and not reference['missed'] and
            reference['work_duration_us']==terminal['compositor_work_duration_us']==7200 and
            measured['stock_interaction_CPU']['0408']['selector_cleanup_qualified'],
            '0409 selection requires qualified 0408 timing and restoration')
    return 10 if terminal['stable_60_fps_observed'] else check.PROFILE['bw_index']


def baseline(*,fresh=True):
    terminal,proof,restored = (load(LAST/name) for name in (
        'result.json','independent-restore.json','restored-capture/result.json'))
    require(terminal['trial']=='0408' and terminal['boot_attempts']==1 and terminal['restored'] and
            terminal['independent_restore_verified'] and terminal['static_root_comparison_passed'] and
            proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and
            proof['misc_original_4096_bytes_match'] and proof['root_header_sha256']==restored['root_header_sha256'] and
            proof['install_plan_sha256']==load(P408/'trial-plan.json')['install_plan_sha256'],
            '0408 independent restoration differs')
    if not fresh:
        return restored
    live = load(BASE/'current-root-capture/result.json')
    require(not live['device_writes'] and len(live['files'])==31 and all(live[key]==restored[key] for key in (
        'root_header_sha256','combined_log_bytes','files','directories')), '0409 recovery root differs')
    return live


def kernel_manifest(index):
    path = check.KERNEL if index==11 else check.PARENT
    kernel = load(path)
    require(kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            sha(kernel['kernel'])==kernel['kernel_sha256'],'0409 kernel differs')
    if index==11:
        host = load(check.HOST)
        require({Path(p).stem for p in kernel['object_replacements'].values()}==
                {'gauguin_gmu_board','gauguin_gmu_firmware'} and host['profile']==check.PROFILE and
                kernel['input_pins'][str(check.PATCH)]==host['patch_sha256']==sha(check.PATCH) and
                kernel['input_pins'][str(check.PARENT)]==sha(check.PARENT),
                '0409 candidate differs beyond reviewed GMU objects')
    return path,kernel


def stage_image():
    budget('package-batch-admission.json',RESERVE+60_000_000)
    kernel_path,kernel = kernel_manifest(11)
    parent = load(P408/'trial-plan.json')
    donor = P408/'edr-native/result.json'
    old = load(donor)
    pack = import_module('package-frame344')
    shim = import_module('prepare-frame388').SHIM
    OFFLINE.mkdir()
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=OFFLINE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=shim,
        command_profile=capture_tools.command_profile)
    control,candidate = (pack.parts(Path(p).read_bytes()) for p in (parent['image'],image['image']))
    require(control[0][:16]==candidate[0][:16] and control[0][20:]==candidate[0][20:] and
            control[1]==candidate[1] and control[3]==candidate[3] and image['command']==parent['boot_command'],
            '0409 image wrapper or physical DPU mode differs')
    helper = pack.edr(image,base=OFFLINE,trial=TRIAL,
        signed_reference=capture_tools.P391/'edr-native/result.json',
        profile=('gpf=4','gpf=5'))
    words = import_module('check-frame395-edr').native_words
    require(sha(old['binary'])==old['binary_sha256'] and words(helper['binary'])==words(old['binary']),
            '0409 signed helper machine code differs')
    helper['matching_0408_machine_code'] = True
    helper['input_pins'].update({str(donor):sha(donor),old['binary']:old['binary_sha256']})
    image['kernel_manifest'] = str(kernel_path)
    save(OFFLINE/'edr-native/result.json',helper)
    save(CANDIDATE,image)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def package():
    index = decision()
    baseline(fresh=False)
    source_image,source_helper = ((CANDIDATE,OFFLINE/'edr-native/result.json') if index==11
                                 else (P408/'frame408-image.json',P408/'edr-native/result.json'))
    image = load(source_image)
    (BASE/'edr-native').mkdir()
    shutil.copyfile(source_helper,BASE/'edr-native/result.json')
    shutil.copyfile(source_image,SELECTED)
    for kind in ('core','c4'):
        receipt = BASE/f'{kind}-native/result.json'
        receipt.parent.mkdir()
        shutil.copyfile(P408/f'{kind}-native/result.json',receipt)
    return dict(native_bandwidth_index=index,reference_comparison_sha256=sha(COMPARISON),
                image_sha256=image['image_sha256'],build_identity=image['build_identity'])


def capture():
    budget('live-batch-admission.json',BATCH)
    return capture_tools.capture_from(BASE,P408,TRIAL,baseline)


def delta():
    return shared.stage.delta(BASE,P408,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    live,index = baseline(),decision()
    kernel_path,kernel = kernel_manifest(index)
    parent_path = P408/'trial-plan.json'
    parent = load(parent_path)
    install_path,helper_path = BASE/'slot-delta/install-plan.json',BASE/'edr-native/result.json'
    install,helper,image = map(load,(install_path,helper_path,SELECTED))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    require(str(kernel_path)==image['kernel_manifest'] and kernel['kernel_sha256']==image['kernel_sha256'] and
            sha(image['image'])==image['image_sha256'] and image['build_identity']==kernel['identity']==helper['kernel_identity'] and
            image['command']==parent['boot_command'] and
            (helper['matching_0408_machine_code'] if index==11 else parent['image_sha256']==image['image_sha256']) and
            sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
            install['core_sha256']==parent['owned_core_sha256'] and install['C4_sha256']==parent['C4_sha256'] and
            install['rows']['core']['new_logical']==parent['owned_core_logical_bytes'] and
            install['rows']['c4']['new_logical']==parent['C4_logical_bytes'] and
            install['trial']==TRIAL and install['root_header_sha256']==header and install['changed_ranges']==12 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
            parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
            parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
            parent['sustained_motion']['normal_reports']==162,'0409 exact timing or recovery scope differs')
    description = ('Use the next stock DDR request at the same 650 MHz GPU point.' if index==11
                   else 'Repeat the exact previously stable 0408 image and userspace.')
    return dict(parent,state='prepared-frame409-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],
        EDR_helper_sha256=helper['binary_sha256'],signed_native_EDR_scope_sha256=sha(helper_path),
        native_bandwidth_index=index,log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,
            max_combined_log_bytes=size+LOG_SUFFIX,sizes={k:live['files'][k]['bytes'] for k in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-parent['log_capture']['measured_baseline_bytes']),
        optimization=description,performance_comparison='Compare warm and fixed-drag scans against independently restored 0408.')


def criteria(plan):
    budget('live-batch-admission.json',BATCH)
    parent = load(P408/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'log_capture','optimization','performance_comparison','native_bandwidth_index'}
    require({k for k in parent.keys()|plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0409 scope differs')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P408,BASE))
    changes = {'admission'} if plan['native_bandwidth_index']==11 else set()
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
            ==changes,'0409 signed userspace differs beyond kernel identity')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0409 recovery model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P408,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P408/'storage-bound-408.json')
    require(old['worst_case_bytes']<=RESERVE,'0409 runtime exceeds reserve')
    return dict(old,state='bounded0409-stock-bandwidth-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
                log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    parent = load(P408/'trial-plan.json')
    index = decision()
    kernel,_ = kernel_manifest(index)
    paths = [*(WORK/p for p in tracked),DOC,kernel,SELECTED,COMPARISON,MAIN/'tools/storage-budget.py',
        BASE/'live-batch-admission.json',BASE/'current-root-capture/result.json',Path(parent['observer_helper']),
        *(P408/p for p in ('ready.json','storage-bound-408.json','trial-plan.json','capture-profile.json',
            'core-native/result.json','c4-native/result.json','edr-native/result.json')),
        *(LAST/p for p in ('result.json','independent-restore.json','restored-capture/result.json',
                           'kernel.log','kernel.log.bin','page-flip-latches.json'))]
    if index==11:
        paths += [check.HOST,check.PATCH,check.FIXTURE,check.TEST,CANDIDATE,BASE/'package-batch-admission.json',
                  OFFLINE/'edr-native/result.json']
    retirement = BASE/'retired-exact-generated-install-archives.json'
    if retirement.is_file():
        paths.append(retirement)
    bindings = capture_tools.scoped_pins(BASE,paths,kernel,SELECTED)
    if index==11:
        host = load(check.HOST)
        for path,digest in (host['input_pins']|host['policy']['input_pins']).items():
            require(sha(path)==digest and bindings.setdefault(path,digest)==digest,'0409 policy proof input differs')
    return bindings


def freeze():
    return shared.freeze(base=BASE,prior=P408,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {fn.__name__:fn for fn in (stage_image,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
