"""0344 scope shared by offline preparation and the one-shot executor."""

from pathlib import Path

from core342_scope import APPROVAL_FLAGS as CORE_FLAGS, MAIN, WORK, load, sha
from core343_scope import require


BASE = WORK/'research/tmp/frame-344'
P343 = MAIN/'research/tmp/gauguin-runtime-issue-worktree-20261119/research/tmp/runtime-issue-343'
MANUAL = MAIN/'research/tmp/gauguin-manual-touch-worktree-20261119/research/tmp/manual-touch-343'
HEADER = 'ff7404f7af73ab90cd8d86dbfa4eeaaa806c1b051189ca9d43b8ef79173a38f0'
RESERVE = 475_000_000
FLAGS = CORE_FLAGS + ('allow_0344_core_encoding_and_frame_capture', 'allow_0344_volatile_intf1_MISR')
SUCCESS = '0344-collection-and-frame-analysis-complete-root-restored'
DOC = WORK/'docs/gauguin-frame-344-trial-20261119.md'
LOG_PATHS = ('/private/var/tmp/gauguin-gles180.log', '/private/var/tmp/gauguin-gles180.stderr.log',
             '/private/var/log/backboardd.log', '/private/var/log/springboard.log')
POST_LOG_BYTES = 128 * 1048576


def expected_plan():
    parent_path = P343/'trial-plan.json'
    plan = load(parent_path)
    image = load(BASE/'frame344-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    host = load(BASE/'core-host-reviewed/result.json')
    proof = load(MANUAL/'execution/independent-restore.json')
    require(proof['root_header_sha256'] == HEADER and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'], 'manual 0343 baseline not independently restored')
    require(image['image_sha256'] == sha(image['image']) and
            image['command'] == plan['boot_command'].replace('sweetfb_stats=1','sweetfb_stats=2') and
            edr['kernel_identity'] == image['build_identity'] and edr['binary_sha256'] == sha(edr['binary']),
            'image or helper outside the 0344 scope')
    require(core['binary_sha256'] == sha(core['binary']) == host['native_sha256'] and
            core['matching_imports_exports_loads_and_platform'] and host['candidate_single_snapshot'] and
            host['replay_iterations'] == 512, 'Core candidate is not host qualified')
    plan.pop('optical_FPS')
    plan.update(state='prepared-frame344-one-shot', trial='0344',
                image=image['image'], image_sha256=image['image_sha256'], image_bytes=image['image_bytes'],
                kernel_identity=image['build_identity'], kernel_banner=image['kernel_banner'],
                boot_command=image['command'], EDR_helper_sha256=edr['binary_sha256'],
                owned_core_sha256=core['binary_sha256'], unchanged_0342_Core_and_frontend=False,
                root_header_sha256=HEADER, install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
                misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
                parent_trial_plan_sha256=sha(parent_path), storage_reserve_bytes=RESERVE,
                hash_only_static_files=True, additional_threads=1,
                optimization='One WorkMeter snapshot; reuse emitted PM4 words and bounded vertex/output packing',
                frame_capture=dict(wire='F344', starts_at='observed-display-on settle',
                    window_seconds=45, records=16384, independent_of_UI254=True,
                    route='Gauguin SM7225 Lagoon DPU 6.4 INTF1 J17 video', target_refresh_hz=60,
                    hardware_poll_interval_us=1200, maximum_poll_calls=40960,
                    opt_in='sweetfb_stats=2', modesets=0, gpu_operation_changes=0,
                    volatile_crc_register_address='0x0ae6b980', maximum_volatile_crc_register_writes=4,
                    zero_control_preimage_required=True, restore_control_if_powered=True,
                    publish_rate_only_for_complete_adjacent_hardware_frames=True,
                    optical_FPS_qualified=False))
    return plan
