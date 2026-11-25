"""The one-shot 0355 identity and the restored starting point."""

from core342_scope import APPROVAL_FLAGS
from frame354_scope import CORE_SHA, FOCUS, LOG_PATHS, MAIN, P346, REF350, REF353, POST_LOG_BYTES, RELEASE_NS, RESERVE, TOOLCHAIN, WORK
from frame354_scope import check_references as check_display_references
from frame354_scope import load, require, sha
from frame355_display import MAX_EMPTY_RECEIPTS

BASE = WORK/'research/tmp/frame-355'
P354 = MAIN/'research/tmp/gauguin-retained-ready-worktree-20261120/research/tmp/frame-354'
REF354 = P354/'execution'
FIX = MAIN/'research/tmp/gauguin-retained-ready-clear-worktree-20261120/research/tmp/retained-ready-clear-host/result.json'
RESULT_354 = '2a477ba9bdb28648d2bdd05c9c5fb30c0b999db1c1b618bbb5fb91f3543f986b'
PROOF_354 = '229dc33ddab414b7526f38d63a19a2d984e1aeb397c41b2c2abeaef697e92bef'
RESTORED_354 = '6d33a8f0422bfbf81e3a64a874de36398ad19b62ca2f9c96d1bdd807b7324757'
HEADER = 'f75154855d381582fd5da9009bc5e95ba83124c115b7166027d772f90af85a6a'
DOC = WORK/'docs/gauguin-frame-355-trial-20261120.md'
EMPTY_FIX = WORK/'xnu/patches/0267-gauguin-guard-empty-display-swaps.patch'
PATCH = WORK/'xnu/patches/0268-gauguin-observe-empty-display-swap.patch'
CLEANUP = MAIN/'research/tmp/0355-storage-retirement'
FLAGS = APPROVAL_FLAGS + ('allow_0355_exact_0346_core','allow_0355_stable_data_MISR_preimage_and_exact_restore',
    'allow_0355_empty_layer_startup_and_completed_fence_retention')
SUCCESS = '0355-empty-layer-and-retained-ready-copy-measured-root-restored'
STARTUP = dict(require_legacy_empty_update_before_first_stroke=True,
    witnessed_update_mask=1,witnessed_surface=0,maximum_completed_empty_swap_receipts=MAX_EMPTY_RECEIPTS,
    no_blanking_slot_or_writer_version=True,no_GPU_read_guards_or_bytes_in_empty_update=True)


def check_references():
    check_display_references()
    result = load(REF354/'result.json')
    proof = load(REF354/'independent-restore.json')
    require(sha(REF354/'result.json')==RESULT_354 and sha(REF354/'independent-restore.json')==PROOF_354 and
        sha(REF354/'restored-capture/result.json')==RESTORED_354 and result['boot_attempts']==1 and
        result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
        len(proof['files'])==6 and proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and
        proof['all_original_slot_bits_allocated'] and proof['root_header_sha256']==HEADER,
        '0354 independent restored baseline differs')


def expected_plan():
    check_references()
    previous = P354/'trial-plan.json'
    plan = load(previous)
    last = load(REF354/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(last['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==last['files'] and current['directories']==last['directories'] and
            not current['device_writes'], 'fresh baseline differs from independently restored 0354')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    kernel_log_bytes = (REF353/'kernel.log').stat().st_size
    reference_rows = load(REF353/'analysis-after-readback/cross-frame-present-audit.json')['trace_rows']
    # Reserve the entire original frame ring remainder and all bounded startup witnesses.
    console_extra = (16383-reference_rows)*160+2048+MAX_EMPTY_RECEIPTS*192
    reference_growth = load(REF353/'restored-capture/result.json')['combined_log_bytes'] - 116_044_306
    require(current['combined_log_bytes']==baseline==120_557_549 and
            baseline-plan['log_capture']['measured_baseline_bytes']==36_903 and
            POST_LOG_BYTES-baseline>=reference_growth==4_476_340 and
            kernel_log_bytes+console_extra<4*1024**2, '0355 log reservation differs')

    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame355-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    original = load(P346/'core-native/result.json')
    fix = load(FIX)
    gpu_object = P354/'native-kernel/GauguinGPU.o'
    require(core['state']=='0355-exact-0346-core-signed' and core['binary']==original['binary'] and
            core['binary_sha256']==sha(core['binary'])==CORE_SHA and core['bytes']==original['bytes']==7_992_224 and
            core['signature_verified'],'0355 signed Core differs from 0346')
    args = plan['boot_command'].split()
    require(args.count('sweetfb_stats=9')==args.count('sweetfb_hz=60')==args.count('swp=3')==1 and
            image['command']==plan['boot_command'] and len(image['command'].encode())==607,'0355 boot command changed')
    require(sha(FIX)=='aa0d3a5fce488fb29f08a77369f6ae5576cb942154846baee4b3fb4729eb9d36' and
            sha(EMPTY_FIX)==fix['patch_sha256']==kernel['input_pins'][str(EMPTY_FIX)] and
            kernel['input_pins'][str(PATCH)]==sha(PATCH) and
            kernel['input_pins'][str(gpu_object)]==sha(gpu_object) and
            sha(BASE/'native-kernel/source/iokit/Kernel/arm/GauguinGPU.cpp')==
            sha(P354/'native-kernel/source/iokit/Kernel/arm/GauguinGPU.cpp'),'0355 source or carried GPU object differs')
    require(image['image_sha256']==sha(image['image']) and image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and kernel['inputs_unchanged'] and
            kernel['baseline_reproduced_except_uuid'] and {name.rsplit('/',1)[-1] for name in kernel['object_replacements'].values()}==
            {'SweetFramebuffer.o','gauguin_ui_trace_board.o'} and edr['binary_sha256']==sha(edr['binary']) and
            edr['scope_checks']==2145 and edr['identity_only_retarget'], '0355 image, kernel or EDR identity differs')
    plan.update(state='prepared-frame355-one-shot',trial='0355',image=image['image'],image_sha256=image['image_sha256'],
        image_bytes=image['image_bytes'],boot_command=image['command'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(previous),optimization='Keep valid empty swaps on the normal path and retain completed GPU-backed swaps',
        performance_comparison='0350 baseline and 0353 comparison on thirteen strokes, same CRC and whole-frame rules, classify missed presents',
        startup_acceptance=STARTUP,log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline,
        maximum_suffix_bytes=POST_LOG_BYTES-baseline,sizes=sizes,metadata_preflight=True,verified_prefixes_required=True,
        previous_verified_suffix_bytes=36_903,reference_qualified_suffix_bytes=reference_growth,
        reference_kernel_log_bytes=kernel_log_bytes,reserved_frame_console_bytes=console_extra))
    return plan
