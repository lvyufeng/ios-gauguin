#!/usr/bin/env python3
"""Freeze the 0419 marker run with passive native completion observations."""

import argparse
from importlib import import_module
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


build = import_module('build-frame425')
marker = build.REFERENCE
phase = marker.phase
prior = phase.prior
BASE, KERNEL, PATCH = build.BASE, build.MANIFEST, build.PATCH
P419, RESERVE = marker.P419, marker.RESERVE
W424 = MAIN / 'research/tmp/gauguin-0419-probe-workloads-20261125'
P423, P424 = (W424 / f'research/tmp/frame-{number}' for number in (423,424))
LAST = P424 / 'execution'
TRIAL = '0425'
IMAGE = BASE / 'frame425-image.json'
SB = P423 / 'sb-native/result.json'
DOC = WORK / 'docs/gauguin-frame-425-passive-completion-20261125.md'
RESOURCES = BASE / 'metadata-snapshot/model-resources/result.json'
FLAGS = (*[f for f in marker.FLAGS if not f.startswith('allow_0423')],
         'allow_0425_one_bounded_0419_marker_passive_completion_trial')
SUCCESS = '0425-passive-completion-and-scanout-measured-root-restored'


def baseline(*, fresh=True):
    end, proof, restored = (load(LAST / path) for path in
                             ('result.json','independent-restore.json','restored-capture/result.json'))
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated']
            and proof['misc_original_4096_bytes_match'] and not proof['device_writes']
            and proof['root_header_sha256'] == restored['root_header_sha256']
            and proof['install_plan_sha256'] == load(P424 / 'trial-plan.json')['install_plan_sha256'],
            '0424 independently restored baseline differs')
    if not fresh:
        return restored
    current = load(BASE / 'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files']) == 31
            and all(current[k] == restored[k] for k in
                    ('root_header_sha256','combined_log_bytes','files','directories')),
            '0425 recovery differs from the 0424 readback')
    return current


def argument(command):
    require(command.split().count('f419=1') == 1 and 'sbp=0' in command.split(),'unexpected 0419 command')
    return command.replace(' f419=1',' f419=2').replace(' sbp=0 ',' sbp=1 ')


def package():
    baseline(fresh=False)
    parent, kernel = load(P419 / 'trial-plan.json'), build.native()
    calibration = load(P423 / 'trial-plan.json')
    pack = import_module('package-frame344')
    shim = load(prior.prior.prior.SHIM)
    require(sha(shim['binary']) == shim['binary_sha256'],'0419 reserved scanout shim differs')
    image = pack.boot_image(load(pack.P343 / 'runtime343-image.json'),kernel,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=Path(shim['binary']),
        private_scanout_slot_bytes=prior.prior.SLOT_BYTES,
        command_profile=lambda cmd:argument(import_module('prepare-frame419').diagnostic_command(
            phase.sustained.sustained_command(prior.prior.manual_command(phase.capture_tools.command_profile(cmd))))))
    old, new = (pack.parts(Path(row['image']).read_bytes()) for row in (calibration,image))
    require(old[0][:16] == new[0][:16] and old[0][20:] == new[0][20:] and old[1] == new[1]
            and old[3] == new[3] and image['command'] == argument(parent['boot_command']),
            'passive capture wrapper or workload differs')
    image['kernel_manifest'] = str(KERNEL)
    phase.save(IMAGE,image)
    helper = prior.retarget_helper(pack,image,parent,base=BASE,reference=P419 / 'edr-native/result.json',trial=TRIAL)
    phase.save(BASE / 'edr-native/result.json',helper)
    for kind in ('core','c4'):
        rel = f'{kind}-native/result.json'
        (BASE / rel).parent.mkdir()
        shutil.copyfile(P419 / rel, BASE / rel)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def delta():
    return phase.shared.stage.delta(BASE,P423,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST / 'restored-capture/result.json',core_logical=load(BASE / 'core-native/result.json')['bytes'],
        c4_receipt=BASE / 'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE / 'restore-model',trial=TRIAL,resources=RESOURCES)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    current, kernel = baseline(), build.native()
    parent_path = P423 / 'trial-plan.json'
    install_path = BASE / 'slot-delta/install-plan.json'
    helper_path = BASE / 'edr-native/result.json'
    parent,image,install,helper = map(load,(parent_path,IMAGE,install_path,helper_path))
    header,size = current['root_header_sha256'],current['combined_log_bytes']
    require(sha(image['image']) == image['image_sha256'] and sha(helper['binary']) == helper['binary_sha256']
            and image['command'] == argument(load(P419 / 'trial-plan.json')['boot_command'])
            and image['build_identity'] == kernel['identity'] == helper['kernel_identity']
            and image['kernel_sha256'] == kernel['kernel_sha256'] and helper['identity_only_retarget']
            and install['trial'] == TRIAL and install['root_header_sha256'] == header and install['changed_ranges'] == 12
            and install['admission_sha256'] == helper['binary_sha256'] and install['core_sha256'] == parent['owned_core_sha256']
            and install['C4_sha256'] == parent['C4_sha256'] and install['rows']['eagl']['new_file_sha256'] == parent['SB_sha256']
            == load(SB)['binary_sha256'] == sha(load(SB)['binary'])
            and sha(BASE / 'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256'],
            'passive display package, user payload or device bounds differ')
    return dict(parent,state='prepared-frame425-passive-completion',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path), install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        new_kernel_builds=1,boot_command=image['command'],kernel_banner=kernel['kernel_banner'],
        kernel_identity=kernel['identity'],EDR_helper_sha256=helper['binary_sha256'],
        signed_native_EDR_scope_sha256=sha(helper_path),
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
                         sizes={name:current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
                         previous_verified_suffix_bytes=size-load(P424/'trial-plan.json')['log_capture']['measured_baseline_bytes']),
        deadline_timeline=dict(parent['deadline_timeline'],boot_option='f419=2'),
        completion_observer=dict(native_call_bracket=True,maximum_raw_records=2304,register_writes=0,
                                 ready_workloop_wakes=0,existing_monitor_only=True),
        optimization='Measure passive completion-word and native-call brackets with the 0419 renderer.',
        performance_comparison='Use the same marker payload and score paired CRCs in the central 30 seconds.')


def criteria(plan):
    old,new = (load(path / 'slot-delta/install-plan.json') for path in (P423,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'admission'},'signed marker or other payload differs')
    proof = load(BASE / 'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12
            and len(proof['checks']) == 49 and proof['all_restore_partial_write_points'] == 17,
            'passive trial restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P423,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P423 / 'storage-bound-423.json')
    return dict(old,state='bounded-0419-passive-marker-runtime',
                fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
                log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK / name for name in tracked),DOC,PATCH,KERNEL,IMAGE,SB,Path(load(SB)['binary']),
             Path(load(P419 / 'trial-plan.json')['observer_helper']),MAIN / 'tools/storage-budget.py',
             BASE / 'total-batch-admission.json',BASE / 'current-root-capture/result.json',P419 / 'trial-plan.json',
             P423 / 'trial-plan.json',P423 / 'storage-bound-423.json',P424 / 'trial-plan.json',
             P424 / 'capture-profile.json',P423 / 'execution/probe-output-deadlines.json',
             *(LAST / name for name in ('result.json','independent-restore.json','restored-capture/result.json'))]
    return phase.capture_tools.scoped_pins(BASE,files,KERNEL,IMAGE)


def freeze():
    return phase.shared.freeze(base=BASE,prior=P424,expected=expected_plan,validate=criteria,
                               storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return phase.shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                               storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__:fn for fn in (package,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=actions)
    print(actions[parser.parse_args().step]())
