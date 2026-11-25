#!/usr/bin/env python3
"""Freeze the bounded 0409-paced managed scanout qualification."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

build = import_module('check-frame411-linear-view')
prior = import_module('prepare-frame410')
BASE, P409 = build.BASE, prior.P409
P410 = MAIN/'research/tmp/gauguin-frame410-compositor-work-margins-worktree-20261124/research/tmp/frame-410'
LAST = P410/'execution'
IMAGE = BASE/'frame411-image.json'
OWNER = BASE/'0409-owner-fixture.json'
REGISTERS = BASE/'0409-flip-fixture.json'
DOC = WORK/'docs/gauguin-frame-411-managed-linear-scanout-20261124.md'
TRIAL = '0411'
CONTROL = '0409'
SLOT_BYTES = 0xab8000
BATCH, RESERVE, shared, save = prior.BATCH, prior.RESERVE, prior.shared, prior.save
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0410')],
         'allow_0411_one_bounded_60Hz_boot_with_reviewed_managed_scanout_layout')
SUCCESS = '0411-managed-linear-DPU-latches-measured-root-restored'


def budget(path,planned):
    receipt = load(path)
    require(receipt['admitted'] and receipt['planned_batch_bytes']==planned and
            receipt['current_accounted_bytes']+planned<=receipt['limit_bytes'],'0411 batch exceeds storage')


def baseline(*,fresh=True):
    end,proof,restored = (load(LAST/name) for name in (
        'result.json','independent-restore.json','restored-capture/result.json'))
    last_plan = load(P410/'trial-plan.json')
    require(end['trial']=='0410' and end['boot_attempts']==1 and end['observer_exit']==0 and
            end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed'] and
            end['DPU_independent_physical_FPS_qualified'] and not end['stable_60_fps_observed'] and
            proof['install_plan_sha256']==last_plan['install_plan_sha256'] and proof['journal_empty'] and
            proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'] and
            not proof['device_writes'] and proof['root_header_sha256']==restored['root_header_sha256'],
            '0411 needs the independently restored 0410 root and unfinished 60 fps')
    if not fresh:
        return restored
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files'])==31 and all(
        current[key]==restored[key] for key in ('root_header_sha256','combined_log_bytes','files','directories')),
        '0411 live recovery root differs from 0410 readback')
    return current


def selected_kernel():
    kernel,host,owner,registers = map(load,(build.NATIVE,build.HOST,OWNER,REGISTERS))
    require(kernel['state']=='0411-native-ARM64-linked' and kernel['inputs_unchanged'] and
            kernel['baseline_reproduced_except_uuid'] and sha(kernel['kernel'])==kernel['kernel_sha256'] and
            kernel['input_pins'][str(build.REFERENCE)]==sha(build.REFERENCE) and
            kernel['input_pins'][str(build.PATCH)]==host['patch_sha256']==sha(build.PATCH) and
            {Path(name).stem for name in kernel['object_replacements'].values()}==
                {'SweetFramebuffer','gauguin_ui_trace_board'} and
            owner['allocation_fault_boundaries']==9 and registers['cases']==8 and
            all(not row['device_commands'] for row in (host,owner,registers)) and
            all(row['input_pins'][str(build.NATIVE)]==sha(build.NATIVE) for row in (owner,registers)),
            '0411 exact rebased kernel or host checks differ')
    return kernel


def package():
    budget(build.ADMISSION,prior.NATIVE_AND_PACKAGE)
    baseline(fresh=False)
    kernel = selected_kernel()
    _,_,_,control,_,_,_ = prior.check.measured(CONTROL)
    pack = import_module('package-frame344')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,
        private_scanout_shim=import_module('prepare-frame388').SHIM,command_profile=prior.capture_tools.command_profile)
    before,after = (pack.parts(Path(path).read_bytes()) for path in (control['image'],image['image']))
    require(before[0][:16]==after[0][:16] and before[0][20:]==after[0][20:] and before[1]==after[1] and
            before[3]==after[3] and image['command']==control['boot_command'],
            '0411 boot wrapper, panel mode or command differs from 0409')
    helper = pack.edr(image,base=BASE,trial=TRIAL,
        signed_reference=prior.capture_tools.P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
    donor = P409/'edr-native/result.json'
    reference = load(donor)
    words = import_module('check-frame395-edr').native_words
    require(sha(reference['binary'])==reference['binary_sha256'] and words(reference['binary'])==words(helper['binary']),
            '0411 signed helper instructions differ')
    helper['matching_physical_control_machine_code'] = True
    helper['input_pins'].update({str(donor):sha(donor),reference['binary']:reference['binary_sha256']})
    save(BASE/'edr-native/result.json',helper)
    image['kernel_manifest'] = str(build.NATIVE)
    save(IMAGE,image)
    for kind in ('core','c4'):
        receipt = BASE/f'{kind}-native/result.json'
        receipt.parent.mkdir()
        shutil.copyfile(P409/f'{kind}-native/result.json',receipt)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def capture():
    budget(BASE/'live-batch-admission.json',BATCH)
    return prior.capture_tools.capture_from(BASE,P410,TRIAL,baseline)


def delta():
    return shared.stage.delta(BASE,P409,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json')


def model():
    receipt = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(receipt['checks']),failure_points=receipt['all_restore_partial_write_points'])


def expected_plan():
    live, kernel = baseline(), selected_kernel()
    parent_path = P409/'trial-plan.json'
    parent = load(parent_path)
    install_path = BASE/'slot-delta/install-plan.json'
    helper_path = BASE/'edr-native/result.json'
    image,install,helper = map(load,(IMAGE,install_path,helper_path))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    frame = parent['frame_capture']
    require(image['kernel_manifest']==str(build.NATIVE) and kernel['kernel_sha256']==image['kernel_sha256'] and
            sha(image['image'])==image['image_sha256'] and image['build_identity']==kernel['identity']==helper['kernel_identity']
            and image['command']==parent['boot_command'] and helper['matching_physical_control_machine_code']
            and sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
            install['core_sha256']==parent['owned_core_sha256'] and install['C4_sha256']==parent['C4_sha256'] and
            install['rows']['core']['new_logical']==parent['owned_core_logical_bytes'] and
            install['rows']['c4']['new_logical']==parent['C4_logical_bytes'] and
            install['trial']==TRIAL and install['root_header_sha256']==header and install['changed_ranges']==12 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
            parent['work_duration_us']==7200 and parent['native_bandwidth_index']==11 and
            frame['target_refresh_hz']==60 and frame['modesets']==0 and frame['crc_required_preimage']==0x01000000 and
            parent['scripted_strokes']==13 and parent['sustained_motion']['normal_reports']==162,
            '0411 planned device, timing or restoration scope differs')
    dma = parent['display_dma']
    slot_geometry = dict(source_width=1125,source_height=2436,pitch_bytes=4608,
                         visible_width=1080,visible_height=2400,crop_x=22,crop_y=18)
    layout = dict(dma,private_managed_linear_bytes=SLOT_BYTES,private_managed_geometry=slot_geometry,
        prospective_buffer_mapping_bytes=2*SLOT_BYTES,readback_failure_discards_mappings=False,
        retain_managed_backings_on_uncertain_latch=True,cache_mode='managed IOKit write-combined',
        volatile_store_addresses=[*dma['volatile_store_addresses'],'0x0ae05008','0x0ae05024'],
        maximum_additional_volatile_stores=dma['maximum_additional_volatile_stores']+4,
        page_flip_mmio_reads_upper_bound=dma['page_flip_mmio_reads_upper_bound']+4*dma['page_flip_position_polls_max']+8)
    policy = dict(frame['presentation_policy'],full_copy_panel_and_source_stride=[4608,4608])
    return dict(parent,state='prepared-frame411-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],
        EDR_helper_sha256=helper['binary_sha256'],signed_native_EDR_scope_sha256=sha(helper_path),
        display_dma=layout,frame_capture=dict(frame,maximum_total_display_register_writes=2058,presentation_policy=policy),
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={key:live['files'][key]['bytes'] for key in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-load(P410/'trial-plan.json')['log_capture']['measured_baseline_bytes']),
        optimization='Qualify two managed padded scanout backings with the exact guarded 0409 copy and 7200 us pacing.',
        performance_comparison='Compare 0409 to 0411 by DPU vblank, hardware CRC and exact scan latch.')


def criteria(plan):
    budget(build.ADMISSION,prior.NATIVE_AND_PACKAGE)
    budget(BASE/'live-batch-admission.json',BATCH)
    parent = load(P409/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'log_capture','optimization','performance_comparison','display_dma','frame_capture'}
    require({key for key in parent.keys()|plan.keys() if plan.get(key)!=parent.get(key)}<=allowed,
            '0411 scope differs outside the managed layout and kernel identity')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P409,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
            =={'admission'},'0411 signed userspace differs beyond kernel identity')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0411 recovery model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P409,plan['root_header_sha256'],plan)


def storage(plan):
    previous = load(P410/'storage-bound-410.json')
    require(previous['worst_case_bytes']<=RESERVE,'0411 runtime exceeds reserve')
    return dict(previous,state='bounded0411-managed-linear-runtime',
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    home,run,_,control,comparison,_,_ = prior.check.measured(CONTROL)
    files = [*(WORK/path for path in tracked),DOC,build.NATIVE,IMAGE,comparison,build.HOST,OWNER,REGISTERS,
        MAIN/'tools/storage-budget.py',build.ADMISSION,BASE/'live-batch-admission.json',
        BASE/'current-root-capture/result.json',Path(control['observer_helper']),
        *(home/name for name in ('ready.json','trial-plan.json','edr-native/result.json','core-native/result.json',
                                 'c4-native/result.json')),
        *(run/name for name in ('result.json','independent-restore.json','kernel.log','kernel.log.bin',
                                'page-flip-latches.json')),
        *(P410/name for name in ('ready.json','trial-plan.json','storage-bound-410.json','capture-profile.json')),
        *(LAST/name for name in ('result.json','independent-restore.json','restored-capture/result.json',
                                 'scanout-comparison-0409-0410.json'))]
    retirement = BASE/'retired-exact-generated-install-archives.json'
    if retirement.is_file():
        files.append(retirement)
    bindings = prior.capture_tools.scoped_pins(BASE,files,build.NATIVE,IMAGE)
    for receipt in (build.HOST,OWNER,REGISTERS):
        for path,digest in load(receipt)['input_pins'].items():
            require(sha(path)==digest and bindings.setdefault(path,digest)==digest,'0411 host evidence differs')
    return bindings


def freeze():
    return shared.freeze(base=BASE,prior=P410,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {action.__name__:action for action in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
