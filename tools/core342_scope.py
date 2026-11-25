"""Exact 0342 driver CPU and program-newBO diagnostics over completed 0341."""
import copy
import hashlib
import json
from pathlib import Path
from core341_scope import APPROVAL_FLAGS as PARENT_FLAGS

MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/io-path-342'
PRIOR=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337'
PARENT=MAIN/'research/tmp/gauguin-program-io-worktree-20261117/research/tmp/program-io-341'
HEADER='c4092dcb66f48d2a697e558826ddec6c6c35164ce591d6f0d52e89a27b0b5f4c'
CORE='5b925bd7d2306c44d4df596fefb38d1cd3b28bd8c95ed68eb332d7fa6087e063'
C4='dc7f4046016cabf3a9e677ad585bc3b6002bf064dcaff259d5eb0bf6da0335ef'
EDR='3977bb489e141801de72df70ec102677c0efda8490d8f126cadca26c326d6d44'
IMAGE='3b993078c71800ec2e659b124631e16290b1f2824579e915a1d8f1c681473859'
IDENTITY='xnu-local342-272d6c88821c91d83d2f06497992d353'
APPROVAL_FLAGS=tuple(PARENT_FLAGS)+('allow_kernel_IO_CPU_phase_trace','allow_program_new_BO_CPU_phase_trace')


def load(p):return json.loads(Path(p).read_text())


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def expected_plan():
    plan=copy.deepcopy(load(PARENT/'trial-plan.json'))
    assert plan['kernel_identity']=='xnu-local337-d846caeab5924ac49b8ac8802e070e95'
    image=load(BASE/'io342-v4-image.json');link=load(BASE/'kernel-link-v4/build-manifest.json')
    assert image['image_sha256']==IMAGE and image['build_identity']==link['identity']==IDENTITY
    trace=dict(plan['core_wait_execution_trace'])
    trace.update(core_wire='CR342',notice_wire='N342',lifecycle_wire='C4Q342',queue_wire='Q342',core_line_bytes=8192)
    plan.update(state='prepared-core342-one-shot',image=image['image'],image_sha256=IMAGE,image_bytes=image['image_bytes'],
        kernel_banner=link['kernel_banner'],kernel_identity=IDENTITY,EDR_helper_sha256=EDR,
        root_header_sha256=HEADER,install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
        owned_core_sha256=CORE,C4_sha256=C4,storage_reserve_bytes=1000000000,
        core_wait_execution_trace=trace,unchanged_337_kernel_helper_SB=False,unchanged_337_SB=True,
        unchanged_333_image=False,unchanged_333_helper=False,unchanged_328_image=False,unchanged_328_helper=False,
        unchanged_324_image=False,new_kernel_builds=1,new_boot_images=1,
        additional_GPU_calls_scope='Existing operations only; per-selector wall/CPU/wall snapshots and program-only newBO CPU stages; no new GPU calls, jobs or threads',
        kernel_IO_CPU_phase_trace=dict(wire='SWEET IO342',window_ns=[210000000000,270000000000],
            selectors=[66,67,70,256],capacity=4096,line_bytes=2048,stream_byte_limit=2097152,
            preflight_entire_stream_before_output=True,
            atomic_whole_line_persistent_RAM_ring_reservations=True,console_chunking_bypassed=True,
            existing_next_profile_record_flushes_complete_stream=True,additional_UFS_flushes=0,overflow_or_pending_or_invalid_refuses_interpretation=True,
            persistent_ring_bytes=4194304,raw_ring_must_not_wrap=True,phase_count=12,
            CPU_clock='thread_get_runtime_self; mach ticks converted by absolutetime_to_nanoseconds',
            wall_clock='mach_absolute_time converted by absolutetime_to_nanoseconds',CPU_clock_slop_ns=2000,
            original_request_and_GPU_locks_only=True,existing_shutdown_dump_only=True,
            nested_unlocked_wait_elapsed_not_additive=True,IOKit_VM_work_outside_callback_not_driver_time=True,
            numeric_thread_selector_handle_shape_queue_fence_and_absolute_span_joins_required=True,
            whole_script_IO_and_each_reported_program_maximum_must_join=True,
            GPU_operations_validation_cache_fence_escrow_lifetimes_unchanged=True),
        program_new_BO_CPU_phase_trace=dict(phases=['validate_metadata','GemNew','GemInfo','map','publication','failure_cleanup'],
            only_program_resident_miss_scope=True,program_scoped_TLS_restored_on_exit=True,
            newBO_calls_must_equal_program_resident_misses=True,aggregate_and_longest_call_identity_and_spans=True,
            maximum_is_partial_evidence=True,queries_per_successful_newBO=6,
            clock='clock_gettime(CLOCK_THREAD_CPUTIME_ID)',CPU_clock_slop_ns=2000,
            whole_call_wall_equals_phase_wall_plus_unique_query_envelopes=True,
            errno_preserved=True,original_cleanup_order_and_address_lifetimes_unchanged=True),
        parent_trial_plan_sha256=sha(PARENT/'trial-plan.json'))
    return plan
