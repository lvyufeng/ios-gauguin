"""Bounds and provenance for the 0352 60 Hz presentation trial."""

from core342_scope import APPROVAL_FLAGS
from frame351_scope import CORE_SHA, FOCUS, LOG_PATHS, MAIN, P346, P350, POST_LOG_BYTES, RELEASE_NS, RESERVE, WORK
from frame351_scope import REFERENCE_PROOF as PROOF_350
from frame351_scope import REFERENCE_RESULT as RESULT_350
from frame351_scope import load, require, sha

BASE = WORK/'research/tmp/frame-352'
P351 = MAIN/'research/tmp/gauguin-present-cadence-worktree-20261119/research/tmp/frame-351'
REF350, REF351 = P350/'execution', P351/'execution'
RESULT_351 = 'f76c488a47ffdd8b9b459c3ccb74f7c81051255ed1b099fc7251a6f4385a875e'
PROOF_351 = '0f6dba1e39600456f173d87fc44b5ac4487ccc526bfbbb3b1a8f22a7aa70c603'
BOUNDARIES_351 = '79ccbb687b6a10a9cdd623c60e5053d9742fab978b63b96da9f12c999574aff5'
HEADER = 'fca346fdc73a9ad117ee85c4230446b922db94193da3fdc07908c1d5d5428b75'
DOC = WORK/'docs/gauguin-frame-352-trial-20261120.md'
PATCH = WORK/'xnu/patches/0264-gauguin-GPU-ready-blanking-copy.patch'
CLEANUP = MAIN/'research/tmp/0352-storage-retirement'
GPU_BUILD = MAIN/'research/tmp/gauguin-frame-345-worktree-20261119/research/tmp/frame-345/native-kernel/build-manifest.json'
COPY_BUDGET_NS = 5_500_000
FLAGS = APPROVAL_FLAGS + ('allow_0352_exact_0346_core','allow_0352_stable_data_MISR_preimage_and_exact_restore',
    'allow_0352_GPU_ready_retry_and_paired_blanking_copy')
SUCCESS = '0352-GPU-ready-blanking-and-output-measured-root-restored'


def check_references():
    for path, result_sha, proof_sha in ((REF350,RESULT_350,PROOF_350), (REF351,RESULT_351,PROOF_351)):
        result = load(path/'result.json')
        proof = load(path/'independent-restore.json')
        require(sha(path/'result.json')==result_sha and sha(path/'independent-restore.json')==proof_sha and
                result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
                len(proof['files'])==6 and proof['journal_empty'] and proof['misc_original_4096_bytes_match'],
                'reference restoration provenance differs')
    require(sha(REF351/'analysis-after-readback/blanking-boundary-verification.json')==BOUNDARIES_351,
            '0351 copy boundary verification differs')


def expected_plan():
    previous = P351/'trial-plan.json'
    plan = load(previous)
    check_references()
    last = load(REF351/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(last['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==last['files'] and current['directories']==last['directories'] and
            not current['device_writes'], 'fresh baseline differs from independent 0351 restoration')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    kernel_log_bytes = (REF351/'kernel.log').stat().st_size
    frame_rows = load(REF351/'analysis-after-readback/blanking-boundary-verification.json')['trace_rows']
    console_extra = (16383-frame_rows)*160+2048
    growth = baseline-plan['log_capture']['measured_baseline_bytes']
    require(current['combined_log_bytes']==baseline==111_554_770 and
            POST_LOG_BYTES-baseline>=growth>0 and kernel_log_bytes+console_extra<4*1024**2,
            'measured 0352 log reservation differs')

    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame352-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    original = load(P346/'core-native/result.json')
    require(core['state']=='0352-exact-0346-core-signed' and core['binary']==original['binary'] and
            core['binary_sha256']==sha(core['binary'])==CORE_SHA and
            core['bytes']==original['bytes']==7_992_224 and core['signature_verified'],
            'Core differs from the signed 0346 baseline')
    args = plan['boot_command'].split()
    require(args.count('sweetfb_stats=7')==args.count('sweetfb_hz=60')==args.count('swp=3')==1 and
            image['command']==plan['boot_command'].replace('sweetfb_stats=7','sweetfb_stats=8') and
            len(image['command'].encode())==607,'only the capture mode token may change')
    require(image['image_sha256']==sha(image['image']) and
            image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            {name.rsplit('/',1)[-1] for name in kernel['object_replacements'].values()}==
                {'GauguinGPU.o','SweetFramebuffer.o','gauguin_ui_trace_board.o'} and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145,
            'kernel, image or EDR identity differs')
    plan['frame_capture']['opt_in'] = 'sweetfb_stats=8'
    policy = plan['frame_capture']['presentation_policy']
    policy.pop('minimum_retry_ns')
    policy.update(copy_budget_ns=COPY_BUDGET_NS, timed_attempts_per_hardware_frame=1,
        ready_retry_attempts_per_hardware_frame=1, ready_ticket_surface_and_pending_generation_required=True,
        wake_after_surface_visibility_and_completion_publication=True, wake_wire_kind=53, fast_copy_flag=4,
        full_copy_panel_and_source_stride=[4320,4608], full_copy_bytes=10_368_000,
        existing_read_guard_required=True)
    plan.update(state='prepared-frame352-one-shot',trial='0352',image=image['image'],image_sha256=image['image_sha256'],
        image_bytes=image['image_bytes'],boot_command=image['command'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(previous),optimization='Matched GPU-ready blanking retry and paired integer panel copy',
        performance_comparison='0350 baseline and 0351 reference, same hardware output/frame rules and 4/6 focused release windows',
        log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline,
            maximum_suffix_bytes=POST_LOG_BYTES-baseline,sizes=sizes,metadata_preflight=True,verified_prefixes_required=True,
            previous_verified_suffix_bytes=growth,reference_kernel_log_bytes=kernel_log_bytes,reserved_frame_console_bytes=console_extra))
    return plan
