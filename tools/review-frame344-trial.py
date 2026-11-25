#!/usr/bin/env python3
"""Re-read the signed candidate, six ranges and exact frozen device effects."""

import json
from pathlib import Path
import struct

from core342_install import BLOCK, EXPECTED
from core342_slots import data_extents
from frame344_scope import BASE, DOC, HEADER, P343, RESERVE, WORK
from frame344_scope import expected_plan, load, require, sha


def check_effect_bounds(base, prior, header, plan):
    delta_path = base/'slot-delta/install-plan.json'
    delta = load(delta_path)
    capture = load(base/'slot-capture/result.json')
    require(plan['install_plan_sha256']==sha(delta_path) and
            delta['root_header_sha256']==capture['root_header_sha256']==plan['root_header_sha256']==header and
            set(delta['rows'])==set(EXPECTED) and delta['no_new_allocation'] and
            not (delta['journal_home_replay_allowed'] or delta['alternate_header_write_allowed']),
            'install or restore scope differs')
    groups = {}
    data_bytes = 0
    data_ranges = 0
    signatures = {row['name']:row for row in load(base/'restore-model/independent-candidate-signatures.json')['checks']}
    original = load(prior/'slot-delta/install-plan.json')
    for name, path in EXPECTED.items():
        row = delta['rows'][name]
        fresh = capture['files'][path]
        candidate = base/'slot-delta'/(name+'-new-data.bin')
        expected = {'admission':plan['EDR_helper_sha256'], 'core':plan['owned_core_sha256'],
                    'eagl':plan.get('SB_sha256',original['rows']['eagl']['new_file_sha256']),
                    'c4':plan.get('C4_sha256',original['rows']['c4']['new_file_sha256'])}.get(
            name,original['rows'][name]['new_file_sha256'])
        require(row['path']==path and fresh['sha256']==row['old_file_sha256'] and
                data_extents(row)==data_extents(dict(fresh,path=path)) and
                row['new_file_sha256']==expected and sha(candidate)==row['new_data_sha256'] and
                candidate.stat().st_size==row['data_blocks']*BLOCK, 'wrong slot contents or range')
        if name in ('admission','core','eagl','c4'):
            require(signatures[name]['signature_verified'] and signatures[name]['sha256']==expected,
                    'independent HFS extraction signature differs')
        catalog = (base/'slot-capture'/(name+'-old-catalog.bin')).read_bytes()
        new_catalog = (base/'slot-delta'/(name+'-new-catalog.bin')).read_bytes()
        require(len(catalog)==len(new_catalog)==BLOCK, 'wrong catalog range length')
        old_bytes, target_bytes, fields = groups.setdefault(row['catalog_block'], [catalog,new_catalog,{}])
        require(old_bytes==catalog and target_bytes==new_catalog and row['catalog_offset'] not in fields,
                'catalog group differs')
        fields[row['catalog_offset']] = row['new_logical']
        data_bytes += candidate.stat().st_size
        data_ranges += len(data_extents(row))
    for before, after, fields in groups.values():
        rebuilt = bytearray(before)
        for field, length in fields.items():
            struct.pack_into('>Q',rebuilt,field,length)
        require(rebuilt==after and before!=after,'unrelated catalog bytes changed')
    install = data_bytes + BLOCK*len(groups)
    restore = plan['maximum_restore_userdata_bytes']
    require(delta['changed_ranges']==data_ranges+len(groups) and
            (install,restore,plan['restore_max_ranges'])==(10301440,10330112,18) and
            plan['normal_userdata_write_bytes_max']==install+restore==20631552 and
            plan['maximum_userdata_write_bytes']==install+2*restore==30961664 and
            plan['misc_write_bytes']==13 and plan['maximum_host_misc_write_bytes']==26 and
            (plan['temporary_boots'],plan['restore_forward_attempts'],plan['boot_retries'],
             plan['failed_restore_retry_limit'],plan['maximum_fastboot_reboot_recovery_fallbacks'])==(1,1,0,0,1),
            'device bounds differ')


def review():
    ready_path, plan_path = BASE/'ready.json', BASE/'trial-plan.json'
    ready, plan = load(ready_path), load(plan_path)
    require(not (BASE/'approval.json').exists() and not (BASE/'execution').exists(),
            'review must precede any 0344 authorization or observation')
    require(ready['state']=='ready-frame344-one-shot' and ready['trial_plan_sha256']==sha(plan_path) and
            ready['install_plan_sha256']==plan['install_plan_sha256'] and
            ready['pin_count']==len(ready['input_pins']) and plan==expected_plan(), 'frozen scope differs')
    old = load(P343/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','kernel_identity','kernel_banner',
               'boot_command','EDR_helper_sha256','owned_core_sha256','unchanged_0342_Core_and_frontend',
               'root_header_sha256','install_plan_sha256','misc_before_sha256','parent_trial_plan_sha256',
               'storage_reserve_bytes','hash_only_static_files','additional_threads','optimization',
               'frame_capture','optical_FPS'}
    require({key for key in set(old)|set(plan) if old.get(key)!=plan.get(key)} <= allowed,
            '0344 changes a device action outside the reviewed scope')
    require(plan['scripted_strokes']==13 and plan['scripted_reports']==442 and
            plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            'script or sampling bound changed')
    frame = plan['frame_capture']
    require(frame['modesets']==0 and frame['maximum_volatile_crc_register_writes']==4 and
            frame['volatile_crc_register_address']=='0x0ae6b980' and frame['target_refresh_hz']==60,
            'CRC or mode effects changed')

    check_effect_bounds(BASE, P343, HEADER, plan)

    model = load(BASE/'restore-model/result.json')
    tests = load(BASE/'frame-host/result.json')
    require(model['all_model_IO_writes_memory_only'] and len(model['checks'])==47 and
            model['all_restore_partial_write_points']==17 and
            model['maximum_actual_model_restore_bytes']<=restore and tests['decoder_tests']==5 and
            'frame-analysis-requires-independent-restore' in tests['control_flow_checks'] and
            'actual-executor-control-hash-prefix-mismatch' in tests['control_flow_checks'], 'host review is incomplete')
    budget = load(BASE/'storage-runtime-admission.json')
    storage = load(BASE/'storage-bound-344.json')
    require(budget['admitted'] and storage['worst_case_bytes']==sum(storage['components'].values()) <= RESERVE and
            budget['current_accounted_bytes']+RESERVE <= budget['limit_bytes'], 'budget differs')
    for name, digest in ready['input_pins'].items():
        require(sha(name)==digest,'pinned file changed: '+name)
    result = dict(state='reviewed-frame344-one-shot', ready_sha256=sha(ready_path),
                  trial_plan_sha256=sha(plan_path), image_sha256=plan['image_sha256'],
                  install_plan_sha256=sha(delta_path), restore_precedes_analysis=True,
                  no_device_mutation_during_preparation=True, pin_count=ready['pin_count'],
                  independent_virtual_hfs_signatures=4, physical_FPS_qualified=False,
                  input_pins={str(path):sha(path) for path in (Path(__file__),DOC,WORK/'tools/run-frame344-trial.py')})
    with (BASE/'final-review.json').open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    return {key:value for key,value in result.items() if key!='input_pins'}


if __name__ == '__main__':
    print(json.dumps(review(),indent=2))
