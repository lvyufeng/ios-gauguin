"""Freeze the single pre-blank fence probe over the measured 0357 path."""

from core342_scope import APPROVAL_FLAGS
from frame355_scope import CORE_SHA, LOG_PATHS, MAIN, P346, RESERVE, TOOLCHAIN, WORK, load, require, sha
from frame358_audit import BASE, FIRST_PROBE_LINE, FRAME_CAPACITY, P357, PROBE_LIMIT, REF357, check_0357

HEADER = 'f8b2368f00f386214a3dc29bb0afa0d1d161413e23b3f9a6e6a57448aa713ca3'
REPLAY_SHA = '6476d445f81dfb696fb4b65c9ee9883426a90821d8d597e6816202b57145fb38'
DOC = WORK/'docs/gauguin-frame-358-trial-20261120.md'
PATCH = WORK/'xnu/patches/0273-gauguin-probe-issued-fence-before-blanking.patch'
CLEANUP = MAIN/'research/tmp/0358-storage-retirement'
LOG_SUFFIX = 8_000_000
FLAGS = APPROVAL_FLAGS + ('allow_0358_exact_0346_core','allow_0358_stable_data_MISR_and_marker_restore',
                          'allow_0358_one_nonblocking_pre_blank_probe_per_frame')
SUCCESS = '0358-probe-and-output-measured-root-restored'
PROBE_SCOPE = dict(first_readonly_scan_line=FIRST_PROBE_LINE,
    already_qualified_60Hz_route=True,exact_pending_native_ticket_and_surface_version=True,
    maximum_additional_requests_per_scan=1,maximum_additional_requests_per_capture=PROBE_LIMIT,
    skip_if_workloop_has_ready_frame_or_current_scan_already_taken=True,
    skip_for_crc_marker_calibration=True,nonblocking_GPU_lock=True,poll_once=True,
    cached_display_reference_until_probe_returns=True,original_completion_path=True,
    fresh_guard_and_live_scan_checked_at_copy=True,additional_submissions=0,
    wire_kind=60,frame_trace_capacity=FRAME_CAPACITY)


def expected_plan():
    check_0357()
    prior = P357/'trial-plan.json'
    plan = load(prior)
    reference = REF357/'restored-capture/result.json'
    recovered = load(reference)
    proof = load(REF357/'independent-restore.json')
    current = load(BASE/'current-root-capture/result.json')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    old_console = (REF357/'kernel.log').stat().st_size
    extra_console = (FRAME_CAPACITY-1-15916)*160+8192
    growth = baseline-plan['log_capture']['measured_baseline_bytes']
    require(proof['root_header_sha256']==recovered['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==recovered['files'] and current['directories']==recovered['directories'] and
            not current['device_writes'] and current['combined_log_bytes']==baseline==133_948_307 and
            growth==4_452_406 and old_console==3_342_852 and old_console+extra_console<4*1024**2 and
            LOG_SUFFIX>growth+extra_console and sha(BASE/'repeat-audit.json')==REPLAY_SHA,
            '0357 baseline or 0358 measured log budget differs')

    image = load(BASE/'frame358-image.json')
    native = load(BASE/'native-kernel/build-manifest.json')
    core = load(BASE/'core-native/result.json')
    edr = load(BASE/'edr-native/result.json')
    original = load(P346/'core-native/result.json')
    replaced = {p.rsplit('/',1)[-1] for p in native['object_replacements'].values()}
    require(native['input_pins'][str(PATCH)]==sha(PATCH) and native['inputs_unchanged'] and
            native['baseline_reproduced_except_uuid'] and replaced==
            {'SweetFramebuffer.o','GauguinGPU.o','gauguin_ui_trace_board.o','gauguin_ui_trace.o'} and
            image['image_sha256']==sha(image['image']) and image['kernel_sha256']==native['kernel_sha256']==sha(native['kernel']) and
            image['build_identity']==native['identity']==edr['kernel_identity'] and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145 and edr['identity_only_retarget'] and
            core['state']=='0358-exact-0346-core-signed' and core['binary']==original['binary'] and core['signature_verified'] and
            core['binary_sha256']==sha(core['binary'])==CORE_SHA and core['bytes']==original['bytes']==7_992_224 and
            image['command']==plan['boot_command'] and len(image['command'].encode())==607,
            '0358 kernel scope, boot command, image or signed userspace differs')
    plan.update(state='prepared-frame358-one-shot',trial='0358',image=image['image'],image_sha256=image['image_sha256'],
        image_bytes=image['image_bytes'],kernel_identity=native['identity'],kernel_banner=native['kernel_banner'],
        EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(prior),optimization='Check once for the bound writer at the pre-blank scan phase',
        performance_comparison='0357 primary control and 0350/0355/0356 references by gesture, phase and hardware ordinal',
        fence_probe=PROBE_SCOPE,
        frame_capture=dict(plan['frame_capture'],records=FRAME_CAPACITY),
        log_capture=dict(max_combined_log_bytes=baseline+LOG_SUFFIX,measured_baseline_bytes=baseline,maximum_suffix_bytes=LOG_SUFFIX,
             sizes=sizes,metadata_preflight=True,verified_prefixes_required=True,previous_verified_suffix_bytes=growth,
             reference_kernel_log_bytes=old_console,reserved_frame_console_bytes=extra_console))
    return plan
