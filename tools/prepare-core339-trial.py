#!/usr/bin/env python3
"""Freeze0339 after host/native/ABI/collection/restoration qualification."""
import copy
import importlib.util
import json
from pathlib import Path
from core339_scope import MAIN,WORK,BASE,PRIOR,PARENT,HEADER,CORE,C4,IMAGE,expected_plan,load,sha


def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')


def runtime_bound(capture):
    logical=sum(capture.BASE.FILE_LIMITS.get(p,1048576) for p in capture.BASE.PATHS)
    assert logical==156793392 and len(capture.BASE.PATHS)==31 and capture.RESULT_MAX==1048576
    parts=dict(three_full_captures=3*(logical+capture.RESULT_MAX),
        four_allocated_log_tails=(48+32+8+8)*1048576,
        kernel_ring_raw_and_decoded=16781312,observer_stdout_stderr=12587008,
        one_restore_preimage_and_target_set=2*10330112,
        eight_executor_receipts=8*2*1048576,other_analysis_metadata=32*1048576,
        lifecycle_analysis=8*1048576,identity_analysis=8*1048576,
        core_analysis=32*1048576,backlog_analysis=8*1048576,
        stage_analysis=2*1048576,BO_analysis=4*1048576,
        surface_submit_collection_analysis=3*131072,map_native_retry_analysis=3*65536,
        progress_and_restore_recipe=1572864)
    total=sum(parts.values());assert total==741723792<760000000
    return dict(state='bounded0339-complete-runtime-batch',components=parts,worst_case_bytes=total,
        reserve_bytes=760000000,full_captures=3,capture_logical_files_max_bytes=logical,
        per_capture_metadata_max_bytes=capture.RESULT_MAX,per_capture_max_bytes=logical+capture.RESULT_MAX,
        limits=dict(backboard=32*1048576,springboard=48*1048576),
        before_after_SB_aliases_allocate_no_extra_copy=True,fixed337_image_reused_without_copy=True,new_kernel_builds=0)


def recipe_storage_bound():
    recipe=copy.deepcopy(load(BASE/'restore-model-v1/all-four-MachO-trims.json')['recipe'])
    recipe['journal']['home_block_sha256']={str(1000000+i):'f'*64 for i in range(16384)}
    recipe['journal']['chunks']=[dict(offset=8388608,sequence=4294967295,entries=5887,bytes=8388608,flags=3) for _ in range(89)]
    # All possible trimmed prefix tails are subsets of these original tails.
    plan=load(BASE/'slot-delta/install-plan.json');tails=0;byte_fields=0
    for row in plan['rows'].values():
        minimum=(row['new_logical']+4095)//4096;n=row['data_blocks']-minimum;tails+=n
        if n:byte_fields+=((row['data_block']+minimum)%8+n+7)//8
    assert tails==237 and byte_fields<=131
    for row in recipe['ranges']:
        if row['kind']=='bitmap':row['fields']=[dict(offset=4095,mask=255) for _ in range(131)]
    recipe['attribute_record_types']={str(k):4294967295 for k in (0x10,0x20,0x30)}
    length=len((json.dumps(recipe,indent=2)+'\n').encode());assert length+65536<=1572864
    return dict(state='conservative0339-journal-recipe-JSON-bound',journal_bytes=8388608,
        maximum_home_hashes=16384,maximum_decimal_block_digits=7,overestimated_chunks=89,
        maximum_all_original_trim_tails=tails,maximum_total_bitmap_byte_fields=byte_fields,
        inflated_fields_per_bitmap_page=131,inflated_serialized_recipe_bytes=length,
        progress_and_extra_fields_bytes=65536,reserved_bytes=1572864,device_writes=0)


def main():
    for leaf in ('trial-plan.json','ready.json','approval.json','execution','final-review.json',
        'capture-profile.json','expected-baseline.json','storage-bound.json','storage-recipe-bound.json'):
        assert not (BASE/leaf).exists(),leaf
    parent=load(PARENT/'ready.json');assert parent['pin_count']==19711
    pins=dict(parent['input_pins'])
    def pin(path,digest=None):
        path=str(Path(path).resolve());digest=digest or sha(path)
        assert path not in pins or pins[path]==digest,path
        pins[path]=digest
    def receipt(path):
        value=load(path);pin(path)
        for p,h in value.get('input_pins',{}).items():pin(p,h['sha256'] if isinstance(h,dict) else h)
        return value
    pin(PARENT/'ready.json');receipt(PARENT/'trial-plan.json')
    prior=receipt(PARENT/'execution/result.json');proof=receipt(PARENT/'execution/independent-restore.json')
    assert prior['state']=='CR338-lossless-wait-execution-observed-root-restored' and prior['restored'] and prior['independent_restore_verified']
    assert proof['root_header_sha256']==HEADER and proof['misc_original_4096_bytes_match'] and proof['journal_empty']
    receipt(PARENT/'post-analysis/comparison-summary.json');receipt(PARENT/'critical-path/result.json')
    prepared=receipt(BASE/'prepared-v2/result.json')
    assert prepared['scheduling_and_resource_captures_unchanged'] and prepared['no_new_per_job_allocation']
    assert prepared['new_GPU_calls']==prepared['new_threads']==0 and prepared['diagnostic_only']
    host=receipt(BASE/'core-host-v3/result.json')
    assert host['state']=='0339-real-core-ownership-categories-submit-phases-passed' and host['inputs_unchanged']
    assert (host['ownership_scenarios_per_variant'],host['prior_async_scenarios'],host['new_profiler_scenarios'])==(23,11,10)
    native=receipt(BASE/'native-v4/result.json')
    assert native['state']=='0339-native-core-baseline-reproduced-candidate-signed' and native['inputs_unchanged']
    assert native['baseline_reproduction']['canonical_signed_bytes_identical'] and native['all_other_core_objects_identical']
    assert native['local_symbol_trim']['all_section_payloads_addresses_sizes_and_offsets_identical']
    assert not any(native[k] for k in ('exports_added','exports_removed','imports_added','imports_removed'))
    assert native['load_commands_unchanged'] and native['products']['candidate']['sha256']==CORE and native['fits_existing_allocation']
    front=receipt(BASE/'frontend-native-v1/result.json')
    assert front['state']=='0339-frontend-baseline-reproduced-candidate-signed' and front['inputs_unchanged']
    assert front['products']['candidate']['sha256']==C4 and front['resources_unchanged'] and front['baseline_exact_0338_signed_bytes']
    assert not front['added_imports'] and not front['removed_imports']
    abi=receipt(BASE/'frontend-abi-v1/result.json')
    assert abi['checked_imports']==355 and not abi['missing_imports'] and abi['optional_hooks_remain_disabled']
    objc=receipt(BASE/'frontend-host-v1/result.json')
    assert objc['state']=='0339-production-ObjC-methods-core-FakeGpu-lifetimes-passed' and objc['scenarios']==5 and objc['inputs_unchanged']
    assert objc['actual_completion_can_finish_before_notice_admission'] and all(s['exit']==0 for s in objc['steps'])
    decoder=receipt(BASE/'log-tests-v1.json')
    assert decoder['tests']==10 and decoder['contract_mutations']==34 and decoder['real_production_core_rows_format_checked']==1
    restore=receipt(BASE/'restore-model-v1/result.json')
    assert restore['state']=='0339-live-metadata-install-and-tail-journal-restore-models-passed' and len(restore['checks'])==47
    assert restore['all_restore_partial_write_points']==17 and restore['all_model_IO_writes_memory_only']
    signatures=receipt(BASE/'restore-model-v1/independent-candidate-signatures.json')
    assert len(signatures['checks'])==4 and all(s['signature_verified'] for s in signatures['checks'])
    pipeline=receipt(BASE/'pipeline-v4/result.json')
    assert pipeline['state']=='0339-executor-analysis-collection-order-host-models-passed' and len(pipeline['checks'])==26
    assert pipeline['saved_analysis_fixture']['complete_cb_count']==776 and not pipeline['saved_analysis_fixture']['real0339_performance_evidence']
    baseline=receipt(BASE/'current-root-capture/result.json');capture=receipt(BASE/'slot-capture/result.json')
    assert baseline['root_header_sha256']==capture['root_header_sha256']==HEADER and len(baseline['files'])==31
    spec=importlib.util.spec_from_file_location('fresh339_root_comparison',WORK/'tools/run-sb-cadence-trial.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    legacy.static_compare(load(PARENT/'execution/restored-capture/result.json'),baseline)
    snapshot=receipt(BASE/'metadata-snapshot/result.json')
    assert snapshot['root_header_sha256']==HEADER and snapshot['compressed_bytes']==12972349
    delta=receipt(BASE/'slot-delta/install-plan.json')
    assert delta['state']=='prepared-six-file-core339-delta' and delta['core_sha256']==CORE and delta['c4_sha256']==C4
    assert delta['install_write_bytes']==10301440 and delta['restore_max_write_bytes']==10330112 and delta['restore_max_ranges']==18
    batch=receipt(BASE/'storage-whole-batch-admission.json');budget=receipt(BASE/'storage-runtime-admission.json')
    assert batch['admitted'] and batch['planned_batch_bytes']==1200000000
    assert budget['admitted'] and budget['planned_batch_bytes']==760000000
    assert budget['current_accounted_bytes']+760000000<=500000000000
    assert budget['current_accounted_bytes']-batch['current_accounted_bytes']+760000000<=1200000000
    for leaf in ('storage-whole-batch-components.json','current-root-profile.json'):pin(BASE/leaf)
    for product in (native,front):
        for item in product['products'].values():pin(item['binary'],item['sha256'])
    for folder in ('prepared-v2','core-host-v3','native-v4','frontend-native-v1','frontend-abi-v1','frontend-host-v1',
        'current-root-capture','slot-capture','slot-delta','metadata-snapshot','restore-model-v1','pipeline-v4'):
        for p in (BASE/folder).rglob('*'):
            if p.is_file():pin(p)
    for folder in ('tools','tests','graphics/gauguin-core-prof'):
        for p in (WORK/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.py','.cpp','.c','.m','.mm','.h','.hpp','.inc'):pin(p)
    for p in (WORK/'docs/gauguin-core-prof-339-trial-20261117.md',WORK/'docs/gauguin-core-prof339-design-20261117.md',
        MAIN/'tools/storage-budget.py'):pin(p)
    for p,h in pins.items():assert sha(p)==h,p
    plan=expected_plan();pin(plan['image'],IMAGE);pin(plan['observer_helper'])
    spec=importlib.util.spec_from_file_location('capture339_limits',WORK/'tools/capture-core339-root.py')
    caps=importlib.util.module_from_spec(spec);spec.loader.exec_module(caps)
    bound=runtime_bound(caps);recipe_bound=recipe_storage_bound()
    profile=load(BASE/'current-root-profile.json');profile.update(out=str((BASE/'execution/fresh-before').relative_to(MAIN)))
    for leaf,value in [('expected-baseline.json',baseline),('capture-profile.json',profile),('trial-plan.json',plan),
        ('storage-bound.json',bound),('storage-recipe-bound.json',recipe_bound)]:save(BASE/leaf,value);pin(BASE/leaf)
    ready=dict(state='ready-core339-one-shot',trial_plan_sha256=sha(BASE/'trial-plan.json'),
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),image_sha256=IMAGE,root_header_sha256=HEADER,
        parent_338_pins_preserved=19711,pin_count=len(pins),input_pins=dict(sorted(pins.items())),
        approval_pending=True,device_writes=0,boot_attempts=0,new_kernel_builds=0)
    save(BASE/'ready.json',ready);print(json.dumps({k:v for k,v in ready.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
