"""Freeze exact 0366 candidate inputs and the narrow lock-only retry scope."""

from frame365_scope import CONTROL, CORE_BYTES, LOG_PATHS, LOG_SUFFIX, MAIN, METADATA_CAP, MOTION
from frame365_scope import RESERVE, SAVED_SLOTS, WORK, load, pacing, require, sha
from frame365_scope import FLAGS as PREVIOUS_FLAGS

TRIAL = '0366'
BASE = WORK/'research/tmp/frame-366'
P365 = MAIN/'research/tmp/gauguin-ca-timing-worktree-20261121/research/tmp/frame-365'
REF365 = P365/'execution'
P363 = MAIN/'research/tmp/gauguin-frame-gate-worktree-20261121/research/tmp/frame-gate-363'
P360 = MAIN/'research/tmp/gauguin-read-guard-worktree-20261120/research/tmp/frame-360'
REFERENCE = REF365/'restored-capture/result.json'
DOC = WORK/'docs/gauguin-frame-366-trial-20261121.md'
PATCH = WORK/'xnu/patches/0277-gauguin-probe-only-issued-writers.patch'
MODEL = MAIN/'research/tmp/gauguin-0366-probe-model/host-result.json'
HEADER = 'fe36680e563f6afae7115f9753dfc6138eaa5d62b3dcf728f670722069133dd2'
RESULT = '092b790f0bcdf721396b2c0dbdadd2d1512d4d4f1fac9f37822557b03bbf1357'
PROOF = '45c1d326eda90fe4173d45ff7aca92d4257a99ffc5c1fd2d863ba3f9feaeb69a'
BATCH = 335_000_000
REPORT_BYTES = 2_000_000
FLAGS = tuple(flag for flag in PREVIOUS_FLAGS if not flag.startswith('allow_0365')) + (
    'allow_0366_0365_userspace_and_one_60Hz_temporary_boot',
    'allow_0366_same_scripts_CRC_and_exact_issued_lock_retry')
SUCCESS = '0366-issued-fence-scanout-measured-root-restored'
CHANGES = {'state','trial','image','image_sha256','image_bytes','kernel_identity','kernel_banner',
    'root_header_sha256','install_plan_sha256','parent_trial_plan_sha256','new_kernel_builds','new_boot_images',
    'EDR_helper_sha256','optimization','performance_comparison','fence_probe','log_capture'}


def check_budget():
    r = load(BASE/'build-storage-admission.json')
    require(r['admitted'] and r['planned_batch_bytes']==BATCH and
            r['current_accounted_bytes']+BATCH<=r['limit_bytes'], '0366 whole batch not admitted')


def check_archive():
    require(sha(REF365/'result.json')==RESULT and sha(REF365/'independent-restore.json')==PROOF,
            '0365 reference or independent proof differs')
    return pacing.check_restored(REF365)


def check_baseline():
    check_archive()
    current,previous = load(BASE/'current-root-capture/result.json'),load(REFERENCE)
    require(current['files']==previous['files'] and current['directories']==previous['directories'] and
            current['root_header_sha256']==previous['root_header_sha256']==HEADER and
            len(current['files'])==31 and current['combined_log_bytes']==previous['combined_log_bytes']==167_928_270 and
            not current['device_writes'], '0366 TWRP baseline differs from 0365 readback')
    return current


def expected_plan():
    current = check_baseline()
    prior = P365/'trial-plan.json'
    plan = load(prior)
    build = load(BASE/'native-kernel/build-manifest.json')
    image = load(BASE/'frame366-image.json')
    edr = load(BASE/'edr-native/result.json')
    delta_path = BASE/'slot-delta/install-plan.json'
    delta = load(delta_path)
    require(load(MODEL)['patch_sha256']==sha(PATCH)==build['input_pins'][str(PATCH)] and
        build['state']=='0366-native-ARM64-linked' and build['baseline_reproduced_except_uuid'] and
        build['inputs_unchanged'] and sha(build['kernel'])==build['kernel_sha256']==image['kernel_sha256'] and
        {path.rsplit('/',1)[-1] for path in build['object_replacements']}
        =={path.rsplit('/',1)[-1] for path in build['object_replacements'].values()}
        =={'GauguinGPU.o','SweetFramebuffer.o'} and build['identity']==image['build_identity']==edr['kernel_identity'],
        '0366 kernel differs outside the reviewed probe units')
    require(image['command']==plan['boot_command'] and image['image_sha256']==sha(image['image']) and
        image['image_bytes']==(BASE/'frame366-image.img').stat().st_size and
        image['kernel_banner']==build['kernel_banner'] and plan['sustained_motion']==MOTION and
        delta['trial']==TRIAL and delta['core_sha256']==plan['owned_core_sha256']==CONTROL and
        delta['rows']['core']['new_logical']==CORE_BYTES and delta['rows']['eagl']['new_file_sha256']==plan['SB_sha256'] and
        delta['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
        sha(BASE/'metadata-snapshot/misc-original.bin')==plan['misc_before_sha256'],
        '0366 image, Core, CA observer or exact scope differs')
    measured = current['combined_log_bytes']
    previous_growth = measured-plan['log_capture']['measured_baseline_bytes']
    raw_ring = load(REF365/'kernel-IO-analysis.json')['ring']['total_bytes']
    require(previous_growth==4_041_332 and raw_ring==3_721_801 and raw_ring+1024*160<4_194_304,
            '0366 log reserve differs')
    sizes={name:current['files'][name]['bytes'] for name in sorted(LOG_PATHS)}
    plan.update(state='prepared-frame366-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(delta_path),new_kernel_builds=1,new_boot_images=1,
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=build['identity'],kernel_banner=build['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        optimization='Offer readiness probes only after native issue and permit one same-writer lock-only retry.',
        performance_comparison='Compare 0365 then 0366 by ordinary gesture and independently scored slow drag.',
        fence_probe=dict(plan['fence_probe'],maximum_additional_requests_per_scan=2,
            maximum_readiness_queries_per_scan=1,maximum_lock_only_retries_per_scan=1,
            native_ticket_publication_required=True,lock_retry_wire_kind=61),
        log_capture=dict(plan['log_capture'],max_combined_log_bytes=measured+LOG_SUFFIX,
            measured_baseline_bytes=measured,sizes=sizes,previous_verified_suffix_bytes=previous_growth,
            reference_kernel_log_bytes=raw_ring,reserved_frame_console_bytes=4_194_304-raw_ring))
    old = load(prior)
    require({k for k in plan.keys()|old.keys() if plan.get(k)!=old.get(k)}<=CHANGES and
            plan['fence_probe']['maximum_additional_requests_per_capture']==1024,
            '0366 differs beyond the scoped lock retry')
    return plan
