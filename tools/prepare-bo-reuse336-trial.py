#!/usr/bin/env python3
"""Freeze BC336 only after offline qualification and a fresh runtime budget."""
from pathlib import Path
import copy
import hashlib
import json

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
STATE = WORK / 'research/tmp/bo-reuse-336'
PRIOR = MAIN / 'research/tmp/gauguin-bo-reuse-worktree-20261116/research/tmp/bo-reuse-335'
HOST = PRIOR.parent / 'bo-reuse-336/host-v1'
CORE_RECEIPT = MAIN / 'research/tmp/gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334/native-v2/result.json'
BO333 = MAIN / 'research/tmp/gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333'
HEADER = 'd68f4831dfed2e264140f000a02dd596d2cbc44d5409ac4388bdf23452df19fa'
CORE = 'dc26b7b613345f84d2e8e2636a1948be75b3d400418291e3b2281176a4070954'
HELPER = '60a90e85a452fa9e2171aa572158f225a9a48a781d5c8a5dcdb424546271b0a5'
IMAGE = '6e67abeb023f922addcb8b789eb46492ff038ee37b09fb00667c01e1d2d83a96'
CACHE = dict(slots=32, bytes=16777216, max_bo_bytes=1048576, exact_size_and_flags=True,
             zero_before_new_handle=True, no_IOSurface=True, no_exported_alias=True,
             completed_only=True, residency_includes_cache=True, allocator_retry_max=1,
             reuse_event_kind=33, maximum_records_per_BO_request=7, new_GPU_commands=0, new_threads=0)


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
    assert sha(PRIOR / 'ready.json') == '631689d09a9cc19a3ea9752f920d6d323153148de20b88d6325adee9c23984e8'
    parent = load(PRIOR / 'ready.json')
    assert parent['pin_count'] == 16983
    pins = dict(parent['input_pins'])

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
                assert Path(source).stat().st_mtime_ns == digest['mtime_ns'], source
                digest = digest['sha256']
            pin(source, digest)
        return data

    terminal = receipt(PRIOR / 'execution/result.json')
    restored = receipt(PRIOR / 'execution/independent-restore.json')
    results_review = receipt(PRIOR / 'execution/results-review.json')
    assert terminal['state'] == 'BO333-allocation-phases-unqualified-root-restored' and terminal['restored']
    assert terminal['boot_attempts'] == 1
    assert sha(PRIOR / 'execution/results-review.json') == 'c95939d0789e7e37ca087c6e60e814f1cef54d0f96302b983d1d9a9b3d6db25b'
    assert results_review['all_pins_unchanged']
    assert restored['state'] == 'independently-verified-six-original-files-and-misc'
    assert restored['misc_original_4096_bytes_match'] and restored['root_header_sha256'] == HEADER
    expected = receipt(STATE / 'expected-baseline.json')
    assert expected == load(PRIOR / 'execution/restored-capture/result.json')
    profile = receipt(STATE / 'capture-profile.json')
    assert profile['expected_header_sha256'] == HEADER and profile['trial_instance'] == 'bo-reuse-336'
    assert profile['files'] == load(PRIOR / 'capture-profile.json')['files']
    capture = receipt(STATE / 'slot-capture/result.json')
    install = receipt(STATE / 'slot-delta/install-plan.json')
    assert capture['state'] == 'readonly-six-file-BC336-capture' and capture['root_header_sha256'] == HEADER
    assert capture['baseline_sha256'] == sha(STATE / 'expected-baseline.json')
    assert install['state'] == 'prepared-six-file-BC336-cadence-delta'
    assert install['capture_sha256'] == sha(STATE / 'slot-capture/result.json')
    assert install['core_sha256'] == CORE and install['admission_sha256'] == HELPER
    assert install['changed_ranges'] == 11 and install['install_write_bytes'] == 10301440
    assert install['restore_max_write_bytes'] == 10305536
    previous_install = load(PRIOR / 'slot-delta/install-plan.json')
    for name, row in install['rows'].items():
        old = previous_install['rows'][name]
        for key in ('path', 'cnid', 'mode', 'old_logical', 'old_file_sha256', 'data_block', 'data_blocks'):
            assert row[key] == old[key], (name, key)
        if name != 'admission':
            assert row['new_file_sha256'] == old['new_file_sha256'], name
    prepared = receipt(STATE / 'source-preparation.json')
    assert prepared['changed_files'] == ['iokit/Kernel/arm/GauguinGPU.cpp']
    assert prepared['source_change_reversible'] and prepared['completion_and_failure_escrow_unchanged']
    assert (STATE / 'kernel-source/iokit/Kernel/arm/GauguinGPU.cpp').read_bytes() == (HOST / 'candidate-GauguinGPU.cpp').read_bytes()
    host = receipt(HOST / 'result.json')
    root = receipt(STATE / 'root-host-v1/result.json')
    native = receipt(STATE / 'kernel-native-v1/result.json')
    replay = receipt(STATE / 'patch-replay-v1/result.json')
    parser = receipt(PRIOR / 'reuse-log-test.json')
    assert host['state'] == 'BC336-actual-cache-replacement-and-working-set-host-passed'
    assert len(host['original_scenarios']) == 13 and len(host['new_scenarios']) == 5
    assert host['paired_hot_observations_identical'] == 1024 and host['replacement_removals_per_return_max'] == 1
    assert host['original_byte_pressure_fallback_preserved'] and host['aliases_pending_fault_zeroing_and_caps_preserved']
    assert host['hot_request_counts'] == {
        'policy-single': {'baseline': {'backing':512,'sync':1024,'hits':0}, 'candidate': {'backing':1,'sync':2,'hits':511}},
        'policy-wave': {'baseline': {'backing':512,'sync':1024,'hits':0}, 'candidate': {'backing':8,'sync':16,'hits':504}}}
    assert host['inputs_unchanged'] and not host['physical_FPS_qualified'] and host['device_commands'] == 0
    assert root['state'] == 'BC336-root-client-equivalence-and-phase-contract-passed'
    assert root['parent_candidate_observations_identical'] and root['paired_request_observations'] == 6900
    assert root['root_cache_disabled'] and root['maximum_records_per_allocation'] == 6
    assert native['state'] == 'passed-native-ARM64-selected-TUs' and native['inputs_unchanged']
    assert native['header_config_inputs'] == 2133 and native['reference_files_unchanged']
    assert replay['state'] == 'BC336-patch-forward-reverse-exact'
    assert parser['positive_cases'] == 2 and parser['negative_cases'] == 16 and parser['actual334_rejected']
    for name in ('ui_trace_log.py','analyze-bo-reuse-log.py','analyze-bo-allocation-log.py'):
        assert sha(WORK / 'tools' / name) == sha(PRIOR.parents[2] / 'tools' / name)
    manifest = receipt(STATE / 'local-link/build-manifest.json')
    image = receipt(STATE / 'ui336-image.json')
    review = receipt(STATE / 'ui336-review.json')
    assert manifest['inputs_unchanged'] and manifest['baseline_relink_identical_except_LC_UUID']
    assert manifest['project_revision'].startswith('1267220') and manifest['link_exit'] == 0
    assert sha(manifest['kernel']['path']) == image['kernel_sha256'] == review['kernel_sha256'] == manifest['kernel']['sha256']
    pin(manifest['kernel']['path'], manifest['kernel']['sha256'])
    assert sha(image['image']) == IMAGE == image['image_sha256'] == review['image_sha256']
    pin(image['image'], IMAGE)
    assert image['command_changes_from_0335'] == [] and image['command'] == load(PRIOR / 'trial-plan.json')['boot_command']
    assert review['raw_MachO_segment_bytes_verified'] and review['undefined_symbol_count'] == 0
    assert review['command_bytes'] == 607 and not image['booted'] and image['device_writes'] == 0
    helper_host = receipt(STATE / 'edr-host-v1/result.json')
    helper = receipt(STATE / 'edr-native-v1/result.json')
    abi = receipt(STATE / 'abi-v1/result.json')
    assert helper_host['checks'] == 2143 and not helper_host['actual_iOS_image_mutated']
    assert helper['state'] == 'native-EDR336-kernel-scope-canonical-baseline-candidate-signed'
    assert helper['baseline_reproduction']['canonical_signed_bytes_identical']
    assert helper['baseline_reproduction']['installed_input_unchanged']
    assert helper['baseline_reproduction']['original_sha256'] == load(PRIOR / 'trial-plan.json')['EDR_helper_sha256']
    assert helper['pointer_write_and_once_contract_unchanged'] and helper['imports_unchanged']
    assert helper['exports_unchanged'] and helper['loads_unchanged'] and helper['inputs_unchanged']
    product = helper['products']['candidate']
    assert product['sha256'] == HELPER == abi['binary_sha256'] and product['bytes'] == 53520 <= 73728
    pin(product['binary'], HELPER)
    assert abi['total_imports'] == 53 and not abi['missing_imports']
    assert install['core_receipt_sha256'] == sha(CORE_RECEIPT)
    for name in ('install', 'restore'):
        model = receipt(STATE / (name + '-model-review.json'))
        assert model['base_plan_sha256'] == sha(STATE / 'slot-delta/install-plan.json')
        assert model['partial_write_failure_tested'] and model['rollback_verified'] and model['rollback_failure_reported']
        assert model['device_writes'] == model['device_boots'] == 0
    order = receipt(STATE / 'analysis-order-test.json')
    assert order['actual333_negative_timeline_refused'] and order['original333_result_unchanged']
    assert order['restoration_precedes_analysis'] and order['surface_and_cache_diagnostics_before_final_failure']
    wake = receipt(STATE / 'wake-validation-test.json')
    logs = receipt(STATE / 'log-storage-test.json')
    assert wake['positive_cases'] == 2 and wake['negative_cases'] == 12 and logs['no_log_truncation']
    assert wake['executor_sha256'] == logs['executor_sha256'] == sha(WORK / 'tools/run-sb-cadence-trial.py')
    plan = copy.deepcopy(load(PRIOR / 'trial-plan.json'))
    plan.update(state='prepared-bcreuse336-one-shot', root_header_sha256=HEADER,
                install_plan_sha256=sha(STATE / 'slot-delta/install-plan.json'),
                image=image['image'], image_sha256=IMAGE, image_bytes=image['image_bytes'],
                kernel_banner=image['kernel_banner'], kernel_identity=image['build_identity'],
                EDR_helper_sha256=HELPER, all_core_TUs_recompiled=False,
                unchanged_333_image=False, unchanged_333_helper=False, unchanged_334_core=True,
                completed_owned_BO_cache=CACHE, unchanged_335_core=True,
                cache_full_replacement=load(STATE / 'cache-policy.json'), storage_reserve_bytes=553648128)
    assert plan['owned_core_sha256'] == CORE and not plan['physical_FPS_qualified']
    assert plan['device_writes'] == plan['boot_attempts'] == 0
    bound = copy.deepcopy(load(PRIOR / 'storage-bound.json'))
    bound.update(per_capture_max_bytes=124287536, extra_log_copies_max_bytes=68157440,
                 reserve_bytes=553648128, worst_case_bytes=548241040)
    total = bound['full_captures'] * bound['per_capture_max_bytes'] + sum(
        v for k, v in bound.items() if k.endswith('_max_bytes') and k != 'per_capture_max_bytes')
    assert total == bound['worst_case_bytes'] < bound['reserve_bytes'] == plan['storage_reserve_bytes'] == 553648128
    budget = receipt(STATE / 'storage-trial-admission.json')
    assert budget['admitted'] and budget['planned_batch_bytes'] == plan['storage_reserve_bytes']
    assert budget['current_accounted_bytes'] + budget['planned_batch_bytes'] <= 500000000000
    batch = receipt(STATE / 'storage-whole-batch-admission.json')
    assert batch['admitted'] and batch['planned_batch_bytes'] == 800000000
    paths = [Path(__file__), WORK / 'tools/review-bo-reuse336-trial.py', PRIOR / 'ready.json',
             WORK / 'docs/gauguin-bo-reuse-336-trial-20261116.md',
             STATE / 'storage-whole-batch-components.json']
    for pattern in ('tools/*sb-cadence*.py', 'tools/sb_cadence_launch.py', 'tests/test_sb_cadence*.py',
                    'tools/*bo*reuse*.py', 'tests/test_bo_reuse*.py', 'tests/fixtures/bo_reuse*',
                    'tools/bo_reuse335_patch.py', 'xnu/patches/0248*', 'xnu/patches/series',
                    'tools/build-edr-kernel-scope.py', 'graphics/gauguin-edr-default/*',
                    'tools/*surface*retir*.py', 'tools/surface_signature_compare.py'):
        paths += list(WORK.glob(pattern))
    for name in ('analyze-process-samples328.py', 'analyze-process-samples.py', 'analyze-submit-reject-log.py',
                 'analyze-stage-cache-log.py', 'analyze-c4-queue-log.py', 'analyze-sb-rate-log.py',
                 'analyze-sb-stack-log.py', 'analyze-ui-timeline.py', 'ui_trace_log.py', 'analyze-map-query-log.py',
                 'analyze-native-perf-log.py', 'analyze-present-retry-log.py', 'analyze-bo-allocation-log.py',
                 'analyze-sb-cadence.py', 'analyze-bo-reuse-log.py'):
        paths.append(WORK / 'tools' / name)
    for folder in ('slot-capture', 'slot-delta', 'kernel-source', 'kernel-native-v1', 'root-host-v1', 'edr-host-v1', 'edr-native-v1', 'abi-v1', 'patch-replay-v1'):
        paths += [p for p in (STATE / folder).rglob('*') if p.is_file()]
    paths += [p for p in HOST.rglob('*') if p.is_file()]
    paths += [STATE / 'cache-policy.json']
    paths += [STATE / n for n in ('relink336.py', 'package336.py', 'review336.py', 'qualify_336_imports.py', 'kernel-identity.json')]
    paths += [p for p in (PRIOR / 'execution/restored-capture').iterdir() if p.is_file()]
    for path in paths:
        if path.is_file():
            pin(path)
    for path, digest in pins.items():
        assert sha(path) == digest, path
    save(STATE / 'trial-plan.json', plan)
    save(STATE / 'storage-bound.json', bound)
    pin(STATE / 'trial-plan.json')
    pin(STATE / 'storage-bound.json')
    ready = dict(state='ready-bcreuse336-one-shot', trial_plan_sha256=sha(STATE / 'trial-plan.json'),
                 install_plan_sha256=sha(STATE / 'slot-delta/install-plan.json'), image_sha256=IMAGE,
                 root_header_sha256=HEADER, input_pins=dict(sorted(pins.items())), pin_count=len(pins),
                 approval_pending=True, device_writes=0, boot_attempts=0)
    save(STATE / 'ready.json', ready)
    print(json.dumps({k: v for k, v in ready.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
