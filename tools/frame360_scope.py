"""Pin 0360 to the restored 0359 root and the renderer measured in 0358."""

from importlib import import_module

from frame358_scope import FLAGS as PROBE_FLAGS
from frame359_scope import LOG_PATHS, MAIN, P358, REF358, WORK, load, require, sha

pacing = import_module('audit-frame-pacing')
REF359 = pacing.REF359
P359 = REF359.parent
BASE = WORK/'research/tmp/frame-360'
DOC = WORK/'docs/gauguin-frame-360-trial-20261120.md'
PATCH = WORK/'xnu/patches/0274-gauguin-pin-completed-surface-read.patch'
HEADER = 'bd45bd579b42b8402a49f4bf650f53c746408c48885a7bb66bc89ab45b62a7a4'
KERNEL = 'b528269b7479e5e374b803d47c3bfec384405273a58b560a0df95a4a947be2b2'
LOG_SUFFIX = 8_000_000
PREPARATION_BYTES = 72_000_000
RESERVE = 192_000_000
METADATA_BYTES = 14_000_000
FLAGS = PROBE_FLAGS + ('allow_0360_exact_0358_userspace_and_0346_core',
    'allow_0360_completed_owned_surface_read_reservation')
SUCCESS = '0360-read-reservation-and-output-measured-root-restored'
POLICY = dict(completed_exact_writer_version=True,owned_kernel_buffer_only=True,copy_mode=9,
    checks_current_scan_after_read_guard=True,retains_surface_through_copy=True,
    same_surface_GPU_admission_waits_for_release=True,native_submission_order_preserved=True,
    additional_GPU_submissions=0,additional_threads=0,additional_frame_records=0,lock_receipt_flag=3)


def check_baseline():
    pacing.references()
    pacing.check_restored(REF359)
    restored = load(REF359/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    proof = load(REF359/'independent-restore.json')
    require(current['files']==restored['files'] and current['directories']==restored['directories'] and
            current['root_header_sha256']==restored['root_header_sha256']==proof['root_header_sha256']==HEADER and
            current['combined_log_bytes']==restored['combined_log_bytes']==142_923_703 and not current['device_writes'],
            'fresh TWRP root or logs differ from the independently restored 0359 baseline')
    return current


def expected_plan():
    current = check_baseline()
    previous = P358/'trial-plan.json'
    plan = load(previous)
    image = load(BASE/'frame360-image.json')
    edr = load(BASE/'edr-native/result.json')
    core = load(BASE/'core-native/result.json')
    signed_core = load(P358/'core-native/result.json')
    link = load(BASE/'native-kernel/build-manifest.json')
    installed = load(BASE/'slot-delta/install-plan.json')
    require(link['state']=='0360-native-ARM64-linked' and link['inputs_unchanged'] and
            link['input_pins'][str(PATCH)]==sha(PATCH) and link['kernel_sha256']==sha(link['kernel'])==KERNEL and
            image['kernel_sha256']==KERNEL and image['build_identity']==link['identity']==edr['kernel_identity'] and
            image['kernel_banner']==link['kernel_banner'] and image['image_sha256']==sha(image['image']) and
            image['command']==plan['boot_command'] and len(image['command'].encode())==607 and
            edr['identity_only_retarget'] and edr['scope_checks']==2145 and
            edr['binary_sha256']==sha(edr['binary'])==installed['admission_sha256'] and
            core['signature_verified'] and core['binary']==signed_core['binary'] and
            core['binary_sha256']==sha(core['binary'])==plan['owned_core_sha256']==installed['core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==plan['SB_sha256'], '0360 kernel or userspace identity differs')
    sizes = {path:current['files'][path]['bytes'] for path in sorted(LOG_PATHS)}
    measured = sum(sizes.values())
    last_growth = measured-load(REF358/'restored-capture/result.json')['combined_log_bytes']
    old_console = (REF358/'kernel.log').stat().st_size
    # The wire change reuses the existing read record and never emits an extra row.
    console_reserve = plan['log_capture']['reserved_frame_console_bytes']
    require(measured==142_923_703 and last_growth==4_540_235 and
            old_console+console_reserve<4*1024**2 and last_growth+console_reserve<LOG_SUFFIX,
            'measured log budget or kernel console ceiling differs')
    plan.update(state='prepared-frame360-one-shot',trial='0360',image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_banner=image['kernel_banner'],
        kernel_identity=link['identity'],EDR_helper_sha256=edr['binary_sha256'],root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),storage_reserve_bytes=RESERVE,
        misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),
        parent_trial_plan_sha256=sha(previous),read_reservation=POLICY,
        optimization='Pin completed display pixels by exact writer version for the guarded copy.',
        performance_comparison='0358 renderer and 13 scripted strokes by phase and hardware ordinal, with 0359 diagnostic reference.',
        log_capture=dict(plan['log_capture'],max_combined_log_bytes=measured+LOG_SUFFIX,
            measured_baseline_bytes=measured,maximum_suffix_bytes=LOG_SUFFIX,sizes=sizes,
            previous_verified_suffix_bytes=last_growth,reference_kernel_log_bytes=old_console))
    return plan
