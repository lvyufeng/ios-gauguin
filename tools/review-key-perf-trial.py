#!/usr/bin/env python3
"""Separate read-only review of the frozen KEYPERF331 scope and rollback bounds."""
from pathlib import Path
import ast
import hashlib
import json

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
B=WORK/'research/tmp/key-perf565-331'
P=MAIN/'research/tmp/gauguin-direct-load-worktree-20261116/research/tmp/direct-load-330'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(Path(p).read_text())


def main():
    assert not (B/'approval.json').exists() and not (B/'execution').exists()
    ready=load(B/'ready.json');plan=load(B/'trial-plan.json');install=load(B/'slot-delta/install-plan.json')
    assert ready['state']=='ready-keyperf331-one-shot' and ready['pin_count']==len(ready['input_pins'])>14195
    assert ready['trial_plan_sha256']==sha(B/'trial-plan.json') and ready['install_plan_sha256']==sha(B/'slot-delta/install-plan.json')
    assert all(sha(p)==h for p,h in ready['input_pins'].items())
    prior=load(P/'trial-plan.json')
    allowed={'state','root_header_sha256','install_plan_sha256','owned_core_sha256','image','image_sha256','kernel_banner','boot_command','kernel_identity','EDR_helper_sha256','GPU_native_profile','unchanged_328_image','unchanged_328_helper','state_key_reuse'}
    changed={k for k in set(plan)|set(prior) if plan.get(k)!=prior.get(k)}
    assert changed==allowed,changed
    assert plan['state']=='prepared-keyperf331-one-shot' and not plan['unchanged_328_image'] and not plan['unchanged_328_helper']
    assert not plan['diagnostic_only'] and plan['performance_candidate'] and not plan['physical_FPS_qualified']
    assert plan['owned_core_sha256']==install['core_sha256']=='1e48b6f1b375519af151db4d09ccf368a56c969cd8ae8305a48c540a2e0eb681'
    assert sha(plan['image'])==ready['image_sha256']=='76dab1f9dc557a2a5903b3994e84d426b9d949efdaeb4972d9d454827ea2ecad'
    assert plan['boot_command']==prior['boot_command'].replace('gpf=3','gpf=4') and plan['kernel_identity']=='xnu-local331-01cb28877a5544d19a5f9e8a9abc556a'
    assert plan['direct_constant_packets']==dict(prefix_words=3,maximum_packet_words=16383,padding_words_max=3,preflight_before_mutation=True,reserve_before_append=True,additional_GPU_commands=0,additional_threads=0)
    assert plan['bounded_draw_scratch']==dict(streams=4,maximum_retained_bytes_per_CB=65536,reset_on_scope_exit=True,additional_GPU_commands=0,additional_threads=0)
    assert plan['state_key_reuse']==dict(stack_key_bytes=325,compile_time_bytes_limit=1024,reuse_pass_storage=True,contents_and_comparison_unchanged=True,additional_GPU_commands=0,additional_threads=0)
    assert plan['GPU_native_profile']==dict(argument='gpf=4',frequency_hz=565000000,perf_index=4,bw_index=9,bandwidth_bytes_per_second=5412000000,ARC_virtual_level=256,GX_index=4,MX_index=5)
    image=load(B/'ui331-image.json');image_review=load(B/'ui331-review.json')
    assert plan['image']==image['image'] and plan['image_sha256']==image['image_sha256']==image_review['image_sha256']
    assert image_review['raw_MachO_segment_bytes_verified'] and image_review['undefined_symbols_unchanged'] and not image_review['adt_changes']
    helper=load(B/'edr-native-v1/result.json');abi=load(B/'abi-v1/result.json')
    assert plan['EDR_helper_sha256']==install['admission_sha256']==helper['products']['candidate']['sha256']==abi['binary_sha256']=='99339db256ace9356fb21de6469eb8f8790d59340eaae7bc573af21dfc22a54d'
    assert helper['products']['baseline']['sha256']==prior['EDR_helper_sha256'] and abi['total_imports']==53 and not abi['missing_imports']
    assert load(B/'edr-host-v1/result.json')['checks']==2142
    assert load(B/'policy-review.json')['profile']['linux_powerlevel']==2
    oracle=load(B/'native-oracle-v1/result.json');firmware=load(B/'firmware-host-result.json')
    assert oracle['native565_sha256']==oracle['port565_sha256'] and oracle['default_store_stream_unchanged']
    assert firmware['checks']==23864961 and firmware['default_and_565_tested']
    assert not plan['GPU_frequency_measured'] and not plan['dynamic_frequency_governor']
    old=load(P/'slot-delta/install-plan.json')
    for name,row in install['rows'].items():
        assert row['old_file_sha256']==old['rows'][name]['old_file_sha256']
        assert row['data_blocks']==old['rows'][name]['data_blocks']
        if name not in ('core','admission'):assert row['new_file_sha256']==old['rows'][name]['new_file_sha256']
    assert install['rows']['core']['new_logical']==8408800<=install['rows']['core']['data_blocks']*4096==8409088
    assert plan['install_userdata_bytes']==install['install_write_bytes']==10301440
    assert plan['maximum_restore_userdata_bytes']==install['restore_max_write_bytes']==10305536
    assert plan['normal_userdata_write_bytes_max']==plan['install_userdata_bytes']+plan['maximum_restore_userdata_bytes']==20606976
    assert plan['maximum_userdata_write_bytes']==plan['install_userdata_bytes']+4*plan['maximum_restore_userdata_bytes']==51523584
    assert plan['misc_write_bytes']==13 and plan['maximum_host_misc_write_bytes']==26
    assert plan['temporary_boots']==1 and plan['boot_retries']==0 and plan['maximum_fastboot_reboot_recovery_fallbacks']==1
    assert plan['scripted_strokes']==13 and plan['scripted_reports']==442 and plan['wake_button_pairs_max']==1
    assert plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024
    assert not plan['main_thread_sampling']['hard_realtime_pause_limit'] and not plan['process_sampling']['hard_realtime_pause_limit']
    restore=load(P/'execution/independent-restore.json')
    assert restore['state']=='independently-verified-six-original-files-and-misc' and restore['misc_original_4096_bytes_match']
    assert ready['root_header_sha256']==plan['root_header_sha256']==restore['root_header_sha256']=='5db01e85733bc6d15510f1a7f7843f1df9b1011945f39c4b5e70cc7765bf0b1e'
    assert load(B/'expected-baseline.json')==load(P/'execution/restored-capture/result.json')
    s=load(B/'storage-bound.json');a=load(B/'storage-trial-admission.json')
    keys=('extra_log_copies_max_bytes','kernel_dump_max_bytes','rollback_temp_max_bytes','metadata_max_bytes','queue_analysis_max_bytes','stage_cache_analysis_max_bytes','map_analysis_max_bytes','map_analysis_result_copy_max_bytes','native_perf_analysis_max_bytes','native_perf_analysis_result_copy_max_bytes','submission_diagnostic_analysis_max_bytes','submission_diagnostic_result_copy_max_bytes')
    total=s['full_captures']*s['per_capture_max_bytes']+sum(s[k] for k in keys)
    assert total==s['worst_case_bytes']==522616464<s['reserve_bytes']==plan['storage_reserve_bytes']==536870912
    assert a['admitted'] and a['planned_batch_bytes']==536870912 and a['current_accounted_bytes']+a['planned_batch_bytes']<=500000000000
    for n in ('install','restore'):
        m=load(B/(n+'-model.log'))
        assert m['base_plan_sha256']==sha(B/'slot-delta/install-plan.json') and m['rollback_verified'] and m['partial_write_failure_tested']
    native=load(B/'core-native-v1/result.json');host=load(B/'core-host-v1/result.json')
    assert native['all_core_TUs_recompiled'] and not native['exports_added'] and not native['exports_removed']
    assert host['equivalence']['cases']==96 and host['equivalence']['bytes']==36206840
    assert 'segments cases=192 invalid=5 allocation_failure=1 warm_allocations=0 failures=0' in (B/'core-host-v1/candidate-segments.log').read_text()
    assert host['equivalence']['raw_byte_comparison'] and host['ownership_scenarios']==23 and host['upstream_regression_results']['unchanged_preexisting_failed_checks']==12
    # Layout users were all rebuilt; unchanged compiler/transport preserves caches.
    for unit,key in [('compiler','compiler_object_sha256'),('iokit_transport','fault_cache_object_sha256')]:
        assert sha(B/f'core-native-v1/candidate/{unit}.o')==plan[key]
    fn=next(x for x in ast.parse((WORK/'tools/run-sb-cadence-trial.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='authorization')
    flags=ast.literal_eval(next(x.value for x in fn.body if isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id=='expected' for y in x.targets)))
    assert len(flags)==30 and 'allow_state_key_reuse' in flags and 'allow_native_GPU_performance_profile' in flags
    assert 'KEYPERF 0331 gate refused before any device command; observation classification checked' in (B/'gate-test.log').read_text()
    assert load(B/'analysis-order-test.json')['strict_negative_M_refusal_preserved']
    paths=[Path(__file__),B/'ready.json',B/'trial-plan.json',B/'gate-test.log',B/'storage-trial-admission.json',WORK/'docs/gauguin-key-perf565-331-trial-20261116.md']
    result=dict(state='reviewed-KEYPERF331-frozen-inputs-no-device-action',pin_count=ready['pin_count'],all_pins_unchanged=True,
        prior_independent_restoration_verified=True,only_core_and_scoped_helper_differ_from330=True,new_stock565_kernel=True,changed_plan_keys=sorted(changed),
        scratch_bound_verified=True,baseline_binary_reproduced=True,GPU_words_and_slabs_equal=True,upstream_existing_failed_checks=12,
        diagnostic_scope_and_byte_bounds_verified=True,storage_bound_independently_recomputed=total,storage_admitted=True,
        consent_flags=len(flags),approval_absent=True,execution_absent=True,device_commands=0,device_writes=0,boot_attempts=0,
        input_pins={str(p):sha(p) for p in paths})
    with (B/'final-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
