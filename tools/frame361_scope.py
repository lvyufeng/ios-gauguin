"""Bind the 0361 Core candidate to the restored root and exact 0360 boot."""

from frame358_scope import APPROVAL_FLAGS as BASE_FLAGS
from frame360_scope import LOG_PATHS, LOG_SUFFIX, MAIN, REF358, RESERVE, WORK, load, pacing, require, sha

BASE = WORK/'research/tmp/frame-361'
P360 = MAIN/'research/tmp/gauguin-read-guard-worktree-20261120/research/tmp/frame-360'
REF360 = P360/'execution'
SAVED_SLOTS = (MAIN/'research/tmp/gauguin-first-frame-worktree-20261120/research/tmp/frame-359/slot-capture')
DOC = WORK/'docs/gauguin-frame-361-trial-20261120.md'
PATCH = WORK/'graphics/gauguin-program-io/0361-warm-draw-setup.patch'
RESULT_360 = 'e5dbbba3fa55d1ce89522cea75a4bf884ac27bef139f764825e6680a0c6cb0f1'
PROOF_360 = 'e09133e26ff43536b6dcd4cb4fca7acd0d6b852fe47f844069489ca2580eafe5'
HEADER = '1bc0cb6c9366779a8101897c6a8ef1337d781eefa9c9a56a608649317da1de8e'
IMAGE = 'da92e191708c3e3a063d8c9fe1911b4a27d1ab58da78594fbd6e1a7fa032bbc5'
CORE = '4ea3f0c78edd18c6ba3d2dbf6c96bc7c02f06bfe0badb2f52e167dfa2444fa71'
CONTROL = '08400c4b1da6915a58102529f87defa12be95f99309ad1847be20b323ec70496'
CORE_BYTES = 7_975_728
BUILD_BATCH_BYTES = 240_000_000
FLAGS = BASE_FLAGS + ('allow_0361_exact_0360_image_and_read_reservation',
    'allow_0361_optimized_SDK27_2_Core', 'allow_0361_60Hz_CRC_pairs_calibration_and_preblank_probe')
SUCCESS = '0361-Core-and-CRC-measured-root-restored'


def check_baseline():
    require(sha(REF360/'result.json')==RESULT_360 and sha(REF360/'independent-restore.json')==PROOF_360,
            '0360 restored reference differs')
    pacing.check_restored(REF360)
    archived = load(REF360/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(current['files']==archived['files'] and current['directories']==archived['directories'] and
            current['root_header_sha256']==archived['root_header_sha256']==HEADER and
            current['combined_log_bytes']==archived['combined_log_bytes']==147_369_420 and
            not current['device_writes'],'TWRP read-only baseline differs from restored 0360')
    return current


def signed_pair(base=BASE):
    path = base/'core-signed-current-sdk/verification.json'
    signed = load(path)
    variants = signed['variants']
    require(signed['state']=='0361-current-SDK-signed-pair-passed-static-verification' and
            signed['code_signatures_strict'] and not signed['device_commands'] and
            variants['candidate']['sha256']==CORE and variants['candidate']['bytes']==CORE_BYTES and
            variants['reference']['sha256']==CONTROL and all(row['sdk']=='27.2' and row['minos']=='16.0' and
            row['platform']=='IOS' and sha(row['binary'])==row['sha256']
            for row in (variants['candidate'], variants['reference'])), 'signed SDK-matched Core pair differs')
    return path,signed


def expected_plan():
    current = check_baseline()
    _,signed = signed_pair()
    prior = P360/'trial-plan.json'
    plan = load(prior)
    install = BASE/'slot-delta/install-plan.json'
    staged = load(install)
    require(plan['image_sha256']==sha(plan['image'])==IMAGE and plan['trial']=='0360' and
            sha(BASE/'metadata-snapshot/misc-original.bin')==plan['misc_before_sha256'] and
            staged['trial']=='0361' and staged['core_sha256']==CORE and
            staged['rows']['core']['new_logical']==CORE_BYTES and
            staged['admission_sha256']==plan['EDR_helper_sha256'] and
            staged['rows']['eagl']['new_file_sha256']==plan['SB_sha256'],
            '0361 changed the exact boot image or non-Core assets')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    measured = sum(sizes.values())
    growth = measured-load(P360/'trial-plan.json')['log_capture']['measured_baseline_bytes']
    console = (REF360/'kernel.log').stat().st_size
    require(growth==4_445_717 and measured==current['combined_log_bytes'] and
            console+plan['log_capture']['reserved_frame_console_bytes']<4*1024**2,
            '0361 measured log budget differs')
    plan.update(state='prepared-frame361-one-shot',trial='0361',root_header_sha256=HEADER,
        install_plan_sha256=sha(install),parent_trial_plan_sha256=sha(prior),
        owned_core_sha256=CORE,owned_core_logical_bytes=CORE_BYTES,unchanged_0342_Core_and_frontend=False,
        new_kernel_builds=0,new_boot_images=0,
        optimization='Defer draw validation diagnostics and copy fragment metadata solely for output masking.',
        performance_comparison='0361 activation and measurement relative to 0360. SDK27.2 control has no device capture yet.',
        matched_Core_control=dict(sdk=signed['variants']['reference']['sdk'],sha256=CONTROL,
            bytes=signed['variants']['reference']['bytes'],installed_this_trial=False),
        log_capture=dict(plan['log_capture'],max_combined_log_bytes=measured+LOG_SUFFIX,
            measured_baseline_bytes=measured,sizes=sizes,previous_verified_suffix_bytes=growth,
            reference_kernel_log_bytes=console))
    return plan
