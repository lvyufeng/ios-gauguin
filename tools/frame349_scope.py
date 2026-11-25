"""Frozen 0349 blanking CRC capture on the exact signed 0346 Core."""

from core342_scope import APPROVAL_FLAGS
from frame348_scope import CORE_SHA, LOG_PATHS, MAIN, P346, POST_LOG_BYTES, RESERVE, WORK
from frame348_scope import load, require, sha


BASE = WORK/'research/tmp/frame-349'
P348 = MAIN/'research/tmp/gauguin-readonly-scanout-worktree-20261119/research/tmp/frame-348'
REFERENCE = P348/'execution'
REFERENCE_RESULT = '70b0df903aa6d2e8a26ac5e85bb58d78e33436257b8e7b8db0df5f2353999660'
REFERENCE_PROOF = 'a53cb63876b55b6c94c0960dc1453eb5853ff40bb3da55bbcacb1f0e9671b2c7'
HEADER = 'cb8c84c2849f8aa7caba0e4f927f529f2400865bb71dfb06660858a250e505c2'
DOC = WORK/'docs/gauguin-frame-349-trial-20261119.md'
PATCH = WORK/'xnu/patches/0261-gauguin-blanking-misr.patch'
FLAGS = APPROVAL_FLAGS + ('allow_0349_exact_0346_core','allow_0349_read_only_intf1_counters',
                          'allow_0349_four_volatile_intf1_MISR_writes')
SUCCESS = '0349-collection-qualified-output-cadence-measured-root-restored'
PAIR_LIMIT = 3000
CONSOLE_EXTRA = PAIR_LIMIT*160+1024


def expected_plan():
    previous = P348/'trial-plan.json'
    plan = load(previous)
    proof = load(REFERENCE/'independent-restore.json')
    last = load(REFERENCE/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(sha(REFERENCE/'result.json')==REFERENCE_RESULT and
            sha(REFERENCE/'independent-restore.json')==REFERENCE_PROOF and
            proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and
            proof['root_header_sha256']==last['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==last['files'] and current['directories']==last['directories'] and
            not current['device_writes'], 'fresh 0349 baseline differs from independent 0348 restoration')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    raw_bytes = (REFERENCE/'kernel.log').stat().st_size
    reference_growth = last['combined_log_bytes']-plan['log_capture']['measured_baseline_bytes']
    require(current['combined_log_bytes']==baseline==98_157_381 and
            POST_LOG_BYTES-baseline>=reference_growth>0 and
            raw_bytes+CONSOLE_EXTRA<4*1024**2, 'measured capture budget differs')

    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame349-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    original = load(P346/'core-native/result.json')
    require(core['state']=='0349-exact-0346-core-signed' and
            core['binary']==original['binary'] and core['binary_sha256']==sha(core['binary'])==CORE_SHA and
            core['bytes']==original['bytes']==7_992_224 and core['signature_verified'],
            'Core differs from the exact signed 0346 baseline')
    args = plan['boot_command'].split()
    require(args.count('sweetfb_stats=4')==args.count('sweetfb_hz=60')==args.count('swp=3')==1 and
            image['command']==plan['boot_command'].replace('sweetfb_stats=4','sweetfb_stats=5') and
            len(image['command'].encode())==607, 'only the frozen capture mode token may change')
    require(image['image_sha256']==sha(image['image']) and
            image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            len(kernel['object_replacements'])==2 and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145,
            'kernel, image or EDR qualification differs')

    plan['frame_capture'].update(opt_in='sweetfb_stats=5',interface_mapping='INTF1 with writes restricted to MISR control',
        controls_observed=[0],maximum_total_display_register_writes=4,maximum_volatile_crc_register_writes=4,
        volatile_crc_register_address='0x0ae6b980',read_only_crc_signature_address='0x0ae6b984',
        crc_enabled=True,crc_enable_requires_exact_zero_preimage=True,crc_gated_60_hz_intervals=3,
        exact_crc_geometry=[462,4910,32,2431],crc_setup_values=[1024,0x81000101],crc_cleanup_values=[1024,0],
        crc_setup_and_cleanup_write_readbacks=True,crc_setup_attempts=1,crc_cleanup_attempts=1,crc_retries=0,
        crc_cleanup_requires_exact_route_and_owned_value=True,crc_blank_lines=[2752,4480],
        crc_timing_line_end_exclusive=True,crc_ready_status_bracketed=True,crc_polls_per_pair=2,
        crc_maximum_read_bracket_us=250,crc_new_frame_warmup_slots=2,crc_sample_rows_max=PAIR_LIMIT,
        publish_new_content_fps=True,fps_requires_unambiguous_latch_calibration=True,optical_FPS_qualified=False)
    plan.update(state='prepared-frame349-one-shot',trial='0349',image=image['image'],image_sha256=image['image_sha256'],
                image_bytes=image['image_bytes'],boot_command=image['command'],kernel_identity=kernel['identity'],
                kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
                root_header_sha256=HEADER,install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
                misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),parent_trial_plan_sha256=sha(previous),
                optimization='Exact signed 0346 Core with INTF1 blanking dual-read CRC and read-only frame/line counters',
                performance_comparison='Same swipe ordinal and phase as restored 0348, using boot-local identities',
                log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline,
                    maximum_suffix_bytes=POST_LOG_BYTES-baseline,sizes=sizes,metadata_preflight=True,
                    verified_prefixes_required=True,previous_verified_suffix_bytes=reference_growth,
                    reference_kernel_log_bytes=raw_bytes,reserved_CRC_console_bytes=CONSOLE_EXTRA))
    return plan
