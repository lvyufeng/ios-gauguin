"""Exact0338 overrides; every other frozen337 trial field remains required."""
import copy
import hashlib
import json
from pathlib import Path

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-async-338'
PRIOR=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337'
HEADER='99624b0524a34e438bc323aa9f2b6344e912b133d4469cae70cb9bcb9ff7f1cd'
CORE='9eeab2b81413cb2cc34f6a1912854c62259decd360414e32fc51c2cbeef0fea1'
C4='c4dd56222f6b55809e7060c593aa80c927ec5c84c3fe6e09efd9c4c49ca230f2'
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
    plan.update(state='prepared-core338-one-shot',root_header_sha256=HEADER,
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
        capture_log_limits=dict(backboard=22*1048576,springboard=48*1048576),
        storage_reserve_bytes=700000000,
        additional_GPU_calls_scope='CPU recorder metering and one notification job per CB; no GPU-only instrumentation',
        async_recording_notification=dict(same_core_FIFO=True,frontend_FIFO_unchanged=True,
            notification_owns_separate_lease=True,completion_may_precede_notice=True,
            allocation_failure_sync_fallback_once=True,callback_cannot_wait_for_GPU_or_throw=True,
            client_handler_serial_order_unchanged=True,turn_and_event_dependencies_preserved=True,
            new_CPU_jobs_per_commit=1,new_GPU_submissions=0,new_threads=0),
        core_wait_execution_trace=dict(core_wire='CR338',notice_wire='N338',lifecycle_wire='C4Q338',
            queue_wire='Q338',core_rows=4096,notice_rows=4096,core_line_bytes=512,notice_line_bytes=128,
            explicit_limit_markers=True,core_wait_split='observed-earlier-worker-body-union; uncovered-residence',
            own_job_execution_sum=True,overlapping_job_queue_latencies_not_additive=True,
            phase4='notification-admission-return; reserved-value-zero',new_GPU_calls=0,new_threads=0),
        restoration_and_independent_readback_before_analysis=True,
        collection_before_backlog_interpretation=True,
        parent_trial_plan_sha256=sha(PRIOR/'trial-plan.json'))
    return plan
