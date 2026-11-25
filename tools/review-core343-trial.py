#!/usr/bin/env python3
"""Read-only, independent review of the frozen 0343 operation bounds."""

import json
from pathlib import Path

from core343_scope import BASE, DOC, EDR, HEADER, IMAGE, P342, STORAGE_RESERVE, WORK, load, require, sha
from core342_install import EXPECTED


def review():
    require(not (BASE/'execution').exists() and not (BASE/'approval.json').exists(),
            'review must precede approval and execution')
    ready_path, plan_path = BASE/'ready.json', BASE/'trial-plan.json'
    ready, plan = load(ready_path), load(plan_path)
    reference = load(P342/'trial-plan.json')
    require(ready['state'] == 'ready-core343-one-shot' and ready['pin_count'] == len(ready['input_pins'])
            and ready['trial_plan_sha256'] == sha(plan_path)
            and ready['parent_342_pins_preserved'] == 28885
            and (ready['device_writes'], ready['boot_attempts']) == (0, 0), 'ready receipt differs')
    permitted = {'state', 'trial', 'image', 'image_bytes', 'image_sha256', 'kernel_identity', 'kernel_banner',
                 'EDR_helper_sha256', 'root_header_sha256', 'install_plan_sha256', 'storage_reserve_bytes',
                 'diagnostic_only', 'parent_trial_plan_sha256', 'strict_frozen_baseline',
                 'unchanged_0342_swipe_script', 'unchanged_0342_Core_and_frontend', 'optimization',
                 'ui_wire_kinds', 'performance_comparison', 'optical_FPS'}
    require({k for k in set(reference)|set(plan) if reference.get(k) != plan.get(k)} <= permitted
            and plan['scripted_strokes'] == 13 and plan['scripted_reports'] == 442
            and plan['main_thread_sampling']['max_samples'] == 64
            and plan['process_sampling']['max_register_samples'] == 1024
            and (plan['boot_retries'], plan['failed_restore_retry_limit'], plan['restore_forward_attempts'],
                 plan['maximum_fastboot_reboot_recovery_fallbacks']) == (0, 0, 1, 1),
            'workload, capture, or device effects changed')
    require(plan['root_header_sha256'] == HEADER and plan['image_sha256'] == IMAGE == sha(plan['image'])
            and plan['image_bytes'] == Path(plan['image']).stat().st_size == 22183936
            and plan['EDR_helper_sha256'] == EDR and plan['misc_write_bytes'] == 13
            and plan['maximum_host_misc_write_bytes'] == 26
            and plan['temporary_boots'] == 1 and set(plan['changed_root_files']) == set(EXPECTED.values()),
            'wrong image, misc marker or root-file scope')
    delta_path = BASE/'slot-delta/install-plan.json'
    delta = load(delta_path)
    capture_path = BASE/'slot-capture/result.json'
    capture = load(capture_path)
    original = load(P342/'slot-delta/install-plan.json')
    require(sha(delta_path) == ready['install_plan_sha256'] == plan['install_plan_sha256']
            and sha(capture_path) == delta['capture_sha256']
            and set(delta['rows']) == set(EXPECTED) and delta['no_new_allocation']
            and not any(delta[k] for k in ('journal_home_replay_allowed', 'alternate_header_write_allowed')),
            'delta/install transaction differs')
    prefixes = {}
    for name, path in EXPECTED.items():
        row = delta['rows'][name]
        data = (delta_path.parent/(name+'-new-data.bin')).read_bytes()
        install = original['rows'][name]
        require(row['path'] == path and row['old_file_sha256'] == capture['files'][path]['sha256']
                and row['new_logical'] == install['new_logical']
                and sha(delta_path.parent/(name+'-new-data.bin')) == row['new_data_sha256']
                and len(data) == row['data_blocks']*4096,
                'six-file allocation or staged data changed')
        require(row['new_file_sha256'] == (EDR if name == 'admission' else install['new_file_sha256']),
                'additional userland semantic changes')
        prefixes[name] = len(data)
    groups = len({row['catalog_block'] for row in delta['rows'].values()})
    install_bytes = sum(prefixes.values())+groups*4096
    restore_cap = plan['maximum_restore_userdata_bytes']
    require((install_bytes, groups, restore_cap, plan['restore_max_ranges']) == (10301440, 5, 10330112, 18)
            and install_bytes == plan['install_userdata_bytes'] == delta['install_write_bytes']
            and plan['maximum_userdata_write_bytes'] == install_bytes+2*restore_cap == 30961664
            and plan['normal_userdata_write_bytes_max'] == install_bytes+restore_cap == 20631552
            and 2*install_bytes <= plan['maximum_userdata_write_bytes'], 'wrong write/writeback limits')
    rollback = load(BASE/'restore-model-343/result.json')
    signed = load(BASE/'restore-model-343/independent-candidate-signatures.json')
    pipeline = load(BASE/'pipeline-343/result.json')
    require(len(rollback['checks']) == 47 and rollback['all_restore_partial_write_points'] == 17
            and rollback['maximum_actual_model_restore_bytes'] <= restore_cap
            and {s['name'] for s in signed['checks']} == {'admission','eagl','c4','core'}
            and all(s['signature_verified'] for s in signed['checks']), 'hardware-shaped restore model incomplete')
    require(len(pipeline['checks']) == 16 and not pipeline['real_optical_capture']
            and 'log-integrity-work-absent-on-failed-restore-or-readback' in pipeline['checks']
            and 'no-timing-or-optical-interpretation-on-incomplete-collection' in pipeline['checks'],
            'executor ordering, optical and comparison host tests incomplete')
    budget = load(BASE/'storage-runtime-admission-343.json')
    bound = load(BASE/'storage-bound-343.json')
    require(budget['admitted'] and plan['storage_reserve_bytes'] == STORAGE_RESERVE == budget['planned_batch_bytes']
            and bound['worst_case_bytes'] == sum(bound['components'].values()) <= STORAGE_RESERVE
            and plan['optical_FPS']['project_artifacts_max_bytes'] <= 8000000
            and budget['current_accounted_bytes'] + STORAGE_RESERVE <= budget['limit_bytes'],
            'complete runtime and optical analysis reserve missing')
    for name, h in ready['input_pins'].items():
        require(sha(name) == h, 'frozen input changed: ' + name)
    review_pins = {str(p):sha(p) for p in (Path(__file__).resolve(), DOC,
                   WORK/'tools/run-core343-trial.py', WORK/'tools/run-core342-trial.py',
                   BASE/'pipeline-343/result.json', BASE/'restore-model-343/result.json')}
    result = dict(state='reviewed-core343-one-shot', ready_sha256=sha(ready_path),
                  trial_plan_sha256=sha(plan_path), install_plan_sha256=sha(delta_path),
                  image_sha256=IMAGE, all_pins_unchanged=True, pin_count=ready['pin_count'],
                  readback_precedes_capture_checks=True, capture_precedes_CPU_queue_comparison=True,
                  optical_capture_protocol_reviewed=True, physical_FPS_qualified=False,
                  device_writes=0, boot_attempts=0, input_pins=review_pins)
    with (BASE/'final-review.json').open('x') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
    return {k:v for k,v in result.items() if k != 'input_pins'}


if __name__ == '__main__':
    print(json.dumps(review(), indent=2))
