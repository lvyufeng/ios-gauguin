#!/usr/bin/env python3
"""Independently audit the exact0336 candidate, scope and restoration bounds."""
from pathlib import Path
import ast
import hashlib
import json

WORK = Path(__file__).resolve().parents[1]
BASE = WORK / 'research/tmp/bo-reuse-336'
PRIOR = WORK.parent / 'gauguin-bo-reuse-worktree-20261116/research/tmp/bo-reuse-335'
HOST = PRIOR.parent / 'bo-reuse-336/host-v1'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def main():
    assert not (BASE / 'approval.json').exists() and not (BASE / 'execution').exists()
    ready, plan, install = (load(BASE / name) for name in ('ready.json', 'trial-plan.json', 'slot-delta/install-plan.json'))
    assert ready['state'] == 'ready-bcreuse336-one-shot'
    assert ready['pin_count'] == len(ready['input_pins']) > 16983
    assert ready['trial_plan_sha256'] == sha(BASE / 'trial-plan.json')
    assert ready['install_plan_sha256'] == sha(BASE / 'slot-delta/install-plan.json')
    for path, digest in ready['input_pins'].items():
        assert sha(path) == digest, path
    old = load(PRIOR / 'trial-plan.json')
    changed = {k for k in set(plan) | set(old) if plan.get(k) != old.get(k)}
    assert changed == {'state', 'root_header_sha256', 'install_plan_sha256', 'image', 'image_sha256',
                       'kernel_banner', 'kernel_identity', 'EDR_helper_sha256', 'unchanged_335_core',
                       'cache_full_replacement', 'storage_reserve_bytes'}, changed
    assert plan['state'] == 'prepared-bcreuse336-one-shot' and plan['performance_candidate']
    assert not plan['diagnostic_only'] and not plan['physical_FPS_qualified']
    assert plan['unchanged_335_core'] and plan['unchanged_334_core'] and not plan['all_core_TUs_recompiled']
    for key in ('owned_core_sha256', 'C4_sha256', 'boot_command', 'GPU_native_profile',
                'process_sampling', 'main_thread_sampling', 'surface_retirement', 'display_retry',
                'BO_allocation_diagnostics', 'completed_owned_BO_cache'):
        assert plan[key] == old[key], key
    assert plan['cache_full_replacement'] == dict(maximum_mappings_removed_per_return=1,
        rotating_cursor=True, single_victim_must_satisfy_byte_limit=True,
        insufficient_single_victim_releases_new=True, cache_slots=32, cache_bytes=16777216,
        eligible_completed_owned_only=True, failure_keeps_DMA_escrow=True, new_GPU_commands=0, new_threads=0)
    image, review = load(BASE / 'ui336-image.json'), load(BASE / 'ui336-review.json')
    assert sha(plan['image']) == image['image_sha256'] == review['image_sha256'] == ready['image_sha256'] == '6e67abeb023f922addcb8b789eb46492ff038ee37b09fb00667c01e1d2d83a96'
    assert image['image_bytes'] == plan['image_bytes'] == 20054016
    assert image['command_changes_from_0335'] == [] and image['command'] == plan['boot_command']
    assert review['raw_MachO_segment_bytes_verified'] and review['undefined_symbol_count'] == 0
    assert review['command_bytes'] == plan['command_bytes'] == 607
    manifest, previous = load(BASE / 'local-link/build-manifest.json'), load(PRIOR / 'local-link/build-manifest.json')
    assert set(manifest['object_replacements']) == set(previous['object_replacements'])
    changes = [k for k in manifest['object_replacements'] if manifest['object_replacements'][k] != previous['object_replacements'][k]]
    assert len(changes) == 1 and changes[0].endswith('/GauguinGPU.cpo')
    assert manifest['inputs_unchanged'] and manifest['baseline_relink_identical_except_LC_UUID']
    assert sha(manifest['kernel']['path']) == manifest['kernel']['sha256'] == review['kernel_sha256'] == '2bf5926f37e0f453ed080ee6602853397332a6c701af67e3b48f4c6bf15cb7aa'
    assert manifest['build_identity']['id'] == plan['kernel_identity'] == 'xnu-local336-b766c80db4f243d7ae172262b13a8bc1'
    assert manifest['kernel_banner'] == plan['kernel_banner']
    assert (BASE / 'kernel-source/iokit/Kernel/arm/GauguinGPU.cpp').read_bytes() == (HOST / 'candidate-GauguinGPU.cpp').read_bytes()
    helper, abi = load(BASE / 'edr-native-v1/result.json'), load(BASE / 'abi-v1/result.json')
    assert plan['EDR_helper_sha256'] == install['admission_sha256'] == helper['products']['candidate']['sha256'] == abi['binary_sha256'] == '60a90e85a452fa9e2171aa572158f225a9a48a781d5c8a5dcdb424546271b0a5'
    assert sha(helper['products']['candidate']['binary']) == plan['EDR_helper_sha256']
    assert helper['products']['baseline']['sha256'] == helper['baseline_reproduction']['original_sha256'] == old['EDR_helper_sha256']
    assert helper['baseline_reproduction']['installed_input_unchanged'] and helper['baseline_reproduction']['canonical_signed_bytes_identical']
    assert helper['imports_unchanged'] and helper['exports_unchanged'] and helper['loads_unchanged']
    assert helper['pointer_write_and_once_contract_unchanged'] and abi['total_imports'] == 53 and not abi['missing_imports']
    assert load(BASE / 'edr-host-v1/result.json')['checks'] == 2143
    previous_install = load(PRIOR / 'slot-delta/install-plan.json')
    for name, row in install['rows'].items():
        for key in ('path', 'cnid', 'mode', 'data_block', 'data_blocks', 'old_logical', 'old_file_sha256'):
            assert row[key] == previous_install['rows'][name][key], (name, key)
        if name != 'admission':
            assert row['new_file_sha256'] == previous_install['rows'][name]['new_file_sha256']
    assert plan['owned_core_sha256'] == install['core_sha256'] == 'dc26b7b613345f84d2e8e2636a1948be75b3d400418291e3b2281176a4070954'
    assert plan['install_userdata_bytes'] == install['install_write_bytes'] == 10301440
    assert plan['maximum_restore_userdata_bytes'] == install['restore_max_write_bytes'] == 10305536
    assert plan['normal_userdata_write_bytes_max'] == 20606976 and plan['maximum_userdata_write_bytes'] == 51523584
    assert plan['misc_write_bytes'] == 13 and plan['maximum_host_misc_write_bytes'] == 26
    assert plan['temporary_boots'] == 1 and plan['boot_retries'] == 0 and plan['maximum_fastboot_reboot_recovery_fallbacks'] == 1
    assert plan['scripted_strokes'] == 13 and plan['scripted_reports'] == 442 and plan['wake_button_pairs_max'] == 1
    assert plan['main_thread_sampling']['max_samples'] == 64 and plan['process_sampling']['max_register_samples'] == 1024
    assert not plan['main_thread_sampling']['hard_realtime_pause_limit'] and not plan['process_sampling']['hard_realtime_pause_limit']
    restore = load(PRIOR / 'execution/independent-restore.json')
    assert restore['misc_original_4096_bytes_match']
    assert plan['root_header_sha256'] == ready['root_header_sha256'] == restore['root_header_sha256'] == 'd68f4831dfed2e264140f000a02dd596d2cbc44d5409ac4388bdf23452df19fa'
    assert load(BASE / 'expected-baseline.json') == load(PRIOR / 'execution/restored-capture/result.json')
    assert load(PRIOR / 'execution/result.json')['state'] == 'BO333-allocation-phases-unqualified-root-restored'
    bound, before = load(BASE / 'storage-bound.json'), load(PRIOR / 'storage-bound.json')
    assert bound['per_capture_max_bytes'] == before['per_capture_max_bytes'] + 3 * 1048576 == 124287536
    assert bound['extra_log_copies_max_bytes'] == before['extra_log_copies_max_bytes'] + 3 * 1048576 == 68157440
    total = bound['full_captures'] * bound['per_capture_max_bytes'] + sum(v for k, v in bound.items() if k.endswith('_max_bytes') and k != 'per_capture_max_bytes')
    assert total == bound['worst_case_bytes'] == 548241040 < bound['reserve_bytes'] == plan['storage_reserve_bytes'] == 553648128
    budget = load(BASE / 'storage-trial-admission.json')
    assert budget['admitted'] and budget['planned_batch_bytes'] == 553648128
    assert budget['current_accounted_bytes'] + 553648128 <= 500000000000
    for name in ('install', 'restore'):
        model = load(BASE / (name + '-model-review.json'))
        assert model['base_plan_sha256'] == sha(BASE / 'slot-delta/install-plan.json')
        assert model['partial_write_failure_tested'] and model['rollback_verified'] and model['rollback_failure_reported']
    host = load(HOST / 'result.json')
    assert host['paired_hot_observations_identical'] == 1024 and len(host['new_scenarios']) == 5
    assert host['hot_request_counts']['policy-single']['candidate'] == {'backing': 1, 'sync': 2, 'hits': 511}
    assert host['hot_request_counts']['policy-wave']['candidate'] == {'backing': 8, 'sync': 16, 'hits': 504}
    assert load(BASE / 'root-host-v1/result.json')['paired_request_observations'] == 6900
    assert load(BASE / 'analysis-order-test.json')['actual333_negative_timeline_refused']
    assert load(PRIOR / 'reuse-log-test.json')['actual334_rejected']
    for name in ('ui_trace_log.py', 'analyze-bo-reuse-log.py', 'analyze-bo-allocation-log.py'):
        assert sha(WORK / 'tools' / name) == sha(PRIOR.parents[2] / 'tools' / name)
    source = (WORK / 'tools/run-sb-cadence-trial.py').read_text()
    assert "headers==[('1','0')]" in source and "allocation['coverage_qualified']" in source
    function = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'authorization')
    flags = ast.literal_eval(next(n.value for n in function.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'expected' for t in n.targets)))
    assert len(flags) == 35 and 'allow_cache_full_replacement' in flags
    assert 'BC 0336 gate refused before any device command; observation classification checked' in (BASE / 'gate-test.log').read_text()
    files = [Path(__file__), BASE / 'ready.json', BASE / 'trial-plan.json', BASE / 'gate-test.log', WORK / 'docs/gauguin-bo-reuse-336-trial-20261116.md']
    report = dict(state='reviewed-BC336-frozen-bounded-cache-replacement-trial', all_pins_unchanged=True,
                  pin_count=ready['pin_count'], unchanged_335_core=True, only_helper_payload_differs_from335=True,
                  changed_plan_keys=sorted(changed), storage_bound_independently_recomputed=total,
                  consent_flags=len(flags), prior335_unqualified_verdict_preserved=True,
                  approval_absent=True, execution_absent=True, device_commands=0,
                  input_pins={str(p.resolve()): sha(p) for p in files})
    with (BASE / 'final-review.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
