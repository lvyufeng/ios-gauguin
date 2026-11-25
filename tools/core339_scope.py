"""Exact0339 overrides; every other frozen337 trial field remains required."""
import copy
import hashlib
import json
from pathlib import Path

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-prof-339'
PRIOR=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337'
PARENT=MAIN/'research/tmp/gauguin-core-async-worktree-20261117/research/tmp/core-async-338'
HEADER='26e0ff45b1b9755214968745d09b4a8d79646903e72eb904de031030d5af22a2'
CORE='6574f5c3f5931c78dd35797ff9b452d356ef299e51f589b0db041045b8a7772e'
C4='65ed6e5f0ea4b981b0bf1c75ff9010a792c533679da2141dac62847accf2166e'
IMAGE='765e7c7cc2efb84d24ee1404f94b3f866dcf98e04e6a755d53a808b35a3841f3'
APPROVAL_FLAGS=('approved','one_shot','allow_install','allow_restore','allow_rollback',
    'allow_misc_marker','allow_temporary_boot','allow_recovery_fallback','allow_scripted_input',
    'allow_wake_button','allow_main_thread_sampling','allow_process_sampling',
    'allow_owned_core_update','allow_frontend_update','allow_async_recording_notification',
    'allow_core_wait_execution_trace','allow_original_tail_reclaim',
    'allow_completed_journal_header','allow_primary_free_count_update')


def load(path):return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def expected_plan():
    plan=copy.deepcopy(load(PRIOR/'trial-plan.json'))
    assert plan['image_sha256']==IMAGE and plan['kernel_identity']=='xnu-local337-d846caeab5924ac49b8ac8802e070e95'
    plan.update(state='prepared-core339-one-shot',root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
        owned_core_sha256=CORE,C4_sha256=C4,unchanged_334_core=False,unchanged_335_core=False,
        diagnostic_only=True,performance_candidate=False,unchanged_337_kernel_helper_SB=True,
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
        capture_log_limits=dict(backboard=32*1048576,springboard=48*1048576),
        storage_reserve_bytes=760000000,
        additional_GPU_calls_scope='CPU category and submit-phase timestamps only; existing notification job unchanged; no GPU-only instrumentation',
        async_recording_notification=dict(same_core_FIFO=True,frontend_FIFO_unchanged=True,
            notification_owns_separate_lease=True,completion_may_precede_notice=True,
            allocation_failure_sync_fallback_once=True,callback_cannot_wait_for_GPU_or_throw=True,
            client_handler_serial_order_unchanged=True,turn_and_event_dependencies_preserved=True,
            new_CPU_jobs_per_commit=1,new_GPU_submissions=0,new_threads=0),
        core_wait_execution_trace=dict(core_wire='CR339',notice_wire='N339',lifecycle_wire='C4Q339',
            queue_wire='Q339',core_rows=4096,notice_rows=4096,core_line_bytes=2048,notice_line_bytes=128,
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
        core_symbol_policy=dict(local_symbols_removed_with_standard_strip_x=True,
            code_and_data_section_bytes_layout_unchanged=True,unstripped_sidecar_retained=True,
            possible_core_trim_tail_blocks=109,original_core_blocks=2053,candidate_minimum_core_blocks=1944),
        restoration_and_independent_readback_before_analysis=True,
        collection_before_backlog_interpretation=True,
        parent_trial_plan_sha256=sha(PARENT/'trial-plan.json'))
    return plan
