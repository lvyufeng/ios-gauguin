#!/usr/bin/env python3
"""Freeze the bounded 0378 native CA timing and frame receipt trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame377')
shared = parent.shared
save = shared.stage.save
TRIAL = '0378'
BASE = WORK/'research/tmp/frame-378'
P375 = parent.P375
P377 = MAIN/'research/tmp/gauguin-frame-377-worktree-20261122/research/tmp/frame-377'
CA_RANGES = parent.CA_RANGES
REFERENCE = P377/'execution'
COMPARISON = REFERENCE/'scanout-comparison-0375-0377.json'
RETIREMENT = MAIN/'research/tmp/0378-storage-retirement/verified-retirement-manifest.json'
HOST = BASE/'host-verification.json'
PATCH = WORK/'xnu/patches/0289-gauguin-restore-copy-and-sample-memory-phases.patch'
DOC = WORK/'docs/gauguin-frame-378-trial-20261122.md'
HEADER = '48770d8a4f24a21d9238a3198381598d819483583fde86c8c13afbac67b6efce'
LOG_BYTES = 212_508_165
BATCH = 335_000_000
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0377')],
         'allow_0378_one_60Hz_boot_with_bounded_read_and_write_timing_probes')
SUCCESS = '0378-memory-phases-and-scanout-measured-root-restored'


def check_budget():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']==BATCH and
            admission['current_accounted_bytes']+BATCH<=admission['limit_bytes'], 'whole 0378 batch not admitted')


def check_reference():
    pins = {
        'result.json': 'ec40f34e55bbb811641a4d9d1d5ac8ba1b8e9b960d8875bfb95a9a5cb65bde5d',
        'independent-restore.json': 'cdf2909fde024e51c5a807ddc7d549d4b0da6f26279fc09ab3cf7b7d710ee0e4',
        'restored-capture/result.json': 'f9a762efb616331a266f607f63234cc68e24d0251e56f43d4f117c931bf26873',
        'kernel.log': '3707650b011b20f73ddef4c2d0011f18894c45c7f297750da034106d3fc62bcc',
        'scanout-comparison-0375-0377.json': '95b0b75aec4a29b073863b4d128df11f09e12003eccca9152ffd045b8d2a7287',
    }
    require(all(sha(REFERENCE/name)==digest for name,digest in pins.items()), '0377 immutable evidence differs')
    parent.check_reference()
    prior,proof,original = (load(REFERENCE/name) for name in
        ('result.json','independent-restore.json','restored-capture/result.json'))
    comparison = load(COMPARISON)
    require(prior['trial']=='0377' and prior['restored'] and prior['independent_restore_verified'] and
            prior['static_root_comparison_passed'] and all(prior['other_log_prefix_preserved'].values()) and
            proof['root_header_sha256']==original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES and comparison['crc_register']['qualified'] and
            comparison['crc_calibration']['qualified'] and comparison['copy_phases']['full_capture_qualified'] and
            len(comparison['copy']['0377']['check_failed'])==2 and not comparison['stable_60_fps_observed'],
            '0377 comparison or independently verified baseline differs')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
            len(current['files'])==31 and not current['device_writes'], '0378 TWRP baseline differs')
    return current


def build():
    check_budget()
    previous = P377/'native-kernel/build-manifest.json'
    return import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',
        parent_trial='0377',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_units=tuple((name,previous,'compile-'+name) for name in ('kdebug','SweetFramebuffer')))


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(native),base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P377/'trial-plan.json')['boot_command'], '0378 boot arguments differ')
    image['kernel_manifest'] = str(native)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P377/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P377/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame378-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P377/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P377/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P377,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P377/'trial-plan.json'
    baseline = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame378-image.json',
                                                    'edr-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    installed = load(slots)
    require(native['state']=='0378-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).name for p in (*native['object_replacements'],*native['object_replacements'].values())}=={'kdebug.o','SweetFramebuffer.o'} and
            sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'], '0378 native change differs')
    require(image['command']==baseline['boot_command'] and sha(image['image'])==image['image_sha256'] and
            image['image_bytes']==Path(image['image']).stat().st_size and installed['trial']==TRIAL and
            installed['changed_ranges']==12 and installed['core_sha256']==baseline['owned_core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==baseline['SB_sha256'] and
            installed['rows']['c4']['new_file_sha256']==baseline['C4_sha256'] and
            installed['rows']['c4']['data_extents']==load(P377/'slot-delta/install-plan.json')['rows']['c4']['data_extents'] and
            installed['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
            sha(BASE/'metadata-snapshot/misc-original.bin')==baseline['misc_before_sha256'],
            '0378 image, EDR or six-slot baseline differs')
    host = load(HOST)
    frame = baseline['frame_capture']
    frame = dict(frame,presentation_policy=dict(frame['presentation_policy'],copy_budget_ns=5_500_000))
    sizes = {name:current['files'][name]['bytes'] for name in baseline['log_capture']['sizes']}
    require(sum(sizes.values())==LOG_BYTES and host['projected_ring_bound']<4_194_304 and
            frame['target_refresh_hz']==60 and frame['records']>19_593 and frame['modesets']==0 and
            frame['crc_preimage_reads']==2 and frame['crc_required_preimage']==0x01000000 and
            frame['maximum_volatile_crc_register_writes']==4 and frame['crc_cleanup_readback_equals_recorded_preimage'] and
            baseline['scripted_strokes']==13 and baseline['sustained_motion']['normal_reports']==162,
            '0378 presentation mode, CRC, input or capture budget differs')
    captures = dict(baseline['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
        max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=host['reference_raw_bytes'],
        reserved_frame_console_bytes=4_194_304-host['reference_raw_bytes'],
        previous_verified_suffix_bytes=LOG_BYTES-baseline['log_capture']['measured_baseline_bytes'])
    return dict(baseline,state='prepared-frame376-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(slots),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],log_capture=captures,
        display_retry=dict(baseline['display_retry'],held_pending_limit=4),
        frame_capture=frame, producer_transport=dict(baseline['producer_transport'],armed=True,
            packed_binary_limit=104000,buckets=4096,ways=4,preserves_live_slots=True,
            bucket_limit_has_separate_loss_counter=True),
        ca_handoff=baseline['ca_handoff'],
        copy_diagnostics=dict(baseline['copy_diagnostics'],prefetch_lookahead_bytes=[160],
            original_0375_row_loop=True, required_early_lead_ns=5_500_000),
        memory_probe=dict(counter='CNTVCT_EL0',rows_per_attempt=8,bytes_per_probe=64,
            row_first=128,row_step=288,record_bytes=55,maximum_attempts=80,
            bounds_per_lane=dict(control=16,stroke2=32,stroke6=32),
            relative_ms=dict(stroke2=[8180,8680],stroke6=[17550,18060]),
            control_attempt_modulus=71,source_completion_barrier='dsb ld',
            midcopy_store_completion_barriers_per_sampled_attempt=1,write_drain_barrier='dsb st',
            minimum_probe_residual_ns=5_700_000,extra_framebuffer_bytes=0,
            measurement='Timed instruction envelopes for a small part of each selected row. The write drain includes earlier pending stores.'),
        native_CA=dict(provider='QuartzCore userspace kdebug via the standard trace syscall',
            exact_receiver='backboardd', selected_debugids=['31ca000d','31ca000e','31ca0084',
                '31ca002c','31ca0010','31ca0000','31ca0110'],
            window_seconds=45, thread_dictionary_capacity=32, boot_trace_subclass='0x31ca', boot_trace_ring_events=8192,
            compact_event_capacity=16384, compact_binary_limit=155000, host_proof_sha256=sha(HOST),
            extra_thread_suspensions=0, extra_GPU_calls=0),
        frame_info_provider=dict(type=3,selectors=[72,73,74],target_tag=1,target_offset=0,
            keys=['Presentation_time','Requested_presentation'],owner='backboardd',
            serialized_on_display_workloop=True,after_timed_copy=False,clock_match_tolerance_ns=2000,maximum_sends=1024,maximum_pending_receipts=8,
            maximum_edge_width_ns=4_000_000,requested_timestamp_max_separation_ns=2_000_000_000,
            drop_unqualified_or_expired_receipts=True,maximum_wait_ns=100_000_000,
            actual_tick='upper bound of next exact paired hardware edge after a full guarded copy',
            path_changes='Use the 0375 delivery order and retain the dedicated display trace.',
            additional_persistent_device_writes=0),
        optimization='Restore the 0375 production copy. Sample source completion, store issue and one store drain in selected attempts.',
        performance_comparison='Compare 0375 and 0377 per workload, phase and scan ordinal. Replay the stroke 2 and 6 tail windows.')



def storage(plan):
    prior = load(P377/'storage-bound-377.json')
    parts = dict(prior['components'])
    parts['native_CA_and_scan_alignment']=5_000_000
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0378 runtime exceeds reservation')
    return dict(prior,state='bounded0378-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P377,BASE))
    require({n for n in new['rows'] if new['rows'][n]['new_file_sha256']!=
             old['rows'][n]['new_file_sha256']}=={'admission'}, '0378 userspace changed beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            rollback['all_restore_partial_write_points']==17 and len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            host['state']=='0378-offline-verified' and host['patch_sha256']==sha(PATCH) and
            host['native_schema_verified'] and host['controls']>=12 and host['full_surface_bytes_verified'] and host['original_loop_and_probe_bytes_match'] and host['reference_windows_verified'] and
            not (host['device_writes'] or host['device_boots']),
            '0378 native CA, collection or rollback proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P377,HEADER,plan)


def pins():
    names = ('native-kernel/build-manifest.json','frame378-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json')
    extra = [REFERENCE/'kernel-IO-analysis.json',COMPARISON,P375/'partial-audit-0375.json',
             RETIREMENT,CA_RANGES,P375/'native-kernel/source/bsd/dev/gauguin_copy356.h',P377/'host-verification.json']
    extra += [Path(row['archive']) for row in load(RETIREMENT)['rows']]
    return shared.pins(base=BASE,prior=P377,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,
                       extra=extra,artifacts=[HOST,*(BASE/name for name in names)])


def freeze():
    return shared.freeze(base=BASE,prior=P377,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=steps)
    print(json.dumps(steps[cli.parse_args().step](),indent=2))
