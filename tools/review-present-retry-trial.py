#!/usr/bin/env python3
"""Independently review frozen0332 scope, ownership checks and rollback bounds."""
from pathlib import Path
import ast
import hashlib
import json

WORK = Path(__file__).resolve().parents[1]
B = WORK / 'research/tmp/present-retry-332'
P = Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-key-perf565-worktree-20261116/research/tmp/key-perf565-331')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def main():
    assert not (B / 'approval.json').exists() and not (B / 'execution').exists()
    ready, plan, install = (load(B / name) for name in ('ready.json', 'trial-plan.json', 'slot-delta/install-plan.json'))
    assert ready['state'] == 'ready-present332-one-shot' and ready['pin_count'] == len(ready['input_pins']) > 15218
    assert ready['trial_plan_sha256'] == sha(B / 'trial-plan.json')
    assert ready['install_plan_sha256'] == sha(B / 'slot-delta/install-plan.json')
    assert all(sha(path) == digest for path, digest in ready['input_pins'].items())
    prior = load(P / 'trial-plan.json')
    changed = {key for key in set(plan) | set(prior) if plan.get(key) != prior.get(key)}
    allowed = {'state', 'root_header_sha256', 'install_plan_sha256', 'image', 'image_sha256',
        'kernel_banner', 'kernel_identity', 'EDR_helper_sha256', 'all_core_TUs_recompiled',
        'unchanged_331_core', 'additional_GPU_calls_scope', 'display_retry'}
    assert changed == allowed, changed
    assert plan['state'] == 'prepared-present332-one-shot' and not plan['physical_FPS_qualified']
    assert plan['performance_candidate'] and not plan['diagnostic_only']
    assert plan['unchanged_331_core'] and not plan['all_core_TUs_recompiled']
    assert plan['owned_core_sha256'] == install['core_sha256'] == prior['owned_core_sha256'] == '1e48b6f1b375519af151db4d09ccf368a56c969cd8ae8305a48c540a2e0eb681'
    assert plan['boot_command'] == prior['boot_command'] and plan['GPU_native_profile'] == prior['GPU_native_profile']
    assert plan['C4_sha256'] == prior['C4_sha256'] and plan['process_sampling'] == prior['process_sampling']
    assert plan['display_retry'] == dict(maximum_additional_attempts_per_frame=8, maximum_total_attempts_per_frame=9,
        one_pending_one_active=True, newer_pending_preferred=True, owner_power_epoch_checked=True,
        epoch_wrap_disables_retry=True, GPU_read_guards_retained=True, additional_GPU_submissions=0,
        additional_threads=0, readiness_reported_in_present_end_flag=1)
    assert plan['additional_GPU_calls_scope'] == 'C4 CPU instrumentation only'
    image, image_review = load(B / 'ui332-image.json'), load(B / 'ui332-review.json')
    assert sha(plan['image']) == ready['image_sha256'] == image['image_sha256'] == image_review['image_sha256'] == 'f3a5c5484cbd024cf7e9112ebcb9413a8a843272762518caa481024d93f441e2'
    assert image['command_changes_from_0331'] == [] and image_review['command_bytes'] == 607
    assert image_review['raw_MachO_segment_bytes_verified'] and image_review['undefined_symbols_unchanged']
    helper, abi = load(B / 'edr-native-v1/result.json'), load(B / 'abi-v1/result.json')
    assert plan['EDR_helper_sha256'] == install['admission_sha256'] == helper['products']['candidate']['sha256'] == abi['binary_sha256'] == '5cce66b7fae4e2cdf374b088b7a9bbc16ce7bbf72fb59ddbd3df73aca55977fd'
    assert helper['products']['baseline']['sha256'] == prior['EDR_helper_sha256']
    assert helper['pointer_write_and_once_contract_unchanged'] and abi['total_imports'] == 53 and not abi['missing_imports']
    assert load(B / 'edr-host-v1/result.json')['checks'] == 2143
    old_install = load(P / 'slot-delta/install-plan.json')
    for name, row in install['rows'].items():
        assert row['old_file_sha256'] == old_install['rows'][name]['old_file_sha256']
        assert row['data_blocks'] == old_install['rows'][name]['data_blocks']
        if name != 'admission':
            assert row['new_file_sha256'] == old_install['rows'][name]['new_file_sha256']
    assert plan['install_userdata_bytes'] == install['install_write_bytes'] == 10301440
    assert plan['maximum_restore_userdata_bytes'] == install['restore_max_write_bytes'] == 10305536
    assert plan['normal_userdata_write_bytes_max'] == plan['install_userdata_bytes'] + plan['maximum_restore_userdata_bytes'] == 20606976
    assert plan['maximum_userdata_write_bytes'] == plan['install_userdata_bytes'] + 4 * plan['maximum_restore_userdata_bytes'] == 51523584
    assert plan['misc_write_bytes'] == 13 and plan['maximum_host_misc_write_bytes'] == 26
    assert plan['temporary_boots'] == 1 and plan['boot_retries'] == 0 and plan['maximum_fastboot_reboot_recovery_fallbacks'] == 1
    assert plan['scripted_strokes'] == 13 and plan['scripted_reports'] == 442 and plan['wake_button_pairs_max'] == 1
    assert plan['main_thread_sampling']['max_samples'] == 64 and plan['process_sampling']['max_register_samples'] == 1024
    assert not plan['main_thread_sampling']['hard_realtime_pause_limit'] and not plan['process_sampling']['hard_realtime_pause_limit']
    restored = load(P / 'execution/independent-restore.json')
    assert restored['state'] == 'independently-verified-six-original-files-and-misc' and restored['misc_original_4096_bytes_match']
    assert plan['root_header_sha256'] == ready['root_header_sha256'] == restored['root_header_sha256'] == 'bc43dc37e6c0760ca9dc0210be2816cff4551312acbeedbadb22102440b4a12d'
    assert load(B / 'expected-baseline.json') == load(P / 'execution/restored-capture/result.json')
    bounds, admission = load(B / 'storage-bound.json'), load(B / 'storage-trial-admission.json')
    keys = ('extra_log_copies_max_bytes', 'kernel_dump_max_bytes', 'rollback_temp_max_bytes', 'metadata_max_bytes',
        'queue_analysis_max_bytes', 'stage_cache_analysis_max_bytes', 'map_analysis_max_bytes',
        'map_analysis_result_copy_max_bytes', 'native_perf_analysis_max_bytes', 'native_perf_analysis_result_copy_max_bytes',
        'submission_diagnostic_analysis_max_bytes', 'submission_diagnostic_result_copy_max_bytes',
        'present_retry_analysis_max_bytes', 'present_retry_analysis_result_copy_max_bytes')
    total = bounds['full_captures'] * bounds['per_capture_max_bytes'] + sum(bounds[key] for key in keys)
    assert total == bounds['worst_case_bytes'] == 522747536 < bounds['reserve_bytes'] == plan['storage_reserve_bytes'] == 536870912
    assert admission['admitted'] and admission['planned_batch_bytes'] == 536870912
    assert admission['current_accounted_bytes'] + admission['planned_batch_bytes'] <= 500000000000
    for name in ('install', 'restore'):
        model = load(B / (name + '-model.log'))
        assert model['base_plan_sha256'] == sha(B / 'slot-delta/install-plan.json')
        assert model['rollback_verified'] and model['partial_write_failure_tested']
    lifetime, pixels = load(B / 'retry-host-v1/result.json'), load(B / 'pixels-host-v1/result.json')
    assert lifetime['baseline_functional_failure_reproduced'] and lifetime['original_lifetime_scenarios_passed']
    assert lifetime['bounded_retries_and_epoch_cancellation_passed'] and lifetime['concurrent_producer_consumer_passed']
    assert pixels['pixel_and_reference_checks_passed'] and pixels['ready_and_refused_timer_result_forwarded']
    assert load(B / 'retry-log-test.json')['actual331_log_rejected']
    function = next(node for node in ast.parse((WORK / 'tools/run-sb-cadence-trial.py').read_text()).body if isinstance(node, ast.FunctionDef) and node.name == 'authorization')
    flags = ast.literal_eval(next(node.value for node in function.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'expected' for target in node.targets)))
    assert len(flags) == 31 and 'allow_bounded_present_retry' in flags
    assert 'PRESENT 0332 gate refused before any device command; observation classification checked' in (B / 'gate-test.log').read_text()
    assert load(B / 'analysis-order-test.json')['strict_negative_M_refusal_preserved']
    paths = [Path(__file__), B / 'ready.json', B / 'trial-plan.json', B / 'gate-test.log',
             B / 'storage-trial-admission.json', WORK / 'docs/gauguin-present-retry-332-trial-20261116.md']
    result = dict(state='reviewed-PRESENT332-frozen-inputs-no-device-action', pin_count=ready['pin_count'],
        all_pins_unchanged=True, prior_independent_restoration_verified=True, only_scoped_helper_differs_from331=True,
        unchanged_331_core=True, bounded_retry_kernel_verified=True, changed_plan_keys=sorted(changed),
        diagnostic_scope_and_byte_bounds_verified=True, storage_bound_independently_recomputed=total,
        storage_admitted=True, consent_flags=len(flags), approval_absent=True, execution_absent=True,
        device_commands=0, device_writes=0, boot_attempts=0, input_pins={str(p):sha(p) for p in paths})
    with (B / 'final-review.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
