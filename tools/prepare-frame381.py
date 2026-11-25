#!/usr/bin/env python3
"""Freeze the 0381 read-only qualification of the inherited display DMA route."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame380')
shared = parent.shared
save = shared.stage.save
TRIAL = '0381'
P380 = MAIN/'research/tmp/gauguin-frame-380-worktree-20261122/research/tmp/frame-380'
REFERENCE = P380/'execution'
BASE = WORK/'research/tmp/frame-381'
DOC = WORK/'docs/gauguin-frame-381-dma-qualification-20261122.md'
PATCH = WORK/'xnu/patches/0292-gauguin-read-inherited-display-dma.patch'
READONLY = BASE/'preflight.json'
HOST = BASE/'host-verification.json'
HEADER = '33a0d8b0f1ffe9224f815370fc38b74b5ef4999c35991a1ec4ecd343a15fe5f6'
LOG_BYTES = 224_473_353
BATCH = 360_000_000
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0380')],
         'allow_0381_one_60Hz_read_only_display_DMA_qualification_boot')
SUCCESS = '0381-display-DMA-qualified-root-restored'


def check_budget():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']==BATCH and
            admission['current_accounted_bytes']+BATCH<=admission['limit_bytes'],
            'whole 0381 batch was not admitted')


def check_reference():
    pins = {
        'result.json': 'f7c7225ff9f2f5dac1cc2b2f8ebc35c9bbb0ffe88658b2b47971c41c386e399d',
        'independent-restore.json': 'f9a6139a14b1247520307024bfe323e6dc1c3318c72e5febda770fa0f108ab47',
        'scanout-comparison-0375-0379-0380.json': '8aad9cd12ca51df8b5c01a2022bf1526694d9a71e49908adac3e7d495ce426fc',
    }
    require(all(sha(REFERENCE/name)==digest for name,digest in pins.items()), '0380 evidence differs')
    original = load(REFERENCE/'restored-capture/result.json')
    proof = load(REFERENCE/'independent-restore.json')
    result = load(REFERENCE/'result.json')
    comparison = load(REFERENCE/'scanout-comparison-0375-0379-0380.json')
    require(result['restored'] and result['independent_restore_verified'] and
            result['static_root_comparison_passed'] and all(result['other_log_prefix_preserved'].values()) and
            proof['root_header_sha256']==original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES and comparison['crc_register']['qualified'] and
            comparison['crc_calibration']['qualified'] and comparison['ring']['qualified'] and
            comparison['ca_phase']['qualified'], '0380 recovery or phase evidence differs')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
            len(current['files'])==31 and not current['device_writes'], '0381 TWRP baseline differs')
    return current


def build():
    check_budget()
    donor = P380/'native-kernel/build-manifest.json'
    import_module('build-frame347').link_scanout(donor,BASE/'native-kernel',
        parent_trial='0380',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_units=(('gauguin_ui_trace_board',donor,'compile-gauguin_ui_trace_board'),))


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(native),base=BASE,trial=TRIAL,
                           frame_capture_mode=9,scripted_motion=True)
    before = pack.parts(Path(load(P380/'trial-plan.json')['image']).read_bytes())
    after = pack.parts(Path(image['image']).read_bytes())
    require(before[1]==after[1] and before[3]==after[3] and
            image['command']==load(P380/'trial-plan.json')['boot_command'],
            'shim, device tree or 0380 boot arguments differ')
    image['kernel_manifest'] = str(native)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P380/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P380/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame381-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P380/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P380/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P380,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P380/'trial-plan.json'
    previous = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame381-image.json',
                                                    'edr-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    installed = load(slots)
    require(native['state']=='0381-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).stem for p in (*native['object_replacements'],*native['object_replacements'].values())}
            =={'gauguin_ui_trace_board'} and sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'], '0381 native change differs')
    require(image['command']==previous['boot_command'] and sha(image['image'])==image['image_sha256'] and
            image['image_bytes']==Path(image['image']).stat().st_size and installed['trial']==TRIAL and
            installed['changed_ranges']==12 and installed['core_sha256']==previous['owned_core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==previous['SB_sha256'] and
            installed['rows']['c4']['new_file_sha256']==previous['C4_sha256'] and
            installed['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
            sha(BASE/'metadata-snapshot/misc-original.bin')==previous['misc_before_sha256'],
            '0381 image, EDR or six-slot scope differs')
    sizes = {name:current['files'][name]['bytes'] for name in previous['log_capture']['sizes']}
    reference_bytes = (REFERENCE/'kernel.log').stat().st_size
    frame = previous['frame_capture']
    require(sum(sizes.values())==LOG_BYTES and reference_bytes+8192<4_194_304 and
            frame['target_refresh_hz']==60 and frame['modesets']==0 and frame['crc_preimage_reads']==2 and
            frame['crc_required_preimage']==0x01000000 and frame['maximum_volatile_crc_register_writes']==4 and
            frame['crc_cleanup_readback_equals_recorded_preimage'] and previous['scripted_strokes']==13 and
            previous['sustained_motion']['normal_reports']==162, '0381 CRC, input or capture scope differs')
    return dict(previous,state='prepared-frame381-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(slots),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        log_capture=dict(previous['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
            max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=reference_bytes,
            reserved_frame_console_bytes=4_194_304-reference_bytes,
            previous_verified_suffix_bytes=LOG_BYTES-previous['log_capture']['measured_baseline_bytes']),
        display_dma=dict(preflight_sha256=sha(READONLY),host_verification_sha256=sha(HOST),
            maximum_attempts=8,min_stable_samples=3,
            max_bracket_ns=1_000_000,groups=71,nonsecure_streams=[0x800,0x802],
            additional_raw_mmio_reads_max=1248,existing_position_probes_max=16,
            register_pages_max=4,register_mapping='read-only',additional_mmio_writes=0,
            inspected_page_tables=False,prospective_buffer_access_bytes=0,flips=0),
        optimization='Qualify the inherited display DMA route before enabling hardware page flips.',
        performance_comparison='Measure the unchanged 0380 path and treat it as a control, separately from page flipping.')


def storage(plan):
    previous = load(P380/'storage-bound-380.json')
    parts = dict(previous['components'])
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0381 runtime exceeds reservation')
    return dict(previous,state='bounded0381-DMA-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    previous = load(P380/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','log_capture',
        'optimization','performance_comparison','display_dma'}
    require({k for k in plan.keys()|previous.keys() if plan.get(k)!=previous.get(k)}<=allowed,
            '0381 changed an effect outside its scope')
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P380,BASE))
    require({n for n in new['rows'] if new['rows'][n]['new_file_sha256']!=
             old['rows'][n]['new_file_sha256']}=={'admission'}, '0381 userspace changed beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    preflight = load(READONLY)
    host = load(HOST)
    require(host['patch_sha256']==sha(PATCH) and host['route_decoder_cases']==10 and
            host['state_space']['states']==242 and host['lifetime']['timeout_pins_both'] and
            host['lifetime']['gpu_cache_and_read_lease'] and not host['device_commands'],
            'offline ordering or replay differs')
    require(rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            rollback['all_restore_partial_write_points']==17 and len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            preflight['scanout_route']['pipe']=='VIG0' and preflight['dt'][0]['iommu_nonsecure_streams']==[0x800,0x802] and
            not (preflight['dt'][0]['smmu_has_explicit_clocks'] or preflight['dt'][0]['smmu_has_explicit_power_domain'] or
                 preflight['flip_allowed'] or preflight['device_writes'] or preflight['boot_attempts']),
            '0381 route or restore proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P380,HEADER,plan)


def pins():
    names = ('native-kernel/build-manifest.json','frame381-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json')
    extra = [READONLY, HOST, REFERENCE/'scanout-comparison-0375-0379-0380.json',
             MAIN/'research/tmp/0381-storage-retirement/verified-retirement-manifest.json']
    return shared.pins(base=BASE,prior=P380,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,
                       extra=extra,artifacts=[BASE/name for name in names])


def freeze():
    return shared.freeze(base=BASE,prior=P380,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
