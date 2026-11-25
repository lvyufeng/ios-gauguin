"""Pin the repaired F344 path to the 0362 restore and signed SDK control."""

from pathlib import Path

from frame362_scope import CONTROL, CORE_BYTES, LOG_PATHS, LOG_SUFFIX, MAIN, METADATA_CAP, MOTION
from frame362_scope import P361, REF361, RESERVE, SAVED_SLOTS, WORK, load, pacing, require, sha, signed_pair
from frame358_scope import APPROVAL_FLAGS

BASE = WORK/'research/tmp/frame-gate-363'
P362 = MAIN/'research/tmp/gauguin-sdk-control-worktree-20261121/research/tmp/frame-362'
REF362 = P362/'execution'
REFERENCE = REF362/'restored-capture/result.json'
DOC = WORK/'docs/gauguin-frame-363-trial-20261121.md'
PATCH = WORK/'xnu/patches/0276-gauguin-arm-frame-capture-for-sustained-drag.patch'
HEADER = 'bb5457ee937bd7cb39100406a447134b804c21e4d5e4477851dcac7e27c8223d'
RESTORED_362 = 'bbb03cfc8cc60d2db08f4bdcc709fda5c4d9523d46467e50a4be8835c08b2fc4'
RESULT_362 = 'aadfd21185cf7d7056573864aed53085de4ff429cfcc3f967cf28d216eff8093'
IMAGE = '0864bb55478cebf41307caec665056e38c8e2ec0233026a707150c760f76d8c0'
KERNEL = 'c6103410473f51b824afd9923157dabde749410bd834d770b7c9d2e4a933bfcf'
BATCH = 260_000_000
CONSOLE_RESERVE = 1_300_000
FLAGS = APPROVAL_FLAGS + ('allow_0363_exact_SDK27_2_unmodified_Core',
    'allow_0363_fixed_motion_with_repaired_F344_gate',
    'allow_0363_60Hz_CRC_pairs_calibration_and_preblank_probe')
SUCCESS = '0363-same-SDK-and-sustained-motion-measured-root-restored'


def check_budget():
    budget = load(BASE/'build-storage-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==BATCH and
            budget['current_accounted_bytes']+BATCH<=budget['limit_bytes'],
            '0363 complete staging and runtime batch was not admitted')
    return budget


def check_baseline():
    proof_path = REF362/'independent-restore.json'
    result_path = REF362/'result.json'
    proof,result = load(proof_path),load(result_path)
    require(sha(proof_path)==RESTORED_362 and sha(result_path)==RESULT_362 and
            result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            all(result['other_log_prefix_preserved'].values()) and
            proof['state']=='independently-verified-six-original-files-misc-and-empty-journal' and
            proof['root_header_sha256']==HEADER and len(proof['files'])==6 and
            proof['all_original_slot_bits_allocated'] and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'] and not (proof['device_writes'] or proof['device_boots']),
            '0362 independent restore proof differs')
    current = load(BASE/'current-root-capture/result.json')
    baseline = load(REFERENCE)
    require(current['files']==baseline['files'] and current['directories']==baseline['directories'] and
            current['root_header_sha256']==baseline['root_header_sha256']==HEADER and
            current['combined_log_bytes']==baseline['combined_log_bytes']==155_865_339 and not current['device_writes'],
            '0363 live baseline differs from restored 0362')
    return current


def expected_plan():
    current = check_baseline()
    pacing.check_restored(REF361)
    prior_path = P362/'trial-plan.json'
    plan = load(prior_path)
    native = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame363-image.json')
    edr = load(BASE/'edr-native/result.json')
    delta_path = BASE/'slot-delta/install-plan.json'
    delta = load(delta_path)
    original = signed_pair(P361)[1]['variants']['reference']
    require(native['state']=='0363-native-ARM64-linked' and native['inputs_unchanged'] and
            native['baseline_reproduced_except_uuid'] and native['kernel_sha256']==sha(native['kernel'])==KERNEL and
            native['input_pins'][str(PATCH)]==sha(PATCH) and len(native['object_replacements'])==1 and
            all(Path(name).name=='gauguin_ui_trace_board.o'
                for key,value in native['object_replacements'].items() for name in (key,value)) and
            image['kernel_sha256']==KERNEL and native['identity']==image['build_identity']==edr['kernel_identity'] and
            image['kernel_banner']==native['kernel_banner'] and
            sha(image['image'])==image['image_sha256']==IMAGE and image['image_bytes']==22_216_704 and
            image['command']==plan['boot_command'] and len(image['command'])==607,
            '0363 changes outside the isolated frame-init guard and version')
    require(delta['trial']=='0363' and delta['core_sha256']==plan['owned_core_sha256']==original['sha256']==CONTROL and
            delta['rows']['core']['new_logical']==original['bytes']==CORE_BYTES and
            delta['rows']['eagl']['new_file_sha256']==plan['SB_sha256'] and
            delta['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and
            edr['identity_only_retarget'] and edr['scope_checks']==2145 and
            sha(BASE/'metadata-snapshot/misc-original.bin')==plan['misc_before_sha256'] and plan['sustained_motion']==MOTION,
            '0363 installed Core, frontend, identity-only helper, motion or misc differs')
    sizes = {filename:current['files'][filename]['bytes'] for filename in sorted(LOG_PATHS)}
    measured = sum(sizes.values())
    growth = measured-plan['log_capture']['measured_baseline_bytes']
    console = (REF362/'kernel.log').stat().st_size
    require(growth==4_010_998 and measured==155_865_339 and console==2_653_158 and
            console+CONSOLE_RESERVE<4*1024**2, '0363 measured console or log budget differs')
    plan.update(state='prepared-frame363-one-shot',trial='0363',root_header_sha256=HEADER,
        install_plan_sha256=sha(delta_path),parent_trial_plan_sha256=sha(prior_path),
        image=image['image'],image_sha256=IMAGE,image_bytes=image['image_bytes'],
        kernel_identity=native['identity'],kernel_banner=native['kernel_banner'],
        EDR_helper_sha256=edr['binary_sha256'],
        optimization='Arm the existing F344 capture for both scripted wake modes.',
        performance_comparison='Use 0361 for the original 13 SDK-matched strokes. Score the appended drag separately.',
        log_capture=dict(plan['log_capture'],max_combined_log_bytes=measured+LOG_SUFFIX,
            measured_baseline_bytes=measured,sizes=sizes,previous_verified_suffix_bytes=growth,
            reference_kernel_log_bytes=console,reserved_frame_console_bytes=CONSOLE_RESERVE))
    return plan
