"""Exact0341 diagnostic overrides over the frozen and completed0340 trial."""
import copy
import hashlib
import json
from pathlib import Path
from core340_scope import APPROVAL_FLAGS as PARENT_FLAGS

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/program-io-341'
PRIOR=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337'
PARENT=MAIN/'research/tmp/gauguin-draw-submit-worktree-20261117/research/tmp/draw-submit-340'
HEADER='b942989e0d8ae65dc049fe84548c23b3e8c319b6f3d3a22a2c7f16927cbe7236'
CORE='2631e83e9dd8ead05addd7783dc8c7c78251880157e55542ae00d90b72ecbbfe'
C4='dea1aff358235777a335a222d8a34fe4df436d0b9b4424be57c92032c09d20be'
IMAGE='765e7c7cc2efb84d24ee1404f94b3f866dcf98e04e6a755d53a808b35a3841f3'
APPROVAL_FLAGS=tuple(PARENT_FLAGS)+('allow_program_table_slab_trace','allow_IO_calling_thread_CPU_accounting')


def load(path):return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def expected_plan():
    plan=copy.deepcopy(load(PARENT/'trial-plan.json'))
    assert plan['image_sha256']==IMAGE and plan['kernel_identity']=='xnu-local337-d846caeab5924ac49b8ac8802e070e95'
    trace=dict(plan['core_wait_execution_trace'])
    trace.update(core_wire='CR341',notice_wire='N341',lifecycle_wire='C4Q341',queue_wire='Q341',core_line_bytes=8192)
    symbols=dict(plan['core_symbol_policy'])
    symbols.update(possible_core_trim_tail_blocks=105,candidate_minimum_core_blocks=1948)
    plan.update(state='prepared-core341-one-shot',root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),owned_core_sha256=CORE,C4_sha256=C4,
        diagnostic_only=True,performance_candidate=False,
        capture_log_limits=dict(backboard=64*1048576,springboard=48*1048576),storage_reserve_bytes=950000000,
        additional_GPU_calls_scope='Program/slab elapsed scopes and two calling-thread CPU clock samples per traced existing IO; no additional GPU operation',
        core_wait_execution_trace=trace,core_symbol_policy=symbols,
        program_table_slab_trace=dict(
            phases=dict(address=['lookup','program_buffer','resource_keep','publication'],
                resident=['lock','lookup_evict','new_BO','upload_publish','exit'],table=['piece'],
                piece=['align','acquire_record','validate','resource_keep_exit'],
                pool=['size_lock','lookup','new_BO','reused_zero','counters','exit']),
            counters=['address_hits','address_misses','uploaded_entries_checked','resident_hits','resident_misses',
                'resident_entries_checked','piece_reuses','piece_slab_requests','piece_large_requests',
                'pool_hits','pool_misses','uploaded_word_bytes','resident_word_bytes','pooled_zero_bytes'],
            longest_call_job_identity_interval_and_phases=True,nested_scopes_not_additive=True,
            original_cache_algorithms_and_resource_operations_unchanged=True,
            original_queue_pool_32MiB_and_resident_policy_unchanged=True,
            inherited_340_CPU_reuse_and_GPU_cache_unchanged=True,new_GPU_calls=0,new_CPU_jobs=0,new_threads=0),
        IO_calling_thread_CPU_accounting=dict(clock='clock_gettime(CLOCK_THREAD_CPUTIME_ID)',
            existing_import_reused=True,queries_per_traced_IO=2,additional_thread_suspend_calls=0,
            CPU_clock_slop_ns=2000,outer_sampling_envelope_measured=True,
            CPU_lower='max(0,CPU_delta-sampling_envelope-2000ns)',
            CPU_upper='min(IO_wall,CPU_delta+2000ns)',
            off_CPU_lower='IO_wall-CPU_upper',off_CPU_upper='IO_wall-CPU_lower',
            off_CPU_scope='blocking, runnable delay, or work on other threads; not classified lock wait',
            elapsed_and_CPU_include_sampling_and_scheduler_effects=True,
            clock_errors_or_incoherent_intervals_disqualify_interpretation=True,
            errno_preserved=True,no_new_threads_or_GPU_operations=True,
            pure_driver_or_GPU_execution_not_inferred=True),
        parent_trial_plan_sha256=sha(PARENT/'trial-plan.json'))
    return plan
