"""Bind the SDK-matched Core control and the separately scored sustained drag."""

from frame361_scope import CONTROL, CORE as OPTIMIZED_CORE, LOG_PATHS, MAIN, P360, SAVED_SLOTS, WORK
from frame361_scope import load, pacing, require, sha, signed_pair
from frame358_scope import APPROVAL_FLAGS

BASE = WORK/'research/tmp/frame-362'
P361 = MAIN/'research/tmp/gauguin-warm-recording-worktree-20261120/research/tmp/frame-361'
P357 = MAIN/'research/tmp/gauguin-issued-frame-worktree-20261120/research/tmp/frame-357'
REF361 = P361/'execution'
REFERENCE = REF361/'restored-capture/result.json'
DOC = WORK/'docs/gauguin-frame-362-trial-20261121.md'
PATCH = WORK/'xnu/patches/0275-gauguin-scripted-sustained-drag.patch'
HEADER = 'f34e6f665e71ec13feb267889ac0891b9c0e2b216a79fcb68049bc29f8308a9e'
RESULT = '7f730194f0f4df75deb55c3e84543d761aee860ed99034ce2ae0b339b261550e'
PROOF = 'bc4f3bb49f439e9e5f2186578ec16a2dabfc33c48c9bb8301d064cf0f2fea10e'
CORE_BYTES = 7_975_712
BATCH = 340_000_000
RESERVE = 202_000_000
LOG_SUFFIX = 10_000_000
METADATA_CAP = 14_000_000
CONSOLE_RESERVE = 740_000
MOTION = dict(start_after_last_release_ms=2500, timeout_from_due_ms=2400,
    step_count=160, sample_interval_ms=10, x_start=900, x_end=180, y=1200,
    normal_reports=162, maximum_reports_including_failure_release=163,
    head_excluded_ms=350, tail_excluded_ms=100, minimum_scored_ms=1100,
    calibrated_before_motion=True, traces_buffered_until_release=True)
FLAGS = APPROVAL_FLAGS + ('allow_0362_SDK27_2_unmodified_Core',
    'allow_0362_touch_only_kernel_and_single_sustained_drag',
    'allow_0362_60Hz_CRC_pairs_calibration_and_preblank_probe')
SUCCESS = '0362-same-SDK-and-sustained-motion-measured-root-restored'


def check_baseline():
    require(sha(REF361/'result.json')==RESULT and sha(REF361/'independent-restore.json')==PROOF,
            '0361 reference or independent proof differs')
    pacing.check_restored(REF361)
    baseline = load(REFERENCE)
    current = load(BASE/'current-root-capture/result.json')
    require(current['files']==baseline['files'] and current['directories']==baseline['directories'] and
            current['root_header_sha256']==baseline['root_header_sha256']==HEADER and
            current['combined_log_bytes']==baseline['combined_log_bytes']==151_854_341 and
            not current['device_writes'], '0362 live preflight differs from restored 0361')
    return current


def check_budget():
    budget = load(BASE/'build-storage-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==BATCH and
            budget['current_accounted_bytes']+BATCH<=budget['limit_bytes'],
            '0362 whole preparation and execution batch not admitted')
    return budget


def expected_plan():
    current = check_baseline()
    reference = P361/'trial-plan.json'
    plan = load(reference)
    _,pair = signed_pair(P361)
    original = pair['variants']['reference']
    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame362-image.json')
    staged_files = BASE/'slot-delta/install-plan.json'
    staged = load(staged_files)
    edr = load(BASE/'edr-native/result.json')
    replacements = kernel['object_replacements']
    require(kernel['state']=='0362-native-ARM64-linked' and kernel['inputs_unchanged'] and
            kernel['baseline_reproduced_except_uuid'] and kernel['input_pins'][str(PATCH)]==sha(PATCH) and
            len(replacements)==1 and all(name.endswith('/sweet_touch.o') for pair in replacements.items()
                                        for name in pair) and
            kernel['kernel_sha256']==sha(kernel['kernel'])==image['kernel_sha256'] and
            kernel['identity']==image['build_identity']==edr['kernel_identity'] and
            kernel['kernel_banner']==image['kernel_banner'] and image['image_sha256']==sha(image['image']) and
            len(image['command'])==607 and image['command']==plan['boot_command'].replace('swp=3','swp=4'),
            '0362 kernel differs beyond the additional stimulus and build identity')
    require(plan['owned_core_sha256']==OPTIMIZED_CORE and staged['trial']=='0362' and
            staged['core_sha256']==original['sha256']==CONTROL and
            staged['rows']['core']['new_logical']==original['bytes']==CORE_BYTES and
            staged['rows']['eagl']['new_file_sha256']==plan['SB_sha256'] and
            staged['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and
            edr['identity_only_retarget'] and edr['scope_checks']==2145 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==plan['misc_before_sha256'],
            '0362 installed control, frontend, identity-only helper, or misc differs')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    observed = sum(sizes.values())
    growth = observed-plan['log_capture']['measured_baseline_bytes']
    console_bytes = (REF361/'kernel.log').stat().st_size
    require(observed==151_854_341 and growth==4_484_921 and console_bytes==3_377_767 and
            console_bytes+CONSOLE_RESERVE<4*1024**2, '0362 measured log budget differs')
    plan.update(state='prepared-frame362-one-shot',trial='0362',root_header_sha256=HEADER,
        install_plan_sha256=sha(staged_files),parent_trial_plan_sha256=sha(reference),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        boot_command=image['command'],kernel_identity=kernel['identity'],kernel_banner=kernel['kernel_banner'],
        EDR_helper_sha256=edr['binary_sha256'],owned_core_sha256=CONTROL,owned_core_logical_bytes=CORE_BYTES,
        new_kernel_builds=1,new_boot_images=1,storage_reserve_bytes=RESERVE,
        optimization='Unmodified iOS 27.2 SDK Core control. Append one independently scored sustained drag.',
        performance_comparison='Same-SDK 0361 comparison for the original 13 strokes and separately scored sustained drag.',
        matched_Core_control=dict(sdk='27.2',sha256=CONTROL,bytes=CORE_BYTES,installed_this_trial=True,
                                  optimized_reference_sha256=OPTIMIZED_CORE),
        sustained_motion=MOTION,
        log_capture=dict(plan['log_capture'],max_combined_log_bytes=observed+LOG_SUFFIX,
            measured_baseline_bytes=observed,maximum_suffix_bytes=LOG_SUFFIX,sizes=sizes,
            previous_verified_suffix_bytes=growth,reference_kernel_log_bytes=console_bytes,
            reserved_frame_console_bytes=CONSOLE_RESERVE))
    return plan
