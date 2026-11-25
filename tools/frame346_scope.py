"""Frozen device scope for the 0346 scanout and program storage trial."""
from core342_scope import APPROVAL_FLAGS
from core343_scope import MAIN, WORK, load, require, sha
from frame345_scope import ANALYSIS, LOG_PATHS, POST_LOG_BYTES, RESERVE

BASE = WORK/'research/tmp/frame-346'
P345 = MAIN/'research/tmp/gauguin-frame-345-worktree-20261119/research/tmp/frame-345'
HEADER = '52c6e8e5a00d15eabd6cf301d1c37f10c37b2f605184f34ec14d119b468a2972'
DOC = WORK/'docs/gauguin-frame-346-trial-20261119.md'
SUCCESS = '0346-collection-and-hardware-analysis-complete-root-restored'
FLAGS = APPROVAL_FLAGS + ('allow_0346_program_slabs_and_submit_guards','allow_0346_volatile_intf1_MISR')


def expected_plan():
    parent=P345/'trial-plan.json'
    plan=load(parent)
    proof=load(P345/'execution/independent-restore.json')
    current=load(BASE/'current-root-capture/result.json')
    previous=load(P345/'execution/restored-capture/result.json')
    require(proof['root_header_sha256']==current['root_header_sha256']==HEADER and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'] and current['files']==previous['files'] and
            current['directories']==previous['directories'] and not current['device_writes'],
            '0345 restored baseline or fresh capture differs')
    image=load(BASE/'frame346-image.json')
    kernel=load(BASE/'native-kernel/build-manifest.json')
    core=load(BASE/'core-native/result.json')
    edr=load(BASE/'edr-native/result.json')
    host=load(BASE/'core-host-reviewed/result.json')
    require(image['image_sha256']==sha(image['image']) and image['command']==plan['boot_command'] and
            image['command'].split().count('sweetfb_hz=60')==1 and
            image['build_identity']==kernel['identity']==edr['kernel_identity'] and
            image['kernel_sha256']==kernel['kernel_sha256']==sha(kernel['kernel']) and
            edr['binary_sha256']==sha(edr['binary']) and edr['scope_checks']==2145,
            '0346 image, 60 Hz configuration or EDR differs')
    require(core['binary_sha256']==sha(core['binary'])==host['native_sha256'] and
            core['matching_imports_exports_loads_and_platform'] and core['compiled_tus']==12 and
            core['bytes']==7_992_224 and host['program_slabs_passed'] and host['replay_iterations']==512 and
            host['ownership_cases']==23 and host['render_cases']==8,
            '0346 Core or program lifetime checks differ')
    plan.update(state='prepared-frame346-one-shot',trial='0346',image=image['image'],image_sha256=image['image_sha256'],
                image_bytes=image['image_bytes'],kernel_identity=image['build_identity'],kernel_banner=image['kernel_banner'],
                EDR_helper_sha256=edr['binary_sha256'],owned_core_sha256=core['binary_sha256'],owned_core_logical_bytes=core['bytes'],
                root_header_sha256=HEADER,install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),
                misc_before_sha256=sha(BASE/'metadata-snapshot/misc-original.bin'),parent_trial_plan_sha256=sha(parent),
                all_core_TUs_recompiled=True,program_storage='immutable-program-slabs-346',
                optimization='Append-only program BO pages, shared shader words and one health proof per adjacent ring/MMIO boundary',
                performance_comparison='0345 matched stroke phase, first 12 comparable release windows, actual new BO and warm no-allocation submits')
    plan['frame_capture'].update(gcc_display_ahb_hwcg_with_software_vote=True, downstream_clock_checks_unchanged=True)
    plan['program_new_BO_CPU_phase_trace'].update(newBO_calls_must_equal_program_resident_misses=False,
        resident_misses_equal_native_new_BO_calls_plus_program_slab_reuses=True,slab_reuse_field='program_slab_reuses')
    return plan
