"""Frozen inputs for a read-only 60 Hz DPU counter trial."""

from frame347_scope import LOG_PATHS, MAIN, P346, POST_LOG_BYTES, RESERVE, WORK
from frame347_scope import REFERENCE as REFERENCE346, REFERENCE_RESULT as RESULT346
from frame347_scope import load, require, sha
from core342_scope import APPROVAL_FLAGS


BASE = WORK/'research/tmp/frame-348'
P347 = MAIN/'research/tmp/gauguin-dpu-counters-worktree-20261119/research/tmp/frame-347'
REFERENCE347 = P347/'execution'
RESULT347 = 'e267d1a05efe9a183594fed7d345d2c67dcbef07c07c84f118969f814fae7714'
HEADER = '12f0fa123ea7bcb001381fe6f7a0021f684b06978120817813f76957668cb45c'
CORE_SHA = '4d18e979001868f949c74c93c298443195a4a4859fe742de6207b2a623143672'
DOC = WORK/'docs/gauguin-frame-348-trial-20261119.md'
FLAGS = APPROVAL_FLAGS + ('allow_0348_exact_0346_core','allow_0348_read_only_intf1_counters')
SUCCESS = '0348-qualified-read-only-vblank-root-restored'
REFERENCES = {'0346':(REFERENCE346,RESULT346), '0347':(REFERENCE347,RESULT347)}


def expected_plan():
    previous = P347/'trial-plan.json'
    plan = load(previous)
    proof = load(REFERENCE347/'independent-restore.json')
    last = load(REFERENCE347/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and
            proof['root_header_sha256']==current['root_header_sha256']==HEADER and
            current['files']==last['files'] and current['directories']==last['directories'] and
            not current['device_writes'], 'restored 0347 and fresh 0348 baselines differ')
    require(all(sha(path/'result.json')==digest for path,digest in REFERENCES.values()),
            '0346 or 0347 reference differs')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    baseline = sum(sizes.values())
    require(current['combined_log_bytes']==baseline and 0<baseline<POST_LOG_BYTES, 'measured log total differs')

    kernel = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame348-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    original = load(P346/'core-native/result.json')
    require(core['state']=='0348-exact-0346-core-signed' and
            core['binary']==original['binary'] and core['binary_sha256']==sha(core['binary'])==CORE_SHA and
            core['bytes']==original['bytes']==7_992_224 and core['signature_verified'],
            'Core differs from the exact signed 0346 baseline')
    args = plan['boot_command'].split()
    require(args.count('sweetfb_stats=3')==args.count('sweetfb_hz=60')==args.count('swp=3')==1 and
            image['command']==plan['boot_command'].replace('sweetfb_stats=3','sweetfb_stats=4') and
            len(image['command'].encode())==607, 'boot argument change exceeds the read-only capture mode')
    require(image['image_sha256']==sha(image['image']) and
            image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            kernel['baseline_reproduced_except_uuid'] and len(kernel['object_replacements'])==2 and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145,
            'read-only variant identity or EDR qualification differs')

    old_frame = plan['frame_capture']
    frame = {key:old_frame[key] for key in ('wire','starts_at','window_seconds','records','independent_of_UI254',
             'route','target_refresh_hz','hardware_poll_interval_us','maximum_poll_calls','modesets',
             'gpu_operation_changes','startup_gate_timeout_ms','gcc_display_ahb_hwcg_with_software_vote',
             'downstream_clock_checks_unchanged')}
    frame.update(opt_in='sweetfb_stats=4',interface_mapping='read-only',stable_control_reads=True,
                 controls_observed=[0,3],motion_wire='F348 MOTION',maximum_total_display_register_writes=0,
                 maximum_volatile_counter_register_writes=0,maximum_volatile_crc_register_writes=0,
                 crc_enabled=False,publish_new_content_fps=False,optical_FPS_qualified=False)
    plan.update(state='prepared-frame348-one-shot',trial='0348',image=image['image'],image_sha256=image['image_sha256'],
                image_bytes=image['image_bytes'],boot_command=image['command'],kernel_identity=kernel['identity'],
                kernel_banner=kernel['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
                owned_core_sha256=CORE_SHA,owned_core_logical_bytes=core['bytes'],all_core_TUs_recompiled=False,
                root_header_sha256=HEADER,install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
                misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),parent_trial_plan_sha256=sha(previous),
                optimization='Exact signed 0346 Core with read-only DPU counter motion and vblank capture',
                performance_comparison='0346 and 0347 same swipe ordinal and phase with boot-local frame and queue identities',
                log_capture=dict(max_combined_log_bytes=POST_LOG_BYTES,measured_baseline_bytes=baseline,
                                 maximum_suffix_bytes=POST_LOG_BYTES-baseline,sizes=sizes,metadata_preflight=True,
                                 verified_prefixes_required=True),frame_capture=frame)
    return plan
