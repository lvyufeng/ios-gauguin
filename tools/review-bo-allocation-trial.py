#!/usr/bin/env python3
"""Independently check BO333 frozen scope, byte budgets and inherited restore."""
from pathlib import Path
import ast,hashlib,json
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/bo-allocation-333'
P=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-present-retry-worktree-20261116/research/tmp/present-retry-332')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(Path(p).read_text())
def main():
    assert not (B/'approval.json').exists() and not (B/'execution').exists()
    ready,plan,install=(load(B/n) for n in ('ready.json','trial-plan.json','slot-delta/install-plan.json'))
    assert ready['state']=='ready-bo333-one-shot' and ready['pin_count']==len(ready['input_pins'])>15569
    assert ready['trial_plan_sha256']==sha(B/'trial-plan.json') and ready['install_plan_sha256']==sha(B/'slot-delta/install-plan.json')
    for path,digest in ready['input_pins'].items():assert sha(path)==digest,path
    old=load(P/'trial-plan.json');changed={k for k in set(plan)|set(old) if plan.get(k)!=old.get(k)}
    assert changed=={'state','root_header_sha256','install_plan_sha256','image','image_sha256','kernel_banner','kernel_identity','EDR_helper_sha256','diagnostic_only','performance_candidate','BO_allocation_diagnostics'},changed
    assert plan['state']=='prepared-bo333-one-shot' and plan['diagnostic_only'] and not plan['performance_candidate'] and not plan['physical_FPS_qualified']
    expected=dict(event_kind=32,maximum_records_per_new_BO=6,capture_capacity=4096,capture_window_seconds=4,numeric_thread_id=True,new_GPU_calls=0,new_MMIO_reads=0,original_validators_waits_ownership_preserved=True,analysis_max_bytes=4194304,result_copy_max_bytes=65536)
    assert plan['BO_allocation_diagnostics']==expected
    assert plan['owned_core_sha256']==install['core_sha256']==old['owned_core_sha256']=='1e48b6f1b375519af151db4d09ccf368a56c969cd8ae8305a48c540a2e0eb681'
    for key in ('boot_command','GPU_native_profile','C4_sha256','process_sampling','main_thread_sampling','display_retry'):
        assert plan[key]==old[key]
    assert plan['display_retry']['maximum_additional_attempts_per_frame']==8 and plan['display_retry']['GPU_read_guards_retained']
    image,review=load(B/'ui333-image.json'),load(B/'ui333-review.json')
    assert sha(plan['image'])==image['image_sha256']==review['image_sha256']==ready['image_sha256']=='373f3bbef16104e5dd08617c6fcfde2d4dc07217a170abde0063a2052af39939'
    assert image['command_changes_from_0332']==[] and review['command_bytes']==607 and review['raw_MachO_segment_bytes_verified'] and review['undefined_symbols_unchanged']
    manifest=load(B/'local-link/build-manifest.json');parent=load(P/'local-link/build-manifest.json')
    assert set(manifest['object_replacements'])==set(parent['object_replacements'])
    differences=[k for k in manifest['object_replacements'] if manifest['object_replacements'][k]!=parent['object_replacements'][k]]
    assert len(differences)==1 and differences[0].endswith('/GauguinGPU.cpo')
    assert manifest['kernel']['sha256']=='78cafe8198bd38f4ecf75b015afa5acfc8d73301438e907db7a11732a0955807'
    helper,abi=load(B/'edr-native-v1/result.json'),load(B/'abi-v2/result.json')
    assert plan['EDR_helper_sha256']==install['admission_sha256']==helper['products']['candidate']['sha256']==abi['binary_sha256']=='c9c7932dd37ae25375f1f54ec91e4dc9a008aedc89f6ae660535359cf939ad2d'
    assert helper['products']['baseline']['sha256']==old['EDR_helper_sha256'] and helper['pointer_write_and_once_contract_unchanged'] and abi['total_imports']==53 and not abi['missing_imports']
    assert load(B/'edr-host-v2/result.json')['checks']==2143
    old_install=load(P/'slot-delta/install-plan.json')
    for name,row in install['rows'].items():
        previous=old_install['rows'][name]
        for key in ('old_file_sha256','data_blocks','cnid','mode','data_block','old_logical'):assert row[key]==previous[key]
        if name!='admission':assert row['new_file_sha256']==previous['new_file_sha256']
    assert plan['install_userdata_bytes']==install['install_write_bytes']==10301440 and plan['maximum_restore_userdata_bytes']==install['restore_max_write_bytes']==10305536
    assert plan['normal_userdata_write_bytes_max']==10301440+10305536==20606976 and plan['maximum_userdata_write_bytes']==10301440+4*10305536==51523584
    assert plan['misc_write_bytes']==13 and plan['maximum_host_misc_write_bytes']==26 and plan['temporary_boots']==1 and plan['boot_retries']==0 and plan['maximum_fastboot_reboot_recovery_fallbacks']==1
    assert plan['scripted_strokes']==13 and plan['scripted_reports']==442 and plan['wake_button_pairs_max']==1 and plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024
    assert not plan['main_thread_sampling']['hard_realtime_pause_limit'] and not plan['process_sampling']['hard_realtime_pause_limit']
    restore=load(P/'execution/independent-restore.json');assert restore['state']=='independently-verified-six-original-files-and-misc' and restore['misc_original_4096_bytes_match']
    assert plan['root_header_sha256']==ready['root_header_sha256']==restore['root_header_sha256']=='059102aec366fd57b104f571bd1074cc5938eb9882f9df266447f75621300cc3'
    assert load(B/'expected-baseline.json')==load(P/'execution/restored-capture/result.json')
    bounds,admission=load(B/'storage-bound.json'),load(B/'storage-trial-admission.json')
    keys=('extra_log_copies_max_bytes','kernel_dump_max_bytes','rollback_temp_max_bytes','metadata_max_bytes','queue_analysis_max_bytes','stage_cache_analysis_max_bytes','map_analysis_max_bytes','map_analysis_result_copy_max_bytes','native_perf_analysis_max_bytes','native_perf_analysis_result_copy_max_bytes','submission_diagnostic_analysis_max_bytes','submission_diagnostic_result_copy_max_bytes','present_retry_analysis_max_bytes','present_retry_analysis_result_copy_max_bytes','BO_allocation_analysis_max_bytes','BO_allocation_result_copy_max_bytes')
    total=bounds['full_captures']*bounds['per_capture_max_bytes']+sum(bounds[k] for k in keys)
    assert total==bounds['worst_case_bytes']==527007376<bounds['reserve_bytes']==plan['storage_reserve_bytes']==536870912
    assert admission['admitted'] and admission['planned_batch_bytes']==536870912 and admission['current_accounted_bytes']+536870912<=500000000000
    for name in ('install','restore'):
        model=load(B/(name+'-model.log'));assert model['base_plan_sha256']==sha(B/'slot-delta/install-plan.json') and model['rollback_verified'] and model['partial_write_failure_tested']
    assert load(B/'host-v1/result.json')['paired_request_observations']==6900 and load(B/'allocation-log-test.json')['negative_cases']==30 and load(B/'allocation-log-test.json')['actual332_log_rejected']
    assert load(B/'analysis-order-test.json')['strict_negative_M_refusal_preserved']
    function=next(n for n in ast.parse((W/'tools/run-sb-cadence-trial.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='authorization')
    flags=ast.literal_eval(next(n.value for n in function.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='expected' for t in n.targets)))
    assert len(flags)==32 and 'allow_BO_allocation_CPU_trace' in flags and 'allow_bounded_present_retry' in flags
    assert 'BO 0333 gate refused before any device command; observation classification checked' in (B/'gate-test.log').read_text()
    paths=[Path(__file__),B/'ready.json',B/'trial-plan.json',B/'gate-test.log',B/'storage-trial-admission.json',W/'docs/gauguin-bo-allocation-333-trial-20261116.md']
    result=dict(state='reviewed-BO333-frozen-inputs-no-device-action',pin_count=ready['pin_count'],all_pins_unchanged=True,prior_independent_restoration_verified=True,only_scoped_helper_differs_from332=True,unchanged_331_core=True,unchanged_332_display_retry=True,allocation_CPU_diagnostics_verified=True,changed_plan_keys=sorted(changed),diagnostic_scope_and_byte_bounds_verified=True,storage_bound_independently_recomputed=total,storage_admitted=True,consent_flags=len(flags),approval_absent=True,execution_absent=True,device_commands=0,device_writes=0,boot_attempts=0,input_pins={str(p):sha(p) for p in paths})
    with (B/'final-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))
if __name__=='__main__':main()
