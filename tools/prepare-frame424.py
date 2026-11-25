#!/usr/bin/env python3
"""Prepare the independent 0419 physical Spotlight workload."""

import argparse
from importlib import import_module
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


marker = import_module('prepare-frame423')
phase = marker.phase
TRIAL = '0424'
BASE = WORK / 'research/tmp/frame-424'
LAST = marker.BASE / 'execution'
P419, KERNEL, RESERVE = marker.P419, marker.KERNEL, marker.RESERVE
DOC = WORK / 'docs/gauguin-0419-probe-workloads-20261125.md'
SOURCE = WORK / 'userland/spotlight_probe.m'
IMAGE = BASE / 'frame424-image.json'
SB = BASE / 'sb-native/result.json'
RESOURCES = BASE / 'metadata-snapshot/model-resources/result.json'
SUBSTITUTIONS = {'sbp=0':'sbp=1', 'swp=5':'swp=0', 'sweetnvt=0':'sweetnvt=1'}
FLAGS = (*[flag for flag in marker.FLAGS if not flag.startswith('allow_0423')],
         'allow_0424_one_bounded_0419_60Hz_physical_search_window', 'allow_physical_NVT_input')
SUCCESS = '0424-0419-Spotlight-capture-restored'


def baseline(*, fresh=True):
    end, proof, restored = (load(LAST / name) for name in
                             ('result.json','independent-restore.json','restored-capture/result.json'))
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and all(end['other_log_prefix_preserved'].values()) and proof['journal_empty']
            and proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match']
            and not proof['device_writes'] and proof['root_header_sha256'] == restored['root_header_sha256']
            and proof['install_plan_sha256'] == load(marker.BASE / 'trial-plan.json')['install_plan_sha256'],
            '0423 independently restored baseline differs')
    if not fresh:
        return restored
    current = load(BASE / 'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files']) == 31
            and all(current[key] == restored[key] for key in
                    ('root_header_sha256','combined_log_bytes','files','directories')),
            'fresh recovery differs from the 0423 readback')
    return current


def package():
    phase.batch_tools.budget(BASE / 'live-batch-admission.json', phase.LIVE_BATCH)
    kernel = phase.native()
    parent = load(P419 / 'trial-plan.json')
    require(kernel['identity'] == parent['kernel_identity'], '0419 kernel identity differs')
    source_sha = sha(SOURCE)
    binary = SB.parent / 'libGauguinEAGL.dylib'
    binary.parent.mkdir()
    subprocess.run(['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0',
        '-O2','-Wall','-Wextra','-Werror','-fobjc-arc','-dynamiclib','-framework','UIKit',
        '-framework','Foundation','-Wl,-install_name,/usr/local/lib/gauguin/libGauguinEAGL.dylib',
        str(SOURCE),'-o',str(binary)],check=True)
    subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(binary)],check=True)
    subprocess.run(['codesign','--verify','--strict',str(binary)],check=True)
    require(sha(SOURCE) == source_sha,'observer source changed during compilation')
    phase.save(SB,dict(binary=str(binary),binary_sha256=sha(binary),bytes=binary.stat().st_size,
                       input_pins={str(SOURCE):source_sha},observes_text_length_only=True))
    image = marker.repack(BASE,parent,SUBSTITUTIONS)
    require(image['command'] == ' '.join(SUBSTITUTIONS.get(word,word) for word in parent['boot_command'].split()),
            'physical input arguments differ')
    phase.save(IMAGE,image)
    for kind in ('core','c4','edr'):
        rel = f'{kind}-native/result.json'
        (BASE / rel).parent.mkdir()
        shutil.copyfile(P419 / rel,BASE / rel)
    return {key:image[key] for key in ('image_sha256','image_bytes','substitutions')}


def capture():
    phase.batch_tools.budget(BASE / 'live-batch-admission.json', phase.LIVE_BATCH)
    result = phase.capture_tools.capture_from(BASE,marker.BASE,TRIAL,baseline)
    phase.prior.prior.capture_resources(current=baseline(),resources=RESOURCES)
    return result


def delta():
    return phase.shared.stage.delta(BASE,P419,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST / 'restored-capture/result.json',core_logical=load(BASE / 'core-native/result.json')['bytes'],
        c4_receipt=BASE / 'c4-native/result.json',sb_receipt=SB)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE / 'restore-model',trial=TRIAL,resources=RESOURCES)
    return dict(checks=len(result['checks']),failure_points=result['all_restore_partial_write_points'])


def expected_plan():
    current, kernel = baseline(), phase.native()
    parent_path = P419 / 'trial-plan.json'
    install_path = BASE / 'slot-delta/install-plan.json'
    parent,image,install,sb = map(load,(parent_path,IMAGE,install_path,SB))
    header,size = current['root_header_sha256'],current['combined_log_bytes']
    require(image['identical_kernel'] and image['substitutions'] == SUBSTITUTIONS
            and sha(image['image']) == image['image_sha256'] and parent['kernel_identity'] == kernel['identity']
            and image['command'] == ' '.join(SUBSTITUTIONS.get(word,word) for word in parent['boot_command'].split())
            and install['trial'] == TRIAL and install['root_header_sha256'] == header and install['changed_ranges'] == 12
            and parent['EDR_helper_sha256'] == install['admission_sha256']
            and parent['owned_core_sha256'] == install['core_sha256'] and parent['C4_sha256'] == install['C4_sha256']
            and sha(BASE / 'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256'],
            'physical input candidate or bounded effects differ')
    return dict(parent,state='prepared-0419-physical-Spotlight-60Hz',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        new_kernel_builds=0,boot_command=image['command'],SB_sha256=sb['binary_sha256'],
        user_input='physical-Novatek-touch-only',scripted_strokes=0,scripted_reports=0,wake_button_pairs_max=0,
        frame_capture=dict(parent['frame_capture'],records=20480,starts_at='first on-display physical contact',
            maximum_total_display_register_writes=2058,motion_wire=None,
            presentation_policy=dict(parent['frame_capture']['presentation_policy'],maximum_private_full_copy_attempts=1024)),
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
                         sizes={name:current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
                         previous_verified_suffix_bytes=size-load(marker.BASE / 'trial-plan.json')['log_capture']['measured_baseline_bytes']),
        probe=dict(workload='physical Home Screen pull-down and warm keyboard taps',max_observer_rows=256,
                   native_input_observation='UIKit delivery only',optical_recording=False),
        optimization='Use the original 0419 render path and its physical input profile.',
        performance_comparison='Measure each complete scanout second and bound input-to-output separately.')


def criteria(plan):
    phase.batch_tools.budget(BASE / 'live-batch-admission.json',phase.LIVE_BATCH)
    old,new = (load(path / 'slot-delta/install-plan.json') for path in (P419,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'eagl'} and load(SB)['input_pins'][str(SOURCE)] == sha(SOURCE),'observer slot or source differs')
    proof = load(BASE / 'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12 and len(proof['checks']) == 49
            and proof['all_restore_partial_write_points'] == 17,'physical input restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P419,plan['root_header_sha256'],plan)


def storage(plan):
    return dict(marker.storage(plan),state='bounded-0419-physical-Spotlight-runtime')


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK / name for name in tracked),DOC,KERNEL,IMAGE,SOURCE,SB,Path(load(SB)['binary']),
             Path(load(P419 / 'trial-plan.json')['observer_helper']),MAIN / 'tools/storage-budget.py',
             BASE / 'current-root-capture/result.json',BASE / 'live-batch-admission.json',P419 / 'trial-plan.json',
             marker.BASE / 'trial-plan.json',marker.BASE / 'capture-profile.json',
             *(LAST / name for name in ('result.json','independent-restore.json','restored-capture/result.json'))]
    return phase.capture_tools.scoped_pins(BASE,files,KERNEL,IMAGE)


def freeze():
    return phase.shared.freeze(base=BASE,prior=marker.BASE,expected=expected_plan,validate=criteria,
                               storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return phase.shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                               storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=actions)
    print(actions[parser.parse_args().step]())
