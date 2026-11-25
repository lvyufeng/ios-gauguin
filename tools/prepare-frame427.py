#!/usr/bin/env python3
"""Freeze a larger compositor budget against the exact passive 0419 control."""

import argparse
from importlib import import_module
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


gpu = import_module('prepare-frame425')
search = import_module('prepare-frame426')
phase = gpu.phase
TRIAL = '0427'
BASE = WORK/'research/tmp/frame-427'
IMAGE = BASE/'frame427-image.json'
HOST = BASE/'passive-baseline-phase-replay.json'
DOC = WORK/'docs/gauguin-frame-427-marker-work-phase-20261125.md'
LAST = search.BASE/'execution'
RESOURCES = BASE/'metadata-snapshot/model-resources/result.json'
CONTROL_US,WORK_US = 7200,12200
FLAGS = (*[f for f in gpu.FLAGS if not f.startswith('allow_0425')],
         'allow_0427_one_bounded_0419_marker_work_budget_trial')
SUCCESS = '0427-marker-work-budget-compared-root-restored'


def baseline(*, fresh=True):
    end,proof,restored = (load(LAST/name) for name in
                            ('result.json','independent-restore.json','restored-capture/result.json'))
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated']
            and proof['misc_original_4096_bytes_match'] and not proof['device_writes']
            and proof['root_header_sha256'] == restored['root_header_sha256']
            and proof['install_plan_sha256'] == load(search.BASE/'trial-plan.json')['install_plan_sha256'],
            '0426 independently restored baseline differs')
    if not fresh:
        return restored
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and all(current[key] == restored[key] for key in
                    ('root_header_sha256','combined_log_bytes','files','directories')),
            '0427 fresh recovery differs from the 0426 readback')
    return current


def package():
    require(load(gpu.BASE/'total-batch-admission.json')['admitted'],'work comparison batch was not admitted')
    host = load(HOST)
    receipt, = (r for r in host['replay'] if r['work_us'] == WORK_US and
                    r['delay_ticks'] == host['max_observed_delay_ticks'] + 19200)
    require(host['kernel_log_sha256'] == sha(gpu.BASE/'execution/kernel.log') and
            receipt['eligible'] == receipt['on_time'] > 2600 and not receipt['invalid'],
            'work allowance was not replayed on the measured hardware edges')
    parent = load(gpu.BASE/'trial-plan.json')
    require(parent['kernel_identity'] == gpu.build.native()['identity'],'phase donor kernel differs')
    image = gpu.marker.repack(BASE,parent,{f'sweet_ca_work_us={CONTROL_US}':f'sweet_ca_work_us={WORK_US}'})
    phase.save(IMAGE,image)
    for kind in ('core','c4','edr'):
        path = f'{kind}-native/result.json'
        (BASE/path).parent.mkdir()
        shutil.copyfile(gpu.BASE/path,BASE/path)
    return {key:image[key] for key in ('image_sha256','image_bytes','substitutions')}


def capture():
    result = phase.capture_tools.capture_from(BASE,search.BASE,TRIAL,baseline)
    phase.prior.prior.capture_resources(current=baseline(),resources=RESOURCES)
    return result


def delta():
    return phase.shared.stage.delta(BASE,gpu.BASE,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=load(BASE/'core-native/result.json')['bytes'],
        c4_receipt=BASE/'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL,resources=RESOURCES)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    current = baseline()
    parent_path = gpu.BASE/'trial-plan.json'
    install_path = BASE/'slot-delta/install-plan.json'
    parent,image,install = map(load,(parent_path,IMAGE,install_path))
    header,size = current['root_header_sha256'],current['combined_log_bytes']
    require(image['identical_kernel'] and sha(image['image']) == image['image_sha256']
            and image['command'] == parent['boot_command'].replace(f'sweet_ca_work_us={CONTROL_US}',f'sweet_ca_work_us={WORK_US}')
            and install['trial'] == TRIAL and install['root_header_sha256'] == header and install['changed_ranges'] == 12
            and sha(BASE/'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256'],
            'marker profile or reversible device effects differ')
    return dict(parent,state='prepared-frame427-marker-work-budget',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        new_kernel_builds=0,boot_command=image['command'],
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
                         sizes={name:current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
                         previous_verified_suffix_bytes=size-load(search.BASE/'trial-plan.json')['log_capture']['measured_baseline_bytes']),
        work_phase=dict(control_us=CONTROL_US,active_us=WORK_US,same_kernel=True,same_marker=True),
        optimization='Advance each eligible compositor notice by 5 ms and retain the original flip deadline.',
        performance_comparison='Compare the same marker CRC cadence and exact native-submit cutoff cases.')


def criteria(plan):
    old,new = (load(path/'slot-delta/install-plan.json') for path in (gpu.BASE,BASE))
    require({name:row['new_file_sha256'] for name,row in old['rows'].items()}
            == {name:row['new_file_sha256'] for name,row in new['rows'].items()},'signed userspace changed from 0425')
    proof = load(BASE/'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12
            and len(proof['checks']) == 49 and proof['all_restore_partial_write_points'] == 17,
            'work margin restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,gpu.BASE,plan['root_header_sha256'],plan)


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK/name for name in tracked),DOC,gpu.KERNEL,IMAGE,HOST,gpu.SB,Path(load(gpu.SB)['binary']),
             Path(load(gpu.BASE/'trial-plan.json')['observer_helper']),MAIN/'tools/storage-budget.py',
             gpu.BASE/'total-batch-admission.json',BASE/'current-root-capture/result.json',
             gpu.BASE/'trial-plan.json',gpu.BASE/'execution/marker-output.json',
             gpu.BASE/'execution/passive-completion.json',search.BASE/'trial-plan.json',search.BASE/'capture-profile.json',
             *(LAST/name for name in ('result.json','independent-restore.json','restored-capture/result.json'))]
    return phase.capture_tools.scoped_pins(BASE,files,gpu.KERNEL,IMAGE)


def freeze():
    return phase.shared.freeze(base=BASE,prior=search.BASE,expected=expected_plan,validate=criteria,
                               storage_bound=gpu.storage,pin_inputs=pins,reserve=gpu.RESERVE)


def review():
    return phase.shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                               storage_bound=gpu.storage,preparer=Path(__file__),reserve=gpu.RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=actions)
    print(actions[parser.parse_args().step]())
