#!/usr/bin/env python3
"""Freeze a guarded GPU mapping/target observation or exact stable repeat."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

gpu = import_module('check-gauguin-shared-scanout')
prior = import_module('prepare-frame413')
capture_tools = import_module('prepare-frame392')
P413 = gpu.P413/'research/tmp/frame-413'
LAST = P413/'execution'
BASE = WORK/'research/tmp/frame-414'
IMAGE = BASE/'frame414-image.json'
DOC = WORK/'docs/gauguin-frame-414-shared-aperture-20261124.md'
PROOF = gpu.BASE/'owner-fixture.json'
BINDING = prior.P411/'target-observation-native/result.json'
SHIM = gpu.P413/'research/tmp/reserved-linear/shim-native/result.json'
TRIAL = '0414'
BATCH,RESERVE,shared,save = prior.BATCH,prior.RESERVE,prior.shared,prior.save
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0413')],
         'allow_0414_one_bounded_60Hz_exact_repeat_or_shared_readonly_aperture_observation')
SUCCESS = '0414-physical-scanout-measured-root-restored'
SLOT_BYTES = prior.DPU_LINEAR_SLOT_BYTES
MAP_RECEIPT = 'SWEET F414 GPU MAP: published-and-removed read-only pages=5488 per-slot=2744'


def baseline(*,fresh=True):
    end,proof,restored = (load(LAST/name) for name in ('result.json','independent-restore.json','restored-capture/result.json'))
    require(end['trial']=='0413' and end['boot_attempts']==1 and end['restored'] and end['independent_restore_verified'] and
            end['static_root_comparison_passed'] and end['DPU_independent_physical_FPS_qualified'] and
            (end['stable_60_fps_observed'] or end.get('reserved_linear_scanout_qualified')) and
            proof['install_plan_sha256']==load(P413/'trial-plan.json')['install_plan_sha256'] and not proof['device_writes'] and
            proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'] and
            proof['root_header_sha256']==restored['root_header_sha256'],'0414 requires qualified and independently restored 0413')
    if not fresh:
        return restored
    live = load(BASE/'current-root-capture/result.json')
    require(not live['device_writes'] and len(live['files'])==31 and all(live[key]==restored[key] for key in (
        'root_header_sha256','combined_log_bytes','files','directories')),'0414 fresh baseline differs')
    return live


def choice():
    baseline(fresh=False)
    result = load(LAST/'result.json')
    parent = load(P413/'trial-plan.json')
    comparison = LAST/result['comparison']
    report = load(comparison)
    require(report['stable_60_fps_observed']==result['stable_60_fps_observed'],'0413 score differs')
    repeat = result['stable_60_fps_observed']
    if not repeat:
        require(parent['display_dma']['private_reserved_linear_bytes']==SLOT_BYTES and
                parent['image_sha256']==load(P413/'frame413-image.json')['image_sha256'] and
                load(P413/'frame413-image.json')['kernel_manifest']==str(gpu.INPUT) and
                report['reserved_linear_scanout']['original_view_restored'] and
                report['reserved_linear_scanout']['bytes_per_slot']==SLOT_BYTES,'0414 mapping baseline differs')
    return repeat,parent,comparison


def native(repeat):
    path = Path(load(P413/'frame413-image.json')['kernel_manifest']) if repeat else gpu.KERNEL
    kernel = load(path)
    require(kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            sha(kernel['kernel'])==kernel['kernel_sha256'],'0414 native kernel differs')
    if not repeat:
        proof = load(PROOF)
        require(kernel['state']=='0414-native-ARM64-linked' and
                kernel['input_pins'][str(gpu.INPUT)]==sha(gpu.INPUT) and
                kernel['input_pins'][str(gpu.PATCH)]==sha(gpu.PATCH) and
                {Path(name).stem for name in kernel['object_replacements'].values()}==
                    {'GauguinGPU','SweetFramebuffer','gauguin_ui_trace_board'} and
                proof['cases']==8 and not proof['device_commands'] and
                proof['input_pins'][str(path)]==sha(path),'0414 linked aperture proof differs')
    return path,kernel


def package():
    repeat,parent,_ = choice()
    prior.budget(BASE/'package-and-run-admission.json',BATCH if repeat else BATCH+60_000_000)
    manifest,kernel = native(repeat)
    previous_helper = P413/'edr-native/result.json'
    reference = load(previous_helper)
    if repeat:
        image = load(P413/'frame413-image.json')
        helper = reference
        (BASE/'edr-native').mkdir()
        frontend = load(P413/'c4-native/result.json')
    else:
        pack = import_module('package-frame344')
        shim = load(SHIM)
        require(sha(shim['binary'])==shim['binary_sha256'] and not shim['device_commands'],'0414 shim differs')
        image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
            frame_capture_mode=9,scripted_motion=True,private_scanout_shim=Path(shim['binary']),
            private_scanout_slot_bytes=SLOT_BYTES,command_profile=capture_tools.command_profile)
        before,after = (pack.parts(Path(name).read_bytes()) for name in (parent['image'],image['image']))
        require(before[0][:16]==after[0][:16] and before[0][20:]==after[0][20:] and before[1]==after[1] and
                before[3]==after[3] and parent['boot_command']==image['command'],'0414 panel or loader changed')
        helper = pack.edr(image,base=BASE,trial=TRIAL,
            signed_reference=capture_tools.P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
        words = import_module('check-frame395-edr').native_words
        require(sha(reference['binary'])==reference['binary_sha256'] and words(reference['binary'])==words(helper['binary']),
                '0414 signed helper instructions differ')
        helper['matching_physical_control_machine_code'] = True
        helper['input_pins'].update({str(previous_helper):sha(previous_helper),reference['binary']:reference['binary_sha256']})
        frontend = load(BINDING)
        require(frontend['strict_signature'] and frontend['fits_existing_C4_extent'] and not frontend['device_commands'] and
                frontend['identical_imports_exports_dependencies'] and frontend['bytes']==429_664 and
                frontend['reconstructed_control_sha256']==parent['C4_sha256'] and
                sha(frontend['binary'])==frontend['binary_sha256'],'0414 signed binding observer differs')
    image['kernel_manifest'] = str(manifest)
    save(IMAGE,image)
    save(BASE/'edr-native/result.json',helper)
    for kind in ('core','c4'):
        (BASE/f'{kind}-native').mkdir()
    shutil.copyfile(P413/'core-native/result.json',BASE/'core-native/result.json')
    save(BASE/'c4-native/result.json',frontend)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def capture():
    prior.budget(BASE/'live-batch-admission.json',BATCH)
    return capture_tools.capture_from(BASE,P413,TRIAL,baseline)


def delta():
    return shared.stage.delta(BASE,P413,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    repeat,parent,_ = choice()
    current = baseline()
    manifest,kernel = native(repeat)
    install_path = BASE/'slot-delta/install-plan.json'
    helper_path = BASE/'edr-native/result.json'
    image,install,helper,c4 = map(load,(IMAGE,install_path,helper_path,BASE/'c4-native/result.json'))
    header,size = (current[key] for key in ('root_header_sha256','combined_log_bytes'))
    frame = parent['frame_capture']
    require(image['kernel_manifest']==str(manifest) and kernel['kernel_sha256']==image['kernel_sha256'] and
            sha(image['image'])==image['image_sha256'] and image['build_identity']==kernel['identity']==helper['kernel_identity']
            and image['command']==parent['boot_command'] and sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256']
            and install['core_sha256']==parent['owned_core_sha256'] and install['C4_sha256']==c4['binary_sha256']==sha(c4['binary'])
            and install['rows']['core']['new_logical']==parent['owned_core_logical_bytes'] and
            install['rows']['c4']['new_logical']==c4['bytes'] and install['trial']==TRIAL and
            install['root_header_sha256']==header and install['changed_ranges']==12 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
            frame['target_refresh_hz']==60 and frame['modesets']==0 and frame['crc_required_preimage']==0x01000000 and
            parent['scripted_strokes']==13 and parent['sustained_motion']['normal_reports']==162,'0414 exact scope differs')
    if repeat:
        require((image['image_sha256'],install['admission_sha256'],install['C4_sha256'])==
                (parent['image_sha256'],parent['EDR_helper_sha256'],parent['C4_sha256']),'0414 repeat changed a binary')
    else:
        require(helper['matching_physical_control_machine_code'] and c4==load(BINDING),'0414 signed observations differ')
    result = dict(parent,state='prepared-frame414-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(P413/'trial-plan.json'),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],
        EDR_helper_sha256=helper['binary_sha256'],signed_native_EDR_scope_sha256=sha(helper_path),
        C4_sha256=c4['binary_sha256'],C4_logical_bytes=c4['bytes'],frame414_exact_repeat=repeat,
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={name:current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-parent['log_capture']['measured_baseline_bytes']),
        optimization=('Confirm the exact physically stable 0413 image.' if repeat else
                      'Observe only the scoped read-only mappings and actual Metal attachment binding.'),
        performance_comparison='Compare 0413 and 0414 physical vblank and CRC after independent restore.')
    if not repeat:
        result['shared_scanout_observation'] = dict(slots=2,bytes_per_slot=SLOT_BYTES,read_only=True,
            maximum_page_table_stores=10976,maximum_translation_syncs=2,additional_GPU_jobs=0,
            maximum_posted_log_records=4096,owned_hardware_latch_required_for_each_slot=True)
    return result


def criteria(plan):
    repeat,parent,_ = choice()
    prior.budget(BASE/'package-and-run-admission.json', BATCH if repeat else BATCH+60_000_000)
    prior.budget(BASE/'live-batch-admission.json',BATCH)
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'log_capture','optimization','performance_comparison','frame414_exact_repeat'}
    if not repeat:
        allowed.update(('C4_sha256','C4_logical_bytes','shared_scanout_observation'))
    require({key for key in parent.keys()|plan.keys() if plan.get(key)!=parent.get(key)}<=allowed,'0414 scope differs')
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P413,BASE))
    expected = set() if repeat else {'admission','c4'}
    require({key for key,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][key]['new_file_sha256']}==expected,
            '0414 signed changes differ from approved observation')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0414 restore model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P413,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P413/'storage-bound-413.json')
    components = dict(old['components'])
    if not plan['frame414_exact_repeat']:
        components['shared_scanout_observation'] = 650_000
    total = sum(components.values())
    require(total<=RESERVE,'0414 audit exceeds runtime reserve')
    return dict(old,state='bounded0414-shared-scanout-runtime',components=components,worst_case_bytes=total,
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    repeat,parent,comparison = choice()
    manifest,_ = native(repeat)
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK/name for name in tracked),DOC,manifest,IMAGE,comparison,Path(parent['observer_helper']),
        MAIN/'tools/storage-budget.py',BASE/'package-and-run-admission.json',BASE/'live-batch-admission.json',
        BASE/'current-root-capture/result.json',
        *(P413/name for name in ('ready.json','trial-plan.json','storage-bound-413.json','capture-profile.json',
                                 'core-native/result.json','c4-native/result.json','edr-native/result.json')),
        *(LAST/name for name in ('result.json','independent-restore.json','restored-capture/result.json',
                                 'kernel.log','kernel.log.bin','page-flip-latches.json'))]
    retirement = BASE/'retired-exact-generated-install-archives.json'
    if retirement.is_file():
        files.append(retirement)
    proofs = [] if repeat else [PROOF,SHIM,BINDING,
        gpu.P413/'research/tmp/next-shared-retirement/retired-exact-generated-install-archives.json']
    bindings = capture_tools.scoped_pins(BASE,files+proofs,manifest,IMAGE)
    for receipt in proofs:
        for name,digest in load(receipt).get('input_pins',{}).items():
            require(sha(name)==digest and bindings.setdefault(name,digest)==digest,'0414 exact offline input differs')
    return bindings


def freeze():
    return shared.freeze(base=BASE,prior=P413,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
