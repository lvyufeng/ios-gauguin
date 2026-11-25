"""Bind 0364's matched replay to the exact restored 0363 device baseline."""

from frame363_scope import CONTROL, CORE_BYTES, LOG_PATHS, LOG_SUFFIX, MAIN, METADATA_CAP, MOTION
from frame363_scope import IMAGE, RESERVE, SAVED_SLOTS, WORK, load, pacing, require, sha
from frame358_scope import APPROVAL_FLAGS

BASE = WORK/'research/tmp/frame-364'
P363 = MAIN/'research/tmp/gauguin-frame-gate-worktree-20261121/research/tmp/frame-gate-363'
REF363 = P363/'execution'
REFERENCE = REF363/'restored-capture/result.json'
DOC = WORK/'docs/gauguin-frame-364-trial-20261121.md'
PATCH = WORK/'xnu/patches/0276-gauguin-arm-frame-capture-for-sustained-drag.patch'
HEADER = '3f6ceb845740bb9e98fbf58af415abe1f3cb967d2ca54054af6b6b050a0675ac'
RESULT = 'a7c321c4199a24d4df1432b024616849f192f731fc30924962c1a03089921d31'
PROOF = 'c56b1273bbe76d2302cbf9f754e6f41169d81c4b006014fdb29b3af54a8d0ce9'
BATCH = 275_000_000
REPORT_BYTES = 2_000_000
FLAGS = APPROVAL_FLAGS + ('allow_0364_exact_0363_kernel_and_userspace',
    'allow_0364_same_13_strokes_and_fixed_slow_drag',
    'allow_0364_60Hz_CRC_pairs_calibration_and_preblank_probe')
SUCCESS = '0364-matched-Core-IO-and-display-deadlines-measured-root-restored'


def check_budget():
    budget = load(BASE/'build-storage-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==BATCH and
            budget['current_accounted_bytes']+BATCH<=budget['limit_bytes'],
            'complete 0364 staging and runtime batch was not admitted')


def check_archive():
    require(sha(REF363/'result.json')==RESULT and sha(REF363/'independent-restore.json')==PROOF,
            '0363 result or independent restoration proof differs')
    return pacing.check_restored(REF363)


def check_baseline():
    check_archive()
    current = load(BASE/'current-root-capture/result.json')
    restored = load(REFERENCE)
    require(current['files']==restored['files'] and current['directories']==restored['directories'] and
            current['root_header_sha256']==restored['root_header_sha256']==HEADER and
            current['combined_log_bytes']==restored['combined_log_bytes']==159_868_421 and
            len(current['files'])==31 and not current['device_writes'],
            '0364 read-only baseline differs from the independently restored 0363 root')
    return current


def expected_plan():
    current = check_baseline()
    previous = P363/'trial-plan.json'
    plan = load(previous)
    image = load(P363/'frame363-image.json')
    delta_path = BASE/'slot-delta/install-plan.json'
    delta = load(delta_path)
    core = load(BASE/'core-native/result.json')
    edr = load(BASE/'edr-native/result.json')
    require(plan['image_sha256']==sha(plan['image'])==image['image_sha256']==IMAGE and
            plan['image_bytes']==image['image_bytes']==22_216_704 and
            plan['boot_command']==image['command'] and plan['kernel_banner']==image['kernel_banner'] and
            plan['kernel_identity']==image['build_identity']==edr['kernel_identity'] and
            {'swp=4','sweetfb_hz=60','sweetfb_stats=9','sweetnvt=0'}<=set(image['command'].split()),
            '0364 image, banner, input or 60 Hz configuration differs from 0363')
    require(delta['trial']=='0364' and delta['core_sha256']==plan['owned_core_sha256']==core['binary_sha256']==CONTROL and
            sha(core['binary'])==CONTROL and delta['rows']['core']['new_logical']==core['bytes']==CORE_BYTES and
            delta['rows']['eagl']['new_file_sha256']==plan['SB_sha256'] and
            delta['admission_sha256']==plan['EDR_helper_sha256']==edr['binary_sha256']==sha(edr['binary']) and
            sha(BASE/'metadata-snapshot/misc-original.bin')==plan['misc_before_sha256'] and
            plan['sustained_motion']==MOTION,
            '0364 signed slots, original misc or input sequence differs')
    sizes = {name:current['files'][name]['bytes'] for name in sorted(LOG_PATHS)}
    measured = sum(sizes.values())
    growth = measured-plan['log_capture']['measured_baseline_bytes']
    console = load(REF363/'kernel-IO-analysis.json')['ring']['total_bytes']
    require(growth==4_003_082 and measured==current['combined_log_bytes'] and console<4_194_304,
            '0363 measured log baseline or persistent ring differs')
    plan.update(state='prepared-frame364-one-shot',trial='0364',root_header_sha256=HEADER,
        install_plan_sha256=sha(delta_path),parent_trial_plan_sha256=sha(previous),
        new_kernel_builds=0,new_boot_images=0,
        optimization='Matched 0363 replay with exact late Core/IO scope and callback-to-swap deadline attribution.',
        performance_comparison='Compare original strokes and slow drag separately with 0363 using certified CRC and copies.',
        log_capture=dict(plan['log_capture'],max_combined_log_bytes=measured+LOG_SUFFIX,
            measured_baseline_bytes=measured,sizes=sizes,previous_verified_suffix_bytes=growth,
            reference_kernel_log_bytes=console,reserved_frame_console_bytes=4_194_304-console))
    return plan
