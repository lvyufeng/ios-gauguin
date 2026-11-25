"""Freeze the 0356 workload against the independently restored 0355 root."""

from core342_scope import APPROVAL_FLAGS
from frame355_scope import CORE_SHA, FOCUS, LOG_PATHS, MAIN, P346, REF350, POST_LOG_BYTES, RELEASE_NS, RESERVE, STARTUP, TOOLCHAIN, WORK
from frame354_scope import PROOF_350, RESULT_350
from frame355_scope import load, require, sha
from frame356_display import FOCUS_COPY_STROKE

BASE = WORK/'research/tmp/frame-356'
P355 = MAIN/'research/tmp/gauguin-empty-swap-worktree-20261120/research/tmp/frame-355'
REF355 = P355/'execution'
RESULT_355 = '9c22c9186554f51d206fe7045c4598025663eb6cb592d061d78a5c32f8f707c9'
PROOF_355 = 'ecf7507fe95b90703dced3c40f11c24d9654bb94f7fcdfd7498c778f23346ca1'
RESTORED_355 = '3141e7f84a800e34c82646c360692c19ed94edc0b91d842a14227faaea98c9fc'
ALIGN_355 = 'e2b2c1f140dfd9c0369643d3f2b9a9dded9c603246e5a876909dd4242fce7173'
DIAG_355 = '59aec48a778dea74929aaac18a8ddd4aac6fce9adf68058e58c57fc9ff52ed89'
HEADER = 'e914fd26b8d8e40b4850351bdfddcf22df2cd1b0782d4b3e00461b67840e8a4b'
DOC = WORK/'docs/gauguin-frame-356-trial-20261120.md'
RUNTIME_PATCH = WORK/'xnu/patches/0269-gauguin-share-adjacent-issue-guards.patch'
PATCH = WORK/'xnu/patches/0270-gauguin-copy-whole-panel-rows.patch'
CLEANUP = MAIN/'research/tmp/0356-storage-retirement'
FLAGS = APPROVAL_FLAGS + ('allow_0356_exact_0346_core','allow_0356_stable_data_MISR_preimage_and_exact_restore',
    'allow_0356_adjacent_issue_checks_and_whole_row_copy_under_existing_guard')
SUCCESS = '0356-startup-retained-ready-and-output-measured-root-restored'
LATENCY = dict(adjoining_async_ack_checks_share_full_samples=True,deadline_checked_before_each_effect=True,
    submission_and_completion_wire_sequence_unchanged=True,full_width_row_bytes=4320,copy_block_bytes=288,
    whole_screen_copy=True,same_copy_admission_and_boundary_proof=True,focus_copy_stroke=FOCUS_COPY_STROKE)


def check_references():
    for path, expected_result, expected_proof in ((REF350,RESULT_350,PROOF_350),(REF355,RESULT_355,PROOF_355)):
        result,proof=(load(path/name) for name in ('result.json','independent-restore.json'))
        require(sha(path/'result.json')==expected_result and sha(path/'independent-restore.json')==expected_proof and
            result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            len(proof['files'])==6 and proof['journal_empty'] and proof['misc_original_4096_bytes_match'],
            'comparison restoration provenance differs')
    result = load(REF355/'result.json')
    require(result['frame_trace_complete'] and result['empty_layer_startup']['qualified'] and result['misr']['qualified'] and
            sha(REF355/'restored-capture/result.json')==RESTORED_355 and
            sha(REF355/'present-alignment-0350-0353-0355.json')==ALIGN_355 and
            sha(REF355/'analysis-after-readback/presentation-diagnosis-0355.json')==DIAG_355,
            '0355 comparison results differ')


def expected_plan():
    check_references()
    previous=P355/'trial-plan.json'
    plan=load(previous)
    last=load(REF355/'restored-capture/result.json')
    current=load(BASE/'current-root-capture/result.json')
    require(last['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==last['files'] and current['directories']==last['directories'] and
            not current['device_writes'],'fresh baseline differs from independently restored 0355')
    sizes={path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline=sum(sizes.values())
    console_bytes=(REF355/'kernel.log').stat().st_size
    ring_rows=13_216
    console_extra=(16383-ring_rows)*160+2048
    growth=baseline-plan['log_capture']['measured_baseline_bytes']
    require(current['combined_log_bytes']==baseline==125_040_375 and growth==4_482_826 and
            POST_LOG_BYTES-baseline>=growth and console_bytes==3_211_573 and
            console_bytes+console_extra<4*1024**2,'0356 measured log reservation differs')

    kernel=load(BASE/'native-kernel/build-manifest.json')
    image=load(BASE/'frame356-image.json')
    edr=load(BASE/'edr-native/result.json')
    core=load(BASE/'core-native/result.json')
    original=load(P346/'core-native/result.json')
    gpu=P355/'native-kernel/source/iokit/Kernel/arm/GauguinGPU.cpp'
    require(core['state']=='0356-exact-0346-core-signed' and core['binary']==original['binary'] and
            core['binary_sha256']==sha(core['binary'])==CORE_SHA and core['bytes']==original['bytes']==7_992_224 and
            core['signature_verified'],'0356 signed 0346 Core differs')
    args=plan['boot_command'].split()
    require(args.count('sweetfb_stats=9')==args.count('sweetfb_hz=60')==args.count('swp=3')==1 and
            image['command']==plan['boot_command'] and len(image['command'].encode())==607 and
            plan['startup_acceptance']==STARTUP,'0356 boot command or empty-update gate differs')
    require(all(kernel['input_pins'][str(p)]==sha(p) for p in (RUNTIME_PATCH,PATCH)) and
            kernel['input_pins'][str(gpu)]==sha(BASE/'native-kernel/source/iokit/Kernel/arm/GauguinGPU.cpp'),
            '0356 runtime, copy, or framebuffer ownership source differs')
    require(image['image_sha256']==sha(image['image']) and image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and kernel['inputs_unchanged'] and
            kernel['baseline_reproduced_except_uuid'] and {name.rsplit('/',1)[-1] for name in kernel['object_replacements'].values()}==
            {'SweetFramebuffer.o','gauguin_ui_trace_board.o','gauguin_gpu_runtime.o'} and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145 and edr['identity_only_retarget'],
            '0356 fixed image, kernel or EDR identity differs')
    plan.update(state='prepared-frame356-one-shot',trial='0356',image=image['image'],image_sha256=image['image_sha256'],
        image_bytes=image['image_bytes'],boot_command=image['command'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(previous),optimization='Reduce serialized issue time and whole-frame copy work with the same FIFO and read guard',
        performance_comparison='0350 baseline and 0355 comparison on all thirteen strokes, with stroke ten copy boundary and missed swaps',
        latency_acceptance=LATENCY,log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline,
        maximum_suffix_bytes=POST_LOG_BYTES-baseline,sizes=sizes,metadata_preflight=True,verified_prefixes_required=True,
        previous_verified_suffix_bytes=growth,reference_kernel_log_bytes=console_bytes,reserved_frame_console_bytes=console_extra))
    return plan
