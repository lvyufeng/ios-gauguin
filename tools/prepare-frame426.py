#!/usr/bin/env python3
"""Prepare the scripted 0419 Spotlight timing trial."""

import argparse
from importlib import import_module
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


gpu = import_module('prepare-frame425')
build = import_module('build-frame426')
phase,prior = gpu.phase,gpu.prior
BASE,KERNEL,PATCH = build.BASE,build.MANIFEST,build.PATCH
TRIAL = '0426'
P419,P424,RESERVE = gpu.P419,gpu.P424,gpu.RESERVE
LAST = gpu.BASE / 'execution'
IMAGE = BASE / 'frame426-image.json'
SB = BASE / 'sb-native/result.json'
SOURCE = WORK / 'userland/spotlight_probe.m'
DOC = WORK / 'docs/gauguin-frame-426-spotlight-timing-20261125.md'
RESOURCES = BASE / 'metadata-snapshot/model-resources/result.json'
FLAGS = (*[f for f in gpu.FLAGS if not f.startswith('allow_0425')],
         'allow_0426_one_bounded_0419_scripted_spotlight_timing_trial')
SUCCESS = '0426-scripted-Spotlight-timing-measured-root-restored'


def baseline(*, fresh=True):
    end,proof,restored = (load(LAST / name) for name in
                            ('result.json','independent-restore.json','restored-capture/result.json'))
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated']
            and proof['misc_original_4096_bytes_match'] and not proof['device_writes']
            and proof['root_header_sha256'] == restored['root_header_sha256']
            and proof['install_plan_sha256'] == load(gpu.BASE/'trial-plan.json')['install_plan_sha256'],
            '0425 independently restored baseline differs')
    if not fresh:
        return restored
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes']
            and all(current[key] == restored[key] for key in
                    ('root_header_sha256','combined_log_bytes','files','directories')),
            '0426 fresh recovery differs from 0425 readback')
    return current


def command_profile(command):
    require(command.endswith(' f419=1') and 'sbp=0' in command.split(),'unexpected 0419 command')
    return command.removesuffix(' f419=1').replace(' sbp=0 ',' sbp=1 s426=1 ')


def package():
    require(load(gpu.BASE/'total-batch-admission.json')['admitted'],'Spotlight package batch was not admitted')
    parent,kernel = load(P419/'trial-plan.json'),build.native()
    pack = import_module('package-frame344')
    shim = load(prior.prior.prior.SHIM)
    require(sha(shim['binary']) == shim['binary_sha256'],'0419 reserved scanout shim differs')
    source_sha = sha(SOURCE)
    binary = SB.parent/'libGauguinEAGL.dylib'
    binary.parent.mkdir(exist_ok=True)
    if not SB.exists():
        subprocess.run(['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0',
            '-O2','-Wall','-Wextra','-Werror','-fobjc-arc','-dynamiclib','-framework','UIKit',
            '-framework','QuartzCore','-framework','CoreGraphics','-framework','Foundation',
            '-Wl,-install_name,/usr/local/lib/gauguin/libGauguinEAGL.dylib',str(SOURCE),'-o',str(binary)],check=True)
        subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(binary)],check=True)
        require(sha(SOURCE) == source_sha,'Spotlight source changed during compilation')
        phase.save(SB,dict(binary=str(binary),binary_sha256=sha(binary),bytes=binary.stat().st_size,
                           input_pins={str(SOURCE):source_sha},text_contents_recorded=False))
    subprocess.run(['codesign','--verify','--strict',str(binary)],check=True)
    receipt = load(SB)
    require(receipt['input_pins'][str(SOURCE)] == source_sha and receipt['binary_sha256'] == sha(binary),
            'Spotlight signed observer differs')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=Path(shim['binary']),
        private_scanout_slot_bytes=prior.prior.SLOT_BYTES,
        command_profile=lambda cmd:command_profile(import_module('prepare-frame419').diagnostic_command(
            phase.sustained.sustained_command(prior.prior.manual_command(phase.capture_tools.command_profile(cmd))))))
    old,new = (pack.parts(Path(row['image']).read_bytes()) for row in (parent,image))
    require(old[0][:16] == new[0][:16] and old[0][20:] == new[0][20:] and old[1] == new[1]
            and old[3] == new[3] and image['command'] == command_profile(parent['boot_command']),
            'Spotlight test changed an unrelated boot setting')
    image['kernel_manifest'] = str(KERNEL)
    phase.save(IMAGE,image)
    helper = prior.retarget_helper(pack,image,parent,base=BASE,reference=P419/'edr-native/result.json',trial=TRIAL)
    phase.save(BASE/'edr-native/result.json',helper)
    for kind in ('core','c4'):
        rel = f'{kind}-native/result.json'
        (BASE/rel).parent.mkdir()
        shutil.copyfile(P419/rel,BASE/rel)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def capture():
    result = phase.capture_tools.capture_from(BASE,gpu.BASE,TRIAL,baseline)
    phase.prior.prior.capture_resources(current=baseline(),resources=RESOURCES)
    return result


def delta():
    return phase.shared.stage.delta(BASE,P424,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json',sb_receipt=SB)


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL,resources=RESOURCES)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    current,kernel = baseline(),build.native()
    parent_path = P424/'trial-plan.json'
    install_path = BASE/'slot-delta/install-plan.json'
    helper_path = BASE/'edr-native/result.json'
    parent,image,sb,install,helper = map(load,(parent_path,IMAGE,SB,install_path,helper_path))
    header,size = current['root_header_sha256'],current['combined_log_bytes']
    require(sha(image['image']) == image['image_sha256'] and sha(helper['binary']) == helper['binary_sha256']
            and image['command'] == command_profile(load(P419/'trial-plan.json')['boot_command'])
            and image['build_identity'] == kernel['identity'] == helper['kernel_identity']
            and image['kernel_sha256'] == kernel['kernel_sha256'] and helper['identity_only_retarget']
            and install['trial'] == TRIAL and install['root_header_sha256'] == header and install['changed_ranges'] == 12
            and install['admission_sha256'] == helper['binary_sha256'] and install['core_sha256'] == parent['owned_core_sha256']
            and install['C4_sha256'] == parent['C4_sha256']
            and sha(BASE/'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256'],
            'Spotlight package, baseline or reversible writes differ')
    return dict(parent,state='prepared-frame426-scripted-Spotlight',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        new_kernel_builds=1,kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],boot_command=image['command'],
        EDR_helper_sha256=helper['binary_sha256'],signed_native_EDR_scope_sha256=sha(helper_path),SB_sha256=sb['binary_sha256'],
        user_input='bounded-synthetic-unlock-search-keyboard',scripted_strokes=11,scripted_reports=176,wake_button_pairs_max=1,
        frame_capture=dict(parent['frame_capture'],starts_at='qualified display-on settle'),
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
                         sizes={name:current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
                         previous_verified_suffix_bytes=size-load(gpu.BASE/'trial-plan.json')['log_capture']['measured_baseline_bytes']),
        probe=dict(workload='one Home Screen pull-down and nine isolated keyboard-position taps',
                   max_observer_rows=256,max_turn_rows=640,observe_existing_CA_transport=True),
        optimization='Time keyboard release, UIKit turns, CA render and the first changed hardware scan.',
        performance_comparison='Record physical output CRC changes; retain input and keyboard admission separately.')


def criteria(plan):
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P424,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'admission','eagl'} and load(SB)['input_pins'][str(SOURCE)] == sha(SOURCE),
            'Spotlight signed code outside the two existing slots changed')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12
            and len(proof['checks']) == 49 and proof['all_restore_partial_write_points'] == 17,
            'Spotlight restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P424,plan['root_header_sha256'],plan)


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK/name for name in tracked),DOC,PATCH,KERNEL,IMAGE,SOURCE,SB,Path(load(SB)['binary']),
             Path(load(P419/'trial-plan.json')['observer_helper']),MAIN/'tools/storage-budget.py',
             gpu.BASE/'total-batch-admission.json',BASE/'current-root-capture/result.json',P419/'trial-plan.json',
             P424/'trial-plan.json',gpu.BASE/'trial-plan.json',gpu.BASE/'capture-profile.json',
             *(LAST/name for name in ('result.json','independent-restore.json','restored-capture/result.json'))]
    return phase.capture_tools.scoped_pins(BASE,files,KERNEL,IMAGE)


def freeze():
    return phase.shared.freeze(base=BASE,prior=gpu.BASE,expected=expected_plan,validate=criteria,
                               storage_bound=gpu.storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return phase.shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                               storage_bound=gpu.storage,preparer=Path(__file__),reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=actions)
    print(actions[parser.parse_args().step]())
