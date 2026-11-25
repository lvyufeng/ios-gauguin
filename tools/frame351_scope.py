"""Frozen 0351 hardware-timed presentation with the exact 0346 Core."""

from core342_scope import APPROVAL_FLAGS
from frame350_scope import CORE_SHA, LOG_PATHS, MAIN, P346, POST_LOG_BYTES, RESERVE, WORK
from frame350_scope import load, require, sha


BASE = WORK/'research/tmp/frame-351'
P350 = MAIN/'research/tmp/gauguin-crc-preimage-worktree-20261119/research/tmp/frame-350'
REFERENCE = P350/'execution'
REFERENCE_RESULT = '69a979c1ef29600af8a17f71cc0e86fde5d72e6d1968076b5e88df52afa4216d'
REFERENCE_PROOF = '4836213a2fc617dcbc3e84a51c502e93bbab2c449ccd17443288741daa11c1d8'
HEADER = 'abc42cdad4c7588931e35a320f200a273cf107dbfe72e590839d3d9c1f73527c'
DOC = WORK/'docs/gauguin-frame-351-trial-20261119.md'
PATCH = WORK/'xnu/patches/0263-gauguin-blanking-present.patch'
CLEANUP = MAIN/'research/tmp/0351-storage-retirement'
FLAGS = APPROVAL_FLAGS + ('allow_0351_exact_0346_core','allow_0351_stable_data_MISR_preimage_and_exact_restore',
                          'allow_0351_guarded_blanking_presentation_and_read_only_prefetch')
SUCCESS = '0351-blanks-and-output-cadence-measured-root-restored'
FOCUS = (4,6)
RELEASE_NS = (580_000_000,658_000_000)


def expected_plan():
    previous = P350/'trial-plan.json'
    plan = load(previous)
    proof = load(REFERENCE/'independent-restore.json')
    last = load(REFERENCE/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(sha(REFERENCE/'result.json')==REFERENCE_RESULT and sha(REFERENCE/'independent-restore.json')==REFERENCE_PROOF and
            proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and
            proof['root_header_sha256']==last['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==last['files'] and current['directories']==last['directories'] and
            not current['device_writes'],'fresh baseline differs from independent 0350 restoration')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    raw = (REFERENCE/'kernel.log').stat().st_size
    extra = (16383-11870)*160+1024
    growth = last['combined_log_bytes']-plan['log_capture']['measured_baseline_bytes']
    require(current['combined_log_bytes']==baseline==107_053_888 and
            POST_LOG_BYTES-baseline>=growth>0 and raw+extra<4*1024**2,'0351 measured capture budget differs')

    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame351-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    original = load(P346/'core-native/result.json')
    require(core['state']=='0351-exact-0346-core-signed' and
            core['binary']==original['binary'] and core['binary_sha256']==sha(core['binary'])==CORE_SHA and
            core['bytes']==original['bytes']==7_992_224 and core['signature_verified'],
            'Core differs from the signed 0346 baseline')
    args = plan['boot_command'].split()
    require(args.count('sweetfb_stats=6')==args.count('sweetfb_hz=60')==args.count('swp=3')==1 and
            image['command']==plan['boot_command'].replace('sweetfb_stats=6','sweetfb_stats=7') and
            len(image['command'].encode())==607,'only the capture mode token may change')
    require(image['image_sha256']==sha(image['image']) and
            image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            len(kernel['object_replacements'])==2 and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145,
            'kernel, image or EDR identity differs')
    plan['frame_capture'].update(opt_in='sweetfb_stats=7',presentation_policy=dict(
        single_layer_mask=1,only_during_45s_frame_capture=True,requires_live_qualified_60Hz_route=True,
        phase_open_line=2480,guard_lines=32,copy_budget_ns=6_000_000,guard_line_ns=3_000,
        nominal_line_ns=3_380,minimum_retry_ns=450_000,maximum_attempts_per_hardware_frame=2,
        maximum_copies_per_hardware_frame=1,read_only_prefetch_registers=['0x0ae6b804','0x0ae6b970'],
        verified_after_guard_before_copy=True,output_store_barrier_and_end_phase_receipt=True,
        wire_kind=52,normal_notification_clock=True,
        existing_reference_and_requeue_rules=True,fallback_when_no_safe_window=True))
    plan.update(state='prepared-frame351-one-shot',trial='0351',image=image['image'],image_sha256=image['image_sha256'],
        image_bytes=image['image_bytes'],boot_command=image['command'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(previous),
        optimization='Prefetch-aware blanking copy scheduling using the existing timer and held-frame ownership',
        performance_comparison='Same CRC and whole-frame rules as 0350, including focused 4/6 release queue waits',
        log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline,
            maximum_suffix_bytes=POST_LOG_BYTES-baseline,sizes=sizes,metadata_preflight=True,verified_prefixes_required=True,
            previous_verified_suffix_bytes=growth,reference_kernel_log_bytes=raw,reserved_frame_console_bytes=extra))
    return plan
