#!/usr/bin/env python3
"""Freeze the bounded 0376 native CA timing and frame receipt trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame375')
shared = parent.shared
save = shared.stage.save
TRIAL = '0376'
BASE = WORK/'research/tmp/frame-376'
P375 = MAIN/'research/tmp/gauguin-frame-receipt-worktree-20261122/research/tmp/frame-375'
P373 = parent.parent.P373
IPA_PROOF = P373/'20H392-publication-order.json'
CA_RANGES = parent.parent.parent.P372.parent/'frame-372-host/20H392-ca-code-ranges.json'
REFERENCE = P375/'execution'
RETIREMENT = MAIN/'research/tmp/0376-storage-retirement/verified-retirement-manifest.json'
HOST = BASE/'host-verification.json'
PATCH = WORK/'xnu/patches/0287-gauguin-isolate-frame-info-and-copy-window.patch'
DOC = WORK/'docs/gauguin-frame-376-trial-20261122.md'
HEADER = 'f111562bc232a04a439814359f3adf9c34c0f7a82cdf947449e2e61313ce9438'
LOG_BYTES = 204_449_533
BATCH = 315_000_000
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0375')],
         'allow_0376_one_60Hz_boot_with_independent_display_and_transport_capture')
SUCCESS = '0376-native-display-and-transport-measured-root-restored'


def check_budget():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']==BATCH and
            admission['current_accounted_bytes']+BATCH<=admission['limit_bytes'], 'whole 0376 batch not admitted')


def check_reference():
    pins = {
        'execution/result.json': '7047b58baa4aecbcf7d16b4406791c4e4f4021eed55e96eb31342290159cdeba',
        'execution/independent-restore.json': '8a9d38a931e5cecfdb2a17f71ea91a3bfb303727d9346b8b47c6a6eeb5303abb',
        'execution/restored-capture/result.json': '362ebca75078d3345eca960731503d27d08031c984c9ef9583687dd22ed9e9b2',
        'execution/frame-scanout-analysis.json': '8ef8a588c178ced99824ece3177c0bf3ad82f3c7a2ed2ac793c711d4b85027af',
        'execution/kernel.log': '9283b007dd143d431ab491f0e24538bbbc882f8ebf4ba2f0e98bbf58ce15e986',
        'partial-audit-0375.json': '8c9853c2ae2da3d607bee831cd6bb667fe5ea46737d84b36bfa4c5647ffd723b',
    }
    require(all(sha(P375/name)==digest for name,digest in pins.items()), '0375 immutable evidence differs')
    prior = load(REFERENCE/'result.json')
    proof = load(REFERENCE/'independent-restore.json')
    original = load(REFERENCE/'restored-capture/result.json')
    frame = load(REFERENCE/'frame-scanout-analysis.json')
    require(prior['trial']=='0375' and prior['restored'] and prior['independent_restore_verified'] and
            prior['static_root_comparison_passed'] and all(prior['other_log_prefix_preserved'].values()) and
            proof['root_header_sha256']==original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES and frame['misr']['qualified'] and
            frame['crc_frame_calibration']['qualified'] and not prior.get('stable_60_fps_observed',False),
            '0375 partial comparison or independently verified baseline differs')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
            len(current['files'])==31 and not current['device_writes'], '0376 TWRP baseline differs')
    return current


def build():
    check_budget()
    previous = P375/'native-kernel/build-manifest.json'
    return import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',
        parent_trial='0375',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_units=(('gauguin_ui_trace_board',previous,'compile-gauguin_ui_trace_board'),
                     ('kdebug',previous,'compile-kdebug'),
                     ('SweetFramebuffer',previous,'compile-SweetFramebuffer'),
                     ('ipc_kmsg',P373/'native-kernel/build-manifest.json','compile-ipc_kmsg')))


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(native),base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P375/'trial-plan.json')['boot_command'], '0376 boot arguments differ')
    image['kernel_manifest'] = str(native)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P375/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P375/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame376-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P375/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P375/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P375,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P375/'trial-plan.json'
    baseline = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame376-image.json',
                                                    'edr-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    installed = load(slots)
    require(native['state']=='0376-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).name for p in (*native['object_replacements'],*native['object_replacements'].values())}=={'kdebug.o','gauguin_ui_trace_board.o','ipc_kmsg.o','SweetFramebuffer.o'} and
            sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'], '0376 native change differs')
    require(image['command']==baseline['boot_command'] and sha(image['image'])==image['image_sha256'] and
            image['image_bytes']==Path(image['image']).stat().st_size and installed['trial']==TRIAL and
            installed['changed_ranges']==12 and installed['core_sha256']==baseline['owned_core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==baseline['SB_sha256'] and
            installed['rows']['c4']['new_file_sha256']==baseline['C4_sha256'] and
            installed['rows']['c4']['data_extents']==parent.parent.parent.parent.C4_EXTENTS and
            installed['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
            sha(BASE/'metadata-snapshot/misc-original.bin')==baseline['misc_before_sha256'],
            '0376 image, EDR or six-slot baseline differs')
    host = load(HOST)
    frame = baseline['frame_capture']
    frame = dict(frame,presentation_policy=dict(frame['presentation_policy'],copy_budget_ns=6_700_000))
    sizes = {name:current['files'][name]['bytes'] for name in baseline['log_capture']['sizes']}
    require(sum(sizes.values())==LOG_BYTES and host['projected_ring_bound']<4_194_304 and
            frame['target_refresh_hz']==60 and frame['records']>19_593 and frame['modesets']==0 and
            frame['crc_preimage_reads']==2 and frame['crc_required_preimage']==0x01000000 and
            frame['maximum_volatile_crc_register_writes']==4 and frame['crc_cleanup_readback_equals_recorded_preimage'] and
            baseline['scripted_strokes']==13 and baseline['sustained_motion']['normal_reports']==162,
            '0376 presentation mode, CRC, input or capture budget differs')
    captures = dict(baseline['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
        max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=host['reference_raw_bytes'],
        reserved_frame_console_bytes=4_194_304-host['reference_raw_bytes'],
        previous_verified_suffix_bytes=LOG_BYTES-baseline['log_capture']['measured_baseline_bytes'])
    return dict(baseline,state='prepared-frame376-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(slots),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],log_capture=captures,
        display_retry=dict(baseline['display_retry'],held_pending_limit=4),
        frame_capture=frame, producer_transport=dict(
            {k:v for k,v in baseline['producer_transport'].items() if k!='record_bytes'},armed=True,
            record_bytes_max=23, packed_binary_limit=110000, thread_dictionary_capacity=64),
        ca_handoff=dict(cache_build='20H392',source='SpringBoard',receiver='backboardd',
            exact_transport_identity='tagged live message serial across send, post and successful copyout',
            application_and_render_membership_required_for_exact_end_to_end=True,
            producer_scheduling_changes=0),
        copy_diagnostics=dict(long_copy_threshold_ticks=96000,maximum_rows=32,
            timebase=[625,12],hardware_end_check_after_surface_store_barrier=True,
            read_guard_held_across_stores=True,required_early_lead_ns=6700000),
        native_CA=dict(provider='QuartzCore userspace kdebug via the standard trace syscall',
            exact_receiver='backboardd', selected_debugids=['31ca000d','31ca000e','31ca0084',
                '31ca002c','31ca0010','31ca0000','31ca0110'],
            window_seconds=45, thread_dictionary_capacity=32, boot_trace_subclass='0x31ca', boot_trace_ring_events=8192,
            compact_event_capacity=16384, compact_binary_limit=164000, host_proof_sha256=sha(HOST),
            extra_thread_suspensions=0, extra_GPU_calls=0),
        frame_info_provider=dict(type=3,selectors=[72,73,74],target_tag=1,target_offset=0,
            keys=['Presentation_time','Requested_presentation'],owner='backboardd',
            serialized_on_display_workloop=True,after_timed_copy=True,clock_match_tolerance_ns=2000,maximum_sends=1024,maximum_pending_receipts=8,
            maximum_edge_width_ns=4_000_000,requested_timestamp_max_separation_ns=2_000_000_000,
            drop_unqualified_or_expired_receipts=True,maximum_wait_ns=100_000_000,
            actual_tick='upper bound of next exact paired hardware edge after a full guarded copy',
            path_changes='Serve qualified receipts after the copy on the same workloop. Increase pre-store scan lead time.',
            additional_persistent_device_writes=0),
        optimization='Reserve FrameInfo coverage and protect the copy window before sending FrameInfo.',
        performance_comparison='Same 0375 Core, C4, scripts and 60 Hz route. Join targets and CRC using exact swap and scan IDs.')



def storage(plan):
    prior = load(P375/'storage-bound-375.json')
    parts = dict(prior['components'])
    parts['native_CA_and_scan_alignment']=5_000_000
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0376 runtime exceeds reservation')
    return dict(prior,state='bounded0376-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P375,BASE))
    require({n for n in new['rows'] if new['rows'][n]['new_file_sha256']!=
             old['rows'][n]['new_file_sha256']}=={'admission'}, '0376 userspace changed beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            rollback['all_restore_partial_write_points']==17 and len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            host['state']=='0376-offline-verified' and host['patch_sha256']==sha(PATCH) and
            host['native_schema_verified'] and host['controls']>=12 and host['reference_crossing_rejected'] and
            not (host['device_writes'] or host['device_boots']),
            '0376 native CA, collection or rollback proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P375,HEADER,plan)


def pins():
    names = ('native-kernel/build-manifest.json','frame376-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json')
    extra = [REFERENCE/'kernel-IO-analysis.json',P375/'partial-audit-0375.json',
             RETIREMENT,IPA_PROOF,CA_RANGES,P373/'execution/kernel.log']
    extra += [Path(row['archive']) for row in load(RETIREMENT)['rows']]
    return shared.pins(base=BASE,prior=P375,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,
                       extra=extra,artifacts=[HOST,*(BASE/name for name in names)])


def freeze():
    return shared.freeze(base=BASE,prior=P375,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=steps)
    print(json.dumps(steps[cli.parse_args().step](),indent=2))
