"""Exact0340 overrides; every other frozen337 trial field remains required."""
import copy
import hashlib
import json
from pathlib import Path

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/draw-submit-340'
PRIOR=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337'
PARENT=MAIN/'research/tmp/gauguin-core-prof-worktree-20261117/research/tmp/core-prof-339'
HEADER='46114302d51d798551816ddd5b4965182cc66e76a8d98ae04e176e6c08b16a8a'
CORE='b1653fd74f1e0ad88752ec40924455a7a7eab67286151c9a98fa1ab53547c94d'
C4='5b04ebe84d2aff5c98856674e571ef23d118f76752fd3de518d8266b810dbb99'
IMAGE='765e7c7cc2efb84d24ee1404f94b3f866dcf98e04e6a755d53a808b35a3841f3'
APPROVAL_FLAGS=('approved','one_shot','allow_install','allow_restore','allow_rollback',
    'allow_misc_marker','allow_temporary_boot','allow_recovery_fallback','allow_scripted_input',
    'allow_wake_button','allow_main_thread_sampling','allow_process_sampling',
    'allow_owned_core_update','allow_frontend_update','allow_async_recording_notification',
    'allow_core_wait_execution_trace','allow_original_tail_reclaim',
    'allow_completed_journal_header','allow_primary_free_count_update',
    'allow_draw_submit_phase_trace','allow_worker_CPU_scratch_reuse')


def load(path):return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def expected_plan():
    plan=copy.deepcopy(load(PRIOR/'trial-plan.json'))
    assert plan['image_sha256']==IMAGE and plan['kernel_identity']=='xnu-local337-d846caeab5924ac49b8ac8802e070e95'
    plan.update(state='prepared-core340-one-shot',root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
        owned_core_sha256=CORE,C4_sha256=C4,unchanged_334_core=False,unchanged_335_core=False,
        diagnostic_only=False,performance_candidate=True,unchanged_337_kernel_helper_SB=True,
        new_kernel_builds=0,new_boot_images=0,
        maximum_restore_userdata_bytes=10330112,normal_userdata_write_bytes_max=20631552,
        maximum_userdata_write_bytes=30961664,failed_restore_retry_limit=0,
        retry_only_after_verified_rollback=False,restore_forward_attempts=1,
        no_new_files_or_HFSX_allocations=False,install_has_no_new_allocation=True,
        restore_reclaims_original_free_unowned_tails_only=True,
        restore_journal_policy='empty-or-all-coalesced-homes-already-applied; no home replay',
        restore_max_ranges=18,restore_max_bitmap_blocks=4,
        alternate_header_write_allowed=False,journal_home_replay_allowed=False,
        unsupported_restore_state='refuse-before-write-and-retain-TWRP; further-recovery-needs-new-review',
        capture_log_limits=dict(backboard=40*1048576,springboard=48*1048576),
        storage_reserve_bytes=800000000,
        additional_GPU_calls_scope='CPU draw/BO descriptor reuse and fine timestamps; one unchanged IO/GPU submit per commit; existing notification job unchanged',
        async_recording_notification=dict(same_core_FIFO=True,frontend_FIFO_unchanged=True,
            notification_owns_separate_lease=True,completion_may_precede_notice=True,
            allocation_failure_sync_fallback_once=True,callback_cannot_wait_for_GPU_or_throw=True,
            client_handler_serial_order_unchanged=True,turn_and_event_dependencies_preserved=True,
            new_CPU_jobs_per_commit=1,new_GPU_submissions=0,new_threads=0),
        core_wait_execution_trace=dict(core_wire='CR340',notice_wire='N340',lifecycle_wire='C4Q340',
            queue_wire='Q340',core_rows=4096,notice_rows=4096,core_line_bytes=4096,notice_line_bytes=128,
            explicit_limit_markers=True,core_wait_split='observed-earlier-worker-body-union; uncovered-residence',
            own_job_execution_sum=True,overlapping_job_queue_latencies_not_additive=True,
            phase4='notification-admission-return; reserved-value-zero',new_GPU_calls=0,new_threads=0),
        core_category_submit_trace=dict(categories=['control','bindings','render','clear','compute','transfer_append','commit','notification'],
            submit_phases=['entry','pass_tail','command_BO','command_copy','queue_lock','fault_query','native_submit','publication'],
            exact_observed_wait_category_partition=True,exact_own_body_category_partition=True,
            retained_0338_notification_job=True,additional_CPU_jobs_per_commit=0,
            worst_job_identity_and_interval=True,absolute_submit_begin_end=True,
            added_per_job_bytes=0,added_per_job_allocations=0,new_GPU_calls=0,new_threads=0,
            physical_FPS_qualified=False,full_script_window_source='qualified collection13-stroke window',
            kernel_BO_capture_window_reported_separately=True),
        draw_submit_phase_trace=dict(draw_common_phases=['entry','vertex_bindings','fragment_bindings','argument_members','draw_state','render_body','resource_keep','exit'],
            render_body_phases=['entry_freshen','null_private','program_table','pass_setup','encode','packets','resource_uses','exit'],
            GPU_submit_phases=['entry','BO_list','descriptor','transport','publication'],
            IO_scope='IOConnectCallStructMethod for kGemSubmit only; syscall elapsed, not pure kernel/GPU time',
            draw_max_job_identity_interval_and_partition=True,BO_uses_unique_comparisons_and_reuse_counts=True,
            actual_IO_begin_end_and_count=True,new_GPU_calls=0,new_CPU_jobs=0,new_threads=0,
            exact_trace_and_reuse_activation_required_before_interpretation=True),
        worker_CPU_scratch_reuse=dict(owner='existing Deferrer::State; TLS borrows only during existing job',
            draw_retained_elements_per_vector=128,draw_vectors=7,submit_retained_BO_descriptors=1024,
            BO_index_buckets=2048,BO_index_heap_allocations=0,retained_payload_bytes_per_worker_upper_bound=40960,
            references_cleared_after_each_draw=True,BO_descriptors_cleared_after_each_submit=True,
            state_destruction_releases_capacity=True,synchronous_and_reentrant_fallback='original local vectors and stable linear dedup',
            over_1024_unique_fallback='stable linear dedup; drop retained capacity above limit',
            optional_reserve_failure='continue original push_back behavior',
            command_BO_index_zero=True,first_seen_BO_order=True,handle_alias_OR_flags=True,
            FIFO_turn_event_completion_and_notification_order_unchanged=True,
            GPU_buffer_mapping_and_BO_cache_policy_unchanged=True),
        core_symbol_policy=dict(local_symbols_removed_with_standard_strip_x=True,
            code_and_data_section_bytes_layout_unchanged=True,unstripped_sidecar_retained=True,
            possible_core_trim_tail_blocks=109,original_core_blocks=2053,candidate_minimum_core_blocks=1944),
        restoration_and_independent_readback_before_analysis=True,
        collection_before_backlog_interpretation=True,
        parent_trial_plan_sha256=sha(PARENT/'trial-plan.json'))
    return plan
