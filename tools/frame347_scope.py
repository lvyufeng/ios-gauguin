"""Pinned effects and baseline for the 0347 counter and packet trial."""

from frame346_scope import ANALYSIS, LOG_PATHS, POST_LOG_BYTES, RESERVE
from frame346_scope import MAIN, WORK, load, require, sha
from core342_scope import APPROVAL_FLAGS


BASE = WORK/'research/tmp/frame-347'
P346 = MAIN/'research/tmp/gauguin-dpu-hwcg-worktree-20261119/research/tmp/frame-346'
REFERENCE = P346/'qualified-analysis'
REFERENCE_RESULT = '26e4ae666b276aa0cc4a1410a68c790bb8c1980d87083c09b52b62ab296e0acc'
HEADER = '180dc2fddc7dd3dfdd465957c493550a5629957161311b33d52d573586b985cb'
DOC = WORK/'docs/gauguin-frame-347-trial-20261119.md'
FLAGS = APPROVAL_FLAGS + ('allow_0347_packet_shadow_candidate','allow_0347_volatile_intf1_frame_line_counter',
                          'allow_0347_volatile_intf1_MISR')
SUCCESS = '0347-collection-and-hardware-analysis-complete-root-restored'


def expected_plan():
    parent = P346/'trial-plan.json'
    plan = load(parent)
    proof = load(P346/'execution/independent-restore.json')
    current = load(BASE/'current-root-capture/result.json')
    previous = load(P346/'analysis-after-readback/restored-capture/result.json')
    require(sha(REFERENCE/'result.json')==REFERENCE_RESULT and
            proof['root_header_sha256']==current['root_header_sha256']==HEADER and
            proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and
            current['files']==previous['files'] and current['directories']==previous['directories'] and
            not current['device_writes'], 'restored 0346 and fresh 0347 baselines differ')
    baseline_log_bytes = sum(current['files'][path]['bytes'] for path in LOG_PATHS)
    require(current['combined_log_bytes']==baseline_log_bytes and 0<baseline_log_bytes<POST_LOG_BYTES,
            'combined measured log size differs')

    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame347-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    host = load(BASE/'core-host-reviewed/result.json')
    args = plan['boot_command'].split()
    require(args.count('sweetfb_stats=2')==1 and args.count('sweetfb_hz=60')==1 and args.count('swp=3')==1 and
            image['command']==plan['boot_command'].replace('sweetfb_stats=2','sweetfb_stats=3') and
            len(image['command'].encode())==len(plan['boot_command'].encode())==607,
            'only the fixed scanout mode argument may change')
    require(image['image_sha256']==sha(image['image']) and
            image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            kernel['baseline_reproduced_except_uuid'] and len(kernel['object_replacements'])==2 and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145,
            'image, kernel or EDR qualification differs')
    require(core['binary_sha256']==sha(core['binary'])==host['native_sha256'] and
            0<core['bytes']<=core['slot_bytes'] and core['compiled_tus']==12 and
            core['matching_imports_exports_loads_and_platform'] and host['replay_iterations']==512 and
            host['program_slabs_passed'] and host['ownership_cases']==23 and host['render_cases']==8,
            'packet equality, ABI or lifetime qualification differs')

    plan.update(state='prepared-frame347-one-shot',trial='0347',image=image['image'],
                image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],boot_command=image['command'],
                kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],
                EDR_helper_sha256=edr['binary_sha256'],owned_core_sha256=core['binary_sha256'],
                owned_core_logical_bytes=core['bytes'],root_header_sha256=HEADER,
                install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
                misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
                parent_trial_plan_sha256=sha(parent),strict_frozen_baseline=True,
                optimization='Contiguous register shadow comparisons with pass-local invalidation',
                performance_comparison='0346 same swipe ordinal and phase with boot-local frame, queue, IO and GPU links',
                log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline_log_bytes,
                                 maximum_suffix_bytes=POST_LOG_BYTES-baseline_log_bytes,
                                 sizes={path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)},
                                 metadata_preflight=True,verified_prefixes_required=True))
    plan['frame_capture'].update(opt_in='sweetfb_stats=3', volatile_counter_register_address='0x0ae6b8a8',
        maximum_volatile_counter_register_writes=2, counter_enable_value=3, counter_restore_value=0,
        exact_counter_zero_preimage=True, stable_counter_geometry_snapshots=2,
        counter_enable_requires_running_timing_engine=True, counter_write_readback=True,
        counter_cleanup_requires_readable_domain_and_owned_value=True, maximum_total_display_register_writes=6,
        counter_cleanup_receipt_required_if_armed=True)
    return plan
