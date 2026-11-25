#!/usr/bin/env python3
"""Freeze SURF334 against the independently restored, failed 0333 trial."""
from pathlib import Path
import copy
import hashlib
import json

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
STATE = WORK / 'research/tmp/surface-retire-334'
PRIOR = MAIN / 'research/tmp/gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333'
HEADER = '2083806fcadb51c5624b0fb78cfc4f4176699bf7727f5ca543ae5c090b4ebd46'
CORE = 'dc26b7b613345f84d2e8e2636a1948be75b3d400418291e3b2281176a4070954'
SURFACE_POLICY = dict(close_before_reimport=True, wait_releases_cache_mutex=True,
                      weak_owner_identity_checked=True, exception_safe_publication=True,
                      Buffer_layout_unchanged=True, wait_pairs_max=64, record_max_bytes=128,
                      analysis_max_bytes=131072, result_copy_max_bytes=65536,
                      additional_threads=0, additional_GPU_submissions=0, hard_wait_limit=False)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def main():
    assert not any((STATE / n).exists() for n in ('ready.json', 'trial-plan.json', 'approval.json', 'execution'))
    assert sha(PRIOR / 'ready.json') == '4467a84fa2f1372fa07693d4ed68feb1b813ad8d56247971734a9dc7930a1bac'
    parent_ready = load(PRIOR / 'ready.json')
    assert parent_ready['pin_count'] == 15952
    pins = dict(parent_ready['input_pins'])
    def pin(path, digest=None):
        path = str(Path(path).resolve())
        digest = digest or sha(path)
        assert path not in pins or pins[path] == digest, path
        pins[path] = digest
    def receipt(path):
        data = load(path)
        pin(path)
        for source, digest in data.get('input_pins', {}).items():
            if isinstance(digest, dict):
                assert Path(source).stat().st_mtime_ns == digest['mtime_ns']
                digest = digest['sha256']
            pin(source, digest)
        return data
    terminal = receipt(PRIOR / 'execution/result.json')
    restored = receipt(PRIOR / 'execution/independent-restore.json')
    assert terminal['state'] == 'trial-incomplete-or-failed' and terminal['restored']
    assert terminal['boot_attempts'] == 1 and 'malformed tl: M record' in terminal['error']
    assert restored['state'] == 'independently-verified-six-original-files-and-misc'
    assert restored['misc_original_4096_bytes_match'] and restored['root_header_sha256'] == HEADER
    expected = receipt(STATE / 'expected-baseline.json')
    assert expected == load(PRIOR / 'execution/restored-capture/result.json')
    assert expected['root_header_sha256'] == HEADER
    profile = receipt(STATE / 'capture-profile.json')
    assert profile['expected_header_sha256'] == HEADER and profile['trial_instance'] == 'surface-retire-334'
    assert profile['files'] == load(PRIOR / 'capture-profile.json')['files']
    capture = receipt(STATE / 'slot-capture/result.json')
    install = receipt(STATE / 'slot-delta/install-plan.json')
    assert capture['state'] == 'readonly-six-file-SURF334-capture' and capture['root_header_sha256'] == HEADER
    assert capture['baseline_sha256'] == sha(STATE / 'expected-baseline.json')
    assert install['state'] == 'prepared-six-file-SURF334-cadence-delta'
    assert install['capture_sha256'] == sha(STATE / 'slot-capture/result.json')
    assert install['core_sha256'] == CORE and install['changed_ranges'] == 11
    assert install['install_write_bytes'] == 10301440 and install['restore_max_write_bytes'] == 10305536
    previous_install = load(PRIOR / 'slot-delta/install-plan.json')
    for name, row in install['rows'].items():
        old = previous_install['rows'][name]
        for key in ('path', 'cnid', 'mode', 'old_logical', 'old_file_sha256', 'data_block', 'data_blocks'):
            assert row[key] == old[key], (name, key)
        if name != 'core':
            assert row['new_file_sha256'] == old['new_file_sha256']
    prepared = receipt(STATE / 'prepared-v1/result.json')
    assert prepared['changed_files'] == ['include/hakios-metal/command.hpp', 'src/command.cpp']
    for variant, entries in prepared['source_pins'].items():
        for name, digest in entries.items():
            pin(Path(prepared['sources'][variant]) / name, digest)
    lifetime = receipt(STATE / 'lifetime-host-v2/result.json')
    core_host = receipt(STATE / 'core-host-v1/result.json')
    retention = receipt(STATE / 'retention-host-v1/result.json')
    native = receipt(STATE / 'native-v2/result.json')
    assert lifetime['state'] == 'SURF334-actual-cache-lifetime-and-publication-checks-passed'
    assert lifetime['simultaneous_importers_tested'] == 16 and lifetime['stress_imports'] == 3200
    assert core_host['state'] == 'SURF334-full-core-host-equivalence-and-ownership-passed'
    assert core_host['equivalence']['cases'] == 96 and core_host['ownership_scenarios'] == 23
    assert core_host['upstream_regression_results']['unchanged_preexisting_failed_cases'] == 7
    assert retention['state'] == 'SURF334-surface-retained-through-completion-passed' and retention['cases_per_variant'] == 2
    assert native['state'] == 'SURF334-native-baseline-canonical-signature-reproduced-candidate-signed'
    assert native['baseline_reproduction']['canonical_signed_bytes_identical']
    assert native['baseline_reproduction']['installed_input_unchanged']
    assert native['baseline_reproduction']['original_sha256'] == previous_install['core_sha256']
    assert native['inputs_unchanged'] and native['imports_unchanged'] and native['loads_unchanged']
    assert not native['exports_added'] and not native['exports_removed']
    assert all(native['baseline_object_matches'].values()) and len(native['baseline_object_matches']) == 12
    product = native['products']['candidate']
    assert product['sha256'] == CORE and product['bytes'] == 8391360 <= 8409088
    pin(product['binary'], CORE)
    assert install['core_receipt_sha256'] == sha(STATE / 'native-v2/result.json')
    for name in ('install', 'restore'):
        model = receipt(STATE / (name + '-model-review.json'))
        assert model['base_plan_sha256'] == sha(STATE / 'slot-delta/install-plan.json')
        assert model['partial_write_failure_tested'] and model['rollback_verified'] and model['rollback_failure_reported']
        assert model['device_writes'] == model['device_boots'] == 0
    parser = receipt(STATE / 'surface-log-test.json')
    order = receipt(STATE / 'analysis-order-test.json')
    assert parser['positive_cases'] == 3 and parser['malformed_cases'] == 6 and parser['actual333_does_not_activate']
    assert order['actual333_negative_timeline_refused'] and order['original333_result_unchanged']
    assert order['restoration_precedes_analysis'] and order['surface_and_cache_diagnostics_before_final_failure']
    wake = receipt(STATE / 'wake-validation-test.json')
    logs = receipt(STATE / 'log-storage-test.json')
    assert wake['positive_cases'] == 2 and wake['negative_cases'] == 12
    assert logs['no_log_truncation'] and wake['executor_sha256'] == logs['executor_sha256'] == sha(WORK / 'tools/run-sb-cadence-trial.py')
    plan = copy.deepcopy(load(PRIOR / 'trial-plan.json'))
    plan.update(state='prepared-surf334-one-shot', root_header_sha256=HEADER,
                install_plan_sha256=sha(STATE / 'slot-delta/install-plan.json'),
                owned_core_sha256=CORE, all_core_TUs_recompiled=True, unchanged_331_core=False,
                unchanged_333_image=True, unchanged_333_helper=True, diagnostic_only=False,
                performance_candidate=True, surface_retirement=SURFACE_POLICY)
    assert sha(plan['image']) == parent_ready['image_sha256'] == plan['image_sha256']
    pin(plan['image'], plan['image_sha256'])
    assert plan['device_writes'] == plan['boot_attempts'] == 0 and not plan['physical_FPS_qualified']
    bound = copy.deepcopy(load(PRIOR / 'storage-bound.json'))
    bound.update(surface_analysis_max_bytes=131072, surface_result_copy_max_bytes=65536,
                 joint_rejection_receipt_max_bytes=65536, worst_case_bytes=527269520)
    assert bound['worst_case_bytes'] < bound['reserve_bytes'] == plan['storage_reserve_bytes'] == 536870912
    budget = receipt(STATE / 'storage-trial-admission.json')
    assert budget['admitted'] and budget['planned_batch_bytes'] == plan['storage_reserve_bytes']
    assert budget['current_accounted_bytes'] + budget['planned_batch_bytes'] <= 500000000000
    receipt(STATE / 'storage-pretrial-whole-admission.json')
    # Pin all trial code, source checks, models, private immutable captures and
    # inherited restoration evidence. NOTES remains a live handoff, not an input.
    paths = [Path(__file__), WORK / 'tools/review-surface-retire-trial.py', PRIOR / 'ready.json',
             WORK / 'docs/gauguin-surface-retire-334-trial-20261116.md',
             WORK / 'docs/gauguin-surface-retire-334-local-20261116.md']
    for pattern in ('tools/*sb-cadence*.py', 'tools/sb_cadence_launch.py', 'tests/test_sb_cadence*.py',
                    'tools/*surface*retir*.py', 'tools/surface_signature_compare.py', 'tests/test_surface_retire*.py',
                    'tests/fixtures/surface_ret*.cpp'):
        paths += list(WORK.glob(pattern))
    for name in ('analyze-process-samples328.py', 'analyze-process-samples.py', 'analyze-submit-reject-log.py',
                 'analyze-stage-cache-log.py', 'analyze-c4-queue-log.py', 'analyze-sb-rate-log.py',
                 'analyze-sb-stack-log.py', 'analyze-ui-timeline.py', 'ui_trace_log.py', 'analyze-map-query-log.py',
                 'analyze-native-perf-log.py', 'analyze-present-retry-log.py', 'analyze-bo-allocation-log.py',
                 'analyze-sb-cadence.py'):
        path = WORK / 'tools' / name
        assert sha(path) == sha(PRIOR.parents[2] / 'tools' / name), name
        paths.append(path)
    paths += [p for p in (PRIOR / 'execution/restored-capture').iterdir() if p.is_file()]
    for folder in ('slot-capture', 'slot-delta'):
        paths += [p for p in (STATE / folder).iterdir() if p.is_file()]
    for path in paths:
        pin(path)
    for path, digest in pins.items():
        assert sha(path) == digest, path
    save(STATE / 'trial-plan.json', plan)
    save(STATE / 'storage-bound.json', bound)
    pin(STATE / 'trial-plan.json')
    pin(STATE / 'storage-bound.json')
    ready = dict(state='ready-surf334-one-shot', trial_plan_sha256=sha(STATE / 'trial-plan.json'),
                 install_plan_sha256=sha(STATE / 'slot-delta/install-plan.json'), image_sha256=plan['image_sha256'],
                 root_header_sha256=HEADER, input_pins=dict(sorted(pins.items())), pin_count=len(pins),
                 approval_pending=True, device_writes=0, boot_attempts=0)
    save(STATE / 'ready.json', ready)
    print(json.dumps({k: v for k, v in ready.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
