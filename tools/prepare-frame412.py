#!/usr/bin/env python3
"""Freeze one stock Android PERF6/BW12 60 Hz comparison."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

check = import_module('check-frame412-stock-max')
previous = import_module('prepare-frame411')
BASE, P411, P409 = check.BASE, check.P411, previous.P409
LAST = P411/'execution'
DOC = WORK/'docs/gauguin-frame-412-stock-gpu-point-20261124.md'
IMAGE = BASE/'frame412-image.json'
TRIAL = '0412'
CONTROL = '0409'
BATCH, RESERVE, shared, save = previous.BATCH, previous.RESERVE, previous.shared, previous.save
FLAGS = (*[flag for flag in previous.FLAGS if not flag.startswith('allow_0411')],
         'allow_0412_one_bounded_60Hz_boot_with_exact_stock_GPU_operating_point')
SUCCESS = '0412-Android-stock-PERF6-BW12-measured-root-restored'


def baseline(*,fresh=True):
    result,proof,restored = (load(LAST/name) for name in (
        'result.json','independent-restore.json','restored-capture/result.json'))
    require(result['trial']=='0411' and result['boot_attempts']==1 and result['restored'] and
            result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            not result.get('stable_60_fps_observed',False) and
            proof['install_plan_sha256']==load(P411/'trial-plan.json')['install_plan_sha256'] and
            proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and
            proof['misc_original_4096_bytes_match'] and not proof['device_writes'] and
            proof['root_header_sha256']==restored['root_header_sha256'],
            '0412 requires the independently restored 0411 root and an unfinished 60 fps target')
    if not fresh:
        return restored
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files'])==31 and all(
        current[key]==restored[key] for key in ('root_header_sha256','combined_log_bytes','files','directories')),
        '0412 live root differs from the independently read original')
    return current


def selected_kernel():
    kernel,off = map(load,(check.KERNEL,check.HOST))
    require(kernel['state']=='0412-native-ARM64-linked' and kernel['inputs_unchanged'] and
            kernel['baseline_reproduced_except_uuid'] and sha(kernel['kernel'])==kernel['kernel_sha256'] and
            kernel['input_pins'][str(check.REFERENCE)]==sha(check.REFERENCE) and
            kernel['input_pins'][str(check.PATCH)]==off['patch_sha256']==sha(check.PATCH) and
            {Path(name).stem for name in kernel['object_replacements'].values()}==
                {'gauguin_gmu_board','gauguin_gmu_firmware'} and off['profile']==check.PROFILE and
            off['scope_checks']==21 and not off['device_commands'],
            '0412 kernel or stock-request evidence differs')
    return kernel


def package():
    previous.budget(BASE/'package-and-run-admission.json',BATCH+60_000_000)
    baseline(fresh=False)
    kernel = selected_kernel()
    _,_,_,control,_,_,_ = check.phase.measured(CONTROL)
    pack = import_module('package-frame344')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,
        private_scanout_shim=import_module('prepare-frame388').SHIM,
        command_profile=previous.prior.capture_tools.command_profile)
    before,after = (pack.parts(Path(path).read_bytes()) for path in (control['image'],image['image']))
    require(before[0][:16]==after[0][:16] and before[0][20:]==after[0][20:] and
            before[1]==after[1] and before[3]==after[3] and image['command']==control['boot_command'],
            '0412 inherits a different loader, DTB or unplanned boot arguments')
    helper = pack.edr(image,base=BASE,trial=TRIAL,
        signed_reference=previous.prior.capture_tools.P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
    prior_helper = P409/'edr-native/result.json'
    expected = load(prior_helper)
    words = import_module('check-frame395-edr').native_words
    require(sha(expected['binary'])==expected['binary_sha256'] and words(expected['binary'])==words(helper['binary']),
            '0412 signed helper instructions differ beyond the kernel binding')
    helper['matching_physical_control_machine_code'] = True
    helper['input_pins'].update({str(prior_helper):sha(prior_helper),expected['binary']:expected['binary_sha256']})
    save(BASE/'edr-native/result.json',helper)
    image['kernel_manifest'] = str(check.KERNEL)
    save(IMAGE,image)
    for kind in ('core','c4'):
        receipt = BASE/f'{kind}-native/result.json'
        receipt.parent.mkdir()
        shutil.copyfile(P409/f'{kind}-native/result.json',receipt)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def capture():
    previous.budget(BASE/'live-batch-admission.json',BATCH)
    return previous.prior.capture_tools.capture_from(BASE,P411,TRIAL,baseline)


def delta():
    return shared.stage.delta(BASE,P409,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(result['checks']),failure_points=result['all_restore_partial_write_points'])


def expected_plan():
    live,kernel = baseline(),selected_kernel()
    parent_path = P409/'trial-plan.json'
    parent = load(parent_path)
    install_path = BASE/'slot-delta/install-plan.json'
    helper_path = BASE/'edr-native/result.json'
    image,install,helper = map(load,(IMAGE,install_path,helper_path))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    frame = parent['frame_capture']
    require(image['kernel_manifest']==str(check.KERNEL) and kernel['kernel_sha256']==image['kernel_sha256'] and
            sha(image['image'])==image['image_sha256'] and image['build_identity']==kernel['identity']==helper['kernel_identity']
            and image['command']==parent['boot_command'] and helper['matching_physical_control_machine_code']
            and sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
            install['core_sha256']==parent['owned_core_sha256'] and install['C4_sha256']==parent['C4_sha256'] and
            install['rows']['core']['new_logical']==parent['owned_core_logical_bytes'] and
            install['rows']['c4']['new_logical']==parent['C4_logical_bytes'] and
            install['trial']==TRIAL and install['root_header_sha256']==header and install['changed_ranges']==12 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
            parent['work_duration_us']==7200 and frame['target_refresh_hz']==60 and frame['modesets']==0 and
            frame['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
            parent['sustained_motion']['normal_reports']==162,'0412 device, timing or recovery scope differs')
    return dict(parent,state='prepared-frame412-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],boot_command=image['command'],
        EDR_helper_sha256=helper['binary_sha256'],signed_native_EDR_scope_sha256=sha(helper_path),
        native_gpu_perf_index=check.PROFILE['perf_index'],native_bandwidth_index=check.PROFILE['bw_index'],
        native_stock_gpu_point=check.PROFILE,
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={key:live['files'][key]['bytes'] for key in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-load(P411/'trial-plan.json')['log_capture']['measured_baseline_bytes']),
        optimization='Request the captured stock Android 800 MHz and default BW12 operating point.',
        performance_comparison='Compare 0409 and 0412 by exact native issue/EOP/cache and physical vblank/CRC.')


def criteria(plan):
    previous.budget(BASE/'package-and-run-admission.json',BATCH+60_000_000)
    previous.budget(BASE/'live-batch-admission.json',BATCH)
    parent = load(P409/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256',
        'signed_native_EDR_scope_sha256','native_gpu_perf_index','native_bandwidth_index','native_stock_gpu_point',
        'log_capture','optimization','performance_comparison'}
    require({key for key in parent.keys()|plan.keys() if plan.get(key)!=parent.get(key)}<=allowed,
            '0412 differs outside the specific stock vote and kernel identity')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P409,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
            =={'admission'},'0412 signed userspace differs beyond kernel identity')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0412 recovery model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P409,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P411/'storage-bound-411.json')
    require(old['worst_case_bytes']<=RESERVE,'0412 runtime exceeds reserve')
    return dict(old,state='bounded0412-stock-GPU-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
                log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    scripts = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    home,run,_,control,comparison,_,_ = check.phase.measured(CONTROL)
    paths = [*(WORK/path for path in scripts),DOC,check.KERNEL,check.HOST,check.PATCH,IMAGE,comparison,
        MAIN/'tools/storage-budget.py',BASE/'package-and-run-admission.json',BASE/'live-batch-admission.json',
        BASE/'current-root-capture/result.json',Path(control['observer_helper']),
        *(home/name for name in ('ready.json','trial-plan.json','edr-native/result.json','core-native/result.json',
                                 'c4-native/result.json')),
        *(run/name for name in ('result.json','independent-restore.json','kernel.log','kernel.log.bin',
                               'page-flip-latches.json')),
        *(P411/name for name in ('ready.json','trial-plan.json','storage-bound-411.json','capture-profile.json')),
        *(LAST/name for name in ('result.json','independent-restore.json','restored-capture/result.json'))]
    retirement = BASE/'retired-exact-generated-install-archives.json'
    if retirement.is_file():
        paths.append(retirement)
    bindings = previous.prior.capture_tools.scoped_pins(BASE,paths,check.KERNEL,IMAGE)
    proof = load(check.HOST)
    for files in (proof['input_pins'],proof['policy']['input_pins']):
        for path,digest in files.items():
            require(sha(path)==digest and bindings.setdefault(path,digest)==digest,'0412 stock proof input differs')
    return bindings


def freeze():
    return shared.freeze(base=BASE,prior=P411,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
