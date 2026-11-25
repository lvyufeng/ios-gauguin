#!/usr/bin/env python3
"""Independently check frozen BC335 scope, actual products and rollback bounds."""
from pathlib import Path
import ast
import hashlib
import json

WORK = Path(__file__).resolve().parents[1]
BASE = WORK / 'research/tmp/bo-reuse-335'
PRIOR = WORK.parent / 'gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334'
BO333 = WORK.parent / 'gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def main():
    assert not (BASE / 'approval.json').exists() and not (BASE / 'execution').exists()
    ready, plan, install = (load(BASE / n) for n in ('ready.json', 'trial-plan.json', 'slot-delta/install-plan.json'))
    assert ready['state'] == 'ready-bcreuse335-one-shot' and ready['pin_count'] == len(ready['input_pins']) > 16570
    assert ready['trial_plan_sha256'] == sha(BASE / 'trial-plan.json')
    assert ready['install_plan_sha256'] == sha(BASE / 'slot-delta/install-plan.json')
    for path, digest in ready['input_pins'].items():
        assert sha(path) == digest, path
    old = load(PRIOR / 'trial-plan.json')
    changed = {k for k in set(plan) | set(old) if plan.get(k) != old.get(k)}
    assert changed == {'state', 'root_header_sha256', 'install_plan_sha256', 'image', 'image_sha256',
                       'kernel_banner', 'kernel_identity', 'EDR_helper_sha256', 'all_core_TUs_recompiled',
                       'unchanged_333_image', 'unchanged_333_helper', 'unchanged_334_core',
                       'completed_owned_BO_cache'}, changed
    assert plan['state'] == 'prepared-bcreuse335-one-shot' and not plan['diagnostic_only']
    assert plan['performance_candidate'] and not plan['physical_FPS_qualified']
    assert plan['unchanged_334_core'] and not plan['all_core_TUs_recompiled']
    for key in ('boot_command', 'C4_sha256', 'owned_core_sha256', 'surface_retirement',
                'GPU_native_profile', 'process_sampling', 'main_thread_sampling', 'display_retry',
                'BO_allocation_diagnostics'):
        assert plan[key] == old[key], key
    assert plan['completed_owned_BO_cache'] == dict(
        slots=32, bytes=16777216, max_bo_bytes=1048576, exact_size_and_flags=True,
        zero_before_new_handle=True, no_IOSurface=True, no_exported_alias=True,
        completed_only=True, residency_includes_cache=True, allocator_retry_max=1,
        reuse_event_kind=33, maximum_records_per_BO_request=7, new_GPU_commands=0, new_threads=0)
    image, review = load(BASE / 'ui335-image.json'), load(BASE / 'ui335-review.json')
    assert sha(plan['image']) == ready['image_sha256'] == image['image_sha256'] == review['image_sha256'] == '492f4208b974b4c6ba934e17d645b4b54fed93de5ae3997427fab3b7d354a311'
    assert plan['image_bytes'] == image['image_bytes'] == 20054016
    assert image['command_changes_from_0333'] == [] and image['command'] == plan['boot_command']
    assert review['raw_MachO_segment_bytes_verified'] and review['undefined_symbol_count'] == 0
    assert review['command_bytes'] == plan['command_bytes'] == 607
    manifest = load(BASE / 'local-link/build-manifest.json')
    original = load(BO333 / 'local-link/build-manifest.json')
    assert set(manifest['object_replacements']) == set(original['object_replacements'])
    replacements = [k for k in manifest['object_replacements'] if manifest['object_replacements'][k] != original['object_replacements'][k]]
    assert len(replacements) == 1 and replacements[0].endswith('/GauguinGPU.cpo')
    assert manifest['baseline_relink_identical_except_LC_UUID'] and manifest['inputs_unchanged']
    assert sha(manifest['kernel']['path']) == manifest['kernel']['sha256'] == review['kernel_sha256'] == 'a0c77658e37b679d5e9eccb3a3fd16fffb9d3830c5835831c783a1dea8bdcbff'
    assert manifest['kernel_banner'] == plan['kernel_banner']
    assert manifest['build_identity']['id'] == plan['kernel_identity'] == 'xnu-local335-c472105b412e4e2f88fd328faa89ce32'
    helper, abi = load(BASE / 'edr-native-v2/result.json'), load(BASE / 'abi-v1/result.json')
    assert plan['EDR_helper_sha256'] == install['admission_sha256'] == helper['products']['candidate']['sha256'] == abi['binary_sha256'] == '9d5e091fd3edfa6ea1bf6165a7e709edefe0febb82bf4bf76a127da7ce98bf65'
    assert sha(helper['products']['candidate']['binary']) == plan['EDR_helper_sha256']
    assert helper['baseline_reproduction']['original_sha256'] == old['EDR_helper_sha256']
    assert helper['baseline_reproduction']['canonical_signed_bytes_identical'] and helper['baseline_reproduction']['installed_input_unchanged']
    assert helper['imports_unchanged'] and helper['exports_unchanged'] and helper['loads_unchanged']
    assert helper['pointer_write_and_once_contract_unchanged'] and helper['additional_threads'] == 0
    assert abi['total_imports'] == 53 and not abi['missing_imports']
    previous = load(PRIOR / 'slot-delta/install-plan.json')
    for name, row in install['rows'].items():
        for key in ('path', 'cnid', 'mode', 'data_block', 'data_blocks', 'old_logical', 'old_file_sha256'):
            assert row[key] == previous['rows'][name][key], (name, key)
        if name != 'admission':
            assert row['new_file_sha256'] == previous['rows'][name]['new_file_sha256']
    core = install['rows']['core']
    assert core['old_logical'] == 8407792 and core['new_logical'] == 8391360 < core['data_blocks'] * 4096 == 8409088
    assert plan['owned_core_sha256'] == core['new_file_sha256'] == install['core_sha256'] == 'dc26b7b613345f84d2e8e2636a1948be75b3d400418291e3b2281176a4070954'
    assert install['rows']['admission']['new_logical'] == 53520 <= install['rows']['admission']['data_blocks'] * 4096
    assert plan['install_userdata_bytes'] == install['install_write_bytes'] == 10301440
    assert plan['maximum_restore_userdata_bytes'] == install['restore_max_write_bytes'] == 10305536
    assert plan['normal_userdata_write_bytes_max'] == 10301440 + 10305536 == 20606976
    assert plan['maximum_userdata_write_bytes'] == 10301440 + 4 * 10305536 == 51523584
    assert plan['misc_write_bytes'] == 13 and plan['maximum_host_misc_write_bytes'] == 26
    assert plan['temporary_boots'] == 1 and plan['boot_retries'] == 0
    assert plan['maximum_fastboot_reboot_recovery_fallbacks'] == 1
    assert plan['scripted_strokes'] == 13 and plan['scripted_reports'] == 442
    assert plan['wake_button_pairs_max'] == 1 and plan['main_thread_sampling']['max_samples'] == 64
    assert plan['process_sampling']['max_register_samples'] == 1024
    assert not plan['process_sampling']['hard_realtime_pause_limit'] and not plan['main_thread_sampling']['hard_realtime_pause_limit']
    restore = load(PRIOR / 'execution/independent-restore.json')
    assert plan['root_header_sha256'] == ready['root_header_sha256'] == restore['root_header_sha256'] == 'bd32497b0e9a8dbf43d6431b5eb35d76502c44653acfde5add464fd9863e20db'
    assert restore['misc_original_4096_bytes_match']
    assert load(BASE / 'expected-baseline.json') == load(PRIOR / 'execution/restored-capture/result.json')
    bound = load(BASE / 'storage-bound.json')
    total = bound['full_captures'] * bound['per_capture_max_bytes'] + sum(
        v for k, v in bound.items() if k.endswith('_max_bytes') and k != 'per_capture_max_bytes')
    assert total == bound['worst_case_bytes'] == 535658128 < bound['reserve_bytes'] == plan['storage_reserve_bytes'] == 536870912
    budget = load(BASE / 'storage-trial-admission.json')
    assert budget['admitted'] and budget['planned_batch_bytes'] == 536870912
    assert budget['current_accounted_bytes'] + 536870912 <= 500000000000
    for name in ('install', 'restore'):
        model = load(BASE / (name + '-model-review.json'))
        assert model['base_plan_sha256'] == sha(BASE / 'slot-delta/install-plan.json')
        assert model['partial_write_failure_tested'] and model['rollback_verified'] and model['rollback_failure_reported']
    assert load(BASE / 'root-host-v1/result.json')['paired_request_observations'] == 6900
    cache = load(BASE / 'cache-host-v3/result.json')
    assert len(cache['scenarios']) == 13 and cache['zero_hit_PTE_sync_allocations_verified']
    workload = load(BASE / 'workload-host-v2/result.json')
    assert workload['requests'] == 512 and workload['counts'] == {'baseline': {'backing': 512, 'sync': 1024}, 'candidate': {'backing': 6, 'sync': 12}}
    assert workload['identical_handles_sizes_flags_and_zeroed_contents'] and not workload['performance_FPS_claimed']
    assert load(BASE / 'reuse-log-test.json')['actual334_rejected']
    assert load(BASE / 'analysis-order-test.json')['actual333_negative_timeline_refused']
    runner_text = (WORK / 'tools/run-sb-cadence-trial.py').read_text()
    assert "native_perf['active']" in runner_text and "fault_cache['active']" in runner_text
    # The inherited active fault-query qualification requires a complete, frozen
    # API prefix (valid=1,pending=0) before a BC335 run can return success.
    inspect = runner_text[runner_text.index('def inspect_fault_query_cache'):runner_text.index('def main')]
    assert "headers==[('1','0')]" in inspect
    function = next(n for n in ast.parse(runner_text).body if isinstance(n, ast.FunctionDef) and n.name == 'authorization')
    flags = ast.literal_eval(next(n.value for n in function.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'expected' for t in n.targets)))
    assert len(flags) == 34 and 'allow_completed_owned_BO_cache' in flags and 'allow_surface_retirement' in flags
    assert 'BC 0335 gate refused before any device command; observation classification checked' in (BASE / 'gate-test.log').read_text()
    files = [Path(__file__), BASE / 'ready.json', BASE / 'trial-plan.json', BASE / 'gate-test.log',
             WORK / 'docs/gauguin-bo-reuse-335-trial-20261116.md']
    result = dict(state='reviewed-BC335-frozen-buffer-reuse-trial', pin_count=ready['pin_count'],
                  all_pins_unchanged=True, unchanged_334_core=True, only_helper_payload_differs_from334=True,
                  changed_plan_keys=sorted(changed), storage_bound_independently_recomputed=total,
                  consent_flags=len(flags), approval_absent=True, execution_absent=True, device_commands=0,
                  input_pins={str(p.resolve()): sha(p) for p in files})
    with (BASE / 'final-review.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
