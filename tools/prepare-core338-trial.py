#!/usr/bin/env python3
"""Freeze0338 owned userland over the unchanged0337 temporary image."""
import hashlib
import json
from pathlib import Path
from core338_scope import MAIN,WORK,BASE,PRIOR,HEADER,CORE,C4,IMAGE,expected_plan,load,sha


def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')


def runtime_bound(capture):
    logical=sum(capture.BASE.FILE_LIMITS.get(p,1048576) for p in capture.BASE.PATHS)
    assert logical==146307632 and len(capture.BASE.PATHS)==31 and capture.RESULT_MAX==1048576
    parts=dict(three_full_captures=3*(logical+capture.RESULT_MAX),
        four_allocated_log_tails=(48+22+8+8)*1048576,
        kernel_ring_raw_and_decoded=16781312,observer_stdout_stderr=12587008,
        one_restore_preimage_and_target_set=2*10330112,
        eight_executor_receipts=8*2*1048576,other_analysis_metadata=32*1048576,
        lifecycle_analysis=8*1048576,identity_analysis=8*1048576,
        core_analysis=32*1048576,backlog_analysis=8*1048576,
        stage_analysis=2*1048576,BO_analysis=4*1048576,
        surface_submit_collection_analysis=3*131072,map_native_retry_analysis=3*65536,
        progress_and_restore_recipe=1572864)
    total=sum(parts.values());assert total==699780752<700000000
    return dict(state='bounded0338-complete-runtime-batch',components=parts,worst_case_bytes=total,
        reserve_bytes=700000000,full_captures=3,capture_logical_files_max_bytes=logical,
        per_capture_metadata_max_bytes=capture.RESULT_MAX,
        per_capture_max_bytes=logical+capture.RESULT_MAX,
        limits=dict(backboard=22*1048576,springboard=48*1048576),
        before_after_SB_aliases_allocate_no_extra_copy=True,
        fixed337_image_reused_without_copy=True,new_kernel_builds=0)


def recipe_storage_bound():
    # An8MiB journal cannot contain more than16384 distinct512-byte sectors;
    # each can name at most one unique4KiB home block. Block numbers are at
    # most7decimal digits.89 full transaction headers already exceed the
    # journal with payload, so using89 here is conservative. Only these fixed
    # shape numeric/hash records and the bounded18-range recipe are serialized.
    import copy
    recipe=copy.deepcopy(load(BASE/'restore-model-v5/all-four-MachO-trims.json')['recipe'])
    recipe['journal']['home_block_sha256']={str(1000000+i):'f'*64 for i in range(16384)}
    recipe['journal']['chunks']=[dict(offset=8388608,sequence=4294967295,entries=5887,bytes=8388608,flags=3) for _ in range(89)]
    for row in recipe['ranges']:
        if row['kind']=='bitmap':row['fields']=[dict(offset=4095,mask=255) for _ in range(131)]
    recipe['attribute_record_types']={str(k):4294967295 for k in (0x10,0x20,0x30)}
    length=len((json.dumps(recipe,indent=2)+'\n').encode())
    assert length+65536<=1572864
    return dict(state='conservative0338-journal-recipe-JSON-bound',
        journal_bytes=8388608,minimum_sector_bytes=512,maximum_home_hashes=16384,
        maximum_decimal_block_digits=7,overestimated_chunks=89,
        inflated_serialized_recipe_bytes=length,progress_and_extra_fields_bytes=65536,
        reserved_bytes=1572864,device_writes=0)


def main():
    for leaf in ('trial-plan.json','ready.json','approval.json','execution','final-review.json',
        'capture-profile.json','expected-baseline.json','storage-bound.json','storage-recipe-bound.json'):
        assert not (BASE/leaf).exists(),leaf
    parent=load(PRIOR/'ready.json');assert parent['pin_count']==18389
    pins=dict(parent['input_pins'])
    def pin(path,digest=None):
        path=str(Path(path).resolve());digest=digest or sha(path)
        assert path not in pins or pins[path]==digest,path
        pins[path]=digest
    def receipt(path):
        value=load(path);pin(path)
        for p,h in value.get('input_pins',{}).items():pin(p,h['sha256'] if isinstance(h,dict) else h)
        return value
    pin(PRIOR/'ready.json');old=receipt(PRIOR/'trial-plan.json')
    assert old['image_sha256']==IMAGE and old['SB_sha256']=='3f6dba175451498e190f17bd4043cba5a79c377127b0422c1111fe3ba38b0925'
    recovered=receipt(PRIOR/'trim-rescue/independent-six-file-restore.json')
    metadata=receipt(PRIOR/'trim-rescue/independent-metadata-restore.json')
    assert recovered['root_header_sha256']==metadata['root_header_sha256']==HEADER
    assert recovered['misc_original_4096_bytes_match'] and metadata['journal_empty']
    prepared=receipt(BASE/'prepared-v2/result.json')
    assert prepared['fixed337_kernel_helper_SB_reused'] and prepared['completion_FIFO_unchanged']
    assert prepared['core_commit_post_order_unchanged'] and prepared['frontend_notification_lease_separate']
    host=receipt(BASE/'core-host-v5/result.json')
    assert host['state']=='0338-core-host-ownership-and-notification-passed' and host['inputs_unchanged']
    assert host['original_ownership_scenarios_per_variant']==23 and host['new_notification_scenarios']==11
    native=receipt(BASE/'native-v1/result.json')
    assert native['state']=='0338-native-core-baseline-reproduced-candidate-signed' and native['inputs_unchanged']
    assert native['all_other_core_objects_identical'] and native['load_commands_unchanged']
    assert len(native['exports_added'])==2 and not native['exports_removed'] and not native['added_import_rows']
    assert native['products']['candidate']['sha256']==CORE and native['fits_existing_allocation']
    front=receipt(BASE/'frontend-native-v1/result.json')
    assert front['state']=='0338-frontend-baseline-reproduced-candidate-signed' and front['inputs_unchanged']
    assert front['products']['candidate']['sha256']==C4 and front['resources_unchanged'] and front['baseline_exact_Q337_signed_bytes']
    abi=receipt(BASE/'frontend-abi-v1/result.json')
    assert abi['checked_imports']==355 and not abi['missing_imports'] and abi['core_imports_unchanged']
    assert abi['optional_hooks_remain_disabled'] and not abi['runtime_behavior_qualified']
    objc=receipt(BASE/'frontend-host-v9/result.json')
    assert objc['state']=='0338-production-ObjC-methods-core-FakeGpu-lifetimes-passed' and objc['scenarios']==5
    assert objc['actual_completion_can_finish_before_notice_admission'] and objc['inputs_unchanged']
    assert all(row['exit']==0 for row in objc['steps'])
    decoder=receipt(BASE/'log-tests-v3.json')
    assert decoder['tests']==6 and decoder['contract_mutations']==21 and decoder['includes_whole_completion_before_notice']
    restore=receipt(BASE/'restore-model-v5/result.json')
    assert restore['state']=='0338-live-metadata-install-and-tail-journal-restore-models-passed' and len(restore['checks'])==47
    assert restore['all_restore_partial_write_points']==17 and restore['all_model_IO_writes_memory_only']
    signatures=receipt(BASE/'restore-model-v5/independent-candidate-signatures.json')
    assert len(signatures['checks'])==4 and all(row['signature_verified'] for row in signatures['checks'])
    pipeline=receipt(BASE/'pipeline-v3/result.json')
    assert pipeline['state']=='0338-executor-analysis-collection-order-host-models-passed' and len(pipeline['checks'])==22
    assert pipeline['saved_analysis_fixture']['complete_cb_count']==776
    assert not pipeline['saved_analysis_fixture']['real0338_performance_evidence']
    baseline=receipt(BASE/'current-root-capture/result.json');capture=receipt(BASE/'slot-capture/result.json')
    assert baseline['root_header_sha256']==capture['root_header_sha256']==HEADER and len(baseline['files'])==31
    snapshot=receipt(BASE/'metadata-snapshot/result.json')
    assert snapshot['root_header_sha256']==HEADER and snapshot['compressed_bytes']==13035896
    delta=receipt(BASE/'slot-delta/install-plan.json')
    assert delta['state']=='prepared-six-file-core338-delta' and delta['core_sha256']==CORE and delta['c4_sha256']==C4
    assert delta['install_write_bytes']==10301440 and delta['restore_max_write_bytes']==10330112 and delta['restore_max_ranges']==18
    assert not delta['journal_home_replay_allowed'] and not delta['alternate_header_write_allowed']
    batch=receipt(BASE/'storage-whole-batch-admission.json');budget=receipt(BASE/'storage-runtime-admission.json')
    assert batch['admitted'] and batch['planned_batch_bytes']==1800000000
    assert budget['admitted'] and budget['planned_batch_bytes']==700000000
    assert budget['current_accounted_bytes']+700000000<=500000000000
    for leaf in ('cleanup338-plan.json','cleanup338-alias-correction.json','cleanup338-result.json',
        'storage-whole-batch-components.json','current-root-profile.json'):pin(BASE/leaf)
    pin(MAIN/'research/tmp/gauguin-edr-once-worktree-20261115/research/tmp/edr-once-320/queue-retired-build-archives/pristine193.tar-06f6431bce3c.zlib')
    for product in (native,front):
        for item in product['products'].values():pin(item['binary'],item['sha256'])
    for folder in ('prepared-v2','core-host-v5','native-v1','frontend-native-v1','frontend-abi-v1','frontend-host-v9',
        'current-root-capture','slot-capture','slot-delta','metadata-snapshot','restore-model-v5'):
        for p in (BASE/folder).rglob('*'):
            if p.is_file():pin(p)
    for folder in ('tools','tests','graphics/gauguin-core-async'):
        for p in (WORK/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.py','.cpp','.c','.m','.mm','.h','.hpp','.inc'):pin(p)
    for p in (Path(__file__),WORK/'docs/gauguin-core-async-338-trial-20261117.md',
        WORK/'tools/review-core338-trial.py',WORK/'docs/gauguin-core-async338-design-20261117.md'):pin(p)
    for p,h in pins.items():assert sha(p)==h,p
    plan=expected_plan();pin(plan['image'],IMAGE);pin(plan['observer_helper'])
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('capture338_limits',WORK/'tools/capture-core338-root.py')
    caps=module_from_spec(spec);spec.loader.exec_module(caps)
    bound=runtime_bound(caps)
    recipe_bound=recipe_storage_bound()
    profile=load(BASE/'current-root-profile.json');profile.update(out=str((BASE/'execution/fresh-before').relative_to(MAIN)))
    save(BASE/'expected-baseline.json',baseline);save(BASE/'capture-profile.json',profile)
    save(BASE/'trial-plan.json',plan);save(BASE/'storage-bound.json',bound)
    save(BASE/'storage-recipe-bound.json',recipe_bound)
    for leaf in ('expected-baseline.json','capture-profile.json','trial-plan.json','storage-bound.json','storage-recipe-bound.json'):pin(BASE/leaf)
    ready=dict(state='ready-core338-one-shot',trial_plan_sha256=sha(BASE/'trial-plan.json'),
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),image_sha256=IMAGE,root_header_sha256=HEADER,
        parent_337_pins_preserved=18389,pin_count=len(pins),input_pins=dict(sorted(pins.items())),
        approval_pending=True,device_writes=0,boot_attempts=0,new_kernel_builds=0)
    save(BASE/'ready.json',ready)
    print(json.dumps({k:v for k,v in ready.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
