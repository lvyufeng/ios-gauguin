"""Shared constants and checks for the frozen 0345 trial."""

from core342_scope import APPROVAL_FLAGS
from core343_scope import MAIN, WORK, load, require, sha
from frame344_scope import LOG_PATHS, POST_LOG_BYTES


BASE = WORK/'research/tmp/frame-345'
P344 = MAIN/'research/tmp/gauguin-frame-344-worktree-20261119/research/tmp/frame-344'
HEADER = 'fadaf0f7d3f0cc18bf8d963f764ef780477900c067a1c026601bf0915e0b76c2'
RESERVE = 228_000_000
ANALYSIS = 80_000_000
DOC = WORK/'docs/gauguin-frame-345-trial-20261119.md'
SUCCESS = '0345-collection-and-hardware-analysis-complete-root-restored'
FLAGS = APPROVAL_FLAGS + ('allow_0345_recording_and_submit_resolution', 'allow_0345_volatile_intf1_MISR')


def expected_plan():
    parent = P344/'trial-plan.json'
    plan = load(parent)
    prior = load(P344/'execution/independent-restore.json')
    current = load(BASE/'current-root-capture/result.json')
    previous = load(P344/'execution/restored-capture/result.json')
    require(prior['root_header_sha256']==current['root_header_sha256']==HEADER and prior['journal_empty'] and
            prior['misc_original_4096_bytes_match'] and current['files']==previous['files'] and
            current['directories']==previous['directories'] and not current['device_writes'],
            '0344 restored baseline or the fresh capture differs')
    image = load(BASE/'frame345-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    host = load(BASE/'core-host-reviewed/result.json')
    submit = load(BASE/'submit-host-final/result.json')
    require(image['image_sha256']==sha(image['image']),'0345 wrapper differs')
    require(image['command']==plan['boot_command'] and 'sweetfb_hz=60' in image['command'].split() and
            image['build_identity']==edr['kernel_identity'] and edr['binary_sha256']==sha(edr['binary']) and
            edr['scope_checks']==2145, '0345 image, 60 Hz command or admission helper differs')
    require(core['binary_sha256']==sha(core['binary'])==host['native_sha256'] and
            core['matching_imports_exports_loads_and_platform'] and host['replay_iterations']==512 and
            host['ownership_cases']==23 and host['render_cases']==8 and submit['inputs_unchanged'] and
            submit['validated_BO_resolved_once'], '0345 Core or submit ownership checks differ')
    frame = plan['frame_capture']
    frame.update(startup_gate_timeout_ms=800, crc_samples_per_frame=2,
                 qualified_early_active_line_offsets=[128,1536],
                 startup_independent_gates=True, read_only_vblank_if_crc_blocked=True,
                 publish_bounds_for_partial_adjacent_hardware_coverage=True)
    plan.update(state='prepared-frame345-one-shot',trial='0345',image=image['image'],image_sha256=image['image_sha256'],
                image_bytes=image['image_bytes'],kernel_identity=image['build_identity'],kernel_banner=image['kernel_banner'],
                EDR_helper_sha256=edr['binary_sha256'],owned_core_sha256=core['binary_sha256'],
                root_header_sha256=HEADER,install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
                misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),parent_trial_plan_sha256=sha(parent),
                storage_reserve_bytes=RESERVE,verified_log_suffixes_only=True,max_analysis_bytes=ANALYSIS,
                all_core_TUs_recompiled=False,
                optimization='Bounded UBO packing; batch unchanged PM4 words; resolve each validated BO once per locked submit',
                performance_comparison='0344 same stroke ordinals, queue and fence identities joined per boot; hardware measured in 0345',
                frame_capture=frame)
    return plan
