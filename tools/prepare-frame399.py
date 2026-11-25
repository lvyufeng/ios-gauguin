#!/usr/bin/env python3
"""Prepare one bounded 60 Hz trial with separate producer and CPU clock receipts."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX,MAIN,WORK,load,require,sha

check = import_module('check-frame399')
previous = import_module('prepare-frame398')
capture_tools = import_module('prepare-frame392')
BASE,P398,KERNEL,HOST = check.BASE,check.P398,check.BASE/'native-kernel/build-manifest.json',check.BASE/'offline.json'
P394 = MAIN/'research/tmp/gauguin-frame394-compositor-qos-worktree-20261123/research/tmp/frame-394'
CONTROL = P394/'execution/scanout-comparison-0398-0394.json'
IMAGE = BASE/'frame399-image.json'
FRONTEND = BASE/'c4-native/result.json'
DOC = WORK/'docs/gauguin-frame-399-producer-observation-20261123.md'
BATCH,RESERVE,shared,save = previous.BATCH,previous.RESERVE,previous.shared,previous.save
TRIAL = '0399'
FLAGS = (*[flag for flag in previous.FLAGS if not flag.startswith('allow_0398')],
         'allow_0399_one_bounded_60Hz_temporary_boot_with_producer_and_CPU_clock_receipts')
SUCCESS = '0399-producer-and-CPU-clock-observations-physically-measured-root-restored'


def budget(name, planned):
    proof = load(BASE/name)
    require(proof['admitted'] and proof['planned_batch_bytes'] == planned and
            proof['current_accounted_bytes']+planned <= proof['limit_bytes'],'0399 batch exceeds storage')


def baseline(*,fresh=True):
    last = P394/'execution'
    terminal, proof, restored = (load(last/name) for name in (
        'result.json','independent-restore.json','restored-capture/result.json'))
    require(terminal['restored'] and terminal['independent_restore_verified'] and
            terminal['static_root_comparison_passed'] and not terminal.get('stable_60_fps_observed') and
            terminal['DPU_independent_physical_FPS_qualified'] and terminal['recorder_qos']['actual_class_raised'] and
            not load(CONTROL)['stable_60_fps_observed'] and
            load(P394/'trial-plan.json')['image_sha256']==load(P398/'trial-plan.json')['image_sha256'] and
            proof['install_plan_sha256']==load(P394/'trial-plan.json')['install_plan_sha256'] and
            proof['root_header_sha256']==restored['root_header_sha256'] and proof['journal_empty'] and
            proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'],
            '0394 requires independent restoration and the visible 60 fps target must remain open')
    if not fresh:
        return restored
    live = load(BASE/'current-root-capture/result.json')
    require(not live['device_writes'] and len(live['files'])==31 and all(live[k]==restored[k] for k in (
        'root_header_sha256','combined_log_bytes','files','directories')), '0399 recovery root differs')
    return live


def package():
    budget('complete-batch-admission.json',BATCH+60_000_000)
    baseline(fresh=False)
    pack = import_module('package-frame344')
    setup = import_module('prepare-frame393')
    manifest = load(KERNEL)
    require(manifest['inputs_unchanged'] and manifest['baseline_reproduced_except_uuid'] and
            manifest['input_pins'][str(check.PATCH)]==sha(check.PATCH)==load(HOST)['patch_sha256'],
            '0399 kernel does not match the host proof')
    parent = load(P394/'trial-plan.json')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),manifest,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=setup.previous.previous.previous.prior388.SHIM,
        command_profile=setup.previous.command_profile)
    control,candidate = (pack.parts(Path(p).read_bytes()) for p in (parent['image'],image['image']))
    require(control[0][:16]==candidate[0][:16] and control[0][20:]==candidate[0][20:] and
            control[1]==candidate[1] and control[3]==candidate[3] and
            image['command']==parent['boot_command'], '0399 boot wrapper, clocking or DPU DTB differed')
    donor = P398/'edr-native/result.json'
    old = load(donor)
    helper = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=check.placement.P391/'edr-native/result.json',
                      profile=('gpf=4','gpf=5'))
    words = import_module('check-frame395-edr').native_words
    require(words(helper['binary'])==words(old['binary']) and sha(old['binary'])==old['binary_sha256'],
            '0399 signed GPU-point scope text differs')
    helper['matching_0398_machine_code'] = True
    helper['input_pins'].update({str(donor):sha(donor),old['binary']:old['binary_sha256']})
    image['kernel_manifest'] = str(KERNEL)
    save(BASE/'edr-native/result.json',helper)
    save(IMAGE,image)
    return {k:image[k] for k in ('image_sha256','image_bytes','build_identity')}


def capture():
    budget('live-batch-admission.json',BATCH)
    return capture_tools.capture_from(BASE,P394,TRIAL,baseline)


def delta():
    core = BASE/'core-native/result.json'
    core.parent.mkdir(exist_ok=True)
    shutil.copyfile(P394/'core-native/result.json',core)
    return shared.stage.delta(BASE,P394,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=P394/'execution/restored-capture/result.json',core_logical=7_975_888,c4_receipt=FRONTEND)


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    live = baseline()
    parent_path = P394/'trial-plan.json'
    parent = load(parent_path)
    install_path,helper_path = BASE/'slot-delta/install-plan.json',BASE/'edr-native/result.json'
    install,helper,image,kernel,host,frontend = map(load,(install_path,helper_path,IMAGE,KERNEL,HOST,FRONTEND))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    require(host['ASan_UBSan'] and host['cases']==10 and not host['device_commands'] and
            kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            {Path(p).stem for p in kernel['object_replacements'].values()}=={'GauguinGPU'} and
            kernel['input_pins'][str(check.PATCH)]==host['patch_sha256']==sha(check.PATCH) and
            sha(kernel['kernel'])==kernel['kernel_sha256']==image['kernel_sha256'] and
            sha(image['image'])==image['image_sha256'] and image['build_identity']==kernel['identity']==helper['kernel_identity'] and
            image['command']==parent['boot_command'] and helper['matching_0398_machine_code'] and
            sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
            frontend['strict_signature'] and not frontend['device_commands'] and
            frontend['reconstructed_control_sha256']==parent['C4_sha256'] and
            sha(frontend['binary'])==frontend['binary_sha256']==install['C4_sha256'] and
            install['rows']['c4']['new_logical']==frontend['bytes'] and install['core_sha256']==parent['owned_core_sha256'] and
            install['trial']==TRIAL and install['root_header_sha256']==header and install['changed_ranges']==12 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
            parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
            parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
            parent['sustained_motion']['normal_reports']==162,'0399 observer, DPU, CRC or restore scope differs')
    prior_size = load(P394/'trial-plan.json')['log_capture']['measured_baseline_bytes']
    return dict(parent,state='prepared-frame399-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=helper['binary_sha256'],
        signed_native_EDR_scope_sha256=sha(helper_path),C4_sha256=frontend['binary_sha256'],
        signed_native_C4_scope_sha256=sha(FRONTEND),
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={k:live['files'][k]['bytes'] for k in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-prior_size),
        optimization='Observe the recorder render target and both CPU frequency domains.',
        performance_comparison='Compare 0394/0399 steady new images and onset. Separate clock and producer evidence.')


def criteria(plan):
    budget('complete-batch-admission.json',BATCH+60_000_000)
    budget('live-batch-admission.json',BATCH)
    parent = load(P394/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'C4_sha256','signed_native_C4_scope_sha256','log_capture','optimization','performance_comparison'}
    require({k for k in parent.keys() | plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0399 effect scope differs')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P394,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
            =={'admission','c4'},'0399 changed outside the observation and its signed admission')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0399 recovery model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P394,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P394/'storage-bound-394.json')
    require(old['worst_case_bytes']<=RESERVE,'0399 runtime exceeds reserve')
    return dict(old,state='bounded0399-read-only-observation-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    parent = load(P394/'trial-plan.json')
    files = [*(WORK/p for p in tracked),DOC,HOST,FRONTEND,KERNEL,IMAGE,CONTROL,check.PATCH,check.FIXTURE,check.placement.FDT,
        MAIN/'tools/storage-budget.py',BASE/'complete-batch-admission.json',BASE/'live-batch-admission.json',
        BASE/'current-root-capture/result.json',Path(parent['observer_helper']),P398/'ready.json',P398/'trial-plan.json',
        P394/'ready.json',P394/'storage-bound-394.json',P394/'capture-profile.json',P394/'trial-plan.json',
        *(P394/'execution'/p for p in ('result.json','independent-restore.json','restored-capture/result.json')),
        *(P394/'execution'/p for p in ('kernel.log','kernel.log.bin','page-flip-latches.json'))]
    bindings = capture_tools.scoped_pins(BASE,files,KERNEL,IMAGE)
    for receipt in (HOST,FRONTEND):
        for path,digest in load(receipt)['input_pins'].items():
            require(sha(path)==digest and bindings.setdefault(path,digest)==digest,'0399 stock or frontend input differs')
    return bindings


def freeze():
    return shared.freeze(base=BASE,prior=P394,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
