"""Exact 0353 bounds and provenance for 60 Hz cross-frame readiness."""

from core342_scope import APPROVAL_FLAGS
from frame352_scope import CORE_SHA, FOCUS, LOG_PATHS, MAIN, P346, P350, POST_LOG_BYTES, RELEASE_NS, RESERVE, WORK
from frame352_scope import REF350, PROOF_350, RESULT_350, load, require, sha

BASE = WORK/'research/tmp/frame-353'
P352 = MAIN/'research/tmp/gauguin-gpu-ready-worktree-20261120/research/tmp/frame-352'
REF352 = P352/'execution'
RESULT_352 = '7a893ad03a3720a6ed14acd65de440d0a0bbb90beca18602d458a62cc83e5425'
PROOF_352 = 'fbf83ceee3799478f1068e3712612a18c8a8a26e487e88fedfb74e6c6f9f052e'
WINDOWS_352 = 'f5e12a93f0b6c2738fbaf72ee5354c04aaf85809f1de4f67ac4b6904f9c01467'
READY_AUDIT_352 = '4906b2e5b41622a635ca140695ad84ecdc48b6b5201ee1d15848f440c8cca310'
HEADER = '62f6021a67349291b6e00b08e921f9c18b623058a3cdaa48a8dd3a36adafc719'
DOC = WORK/'docs/gauguin-frame-353-trial-20261120.md'
PATCH = WORK/'xnu/patches/0265-gauguin-carry-ready-frame-to-next-scan.patch'
CLEANUP = MAIN/'research/tmp/0353-storage-retirement'
TOOLCHAIN = '/Library/Developer/CommandLineTools'
FLAGS = APPROVAL_FLAGS + ('allow_0353_exact_0346_core','allow_0353_stable_data_MISR_preimage_and_exact_restore',
    'allow_0353_cross_frame_ready_latch_with_fresh_GPU_read_guard')
SUCCESS = '0353-cross-frame-ready-copy-and-output-measured-root-restored'


def check_references():
    for path, result_sha, proof_sha in ((REF350,RESULT_350,PROOF_350), (REF352,RESULT_352,PROOF_352)):
        result = load(path/'result.json')
        proof = load(path/'independent-restore.json')
        require(sha(path/'result.json')==result_sha and sha(path/'independent-restore.json')==proof_sha and
                result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
                len(proof['files'])==6 and proof['journal_empty'] and proof['misc_original_4096_bytes_match'],
                'reference restoration provenance differs')
    require(sha(REF352/'present-alignment-0350-0351-0352.json')==WINDOWS_352 and
            sha(REF352/'analysis-after-readback/gpu-ready-window-audit.json')==READY_AUDIT_352,
            '0352 presentation or deadline audit differs')


def expected_plan():
    previous = P352/'trial-plan.json'
    plan = load(previous)
    check_references()
    last = load(REF352/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(last['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==last['files'] and current['directories']==last['directories'] and
            not current['device_writes'], 'fresh baseline differs from independent 0352 restoration')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    kernel_log_bytes = (REF352/'kernel.log').stat().st_size
    frame_rows = load(REF352/'analysis-after-readback/gpu-ready-window-audit.json')['trace_rows']
    console_extra = (16383-frame_rows)*160+2048
    growth = baseline-plan['log_capture']['measured_baseline_bytes']
    require(current['combined_log_bytes']==baseline==116_044_306 and
            POST_LOG_BYTES-baseline>=growth>0 and kernel_log_bytes+console_extra<4*1024**2,
            'measured 0353 log reservation differs')

    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame353-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    original = load(P346/'core-native/result.json')
    require(core['state']=='0353-exact-0346-core-signed' and core['binary']==original['binary'] and
            core['binary_sha256']==sha(core['binary'])==CORE_SHA and
            core['bytes']==original['bytes']==7_992_224 and core['signature_verified'],
            'Core differs from the signed 0346 baseline')
    args = plan['boot_command'].split()
    require(args.count('sweetfb_stats=8')==args.count('sweetfb_hz=60')==args.count('swp=3')==1 and
            image['command']==plan['boot_command'].replace('sweetfb_stats=8','sweetfb_stats=9') and
            len(image['command'].encode())==607,'only the capture mode token may change')
    require(image['image_sha256']==sha(image['image']) and
            image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            {name.rsplit('/',1)[-1] for name in kernel['object_replacements'].values()}==
                {'GauguinGPU.o','SweetFramebuffer.o','gauguin_ui_trace_board.o'} and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145,
            'kernel, image or EDR identity differs')
    plan['frame_capture']['opt_in'] = 'sweetfb_stats=9'
    policy = plan['frame_capture']['presentation_policy']
    for key in ('timed_attempts_per_hardware_frame','ready_retry_attempts_per_hardware_frame','wake_wire_kind'):
        policy.pop(key)
    policy.update(maximum_attempts_per_hardware_frame=1, readiness_watched_at_swap=True,
        observed_ready_kept_with_latest_pending_generation=True, readiness_probe_at_most_once_per_software_callback=True,
        readiness_probe_uses_GPU_try_lock_outside_framebuffer_lock=True, target_hardware_slot_selected_after_readiness=True,
        ready_wire_kind=54, selection_wire_kind=55)
    plan.update(state='prepared-frame353-one-shot',trial='0353',image=image['image'],image_sha256=image['image_sha256'],
        image_bytes=image['image_bytes'],boot_command=image['command'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(previous),optimization='Latest valid ready swap retained until a safe hardware scan',
        performance_comparison='0350 baseline and 0352 comparison with the same CRC and whole-frame rules on all thirteen strokes',
        log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline,
            maximum_suffix_bytes=POST_LOG_BYTES-baseline,sizes=sizes,metadata_preflight=True,verified_prefixes_required=True,
            previous_verified_suffix_bytes=growth,reference_kernel_log_bytes=kernel_log_bytes,reserved_frame_console_bytes=console_extra))
    return plan
