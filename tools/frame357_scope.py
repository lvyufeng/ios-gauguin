"""Freeze issued-frame retention and isolated latch evidence over 0356."""

from core342_scope import APPROVAL_FLAGS
from frame355_scope import CORE_SHA, LOG_PATHS, MAIN, P346, RESERVE, TOOLCHAIN, WORK, load, require, sha
from frame356_scope import check_references
from frame357_replay import P356, REF356, RESULT_356, PROOF_356

BASE = WORK/'research/tmp/frame-357'
HEADER = '87e44840e8d2ff18cf95579f45cdd1d744160855e3891f7fee305daf15d058c1'
RESTORED_356 = '1c8d0aa42684d666f777cd64afa6d0a0d9c0cba6764ecf6805c4a7260d3f585f'
REPLAY = 'c704ef866c6712b4f58c017224599d006cb4b02a4f15059b6626d2e890b8b478'
DOC = WORK/'docs/gauguin-frame-357-trial-20261120.md'
PATCH = WORK/'xnu/patches/0271-gauguin-retain-issued-display-swaps.patch'
CALIBRATION_PATCH = WORK/'xnu/patches/0272-gauguin-isolated-crc-calibration.patch'
CLEANUP = MAIN/'research/tmp/0357-storage-retirement'
LOG_SUFFIX = 8_000_000
FLAGS = APPROVAL_FLAGS + ('allow_0357_exact_0346_core','allow_0357_stable_data_MISR_preimage_and_exact_restore',
    'allow_0357_issued_frame_retention_and_bounded_post_script_pixel_calibration')
SUCCESS = '0357-issued-retention-and-output-measured-root-restored'
POLICY = dict(waiting_candidates=1,issued_mailbox_cells=2,native_fences_in_flight=1,ready_candidates=1,
    exact_ticket_version_bound_before_doorbell=True,only_visible_fence_promotes=True,
    failure_cancellation_retires_only_display_references=True,nondecreasing_present_generation=True,
    original_fresh_read_guard=True,original_core_runtime_copy_and_slot_budget=True)
CALIBRATION = dict(first_eligible_after_last_script_release_ms=750,termination_deadline_after_last_script_release_ms=1500,
    post_scoring=True,normal_present_takes_paused_only_during_calibration=True,
    dedicated_witnesses=3,minimum_hardware_frames_between_steps=8,
    one_volatile_scanout_pixel=True,maximum_total_pixel_stores=3,
    failure_restore_included_and_same_owned_pixel_only=True,original_pixel_readback_required=True,
    begin_after_agreeing_current_frame_crc_pair=True,minimum_admission_headroom_ns=2_400_000,
    next_edge_independent_margin_ns=1_000_000,additional_crc_register_writes=0,
    actual_fps_requires_all_dedicated_witnesses=True)


def expected_plan():
    check_references()
    previous = P356/'trial-plan.json'
    plan = load(previous)
    reference = REF356/'restored-capture/result.json'
    recovered = load(reference)
    proof = load(REF356/'independent-restore.json')
    parent = load(REF356/'result.json')
    require(sha(reference)==RESTORED_356 and sha(REF356/'result.json')==RESULT_356 and
            sha(REF356/'independent-restore.json')==PROOF_356 and parent['independent_restore_verified'] and
            parent['static_root_comparison_passed'] and parent['frame_trace_complete'] and
            not parent['crc_frame_calibration']['qualified'] and len(proof['files'])==6 and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'] and proof['root_header_sha256']==HEADER,
            '0356 independent restored inputs or incomplete CRC classification differ')
    current = load(BASE/'current-root-capture/result.json')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    log_bytes = (REF356/'kernel.log').stat().st_size
    ring_room_bytes = (16383-13239)*160+8192
    growth = baseline-plan['log_capture']['measured_baseline_bytes']
    require(recovered['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==recovered['files'] and current['directories']==recovered['directories'] and
            not current['device_writes'] and current['combined_log_bytes']==baseline==129_495_901 and
            growth==4_455_526 and log_bytes==3_191_489 and log_bytes+ring_room_bytes<4*1024**2 and
            LOG_SUFFIX>growth+ring_room_bytes and sha(BASE/'offline-replay.json')==REPLAY,
            'restored bytes, replay or measured log reservation differs')

    image = load(BASE/'frame357-image.json')
    kernel = load(BASE/'native-kernel/build-manifest.json')
    core = load(BASE/'core-native/result.json')
    edr = load(BASE/'edr-native/result.json')
    original = load(P346/'core-native/result.json')
    replacement_names = {name.rsplit('/',1)[-1] for name in kernel['object_replacements'].values()}
    require(all(kernel['input_pins'][str(p)]==sha(p) for p in (PATCH,CALIBRATION_PATCH)) and
            kernel['baseline_reproduced_except_uuid'] and kernel['inputs_unchanged'] and
            replacement_names=={'SweetFramebuffer.o','GauguinGPU.o','gauguin_ui_trace_board.o','sweet_touch.o'} and
            image['image_sha256']==sha(image['image']) and image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145 and edr['identity_only_retarget'] and
            core['state']=='0357-exact-0346-core-signed' and core['binary']==original['binary'] and core['signature_verified'] and
            core['binary_sha256']==sha(core['binary'])==CORE_SHA and core['bytes']==original['bytes']==7_992_224 and
            image['command']==plan['boot_command'] and len(image['command'].encode())==607 and
            all(image['command'].split().count(arg)==1 for arg in ('sweetfb_stats=9','sweetfb_hz=60','swp=3')),
            'fixed image, carried 0346 Core or exact 0356 command differs')
    plan.update(state='prepared-frame357-one-shot',trial='0357',image=image['image'],image_sha256=image['image_sha256'],
        image_bytes=image['image_bytes'],kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],
        EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(previous),optimization='Retain bound frames across later swaps until their exact fences finish',
        performance_comparison='0350, 0355, 0356 and 0357 by stroke, phase and hardware refresh ordinal',
        issued_retention=POLICY,latch_calibration=CALIBRATION,
        log_capture=dict(max_combined_log_bytes=baseline+LOG_SUFFIX,measured_baseline_bytes=baseline,
            maximum_suffix_bytes=LOG_SUFFIX,sizes=sizes,metadata_preflight=True,verified_prefixes_required=True,
            previous_verified_suffix_bytes=growth,reference_kernel_log_bytes=log_bytes,reserved_frame_console_bytes=ring_room_bytes))
    return plan
