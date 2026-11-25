"""Freeze the first-frame observer over the exact measured 0358 renderer."""

from frame355_scope import MAIN, WORK, LOG_PATHS, RESERVE, load, require, sha
from frame358_scope import FLAGS as INHERITED_FLAGS

P358 = MAIN/'research/tmp/gauguin-fence-probe-worktree-20261120/research/tmp/frame-358'
REF358 = P358/'execution'
BASE = WORK/'research/tmp/frame-359'
DOC = WORK/'docs/gauguin-frame-359-trial-20261120.md'
HEADER = 'a8c825e0b3c3309cc3921dd77a9ebf9c06a5e0f5ab44cc171d764a824c331a0e'
RESULT_358 = '77dbf0fa729143ef2cd3bf783d83ddda566e0f55056109d21af7e44eb7685c55'
PROOF_358 = '31326dd8529f81435f6f2e5787504da2654b9a2f553e25e8109bb73e16f73249'
LOG_SUFFIX = 8_000_000
FLAGS = INHERITED_FLAGS + ('allow_0359_exact_0358_image_and_renderer',
    'allow_0359_input_and_explicit_CA_milestones', 'allow_0359_retarget_main_thread_sampling')
SUCCESS = '0359-first-frame-and-output-measured-root-restored'
SAMPLING = dict(version=359,start_us=220000000,end_us=270000000,period_us=20000,
    min_turn_us=35000,budget_us=2000,max_samples=8,depth=16,stack_window_bytes=65536,
    hard_realtime_pause_limit=False)
OBSERVATION = dict(main_thread_only=True,additional_threads=0,maximum_new_rows=8192,
    exact_original_call_interval=True,maximum_samples_per_callback=1,
    explicit_CA_methods=['commit','flush'],ordered_before_after_observers_preserved=True,
    display_and_GPU_candidate='0358',timing_scope='Shared monotonic clock with exact stack, writer and scan joins.')


def check_0358():
    result = load(REF358/'result.json')
    proof = load(REF358/'independent-restore.json')
    require(sha(REF358/'result.json')==RESULT_358 and sha(REF358/'independent-restore.json')==PROOF_358 and
            result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            all(result['other_log_prefix_preserved'].values()) and result['dpu_new_content_FPS_qualified'] and
            proof['root_header_sha256']==HEADER and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'] and len(proof['files'])==6,'0358 baseline differs')


def expected_plan():
    check_0358()
    previous = P358/'trial-plan.json'
    plan = load(previous)
    require(sha(plan['image'])==plan['image_sha256'],'exact 0358 image differs')
    old = load(REF358/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    measured = sum(sizes.values())
    growth = measured-plan['log_capture']['measured_baseline_bytes']
    require(current['files']==old['files'] and current['directories']==old['directories'] and
            current['root_header_sha256']==old['root_header_sha256']==HEADER and
            current['combined_log_bytes']==measured==138_383_468 and not current['device_writes'] and
            growth==4_435_161 and growth+8192*160+32_768<LOG_SUFFIX,'baseline or observer log budget differs')
    receipt = load(BASE/'sb-native/result.json')
    install = load(BASE/'slot-delta/install-plan.json')
    require(receipt['signature_verified'] and receipt['inputs_unchanged'] and receipt['runtime_imports_qualified'] and
            sha(receipt['binary'])==receipt['binary_sha256']==install['rows']['eagl']['new_file_sha256'] and
            install['admission_sha256']==plan['EDR_helper_sha256'] and
            install['core_sha256']==plan['owned_core_sha256'],'signed trial slots differ')
    plan.update(state='prepared-frame359-one-shot',trial='0359',parent_trial_plan_sha256=sha(previous),
        root_header_sha256=HEADER,install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
        misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),SB_sha256=receipt['binary_sha256'],
        unchanged_337_SB=False,new_kernel_builds=0,new_boot_images=0,diagnostic_only=True,performance_candidate=False,
        main_thread_sampling=SAMPLING,first_frame_observation=OBSERVATION,
        optimization='Locate the long input callback and the delay to the first complete new output.',
        performance_comparison='0358, same 13 scripted strokes and CRC windows; instrumented timing.',
        log_capture=dict(plan['log_capture'],max_combined_log_bytes=measured+LOG_SUFFIX,
            measured_baseline_bytes=measured,maximum_suffix_bytes=LOG_SUFFIX,sizes=sizes,
            previous_verified_suffix_bytes=growth,observer_addition_bound_bytes=8192*160+32_768))
    return plan
