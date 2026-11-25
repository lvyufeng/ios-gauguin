#!/usr/bin/env python3
"""Independently check the frozen SURF334 userland delta and inherited boot scope."""
from pathlib import Path
import ast
import hashlib
import json

WORK = Path(__file__).resolve().parents[1]
BASE = WORK / 'research/tmp/surface-retire-334'
PRIOR = WORK.parent / 'gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def main():
    assert not (BASE / 'approval.json').exists() and not (BASE / 'execution').exists()
    ready, plan, install = (load(BASE / n) for n in ('ready.json', 'trial-plan.json', 'slot-delta/install-plan.json'))
    assert ready['state'] == 'ready-surf334-one-shot' and ready['pin_count'] == len(ready['input_pins']) > 15952
    assert ready['trial_plan_sha256'] == sha(BASE / 'trial-plan.json')
    assert ready['install_plan_sha256'] == sha(BASE / 'slot-delta/install-plan.json')
    for path, digest in ready['input_pins'].items():
        assert sha(path) == digest, path
    old = load(PRIOR / 'trial-plan.json')
    changed = {key for key in set(plan) | set(old) if plan.get(key) != old.get(key)}
    assert changed == {'state', 'root_header_sha256', 'install_plan_sha256', 'owned_core_sha256',
                       'all_core_TUs_recompiled', 'unchanged_331_core', 'diagnostic_only',
                       'performance_candidate', 'unchanged_333_image', 'unchanged_333_helper', 'surface_retirement'}, changed
    assert plan['state'] == 'prepared-surf334-one-shot' and not plan['diagnostic_only'] and plan['performance_candidate']
    assert not plan['physical_FPS_qualified']
    for key in ('image', 'image_sha256', 'kernel_banner', 'kernel_identity', 'boot_command',
                'EDR_helper_sha256', 'C4_sha256', 'GPU_native_profile', 'process_sampling',
                'main_thread_sampling', 'display_retry', 'BO_allocation_diagnostics'):
        assert plan[key] == old[key], key
    assert sha(plan['image']) == ready['image_sha256'] == '373f3bbef16104e5dd08617c6fcfde2d4dc07217a170abde0063a2052af39939'
    assert plan['surface_retirement'] == dict(close_before_reimport=True, wait_releases_cache_mutex=True,
        weak_owner_identity_checked=True, exception_safe_publication=True, Buffer_layout_unchanged=True,
        wait_pairs_max=64, record_max_bytes=128, analysis_max_bytes=131072, result_copy_max_bytes=65536,
        additional_threads=0, additional_GPU_submissions=0, hard_wait_limit=False)
    previous = load(PRIOR / 'slot-delta/install-plan.json')
    for name, row in install['rows'].items():
        for key in ('path', 'cnid', 'mode', 'data_block', 'data_blocks', 'old_logical', 'old_file_sha256'):
            assert row[key] == previous['rows'][name][key]
        if name != 'core':
            assert row['new_file_sha256'] == previous['rows'][name]['new_file_sha256']
    core = install['rows']['core']
    assert core['old_logical'] == 8407792 and core['new_logical'] == 8391360 < core['data_blocks'] * 4096 == 8409088
    assert plan['owned_core_sha256'] == core['new_file_sha256'] == install['core_sha256'] == 'dc26b7b613345f84d2e8e2636a1948be75b3d400418291e3b2281176a4070954'
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
    assert plan['root_header_sha256'] == ready['root_header_sha256'] == restore['root_header_sha256'] == '2083806fcadb51c5624b0fb78cfc4f4176699bf7727f5ca543ae5c090b4ebd46'
    assert restore['misc_original_4096_bytes_match']
    assert load(BASE / 'expected-baseline.json') == load(PRIOR / 'execution/restored-capture/result.json')
    bound = load(BASE / 'storage-bound.json')
    total = bound['full_captures'] * bound['per_capture_max_bytes'] + sum(
        value for key, value in bound.items() if key.endswith('_max_bytes') and key != 'per_capture_max_bytes')
    assert total == bound['worst_case_bytes'] == 527269520 < bound['reserve_bytes'] == plan['storage_reserve_bytes'] == 536870912
    budget = load(BASE / 'storage-trial-admission.json')
    assert budget['admitted'] and budget['planned_batch_bytes'] == 536870912
    assert budget['current_accounted_bytes'] + 536870912 <= 500000000000
    for name in ('install', 'restore'):
        model = load(BASE / (name + '-model-review.json'))
        assert model['base_plan_sha256'] == sha(BASE / 'slot-delta/install-plan.json')
        assert model['partial_write_failure_tested'] and model['rollback_verified'] and model['rollback_failure_reported']
    native = load(BASE / 'native-v2/result.json')
    assert native['baseline_reproduction']['canonical_signed_bytes_identical']
    assert native['baseline_reproduction']['original_sha256'] == previous['core_sha256']
    assert native['imports_unchanged'] and native['loads_unchanged'] and not native['exports_added'] and not native['exports_removed']
    assert sha(native['products']['candidate']['binary']) == plan['owned_core_sha256']
    assert load(BASE / 'retention-host-v1/result.json')['callback_reimport_same_owner']
    assert load(BASE / 'analysis-order-test.json')['actual333_negative_timeline_refused']
    assert load(BASE / 'surface-log-test.json')['actual333_does_not_activate']
    function = next(n for n in ast.parse((WORK / 'tools/run-sb-cadence-trial.py').read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'authorization')
    flags = ast.literal_eval(next(n.value for n in function.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'expected' for t in n.targets)))
    assert len(flags) == 33 and 'allow_surface_retirement' in flags
    assert 'SURF 0334 gate refused before any device command; observation classification checked' in (BASE / 'gate-test.log').read_text()
    files = [Path(__file__), BASE / 'ready.json', BASE / 'trial-plan.json', BASE / 'gate-test.log',
             WORK / 'docs/gauguin-surface-retire-334-trial-20261116.md']
    result = dict(state='reviewed-SURF334-frozen-userland-trial', pin_count=ready['pin_count'],
                  all_pins_unchanged=True, only_core_payload_differs_from333=True,
                  unchanged_kernel_image_and_helper=True, changed_plan_keys=sorted(changed),
                  storage_bound_independently_recomputed=total, consent_flags=len(flags),
                  approval_absent=True, execution_absent=True, device_commands=0,
                  input_pins={str(p.resolve()): sha(p) for p in files})
    with (BASE / 'final-review.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
