#!/usr/bin/env python3
"""Freeze the qualified 0342 sources, exact image and bounded recovery scope."""
import copy
import importlib.util
import json
from pathlib import Path
from core342_scope import MAIN,WORK,BASE,PRIOR,PARENT,HEADER,CORE,C4,EDR,IMAGE,IDENTITY,expected_plan,load,sha


def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')


def runtime_bound(capture):
    logical=sum(capture.BASE.FILE_LIMITS.get(p,1048576) for p in capture.BASE.PATHS)
    assert logical==190347824 and len(capture.BASE.PATHS)==31 and capture.RESULT_MAX==1048576
    parts=dict(three_full_captures=3*(logical+capture.RESULT_MAX),
        four_allocated_log_tails=(48+64+8+8)*1048576,kernel_ring_raw_and_decoded=16781312,
        observer_stdout_stderr=12587008,one_restore_preimage_and_target_set=2*10330112,
        eight_executor_receipts=8*2*1048576,other_analysis_metadata=32*1048576,
        lifecycle_analysis=8*1048576,identity_analysis=8*1048576,core_analysis=64*1048576,
        backlog_analysis=8*1048576,stage_analysis=2*1048576,BO_analysis=4*1048576,
        surface_submit_collection_analysis=3*131072,map_native_retry_analysis=3*65536,
        progress_and_restore_recipe=1572864,kernel_IO_analysis=32*1048576,
        kernel_IO_identity_analysis=8*1048576,kernel_IO_backlog_analysis=8*1048576)
    total=sum(parts.values());assert total==959827600<1000000000
    return dict(state='bounded0342-complete-runtime-batch',components=parts,worst_case_bytes=total,
        reserve_bytes=1000000000,full_captures=3,capture_logical_files_max_bytes=logical,
        per_capture_metadata_max_bytes=capture.RESULT_MAX,per_capture_max_bytes=logical+capture.RESULT_MAX,
        limits=dict(backboard=64*1048576,springboard=48*1048576),
        before_after_SB_aliases_allocate_no_extra_copy=True,fixed342_image_not_copied_during_trial=True)


def recipe_storage_bound():
    recipe=copy.deepcopy(load(BASE/'restore-model-v3/all-four-MachO-trims.json')['recipe'])
    recipe['journal']['home_block_sha256']={str(1000000+i):'f'*64 for i in range(16384)}
    recipe['journal']['chunks']=[dict(offset=8388608,sequence=4294967295,entries=5887,bytes=8388608,flags=3) for _ in range(89)]
    tails=fields=0
    for row in load(BASE/'slot-delta/install-plan.json')['rows'].values():
        minimum=(row['new_logical']+4095)//4096;n=row['data_blocks']-minimum;tails+=n
        if n:fields+=((row['data_block']+minimum)%8+n+7)//8
    assert tails==233 and fields<=131
    for row in recipe['ranges']:
        if row['kind']=='bitmap':row['fields']=[dict(offset=4095,mask=255) for _ in range(131)]
    recipe['attribute_record_types']={str(k):4294967295 for k in (0x10,0x20,0x30)}
    length=len((json.dumps(recipe,indent=2)+'\n').encode());assert length+65536<=1572864
    return dict(state='conservative0342-journal-recipe-JSON-bound',journal_bytes=8388608,
        maximum_home_hashes=16384,maximum_decimal_block_digits=7,overestimated_chunks=89,
        maximum_all_original_trim_tails=tails,maximum_total_bitmap_byte_fields=fields,
        inflated_fields_per_bitmap_page=131,inflated_serialized_recipe_bytes=length,
        progress_and_extra_fields_bytes=65536,reserved_bytes=1572864,device_writes=0)


def main():
    for name in ('trial-plan.json','ready.json','approval.json','execution','final-review.json',
        'expected-baseline.json','capture-profile.json','storage-bound.json','storage-recipe-bound.json'):
        assert not (BASE/name).exists(),name
    parent=load(PARENT/'ready.json');assert parent['pin_count']==24906
    pins=dict(parent['input_pins'])
    def pin(path,digest=None):
        p=str(Path(path).resolve());h=digest or sha(p)
        assert p not in pins or pins[p]==h,p;pins[p]=h
    def receipt(path,state=None):
        value=load(path);pin(path)
        if state is not None:assert value['state']==state,(str(path),value['state'])
        for p,h in value.get('input_pins',{}).items():pin(p,h['sha256'] if isinstance(h,dict) else h)
        return value
    pin(PARENT/'ready.json');pin(PARENT/'trial-plan.json')
    prior=receipt(PARENT/'execution/result.json','CR341-lossless-wait-execution-observed-root-restored')
    proof=receipt(PARENT/'execution/independent-restore.json')
    assert prior['restored'] and prior['independent_restore_verified'] and proof['root_header_sha256']==HEADER
    assert proof['misc_original_4096_bytes_match'] and proof['journal_empty']
    prepared=receipt(BASE/'prepared-v3/result.json','prepared0342-user-IO-identity-and-program-allocation-stages')
    assert prepared['job_shape_unchanged'] and prepared['original_GPU_ownership_captures_preserved']
    assert prepared['new_GPU_calls']==prepared['new_threads']==prepared['new_CPU_jobs']==0
    assert prepared['GPU_cache_slots']==32 and prepared['GPU_cache_maximum_bytes']==16777216
    host=receipt(BASE/'core-host-v2/result.json','0342-real-core-ownership-program-slab-diagnostics-passed')
    assert host['inputs_unchanged'] and (host['ownership_scenarios_per_variant'],host['inherited_async_scenarios'],host['inherited_profiler_scenarios'],host['new_State_lifetime_scenarios'],host['new_program_slab_scenarios'])==(23,11,10,2,4)
    clock=receipt(BASE/'clock-host-v1/result.json');assert clock['scenarios']==7 and clock['inputs_unchanged'] and clock['actual_production_IO_wrapper_tested']
    alloc=receipt(BASE/'allocation-host-v3/result.json');assert alloc['scenarios']==4 and alloc['inputs_unchanged']
    receipt(BASE/'phase-host-v1/result.json')
    native=receipt(BASE/'native-v2/result.json','0342-native-core-baseline341-exact-candidate-signed')
    assert native['inputs_unchanged'] and native['baseline_signed_bytes_identical'] and native['all_five_baseline_objects_identical']
    assert native['seven_other_objects_reused_without_copy'] and native['fits_existing_allocation']
    assert native['all_code_data_section_payloads_addresses_offsets_unchanged_by_strip'] and native['load_commands_unchanged']
    assert native['products']['candidate']['sha256']==CORE and native['only_new_import_pthread_threadid_np']
    assert not any(native[k] for k in ('exports_added','exports_removed','imports_removed'))
    front=receipt(BASE/'frontend-native-v2/result.json','0342-frontend-baseline-reproduced-candidate-signed')
    assert front['inputs_unchanged'] and front['baseline_exact_0341_signed_bytes'] and front['resources_unchanged']
    assert not front['added_imports'] and not front['removed_imports'] and front['products']['candidate']['sha256']==C4
    objc=receipt(BASE/'frontend-host-v2/result.json');assert objc['scenarios']==5 and objc['inputs_unchanged']
    abi=receipt(BASE/'abi-v1/result.json');assert abi['checked_imports']==355 and not abi['missing_imports']
    assert abi['new_thread_ID_import_resolved']['symbol']=='_pthread_threadid_np' and abi['optional_hooks_remain_disabled']
    kernel=receipt(BASE/'kernel-prepared-v8/result.json');assert kernel['identity']==IDENTITY and kernel['inputs_unchanged']
    driver=receipt(BASE/'kernel-host-v8/result.json');assert driver['paired_request_observations']==6900 and driver['parent_candidate_observations_identical']
    phase=receipt(BASE/'kernel-phase-host-v5/result.json');assert phase['scenarios']==9 and phase['inputs_unchanged']
    knative=receipt(BASE/'kernel-native-v4/result.json');assert knative['baseline_object_bytes_identical'] and knative['inputs_unchanged']
    assert knative['new_undefined_symbols']==['_sweet_log_append','_thread_get_runtime_self']
    link=receipt(BASE/'kernel-link-v4/build-manifest.json');assert link['baseline_raw_and_stripped_equal_except_LC_UUID'] and link['actual_implementation_object_replacements']==1
    image=receipt(BASE/'io342-v4-image.json');review=receipt(BASE/'io342-v4-review.json')
    assert image['image_sha256']==review['image_sha256']==IMAGE and image['build_identity']==IDENTITY and image['inputs_unchanged']
    assert review['undefined_symbol_count']==0 and review['low_pas_request_checked'] and not image['command_changes_from_0337']
    edrhost=receipt(BASE/'edr-host-v3/result.json');assert edrhost['checks']==2144
    edr=receipt(BASE/'edr-native-v3/result.json');assert edr['inputs_unchanged'] and edr['products']['candidate']['sha256']==EDR
    assert edr['kernel_identity']==IDENTITY and edr['baseline_reproduction']['canonical_signed_bytes_identical']
    decoder=receipt(BASE/'log-tests-v4.json');assert decoder['tests']==10 and decoder['worst_case_all_integer_widths_formatter_bytes']==6918
    restore=receipt(BASE/'restore-model-v3/result.json');assert len(restore['checks'])==47 and restore['all_restore_partial_write_points']==17
    signatures=receipt(BASE/'restore-model-v3/independent-candidate-signatures.json');assert len(signatures['checks'])==4 and all(s['signature_verified'] for s in signatures['checks'])
    pipeline=receipt(BASE/'pipeline-v4/result.json');assert len(pipeline['checks'])==37 and not pipeline['saved_analysis_fixture']['real0342_performance_evidence']
    baseline=receipt(BASE/'current-root-capture/result.json');capture=receipt(BASE/'slot-capture/result.json')
    assert baseline['root_header_sha256']==capture['root_header_sha256']==HEADER and len(baseline['files'])==31
    snapshot=receipt(BASE/'metadata-snapshot/result.json');assert snapshot['root_header_sha256']==HEADER and 0<snapshot['compressed_bytes']<=30*1048576
    delta=receipt(BASE/'slot-delta/install-plan.json');assert delta['core_sha256']==CORE and delta['c4_sha256']==C4 and delta['admission_sha256']==EDR
    assert delta['install_write_bytes']==10301440 and delta['restore_max_write_bytes']==10330112 and delta['restore_max_ranges']==18
    batch=receipt(BASE/'storage-whole-batch-admission.json');budget=receipt(BASE/'storage-runtime-admission.json')
    assert batch['admitted'] and batch['planned_batch_bytes']==2400000000
    assert budget['admitted'] and budget['planned_batch_bytes']==1000000000
    assert budget['current_accounted_bytes']+1000000000<=500000000000
    assert budget['current_accounted_bytes']-batch['current_accounted_bytes']+1000000000<=2400000000
    scout=MAIN/'research/tmp/io-path342-scout';retired=receipt(scout/'archived-build-logs-v1/retirement-plan.json')
    assert sha(scout/'archived-build-logs-v1/retirement-plan.json')=='4e7240f6fca3cfaf0f182aef217510adcb79d3c54e109ccfa28fa5e4dfe53ffc'
    receipt(scout/'archived-build-logs-v1/result.json');pin(scout/'archive_build_logs342.py')
    pin(scout/'protected-reference-closure.json');pin(scout/'archive-protected-closure.json')
    for path in (scout/'archived-build-logs-v1').rglob('*'):
        if path.is_file():pin(path)
    for leaf in ('storage-whole-batch-components.json','current-root-profile.json','kernel-identity-v3.json','retained-prototype-move.json'):pin(BASE/leaf)
    selected=('prepared-v3','core-host-v2','clock-host-v1','phase-host-v1','allocation-host-v3','native-v2',
        'frontend-native-v2','frontend-host-v2','abi-v1','kernel-prepared-v8','kernel-host-v8','kernel-phase-host-v5',
        'kernel-native-v4','kernel-link-v4','edr-host-v3','edr-native-v3','log-tests-v4',
        'current-root-capture','slot-capture','slot-delta','metadata-snapshot','restore-model-v3','pipeline-v4')
    for folder in selected:
        for p in (BASE/folder).rglob('*'):
            if p.is_file():pin(p)
    for product in (native,front,edr):
        for v in product['products'].values():pin(v['binary'],v['sha256'])
    for folder in (PARENT,MAIN/'research/tmp/gauguin-draw-submit-worktree-20261117/research/tmp/draw-submit-340'):
        if folder.exists():
            for p in folder.rglob('*'):
                if p.is_file() and '__pycache__' not in p.parts:pin(p)
    for folder in ('tools','tests','graphics/gauguin-io-path'):
        for p in (WORK/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.py','.cpp','.c','.m','.mm','.h','.hpp','.inc'):pin(p)
    for p in (WORK/'docs/gauguin-io-path-342-trial-20261117.md',WORK/'docs/gauguin-io-path342-design-20261117.md',
        WORK/'xnu/patches/0250-gauguin-IO-CPU-phase-trace.patch',WORK/'xnu/patches/series',MAIN/'tools/storage-budget.py'):pin(p)
    plan=expected_plan();pin(plan['image'],IMAGE);pin(plan['observer_helper'])
    spec=importlib.util.spec_from_file_location('cap342_bound',WORK/'tools/capture-core342-root.py')
    caps=importlib.util.module_from_spec(spec);spec.loader.exec_module(caps)
    bound=runtime_bound(caps);recipe=recipe_storage_bound()
    profile=load(BASE/'current-root-profile.json');profile.update(out=str((BASE/'execution/fresh-before').relative_to(MAIN)))
    for name,value in (('expected-baseline.json',baseline),('capture-profile.json',profile),('trial-plan.json',plan),('storage-bound.json',bound),('storage-recipe-bound.json',recipe)):
        save(BASE/name,value);pin(BASE/name)
    for p,h in pins.items():assert sha(p)==h,p
    ready=dict(state='ready-core342-one-shot',trial_plan_sha256=sha(BASE/'trial-plan.json'),
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),image_sha256=IMAGE,root_header_sha256=HEADER,
        parent_341_pins_preserved=24906,pin_count=len(pins),input_pins=dict(sorted(pins.items())),
        selected_folders=selected,approval_pending=True,device_writes=0,boot_attempts=0,new_kernel_builds=1)
    save(BASE/'ready.json',ready);print(json.dumps({k:v for k,v in ready.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
