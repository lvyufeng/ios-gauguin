"""Frozen inputs for the 0343 async ring-guard trial."""

from pathlib import Path

from core342_scope import APPROVAL_FLAGS as IO342_APPROVAL
from core342_scope import MAIN, WORK, load, sha

BASE = WORK / 'research/tmp/runtime-issue-343'
P342 = MAIN / 'research/tmp/gauguin-io-path-worktree-20261117/research/tmp/io-path-342'
REFERENCE = P342 / 'post-analysis-wire-v1'
HEADER = 'a1390987d2c7ae4de23980b15b34746752dbae706d195040ae3918bbdb585b4a'
IMAGE = '8c3627cc69e8ab965c4fadbc35c13098e1cbda855f78040a84ccb9102402ef3e'
EDR = '3d5299a1f5fdb95a81da58019979fcaa0cb3c714b65e2f79a2e82857f74d9252'
IDENTITY = 'xnu-local343-d6c5fd87f322ea1c092e43017bb71b01'
REFERENCE_RESULT = '88e0cd230d758b17b3c65e43c87a5ce8712845c896b812ddcc8242e043ed8e88'
APPROVAL_FLAGS = IO342_APPROVAL + ('allow_0343_async_ring_guard_candidate',)
COMPLETE = 'CR343-lossless-CPU-queue-comparison-root-restored'
DOC = WORK / 'docs/gauguin-runtime-issue-343-trial-20261119.md'
STORAGE_RESERVE = 1020000000
ROOT_FILES = ('expected-baseline.json', 'capture-profile.json', 'storage-bound-343.json')
REF_DECODE = ('kernel-IO-identity-analysis.json', 'core-wait-execution-analysis.json',
              'collection-analysis.json', 'queue-identity-analysis.json', 'kernel.log', 'result.json')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def expected_plan():
    plan = load(P342 / 'trial-plan.json')
    image = load(BASE / 'runtime343-image.json')
    link = load(BASE / 'kernel-native/build-manifest.json')
    edr = load(BASE / 'edr-native/result.json')
    prior_restore = load(P342 / 'execution/independent-restore.json')
    require(prior_restore['root_header_sha256'] == HEADER
            and prior_restore['misc_original_4096_bytes_match']
            and prior_restore['journal_empty'], '0342 restoration not independently verified')
    require(sha(REFERENCE / 'result.json') == REFERENCE_RESULT, '0342 qualified reference changed')
    require(image['image_sha256'] == IMAGE and image['build_identity'] == link['identity'] == IDENTITY
            and link['no_undefined_kernel_symbols']
            and image['command'] == plan['boot_command']
            and edr['kernel_identity'] == IDENTITY and edr['binary_sha256'] == EDR,
            'pinned 0343 kernel, boot command or EDR differs')
    plan.update(
        state='prepared-core343-one-shot', trial='0343', image=image['image'],
        image_bytes=image['image_bytes'], image_sha256=IMAGE,
        kernel_identity=IDENTITY, kernel_banner=image['kernel_banner'], EDR_helper_sha256=EDR,
        root_header_sha256=HEADER, install_plan_sha256=sha(BASE / 'slot-delta/install-plan.json'),
        storage_reserve_bytes=STORAGE_RESERVE, diagnostic_only=False,
        parent_trial_plan_sha256=sha(P342 / 'trial-plan.json'),
        strict_frozen_baseline=True,
        unchanged_0342_swipe_script=True, unchanged_0342_Core_and_frontend=True,
        optimization='Two full board guards shared at adjacent async CPU-owned ROOT ring/barrier boundaries',
        ui_wire_kinds={'HID_QUEUE_STATE': 31, 'BO_ALLOC': 32, 'BO_REUSE': 33},
        performance_comparison={
            'reference_result_sha256': REFERENCE_RESULT,
            'require_independent_restore_then_complete_capture': True,
            'join_within_boot': ['core_queue', 'ticket', 'job', 'driver_queue', 'driver_fence',
                                 'caller_thread', 'request_shape', 'absolute_time_bounds'],
            'align_between_boots': 'script stroke ordinal and 13-stroke window; ticket IDs are boot-local',
            'measure': ['runtime_issue_thread_CPU_lower_upper', 'runtime_issue_wall',
                        'core_queue_wait', 'commit_done', '12_consecutive_ticket_wait_growth'],
            'quantiles': ['p50', 'p95', 'p99', 'max'],
            'frame_budget_ns': [1000000000, 60],
        },
        optical_FPS={
            'measure': 'new optical screen content frames during horizontal motion',
            'nominal_camera_fps': [120, 240], 'preferred_camera_fps': 240,
            'clip_scope': 'continuous original-rate clip from before unlock to after stroke 12 settles',
            'analysis_requires_qualified_trace_and_all_strokes_in_order': True,
            'screen_roi_and_still_reference_required': True,
            'optical_measurement_does_not_delay_automatic_restore': True,
            'separate_from_software_present_and_GPU_service_rates': True,
            'project_artifacts_max_bytes': 8000000,
        },
    )
    return plan
