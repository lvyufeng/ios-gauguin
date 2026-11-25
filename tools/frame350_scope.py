"""Frozen 0350 stable MISR control preimage and matched queue-tail scope."""

from core342_scope import APPROVAL_FLAGS
from frame349_log import DATA_INPUT
from frame349_scope import CONSOLE_EXTRA, CORE_SHA, LOG_PATHS, MAIN, P346, POST_LOG_BYTES, RESERVE, WORK
from frame349_scope import load, require, sha


BASE = WORK/'research/tmp/frame-350'
P349 = MAIN/'research/tmp/gauguin-crc-blanking-worktree-20261119/research/tmp/frame-349'
REFERENCE = P349/'execution'
REFERENCE_RESULT = '359a8dc36082dee47bcba1b1bd798f3c2a73a961a9643b260e19479f56bbb09a'
REFERENCE_PROOF = '3441b1dc09db0caa4cd83a0dfecf523b70146698914c00e583a078355f0c34ee'
HEADER = '9ef376d2a4af1499db900fdd0e5b199531524b26016a177a549a05270766b628'
DOC = WORK/'docs/gauguin-frame-350-trial-20261119.md'
PATCH = WORK/'xnu/patches/0262-gauguin-verify-and-restore-misr-preimage.patch'
FLAGS = APPROVAL_FLAGS + ('allow_0350_exact_0346_core','allow_0350_read_only_intf1_counters',
                          'allow_0350_stable_data_MISR_preimage_and_exact_restore')
SUCCESS = '0350-collection-qualified-output-cadence-measured-root-restored'


def expected_plan():
    previous = P349/'trial-plan.json'
    plan = load(previous)
    proof = load(REFERENCE/'independent-restore.json')
    last = load(REFERENCE/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(sha(REFERENCE/'result.json')==REFERENCE_RESULT and sha(REFERENCE/'independent-restore.json')==REFERENCE_PROOF and
            proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and
            proof['root_header_sha256']==last['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==last['files'] and current['directories']==last['directories'] and
            not current['device_writes'], 'fresh baseline differs from the independent 0349 restoration')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    raw_bytes = (REFERENCE/'kernel.log').stat().st_size
    reference_growth = last['combined_log_bytes']-plan['log_capture']['measured_baseline_bytes']
    require(current['combined_log_bytes']==baseline==102_573_456 and
            POST_LOG_BYTES-baseline>=reference_growth>0 and raw_bytes+CONSOLE_EXTRA<4*1024**2,
            'measured 0350 capture budget differs')

    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame350-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    original = load(P346/'core-native/result.json')
    require(core['state']=='0350-exact-0346-core-signed' and
            core['binary']==original['binary'] and core['binary_sha256']==sha(core['binary'])==CORE_SHA and
            core['bytes']==original['bytes']==7_992_224 and core['signature_verified'],
            'Core differs from the signed 0346 baseline')
    args = plan['boot_command'].split()
    require(args.count('sweetfb_stats=5')==args.count('sweetfb_hz=60')==args.count('swp=3')==1 and
            image['command']==plan['boot_command'].replace('sweetfb_stats=5','sweetfb_stats=6') and
            len(image['command'].encode())==607, 'only the capture mode token may change')
    require(image['image_sha256']==sha(image['image']) and
            image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            kernel['inputs_unchanged'] and kernel['baseline_reproduced_except_uuid'] and
            len(kernel['object_replacements'])==2 and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145,
            'kernel, image or EDR identity differs')
    frame = plan['frame_capture']
    frame.pop('crc_enable_requires_exact_zero_preimage')
    frame.update(opt_in='sweetfb_stats=6',crc_required_preimage=DATA_INPUT,
        crc_preimage_reads=2,crc_preimage_requires_adjacent_qualified_edges=True,
        crc_cleanup_values=[1024,DATA_INPUT],crc_cleanup_readback_equals_recorded_preimage=True,
        crc_no_cleanup_stores_after_ownership_fault=True)

    plan.update(state='prepared-frame350-one-shot',trial='0350',image=image['image'],image_sha256=image['image_sha256'],
        image_bytes=image['image_bytes'],boot_command=image['command'],kernel_identity=kernel['identity'],
        kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(previous),optimization='Exact 0346 Core with a dual-read idle MISR preimage and exact restoration',
        performance_comparison='0349 and 0350 matched stroke/phase with boot-local identities and focused waits in swipes 3 and 11',
        log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline,
            maximum_suffix_bytes=POST_LOG_BYTES-baseline,sizes=sizes,metadata_preflight=True,verified_prefixes_required=True,
            previous_verified_suffix_bytes=reference_growth,reference_kernel_log_bytes=raw_bytes,
            reserved_CRC_console_bytes=CONSOLE_EXTRA))
    return plan
