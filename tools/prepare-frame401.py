#!/usr/bin/env python3
"""Freeze the exact-producer display trial with the latest independently restored root."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess

from frame366_scope import LOG_SUFFIX,MAIN,WORK,load,require,sha

check = import_module('stage-frame401-producer')
prior = import_module('prepare-frame400')
previous = prior.previous
BASE,P400 = check.BASE,check.P400
P394 = previous.P394
P402 = MAIN/'research/tmp/gauguin-frame402-stock-cpu-opp-worktree-20261124/research/tmp/frame-402'
CONTROL = P400/'execution/scanout-comparison-0394-0400.json'
LAST = P402/'execution'
KERNEL = BASE/'native-kernel/build-manifest.json'
HOST = BASE/'producer-native-pins.json'
PATCH = BASE/'producer401-native.patch'
IMAGE = BASE/'frame401-image.json'
DOC = WORK/'docs/gauguin-frame-401-render-ownership-20261124.md'
BATCH,RESERVE,shared,save = previous.BATCH,previous.RESERVE,previous.shared,previous.save
TRIAL = '0401'
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0400')],
         'allow_0401_one_bounded_60Hz_temporary_boot_with_exact_pre_issue_writer')
SUCCESS = '0401-exact-render-writer-physically-measured-root-restored'


def budget(name, planned):
    proof = load(BASE/name)
    require(proof['admitted'] and proof['planned_batch_bytes']==planned and
            proof['current_accounted_bytes']+planned<=proof['limit_bytes'],'0401 batch exceeds storage')


def baseline(*,fresh=True):
    terminal,proof,restored = (load(LAST/name) for name in (
        'result.json','independent-restore.json','restored-capture/result.json'))
    require(terminal['restored'] and terminal['independent_restore_verified'] and terminal['static_root_comparison_passed'] and
            not terminal.get('stable_60_fps_observed') and not load(CONTROL)['stable_60_fps_observed'] and
            proof['install_plan_sha256']==load(P402/'trial-plan.json')['install_plan_sha256'] and
            proof['root_header_sha256']==restored['root_header_sha256'] and proof['all_original_slot_bits_allocated'] and
            proof['journal_empty'] and proof['misc_original_4096_bytes_match'],'0402 independent restoration differs')
    if not fresh:
        return restored
    live = load(BASE/'current-root-capture/result.json')
    require(not live['device_writes'] and len(live['files'])==31 and all(live[k]==restored[k] for k in (
        'root_header_sha256','combined_log_bytes','files','directories')), '0401 recovery root differs')
    return live


def package():
    budget('complete-batch-admission.json',BATCH+60_000_000)
    baseline(fresh=False)
    pack = import_module('package-frame344')
    setup = import_module('prepare-frame393')
    kernel = load(KERNEL)
    source = load(HOST)
    require(kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            kernel['input_pins'][str(PATCH)]==source['patch_sha256']==sha(PATCH),
            '0401 kernel does not match the producer fixture')
    parent = load(P400/'trial-plan.json')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=setup.previous.previous.previous.prior388.SHIM,
        command_profile=setup.previous.command_profile)
    control,candidate = (pack.parts(Path(p).read_bytes()) for p in (parent['image'],image['image']))
    require(control[0][:16]==candidate[0][:16] and control[0][20:]==candidate[0][20:] and
            control[1]==candidate[1] and control[3]==candidate[3] and
            image['command']==parent['boot_command'],'0401 boot wrapper or DPU cadence differs')
    donor = P400/'edr-native/result.json'
    old = load(donor)
    helper = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=previous.check.placement.P391/'edr-native/result.json',
                      profile=('gpf=4','gpf=5'))
    words = import_module('check-frame395-edr').native_words
    require(sha(old['binary'])==old['binary_sha256'] and words(helper['binary'])==words(old['binary']),
            '0401 signed GPU operating-point checks differ')
    helper['matching_0400_machine_code'] = True
    helper['input_pins'].update({str(donor):sha(donor),old['binary']:old['binary_sha256']})
    image['kernel_manifest'] = str(KERNEL)
    save(BASE/'edr-native/result.json',helper)
    save(IMAGE,image)
    return {k:image[k] for k in ('image_sha256','image_bytes','build_identity')}


def capture():
    budget('live-batch-admission.json',BATCH)
    return previous.capture_tools.capture_from(BASE,P402,TRIAL,baseline)


def delta():
    core = load(BASE/'core-native/result.json')
    c4 = BASE/'c4-native/result.json'
    return shared.stage.delta(BASE,P400,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=core['bytes'],c4_receipt=c4)

def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    live = baseline()
    parent_path = P400/'trial-plan.json'
    parent = load(parent_path)
    install_path,helper_path = BASE/'slot-delta/install-plan.json',BASE/'edr-native/result.json'
    install,helper,image,kernel,host = map(load,(install_path,helper_path,IMAGE,KERNEL,HOST))
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    core,c4 = (load(BASE/f'{kind}-native/result.json') for kind in ('core','c4'))
    require(host['pre_issue_exact_cases']==5 and not host['device_commands'] and
            core['signature_verified'] and c4['strict_signature'] and
            core['reconstructed_control_sha256']==parent['owned_core_sha256'] and
            c4['reconstructed_control_sha256']==parent['C4_sha256'] and
            kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            {Path(p).stem for p in kernel['object_replacements'].values()}=={'GauguinGPU','SweetFramebuffer','kdebug'} and
            kernel['input_pins'][str(PATCH)]==host['patch_sha256']==sha(PATCH) and
            sha(kernel['kernel'])==kernel['kernel_sha256']==image['kernel_sha256'] and
            sha(image['image'])==image['image_sha256'] and image['build_identity']==kernel['identity']==helper['kernel_identity'] and
            image['command']==parent['boot_command'] and helper['matching_0400_machine_code'] and
            sha(helper['binary'])==helper['binary_sha256']==install['admission_sha256'] and
            install['core_sha256']==core['binary_sha256']==sha(core['binary']) and
            install['C4_sha256']==c4['binary_sha256']==sha(c4['binary']) and
            install['rows']['core']['new_logical']==core['bytes']==7_975_984 and
            install['rows']['c4']['new_logical']==c4['bytes']==429_504 and
            install['trial']==TRIAL and install['root_header_sha256']==header and install['changed_ranges']==12 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
            parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
            parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
            parent['sustained_motion']['normal_reports']==162,'0401 producer or recovery scope differs')
    prior_size = load(P402/'trial-plan.json')['log_capture']['measured_baseline_bytes']
    return dict(parent,state='prepared-frame401-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=helper['binary_sha256'],
        signed_native_EDR_scope_sha256=sha(helper_path),
        owned_core_sha256=core['binary_sha256'],owned_core_logical_bytes=core['bytes'],
        C4_sha256=c4['binary_sha256'],C4_logical_bytes=c4['bytes'],
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={k:live['files'][k]['bytes'] for k in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-prior_size),
        optimization='Bind the exact in-render GPU producer before issue when the display version is busy.',
        performance_comparison='Compare 0400/0401 ordinary motion, first visible image and fixed drag.')


def criteria(plan):
    budget('complete-batch-admission.json',BATCH+60_000_000)
    budget('live-batch-admission.json',BATCH)
    parent = load(P400/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','signed_native_EDR_scope_sha256',
        'log_capture','optimization','performance_comparison','owned_core_sha256','owned_core_logical_bytes',
        'C4_sha256','C4_logical_bytes'}
    require({k for k in parent.keys()|plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0401 scope differs')
    old,new = (load(p/'slot-delta/install-plan.json') for p in (P400,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
            =={'admission','core','c4'},'0401 changed userspace outside the three verified signed files')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges']==12 and len(proof['checks'])==49 and
            proof['all_restore_partial_write_points']==17,'0401 recovery model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P400,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P400/'storage-bound-400.json')
    require(old['worst_case_bytes']<=RESERVE,'0401 runtime exceeds reserve')
    return dict(old,state='bounded0401-exact-render-writer-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    parent = load(P400/'trial-plan.json')
    paths = [*(WORK/p for p in tracked),DOC,HOST,KERNEL,IMAGE,CONTROL,
        BASE/'producer401-native.patch',check.ELIGIBILITY,check.DEVELOPMENT,
        *(check.ROOT/path for path in check.HEADERS),
        MAIN/'tools/storage-budget.py',BASE/'complete-batch-admission.json',
        BASE/'live-batch-admission.json',BASE/'current-root-capture/result.json',Path(parent['observer_helper']),
        P400/'ready.json',P400/'storage-bound-400.json',P400/'trial-plan.json',P402/'capture-profile.json',P402/'trial-plan.json',
        *(LAST/p for p in ('result.json','independent-restore.json','restored-capture/result.json')),
        *(P400/'execution'/p for p in ('kernel.log','kernel.log.bin','page-flip-latches.json')),
        prior.CONTROL,P394/'trial-plan.json']
    bindings = previous.capture_tools.scoped_pins(BASE,paths,KERNEL,IMAGE)
    for path,digest in load(HOST)['input_pins'].items():
        require(sha(path)==digest and bindings.setdefault(path,digest)==digest,'0401 reference timing evidence differs')
    return bindings


def freeze():
    return shared.freeze(base=BASE,prior=P402,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
