"""0354 frame identity, effect limits and reference provenance."""

from core342_scope import APPROVAL_FLAGS
from frame352_scope import CORE_SHA, FOCUS, LOG_PATHS, MAIN, P346, POST_LOG_BYTES, RELEASE_NS, RESERVE, WORK
from frame352_scope import REF350, PROOF_350, RESULT_350, load, require, sha

BASE = WORK/'research/tmp/frame-354'
P353 = MAIN/'research/tmp/gauguin-ready-scan-worktree-20261120/research/tmp/frame-353'
REF353 = P353/'execution'
RESULT_353 = '938dc8328a3261b554f8997d7fa5264331c4deb1215b6e519cfb46d6b1dcb7f8'
PROOF_353 = '78518204f47b9c4b2a527d66e421b96947df511e176c5bbe4807a32fad69e531'
ALIGN_353 = '7947d3e1eb7e803c21734741ee6d1654505bd76a4ec6f48c5f4bdcd8a4f9c61a'
SELECT_353 = '34c014d9dcbfee86e024bff4bd4d409093a7f718c27cff08bbb2794aca580660'
HEADER = '27523e2fd3399a198b993fb72a32af86f08975f72952e93336dc6af563ba4ee6'
DOC = WORK/'docs/gauguin-frame-354-trial-20261120.md'
PATCH = WORK/'xnu/patches/0266-gauguin-retain-ready-swap.patch'
CLEANUP = MAIN/'research/tmp/0354-storage-retirement'
TOOLCHAIN = '/Library/Developer/CommandLineTools'
FLAGS = APPROVAL_FLAGS + ('allow_0354_exact_0346_core','allow_0354_stable_data_MISR_preimage_and_exact_restore',
                          'allow_0354_ready_retention_across_waiting_swaps_and_fresh_GPU_guard')
SUCCESS = '0354-retained-ready-copy-and-output-measured-root-restored'
POLICY = dict(ready_and_waiting_have_independent_display_holds=True, ready_replaced_only_on_completed_watched_GPU_write=True,
              completed_GPU_write_bound_to_waiting_ticket_at_admission=True, idle_only_probe_cannot_promote=True,
              fresh_GPU_read_guard_checks_exact_surface_write_version=True, ready_retry_does_not_replace_waiting=True,
              maximum_resident_ready_candidates=1, promotion_wire_kind=56, read_validation_wire_kind=57)


def check_references():
    for path, result_sha, proof_sha in ((REF350,RESULT_350,PROOF_350), (REF353,RESULT_353,PROOF_353)):
        result = load(path/'result.json')
        proof = load(path/'independent-restore.json')
        require(sha(path/'result.json')==result_sha and sha(path/'independent-restore.json')==proof_sha and
                result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
                len(proof['files'])==6 and proof['journal_empty'] and proof['misc_original_4096_bytes_match'],
                'reference restoration provenance differs')
    require(sha(REF353/'present-alignment-0350-0352-0353.json')==ALIGN_353 and
            sha(REF353/'ready-selection-analysis.json')==SELECT_353, '0353 presentation evidence differs')


def expected_plan():
    check_references()
    previous = P353/'trial-plan.json'
    plan = load(previous)
    last = load(REF353/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(last['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==last['files'] and current['directories']==last['directories'] and
            not current['device_writes'], 'fresh baseline differs from independent 0353 restoration')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    kernel_log_bytes = (REF353/'kernel.log').stat().st_size
    frame_rows = load(REF353/'analysis-after-readback/cross-frame-present-audit.json')['trace_rows']
    console_extra = (16383-frame_rows)*160+2048
    growth = baseline-plan['log_capture']['measured_baseline_bytes']
    require(current['combined_log_bytes']==baseline==120_520_646 and growth==4_476_340 and
            POST_LOG_BYTES-baseline>=growth and kernel_log_bytes+console_extra<4*1024**2, 'log reservation differs')

    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame354-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    original = load(P346/'core-native/result.json')
    require(core['state']=='0354-exact-0346-core-signed' and core['binary']==original['binary'] and
            core['binary_sha256']==sha(core['binary'])==CORE_SHA and
            core['bytes']==original['bytes']==7_992_224 and core['signature_verified'], 'signed 0346 Core differs')
    args = plan['boot_command'].split()
    require(args.count('sweetfb_stats=9')==args.count('sweetfb_hz=60')==args.count('swp=3')==1 and
            image['command']==plan['boot_command'] and len(image['command'].encode())==607, '0353 boot command changed')
    require(image['image_sha256']==sha(image['image']) and image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            {name.rsplit('/',1)[-1] for name in kernel['object_replacements'].values()}==
                {'GauguinGPU.o','SweetFramebuffer.o','gauguin_ui_trace_board.o'} and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145 and edr['identity_only_retarget'],
            'kernel, image or EDR identity differs')
    policy = plan['frame_capture']['presentation_policy']
    policy.pop('observed_ready_kept_with_latest_pending_generation')
    policy.update(POLICY)
    plan.update(state='prepared-frame354-one-shot',trial='0354',image=image['image'],image_sha256=image['image_sha256'],
        image_bytes=image['image_bytes'],boot_command=image['command'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(previous),optimization='Keep the valid ready swap until a newer watched GPU write completes',
        performance_comparison='0350 baseline and 0353 comparison on all thirteen strokes using the same CRC and whole-frame rules',
        log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline,
            maximum_suffix_bytes=POST_LOG_BYTES-baseline,sizes=sizes,metadata_preflight=True,verified_prefixes_required=True,
            previous_verified_suffix_bytes=growth,reference_kernel_log_bytes=kernel_log_bytes,
            reserved_frame_console_bytes=console_extra))
    return plan
