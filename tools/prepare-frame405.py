#!/usr/bin/env python3
"""Freeze one 60 Hz boot with bounded read-only Adreno completion samples."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX,MAIN,WORK,load,require,sha
from kernel342_log import ring_status

probe = import_module('check-frame405')
prior = import_module('prepare-frame404')
BASE,P404 = probe.BASE,probe.P401/'frame-404'
LAST = P404/'execution'
COMPARISON = LAST/'scanout-comparison-0403-0404.json'
KERNEL = BASE/'native-kernel/build-manifest.json'
HOST = BASE/'offline.json'
IMAGE = BASE/'frame405-image.json'
DOC = WORK/'docs/gauguin-frame-405-completion-sampling-20261124.md'
TRIAL = '0405'
BATCH,RESERVE,shared,save = prior.BATCH,prior.RESERVE,prior.shared,prior.save
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0404')],
         'allow_0405_one_bounded_60Hz_temporary_boot_with_read_only_exact_GPU_completion_samples')
SUCCESS = '0405-DPU-and-raw-EOP-measured-root-restored'
MAX_CONSOLE_ADDITION = 256*96+128


def budget(name,planned):
    proof = load(BASE/name)
    require(proof['admitted'] and proof['planned_batch_bytes']==planned and
            proof['current_accounted_bytes']+planned<=proof['limit_bytes'],'0405 batch exceeds storage')


def baseline(*,fresh=True):
    result,proof,restored = (load(LAST/name) for name in (
        'result.json','independent-restore.json','restored-capture/result.json'))
    require(result['trial']=='0404' and result['boot_attempts']==1 and result['restored'] and
            result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            not result.get('stable_60_fps_observed') and proof['journal_empty'] and
            proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'] and
            proof['root_header_sha256']==restored['root_header_sha256'] and
            proof['install_plan_sha256']==load(P404/'trial-plan.json')['install_plan_sha256'],
            '0404 independent restoration differs')
    if not fresh:
        return restored
    live = load(BASE/'current-root-capture/result.json')
    require(not live['device_writes'] and len(live['files'])==31 and all(live[k]==restored[k] for k in (
        'root_header_sha256','combined_log_bytes','files','directories')), '0405 recovery root differs')
    return live


def native():
    kernel,host = load(KERNEL),load(HOST)
    require(kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            {Path(p).stem for p in kernel['object_replacements'].values()}==
                {'GauguinGPU','gauguin_gmu_board','gauguin_ui_trace_board'} and host['ASan_UBSan'] and
            kernel['input_pins'][str(probe.PATCH)]==host['patch_sha256']==sha(probe.PATCH) and
            sha(kernel['kernel'])==kernel['kernel_sha256'],'0405 observation-only overlay differs')
    return kernel


def package():
    budget('complete-batch-admission.json',BATCH+60_000_000)
    baseline(fresh=False)
    console = ring_status((LAST/'kernel.log.bin').read_bytes(),(LAST/'kernel.log').read_text())
    require(console['qualified'] and console['total_bytes']+MAX_CONSOLE_ADDITION<=console['ring_bytes'],
            '0405 completion samples exceed exact control console capacity')
    pack = import_module('package-frame344')
    setup = import_module('prepare-frame393')
    kernel = native()
    parent = load(P404/'trial-plan.json')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=setup.previous.previous.previous.prior388.SHIM,
        command_profile=setup.previous.command_profile)
    control,candidate = (pack.parts(Path(p).read_bytes()) for p in (parent['image'],image['image']))
    require(control[0][:16]==candidate[0][:16] and control[0][20:]==candidate[0][20:] and
            control[1]==candidate[1] and control[3]==candidate[3] and image['command']==parent['boot_command'],
            '0405 boot wrapper or DPU cadence differs')
    donor = P404/'edr-native/result.json'
    old = load(donor)
    helper = pack.edr(image,base=BASE,trial=TRIAL,
        signed_reference=prior.previous.check.placement.P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
    words = import_module('check-frame395-edr').native_words
    require(sha(old['binary'])==old['binary_sha256'] and words(helper['binary'])==words(old['binary']),
            '0405 signed stock GPU point differs')
    helper['matching_0404_machine_code'] = True
    helper['input_pins'].update({str(donor):sha(donor),old['binary']:old['binary_sha256']})
    image['kernel_manifest'] = str(KERNEL)
    save(BASE/'edr-native/result.json',helper)
    save(IMAGE,image)
    for kind in ('core','c4'):
        receipt = BASE/f'{kind}-native/result.json'
        receipt.parent.mkdir()
        shutil.copyfile(P404/f'{kind}-native/result.json',receipt)
    return {k:image[k] for k in ('image_sha256','image_bytes','build_identity')}


def capture():
    budget('live-batch-admission.json',BATCH)
    return prior.previous.capture_tools.capture_from(BASE,P404,TRIAL,baseline)


def delta():
    return shared.stage.delta(BASE,P404,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    live,kernel = baseline(),native()
    parent_path = P404/'trial-plan.json'
    parent = load(parent_path)
    install_path,helper_path = BASE/'slot-delta/install-plan.json',BASE/'edr-native/result.json'
    install,helper,image = map(load,(install_path,helper_path,IMAGE))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    core,c4 = (load(BASE/f'{kind}-native/result.json') for kind in ('core','c4'))
    require(core['signature_verified'] and c4['strict_signature'] and
            kernel['kernel_sha256']==image['kernel_sha256'] and sha(image['image'])==image['image_sha256'] and
            image['build_identity']==kernel['identity']==helper['kernel_identity'] and
            image['command']==parent['boot_command'] and helper['matching_0404_machine_code'] and
            sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
            install['core_sha256']==core['binary_sha256']==sha(core['binary'])==parent['owned_core_sha256'] and
            install['C4_sha256']==c4['binary_sha256']==sha(c4['binary'])==parent['C4_sha256'] and
            install['rows']['core']['new_logical']==core['bytes']==parent['owned_core_logical_bytes'] and
            install['rows']['c4']['new_logical']==c4['bytes']==parent['C4_logical_bytes'] and
            install['trial']==TRIAL and install['root_header_sha256']==header and install['changed_ranges']==12 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
            parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
            parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
            parent['sustained_motion']['normal_reports']==162,'0405 exact no-timing-change scope differs')
    return dict(parent,state='prepared-frame405-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=helper['binary_sha256'],
        signed_native_EDR_scope_sha256=sha(helper_path),
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={k:live['files'][k]['bytes'] for k in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-parent['log_capture']['measured_baseline_bytes']),
        optimization='Observe the exact raw GPU completion word while retaining original guarded readiness.',
        performance_comparison='Align physical warm and drag scans with 0404 and bound raw EOP separately.')


def criteria(plan):
    budget('complete-batch-admission.json',BATCH+60_000_000)
    budget('live-batch-admission.json',BATCH)
    parent = load(P404/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'log_capture','optimization','performance_comparison'}
    require({k for k in parent.keys()|plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0405 scope differs')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P404,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
            =={'admission'},'0405 userspace differs beyond signed identity')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0405 recovery model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P404,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P404/'storage-bound-404.json')
    require(old['worst_case_bytes']<=RESERVE,'0405 runtime exceeds reserve')
    return dict(old,state='bounded0405-exact-completion-observation-runtime',
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    parent = load(P404/'trial-plan.json')
    paths = [*(WORK/p for p in tracked),DOC,HOST,KERNEL,IMAGE,probe.PATCH,BASE/'native-admission.json',
        prior.P403/'trial-plan.json',prior.CONTROL,prior.prior.CONTROL,
        *(prior.P403_TOOLS/f for f in ('run-frame402-trial.py','prepare-frame402.py','check-frame402.py')),
        MAIN/'tools/storage-budget.py',BASE/'complete-batch-admission.json',
        BASE/'live-batch-admission.json',BASE/'current-root-capture/result.json',Path(parent['observer_helper']),
        *(P404/p for p in ('ready.json','storage-bound-404.json','trial-plan.json','capture-profile.json',
            'core-native/result.json','c4-native/result.json')),
        *(LAST/p for p in ('result.json','independent-restore.json','restored-capture/result.json')),
        *(LAST/p for p in ('kernel.log','kernel.log.bin','page-flip-latches.json') if (LAST/p).is_file())]
    if COMPARISON.is_file():
        paths.append(COMPARISON)
    retirement = BASE/'retired-exact-generated-install-archives.json'
    if retirement.is_file():
        paths.append(retirement)
    bindings = prior.previous.capture_tools.scoped_pins(BASE,paths,KERNEL,IMAGE)
    for path,digest in load(HOST)['input_pins'].items():
        require(sha(path)==digest and bindings.setdefault(path,digest)==digest,'0405 host proof input differs')
    return bindings


def freeze():
    return shared.freeze(base=BASE,prior=P404,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
