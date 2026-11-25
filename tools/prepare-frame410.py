#!/usr/bin/env python3
"""Freeze one measured compositor budget or an exact 60 Hz confirmation boot."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

check = import_module('check-frame410-phase')
prior = import_module('prepare-frame409')
BASE,P408,P409,LAST = check.BASE,check.P408,check.P409,check.LAST
DOC = WORK/'docs/gauguin-frame-410-compositor-work-margin-20261124.md'
IMAGE = BASE/'frame410-image.json'
TRIAL = '0410'
BATCH,RESERVE,shared,save = prior.BATCH,prior.RESERVE,prior.shared,prior.save
capture_tools = prior.capture_tools
NATIVE_AND_PACKAGE = BATCH + 60_000_000 + check.NATIVE_BATCH
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0409')],
         'allow_0410_one_bounded_60Hz_temporary_boot_with_reviewed_work_budget_or_exact_repeat')
SUCCESS = '0410-DPU-frame-deadline-physically-measured-root-restored'


def budget(file,planned):
    row = load(BASE/file)
    require(row['admitted'] and row['planned_batch_bytes']==planned and
            row['current_accounted_bytes']+planned<=row['limit_bytes'],'0410 batch exceeds storage')


def decision():
    choice = load(check.CHOICE)
    require(choice==check.select(),'0410 measured selection differs')
    return choice


def baseline(*,fresh=True):
    _,run,_,_ = check.archive('0409')
    restored = load(run/'restored-capture/result.json')
    proof = load(run/'independent-restore.json')
    require(proof['root_header_sha256']==restored['root_header_sha256'],'0409 independent restore root differs')
    if not fresh:
        return restored
    live = load(BASE/'current-root-capture/result.json')
    require(not live['device_writes'] and len(live['files'])==31 and all(live[key]==restored[key] for key in (
        'root_header_sha256','combined_log_bytes','files','directories')),'0410 fresh original root differs')
    return live


def selected_kernel(choice):
    path = check.source_manifest(choice['control']) if choice['repeat'] else check.KERNEL
    kernel = load(path)
    require(kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            sha(kernel['kernel'])==kernel['kernel_sha256'],'0410 selected kernel differs')
    if not choice['repeat']:
        proof = load(check.HOST)
        parent = check.source_manifest(choice['control'])
        require({Path(p).stem for p in kernel['object_replacements'].values()}=={'SweetFramebuffer'} and
                proof['work_us']==choice['work_us'] and proof['control']==choice['control'] and
                kernel['input_pins'][str(parent)]==sha(parent) and
                kernel['input_pins'][str(check.PATCH)]==proof['input_pins'][str(check.PATCH)]==sha(check.PATCH),
                '0410 candidate differs beyond the reviewed framebuffer unit')
    return path,kernel


def package():
    choice = decision()
    budget('complete-batch-admission.json',BATCH if choice['repeat'] else NATIVE_AND_PACKAGE)
    baseline(fresh=False)
    where,_,_,ref,_,_,_ = check.measured(choice['control'])
    manifest,kernel = selected_kernel(choice)
    ref_name = f'{int(choice["control"])}'
    if choice['repeat']:
        image = load(where/f'frame{ref_name}-image.json')
        helper = load(where/'edr-native/result.json')
        (BASE/'edr-native').mkdir()
    else:
        pack = import_module('package-frame344')
        image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
            frame_capture_mode=9,scripted_motion=True,
            private_scanout_shim=import_module('prepare-frame388').SHIM,command_profile=capture_tools.command_profile)
        prior_wrap,selected_wrap = (pack.parts(Path(path).read_bytes()) for path in (ref['image'],image['image']))
        require(prior_wrap[0][:16]==selected_wrap[0][:16] and prior_wrap[0][20:]==selected_wrap[0][20:] and
                prior_wrap[1]==selected_wrap[1] and prior_wrap[3]==selected_wrap[3] and
                image['command']==ref['boot_command'],'0410 physical timing or boot wrapper differs')
        helper = pack.edr(image,base=BASE,trial=TRIAL,
            signed_reference=capture_tools.P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
        donor = where/'edr-native/result.json'
        control = load(donor)
        words = import_module('check-frame395-edr').native_words
        require(sha(control['binary'])==control['binary_sha256'] and words(control['binary'])==words(helper['binary']),
                '0410 signed helper machine instructions differ')
        helper['matching_physical_control_machine_code'] = True
        helper['input_pins'].update({str(donor):sha(donor),control['binary']:control['binary_sha256']})
    image['kernel_manifest'] = str(manifest)
    save(IMAGE,image)
    save(BASE/'edr-native/result.json',helper)
    for kind in ('core','c4'):
        receipt = BASE/f'{kind}-native/result.json'
        receipt.parent.mkdir()
        shutil.copyfile(P409/f'{kind}-native/result.json',receipt)
    return {k:image[k] for k in ('image_sha256','image_bytes','build_identity')}


def capture():
    budget('live-batch-admission.json',BATCH)
    return capture_tools.capture_from(BASE,P409,TRIAL,baseline)


def delta():
    return shared.stage.delta(BASE,P409,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    live,choice = baseline(),decision()
    selected_manifest,kernel = selected_kernel(choice)
    reference = check.measured(choice['control'])[3]
    parent_path = P409/'trial-plan.json'
    parent = load(parent_path)
    install_path,helper_path = BASE/'slot-delta/install-plan.json',BASE/'edr-native/result.json'
    install,helper,image = map(load,(install_path,helper_path,IMAGE))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    require(str(selected_manifest)==image['kernel_manifest'] and
            kernel['kernel_sha256']==image['kernel_sha256'] and sha(image['image'])==image['image_sha256'] and
            image['build_identity']==kernel['identity']==helper['kernel_identity'] and
            image['command']==reference['boot_command']==parent['boot_command'] and
            (reference['image_sha256']==image['image_sha256'] if choice['repeat']
             else helper['matching_physical_control_machine_code']) and
            sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
            install['core_sha256']==reference['owned_core_sha256']==parent['owned_core_sha256'] and
            install['C4_sha256']==reference['C4_sha256']==parent['C4_sha256'] and
            install['rows']['core']['new_logical']==parent['owned_core_logical_bytes'] and
            install['rows']['c4']['new_logical']==parent['C4_logical_bytes'] and
            install['trial']==TRIAL and install['root_header_sha256']==header and install['changed_ranges']==12 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
            parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
            parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
            parent['sustained_motion']['normal_reports']==162,'0410 exact timing or recovery scope differs')
    description = ('Repeat the exact previously stable 0409 image and userspace.' if choice['repeat']
                   else f'Use a {choice["work_us"]} us compositor work allowance on existing physical cadence.')
    return dict(parent,state='prepared-frame410-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],
        EDR_helper_sha256=helper['binary_sha256'],signed_native_EDR_scope_sha256=sha(helper_path),
        work_duration_us=choice['work_us'],native_bandwidth_index=choice['native_bandwidth_index'],
        phase_control_trial=choice['control'],exact_repeat=choice['repeat'],
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={k:live['files'][k]['bytes'] for k in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-parent['log_capture']['measured_baseline_bytes']),
        optimization=description,performance_comparison=f'Compare physical scans against {choice["control"]}.')


def criteria(plan):
    budget('complete-batch-admission.json',BATCH if plan['exact_repeat'] else NATIVE_AND_PACKAGE)
    budget('live-batch-admission.json',BATCH)
    parent = load(P409/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'log_capture','optimization','performance_comparison','work_duration_us','native_bandwidth_index',
        'phase_control_trial','exact_repeat'}
    require({k for k in parent.keys()|plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0410 scope differs')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P409,BASE))
    changes = set() if plan['exact_repeat'] else {'admission'}
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
            ==changes,'0410 signed userspace differs beyond kernel identity')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0410 recovery model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P409,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P409/'storage-bound-409.json')
    require(old['worst_case_bytes']<=RESERVE,'0410 runtime exceeds reserve')
    return dict(old,state='bounded0410-physical-work-budget-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
                log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    choice = decision()
    kernel,_ = selected_kernel(choice)
    where,run,_,_,comparison,_,_ = check.measured(choice['control'])
    parent = load(P409/'trial-plan.json')
    paths = [*(WORK/p for p in tracked),DOC,kernel,IMAGE,comparison,check.CHOICE,MAIN/'tools/storage-budget.py',
        BASE/'complete-batch-admission.json',BASE/'live-batch-admission.json',BASE/'current-root-capture/result.json',
        Path(parent['observer_helper']),where/'trial-plan.json',where/'edr-native/result.json',
        run/'result.json',run/'independent-restore.json',run/'kernel.log',run/'kernel.log.bin',run/'page-flip-latches.json',
        *(P409/p for p in ('ready.json','storage-bound-409.json','trial-plan.json','capture-profile.json',
            'core-native/result.json','c4-native/result.json','edr-native/result.json')),
        *(LAST/p for p in ('result.json','independent-restore.json','restored-capture/result.json'))]
    if not choice['repeat']:
        paths += [check.HOST,check.PATCH]
    retirement = BASE/'retired-exact-generated-install-archives.json'
    if retirement.is_file():
        paths.append(retirement)
    bindings = capture_tools.scoped_pins(BASE,paths,kernel,IMAGE)
    if not choice['repeat']:
        for path,digest in load(check.HOST)['input_pins'].items():
            require(sha(path)==digest and bindings.setdefault(path,digest)==digest,'0410 timing proof input differs')
    return bindings


def freeze():
    return shared.freeze(base=BASE,prior=P409,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
