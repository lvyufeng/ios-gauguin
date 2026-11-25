"""Bind a pass-through CA timing probe to the restored 0364 graphics baseline."""

from frame364_scope import IMAGE, CONTROL, CORE_BYTES, MAIN, WORK, LOG_PATHS, LOG_SUFFIX, METADATA_CAP
from frame364_scope import MOTION, PATCH, RESERVE, SAVED_SLOTS, load, pacing, require, sha
from frame358_scope import APPROVAL_FLAGS

TRIAL = '0365'
BASE = WORK/'research/tmp/frame-365'
P364 = MAIN/'research/tmp/gauguin-motion-identity-worktree-20261121/research/tmp/frame-364'
REF364 = P364/'execution'
REFERENCE = REF364/'restored-capture/result.json'
DOC = WORK/'docs/gauguin-frame-365-trial-20261121.md'
HEADER = 'd7f3657f9949bff23a0199ee597ab11ba3219f45837840dfe0f356b5ccd30ea9'
RESULT = '82a0eb507600e21e3f7b647e3c360b2bc3248cb7cb6994742b6c097e2efebc44'
PROOF = 'f0ac143ac7d697701e1340cdaa752ebde9323a103e9d420f2b874d59d104f774'
BATCH = 275_000_000
REPORT_BYTES = 2_000_000
CA_ROWS = 8192
FLAGS = APPROVAL_FLAGS + ('allow_0365_0364_kernel_and_Core',
    'allow_0365_same_13_strokes_and_fixed_slow_drag',
    'allow_0365_60Hz_CRC_pairs_calibration_and_preblank_probe',
    'allow_0365_passthrough_SpringBoard_CA_observation')
SUCCESS = '0365-CA-handoff-timing-and-output-measured-root-restored'
CHANGES = {'state','trial','root_header_sha256','install_plan_sha256','parent_trial_plan_sha256',
    'SB_sha256','unchanged_337_SB','optimization','performance_comparison','log_capture','CA_observation'}


def check_budget():
    budget = load(BASE/'build-storage-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==BATCH and
            budget['current_accounted_bytes']+BATCH<=budget['limit_bytes'], '0365 batch admission is missing')


def check_archive():
    require(sha(REF364/'result.json')==RESULT and sha(REF364/'independent-restore.json')==PROOF,
            '0364 independently restored reference differs')
    return pacing.check_restored(REF364)


def check_baseline():
    check_archive()
    current,previous = load(BASE/'current-root-capture/result.json'),load(REFERENCE)
    require(current['files']==previous['files'] and current['directories']==previous['directories'] and
            current['root_header_sha256']==previous['root_header_sha256']==HEADER and
            current['combined_log_bytes']==previous['combined_log_bytes']==163_886_938 and
            len(current['files'])==31 and not current['device_writes'], '0365 TWRP preflight differs')
    return current


def expected_plan():
    current = check_baseline()
    prior = P364/'trial-plan.json'
    plan = load(prior)
    staged_path = BASE/'slot-delta/install-plan.json'
    staged = load(staged_path)
    sb = load(BASE/'sb-native/result.json')
    require(plan['image_sha256']==sha(plan['image'])==IMAGE and plan['image_bytes']==22_216_704 and
            plan['owned_core_sha256']==staged['core_sha256']==CONTROL and
            staged['rows']['core']['new_logical']==CORE_BYTES and staged['trial']==TRIAL and
            staged['admission_sha256']==plan['EDR_helper_sha256'] and plan['sustained_motion']==MOTION and
            sha(BASE/'metadata-snapshot/misc-original.bin')==plan['misc_before_sha256'],
            '0365 boot, Core, motion or original misc scope differs')
    require(sb['state']=='0365-passthrough-CA-timing-signed' and sb['signature_verified'] and
            sb['runtime_imports_qualified'] and not sb['device_commands'] and sb['stack_sampling_version']==315 and
            sb['binary_sha256']==sha(sb['binary'])==staged['SB_sha256']==staged['rows']['eagl']['new_file_sha256'] and
            sb['bytes']==staged['rows']['eagl']['new_logical'] and sb['bytes']<=94_208,
            '0365 CA timing binary or file slot differs')
    sizes = {name:current['files'][name]['bytes'] for name in sorted(LOG_PATHS)}
    measured = sum(sizes.values())
    growth = measured-plan['log_capture']['measured_baseline_bytes']
    console = load(REF364/'kernel-IO-analysis.json')['ring']['total_bytes']
    require(growth==4_018_517 and measured==current['combined_log_bytes'] and console==3_735_901 and
            growth+CA_ROWS*192<LOG_SUFFIX, '0365 measured log growth or CA trace reserve differs')
    plan.update(state='prepared-frame365-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(staged_path),
        SB_sha256=sb['binary_sha256'],unchanged_337_SB=False,
        CA_observation=dict(max_rows=CA_ROWS,start_us=220_000_000,end_us=270_000_000,
                            methods=['commit','flush'],CPU_stack_sampling_version=315,
                            records=['enter','return','caller_image','nesting_depth']),
        optimization='Break down the pre-Core producer gap with pass-through public CA timing.',
        performance_comparison='Hold 0364 render and scanout fixed and measure original input and fixed motion.',
        log_capture=dict(plan['log_capture'],max_combined_log_bytes=measured+LOG_SUFFIX,
            measured_baseline_bytes=measured,sizes=sizes,previous_verified_suffix_bytes=growth,
            reference_kernel_log_bytes=console,reserved_frame_console_bytes=4_194_304-console,
            maximum_additional_CA_log_bytes=CA_ROWS*192))
    previous = load(prior)
    require({k for k in plan.keys()|previous.keys() if plan.get(k)!=previous.get(k)}<=CHANGES,
            '0365 broadens the 60 Hz device effect scope')
    return plan
