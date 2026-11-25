#!/usr/bin/env python3
"""Freeze a measured exact repeat or qualify the padded low-memory scanout."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha
from mkpayload import DPU_LINEAR_SLOT_BYTES

layout = import_module('check-gauguin-reserved-linear')
prior = import_module('prepare-frame412')
P412, P409, P411 = layout.ADMISSION.parent, prior.P409, prior.P411
LAST = P412/'execution'
BASE = WORK/'research/tmp/frame-413'
IMAGE = BASE/'frame413-image.json'
DOC = WORK/'docs/gauguin-frame-413-reserved-linear-20261124.md'
TRIAL = '0413'
BATCH,RESERVE,shared,save = prior.BATCH,prior.RESERVE,prior.shared,prior.save
budget = prior.previous.budget
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0412')],
         'allow_0413_one_bounded_60Hz_exact_repeat_or_reserved_padded_view')
SUCCESS = '0413-hardware-motion-measured-root-restored'


def baseline(*,fresh=True):
    status,proof,restored = (load(LAST/name) for name in (
        'result.json','independent-restore.json','restored-capture/result.json'))
    require(status['trial']=='0412' and status['boot_attempts']==1 and status['restored'] and
            status['independent_restore_verified'] and status['static_root_comparison_passed'] and
            proof['install_plan_sha256']==load(P412/'trial-plan.json')['install_plan_sha256'] and not proof['device_writes']
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match']
            and proof['root_header_sha256']==restored['root_header_sha256'],'0413 needs independent 0412 readback')
    if not fresh:
        return restored
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files'])==31 and all(
        current[key]==restored[key] for key in ('root_header_sha256','combined_log_bytes','files','directories')),
        '0413 TWRP baseline differs')
    return current


def measurement():
    baseline(fresh=False)
    status = load(LAST/'result.json')
    if not status.get('DPU_independent_physical_FPS_qualified'):
        return dict(control='0409',repeat=False)
    reference = load(LAST/status['comparison'])
    require(reference['stable_60_fps_observed']==status['stable_60_fps_observed'] and
            reference['native_GPU_profile']['native_request_accepted'] and
            reference['measurements']['0412']['ca_phase']['work_duration_us']==7200,
            '0412 physical comparison does not reproduce')
    if status['stable_60_fps_observed']:
        return dict(control='0412',repeat=True)
    old_reference = layout.phase.measured('0409')[5]
    rank = []
    for trial,report in (('0409',old_reference),('0412',reference)):
        row = report['measurements'][trial]
        counts = (report['motion_after_onset']['counts'],row['metrics']['slow_drag']['scans'])
        bad = sum(item.get('repeated',0)+item.get('unknown',0) for item in counts)
        rank.append((bad/sum(sum(item.values()) for item in counts),
                     row['onset']['warm']['p95_first_new_image_ns'][1],trial))
    return dict(control=min(rank)[-1],repeat=False)


def control(choice):
    if choice['control']=='0409':
        path,run,_,plan,report,_,_ = layout.phase.measured('0409')
        return path,run,plan,report
    terminal = load(LAST/'result.json')
    return P412,LAST,load(P412/'trial-plan.json'),LAST/terminal['comparison']


def kernel_receipt(choice):
    if choice['repeat']:
        native = layout.selected(choice['control'])
    else:
        native = layout.BASE/f'native-kernel-{choice["control"]}/build-manifest.json'
    kernel = load(native)
    require(kernel['baseline_reproduced_except_uuid'] and kernel['inputs_unchanged'] and
            sha(kernel['kernel'])==kernel['kernel_sha256'], '0413 selected kernel differs')
    if not choice['repeat']:
        original = layout.selected(choice['control'])
        require(kernel['state']=='0413-native-ARM64-linked' and
                kernel['input_pins'][str(original)]==sha(original) and
                {Path(name).stem for name in kernel['object_replacements'].values()}==
                    {'SweetFramebuffer','gauguin_ui_trace_board'},'0413 native replacements differ')
        for label in ('owner','registers'):
            proof = load(layout.BASE/f'{choice["control"]}-{label}.json')
            require(proof['cases']==8 and not proof['device_commands'] and
                    proof['input_pins'][str(native)]==sha(native),'0413 backing host cases differ')
    return native,kernel


def package():
    choice = measurement()
    budget(BASE/'package-and-run-admission.json', BATCH if choice['repeat'] else BATCH+60_000_000)
    path,_,reference,_ = control(choice)
    native,kernel = kernel_receipt(choice)
    donor = path/'edr-native/result.json'
    older = load(donor)
    if choice['repeat']:
        image = load(path/f'frame{int(choice["control"])}-image.json')
        helper = older
        (BASE/'edr-native').mkdir()
    else:
        pack = import_module('package-frame344')
        shim = layout.shim()
        image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
            frame_capture_mode=9,scripted_motion=True,private_scanout_shim=Path(shim['image']),
            private_scanout_slot_bytes=DPU_LINEAR_SLOT_BYTES,
            command_profile=prior.previous.prior.capture_tools.command_profile)
        previous,current = (pack.parts(Path(name).read_bytes()) for name in (reference['image'],image['image']))
        require(previous[0][:8]==current[0][:8] and previous[0][12:16]==current[0][12:16] and
                previous[0][20:]==current[0][20:] and previous[3]==current[3] and
                current[1]==Path(shim['image']).read_bytes() and image['command']==reference['boot_command'],
                '0413 changed boot loader geometry, console options or device tree')
        helper = pack.edr(image,base=BASE,trial=TRIAL,
            signed_reference=prior.previous.prior.capture_tools.P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
        words = import_module('check-frame395-edr').native_words
        require(sha(older['binary'])==older['binary_sha256'] and words(older['binary'])==words(helper['binary']),
                '0413 signed helper instructions differ')
        helper['matching_physical_control_machine_code'] = True
        helper['input_pins'].update({str(donor):sha(donor),older['binary']:older['binary_sha256']})
    image['kernel_manifest'] = str(native)
    save(IMAGE,image)
    save(BASE/'edr-native/result.json',helper)
    for kind in ('core','c4'):
        receipt = BASE/f'{kind}-native/result.json'
        receipt.parent.mkdir()
        shutil.copyfile(path/f'{kind}-native/result.json',receipt)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def capture():
    budget(BASE/'live-batch-admission.json',BATCH)
    return prior.previous.prior.capture_tools.capture_from(BASE,P412,TRIAL,baseline)


def delta():
    path,*_ = control(measurement())
    return shared.stage.delta(BASE,path,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    choice,live = measurement(),baseline()
    source,_,parent,_ = control(choice)
    native,kernel = kernel_receipt(choice)
    plan_path = source/'trial-plan.json'
    install_path = BASE/'slot-delta/install-plan.json'
    helper_path = BASE/'edr-native/result.json'
    image,install,helper = map(load,(IMAGE,install_path,helper_path))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    frame,dma = parent['frame_capture'],parent['display_dma']
    require(image['kernel_manifest']==str(native) and kernel['kernel_sha256']==image['kernel_sha256'] and
            sha(image['image'])==image['image_sha256'] and image['build_identity']==kernel['identity']==helper['kernel_identity']
            and image['command']==parent['boot_command'] and sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256']
            and install['core_sha256']==parent['owned_core_sha256'] and install['C4_sha256']==parent['C4_sha256']
            and install['rows']['core']['new_logical']==parent['owned_core_logical_bytes']
            and install['rows']['c4']['new_logical']==parent['C4_logical_bytes'] and install['trial']==TRIAL
            and install['root_header_sha256']==header and install['changed_ranges']==12
            and sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and parent['work_duration_us']==7200
            and frame['target_refresh_hz']==60 and frame['modesets']==0 and frame['crc_required_preimage']==0x01000000
            and parent['scripted_strokes']==13 and parent['sustained_motion']['normal_reports']==162,'0413 exact scope differs')
    if choice['repeat']:
        require(image['image_sha256']==parent['image_sha256'] and helper['binary_sha256']==parent['EDR_helper_sha256'],
                '0413 exact physical repeat changed an image or binary')
    else:
        require(helper['matching_physical_control_machine_code'],'0413 signed helper differs')
        geometry = dict(source_width=1125,source_height=2436,pitch_bytes=4608,
                        visible_width=1080,visible_height=2400,crop_x=22,crop_y=18)
        dma = dict(dma,private_reserved_linear_bytes=DPU_LINEAR_SLOT_BYTES,private_reserved_geometry=geometry,
            prospective_buffer_mapping_bytes=2*DPU_LINEAR_SLOT_BYTES,
            retain_backings_on_uncertain_latch=True,cache_mode='boot-reserved IOKit write-combined',
            volatile_store_addresses=[*dma['volatile_store_addresses'],'0x0ae05008','0x0ae05024'],
            maximum_additional_volatile_stores=dma['maximum_additional_volatile_stores']+4,
            page_flip_mmio_reads_upper_bound=dma['page_flip_mmio_reads_upper_bound']+4*dma['page_flip_position_polls_max']+8)
        policy = dict(frame['presentation_policy'],full_copy_panel_and_source_stride=[4608,4608])
        frame = dict(frame,maximum_total_display_register_writes=2058,presentation_policy=policy)
    return dict(parent,state='prepared-frame413-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(plan_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],
        EDR_helper_sha256=helper['binary_sha256'],signed_native_EDR_scope_sha256=sha(helper_path),
        display_dma=dma,frame_capture=frame,frame413_control=choice['control'],frame413_exact_repeat=choice['repeat'],
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={name:live['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-load(P412/'trial-plan.json')['log_capture']['measured_baseline_bytes']),
        optimization=('Exact repeat of the first physically stable 0412 profile.' if choice['repeat'] else
                      'Use two enlarged low-memory boot-reserved buffers with guarded copy and measured DPU pacing.'),
        performance_comparison=f'Compare physical vblank and CRC scan by scan against {choice["control"]}.')


def criteria(plan):
    choice = measurement()
    path,_,parent,_ = control(choice)
    budget(BASE/'package-and-run-admission.json', BATCH if choice['repeat'] else BATCH+60_000_000)
    budget(BASE/'live-batch-admission.json',BATCH)
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'log_capture','optimization','performance_comparison','frame413_control','frame413_exact_repeat'}
    if not choice['repeat']:
        allowed.update(('display_dma','frame_capture'))
    require({key for key in parent.keys()|plan.keys() if plan.get(key)!=parent.get(key)}<=allowed,
            '0413 scope differs from the narrow reviewed choice')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (path,BASE))
    differences = {name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
    require(differences==(set() if choice['repeat'] else {'admission'}),'0413 installed signed userspace differs')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0413 recovery model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,path,plan['root_header_sha256'],plan)


def storage(plan):
    previous = load(P412/'storage-bound-412.json')
    require(previous['worst_case_bytes']<=RESERVE,'0413 runtime exceeds reserve')
    return dict(previous,state='bounded0413-physical-scanout-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    choice = measurement()
    path,run,plan,comparison = control(choice)
    native,_ = kernel_receipt(choice)
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK/name for name in tracked),DOC,native,IMAGE,comparison,Path(plan['observer_helper']),
        MAIN/'tools/storage-budget.py',BASE/'package-and-run-admission.json',BASE/'live-batch-admission.json',
        BASE/'current-root-capture/result.json',
        *(path/name for name in ('ready.json','trial-plan.json','edr-native/result.json','core-native/result.json',
                                 'c4-native/result.json')),
        *(run/name for name in ('result.json','independent-restore.json','kernel.log','kernel.log.bin',
                                'page-flip-latches.json')),
        *(P412/name for name in ('ready.json','trial-plan.json','storage-bound-412.json','capture-profile.json')),
        *(LAST/name for name in ('result.json','independent-restore.json','restored-capture/result.json'))]
    evidence = [] if choice['repeat'] else [layout.SHIM,layout.BASE/f'{choice["control"]}-owner.json',
                                            layout.BASE/f'{choice["control"]}-registers.json']
    retirement = BASE/'retired-exact-generated-install-archives.json'
    if retirement.is_file():
        files.append(retirement)
    result = prior.previous.prior.capture_tools.scoped_pins(BASE,files+evidence,native,IMAGE)
    for receipt in evidence:
        for name,digest in load(receipt)['input_pins'].items():
            require(sha(name)==digest and result.setdefault(name,digest)==digest,'0413 tested input differs')
    return result


def freeze():
    return shared.freeze(base=BASE,prior=P412,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {fn.__name__:fn for fn in (measurement,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
