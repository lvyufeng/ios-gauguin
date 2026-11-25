#!/usr/bin/env python3
"""Prepare one 60 Hz swap timing run with a two-extent C4 rollback."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import FLAGS as PRIOR_FLAGS, LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

TRIAL = '0369'
BASE = WORK/'research/tmp/frame-369'
P368 = MAIN/'research/tmp/gauguin-route-lifetime-worktree-20261121/research/tmp/frame-368'
P366 = MAIN/'research/tmp/gauguin-issued-probe-worktree-20261121/research/tmp/frame-366'
RESCUE = MAIN/'research/tmp/0368-tail-recovery'
REFERENCE = RESCUE/'restored-capture/result.json'
C4 = MAIN/'research/tmp/gauguin-c4-tail-rescue-worktree-20261121/research/tmp/c4-full-allocation-reproduced-2/result.json'
C4_SHA = '0432845df815a3ff9c62b7302a643d63dc47089c2abf184db64d1b7d4a2ba2fc'
C4_EXTENTS = [[3817791,101],[3818294,4]]
PATCH = WORK/'xnu/patches/0280-gauguin-observe-swap-version-selection.patch'
DOC = WORK/'docs/gauguin-frame-369-trial-20261121.md'
RETIREMENT = MAIN/'research/tmp/0369-storage-retirement/verified-retirement-manifest.json'
HEADER = '68f527db09794fa38c9f8f2bfcdf020f1c00536026c57c4a50fc2f377529878b'
RESTORED_LOG_BYTES = 176_221_919
BATCH = 430_000_000
FLAGS = tuple(flag for flag in PRIOR_FLAGS if not flag.startswith('allow_0366')) + (
    'allow_0369_one_60Hz_boot_with_same_client_swap_timing_and_exact_C4_extents',)
SUCCESS = '0369-swap-version-timing-measured-root-restored'
shared = import_module('prepare-frame349')
save = shared.stage.save


def check_budget():
    r = load(BASE/'build-storage-admission.json')
    require(r['admitted'] and r['planned_batch_bytes']==BATCH and
            r['current_accounted_bytes']+BATCH<=r['limit_bytes'], '0369 whole batch not admitted')


def check_baseline():
    receipt = RESCUE/'independent-restore.json'
    require(sha(receipt)=='d2e7f7d918441fc5b7911d23b247168877b28d0e4fd9869457ca76dea82236e1' and
        sha(RESCUE/'scoped-scan-audit.json')=='b9ae9e08d001305f050d28262a536341551c701040a986fdeb3c4a3586431581',
        '0368 independently restored reference changed')
    proof = load(receipt)
    require(proof['relocated_c4_extents']==C4_EXTENTS and proof['wal_data_and_fork_unchanged'] and
        proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and len(proof['files'])==6,
        '0368 split-C4 proof incomplete')
    current,previous = load(BASE/'current-root-capture/result.json'),load(REFERENCE)
    require(current['files']==previous['files'] and current['directories']==previous['directories'] and
        current['root_header_sha256']==previous['root_header_sha256']==proof['root_header_sha256']==HEADER and
        len(current['files'])==31 and current['combined_log_bytes']==previous['combined_log_bytes']==RESTORED_LOG_BYTES and
        not current['device_writes'], '0369 live TWRP differs from 0368 restored state')
    return current


def build():
    check_budget()
    import_module('build-frame347').link_scanout(P368/'native-kernel/build-manifest.json',BASE/'native-kernel',
        parent_trial='0368',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_units=(('SweetFramebuffer',P366/'native-kernel/build-manifest.json','compile-SweetFramebuffer'),))


def package():
    check_budget()
    pack = import_module('package-frame344')
    manifest = BASE/'native-kernel/build-manifest.json'
    build = load(manifest)
    require(build['input_pins'][str(PATCH)]==sha(PATCH) and build['inputs_unchanged'],'unexpected native build')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),build,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P368/'trial-plan.json')['boot_command'],'0369 boot command changed')
    image['kernel_manifest'] = str(manifest)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P368/'edr-native/result.json')
    c4 = load(C4)
    require(c4['bytes']==429_040 and c4['blocks']==105 and c4['strict_signature'] and
        sha(c4['candidate'])==c4['candidate_sha256']==C4_SHA and c4['same_sdk_imports_exports_loads_and_resources'],
        '0369 C4 fixed allocation candidate differs')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
    shutil.copyfile(P368/'core-native/result.json',BASE/'core-native/result.json')
    save(BASE/'c4-native/result.json',dict(binary=c4['candidate'],binary_sha256=C4_SHA,bytes=c4['bytes'],
        input_pins={str(C4):sha(C4),c4['control']:c4['control_sha256'],c4['candidate']:C4_SHA},
        comparison_uses_sdk_27_2=True,signature_verified=True,device_commands=0))
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame369-image.json',image)
    return {name:image[name] for name in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    profile = load(P368/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
        max_combined_log_bytes=RESTORED_LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',str(REFERENCE),
        '--out',str(BASE/'slot-capture'),'--reuse-data-from',str(P368/'slot-capture')],
        check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
        maximum_compressed_bytes=28_000_000)
    return {key:meta[key] for key in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P368,trial=TRIAL,header=HEADER,baseline=REFERENCE,
        c4_receipt=BASE/'c4-native/result.json')


def model():
    r = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in r.items() if k!='input_pins'}


def expected_plan():
    current = check_baseline()
    prior = P368/'trial-plan.json'
    original = load(prior)
    build,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame369-image.json',
                                                   'edr-native/result.json'))
    install = BASE/'slot-delta/install-plan.json'
    d = load(install)
    require(build['state']=='0369-native-ARM64-linked' and build['baseline_reproduced_except_uuid'] and
        build['inputs_unchanged'] and build['input_pins'][str(PATCH)]==sha(PATCH) and
        {Path(p).name for p in (*build['object_replacements'],*build['object_replacements'].values())}
            =={'SweetFramebuffer.o'} and
        sha(build['kernel'])==build['kernel_sha256']==image['kernel_sha256'] and
        build['identity']==image['build_identity']==edr['kernel_identity'],'0369 replaced an unexpected kernel unit')
    require(image['command']==original['boot_command'] and sha(image['image'])==image['image_sha256'] and
        image['image_bytes']==Path(image['image']).stat().st_size and d['trial']==TRIAL and
        d['core_sha256']==original['owned_core_sha256'] and d['rows']['eagl']['new_file_sha256']==original['SB_sha256'] and
        d['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
        d['rows']['c4']['data_extents']==C4_EXTENTS and d['rows']['c4']['new_file_sha256']==C4_SHA and
        d['rows']['c4']['new_logical']==429040 and d['changed_ranges']==12 and
        sha(BASE/'metadata-snapshot/misc-original.bin')==original['misc_before_sha256'],
        '0369 image, userspace or split allocation is outside the exact scope')
    sizes = {name:current['files'][name]['bytes'] for name in original['log_capture']['sizes']}
    raw_bytes = load(RESCUE/'score/kernel-IO-analysis.json')['ring']['total_bytes']
    require(sum(sizes.values())==RESTORED_LOG_BYTES and raw_bytes+1024*160<4_194_304,
        '0369 capture storage cannot contain the bounded timing trace')
    capture = dict(original['log_capture'],measured_baseline_bytes=RESTORED_LOG_BYTES,
        max_combined_log_bytes=RESTORED_LOG_BYTES+LOG_SUFFIX,sizes=sizes,reference_kernel_log_bytes=raw_bytes,
        reserved_frame_console_bytes=4_194_304-raw_bytes,
        previous_verified_suffix_bytes=RESTORED_LOG_BYTES-original['log_capture']['measured_baseline_bytes'])
    return dict(original,state='prepared-frame369-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(install),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=build['identity'],
        kernel_banner=build['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],C4_sha256=C4_SHA,
        optimization='Observe the same-client SwapBegin and the selected exact source version without changing scheduling.',
        performance_comparison='Use the 0368 strokes and fixed drag. Requalify the newer SDK C4 separately.',
        swap_timing=dict(wire_kind=62,maximum_records=1024,no_new_GPU_calls=True,changes_selection=False),
        C4_split_extent=dict(extents=C4_EXTENTS,logical_bytes=429040,require_no_trim=True,SDK='27.2'),
        log_capture=capture)


def storage(plan):
    prior = load(P368/'storage-bound-368.json')
    components = dict(prior['components'],swap_timing_and_scoped_comparison=3_500_000)
    worst = sum(components.values())
    require(worst<=RESERVE and plan['log_capture']['measured_baseline_bytes']==RESTORED_LOG_BYTES,
        '0369 runtime exceeds reservation')
    return dict(prior,state='bounded0369-runtime-batch',components=components,worst_case_bytes=worst,
        fresh_log_bytes=RESTORED_LOG_BYTES,log_cap_bytes=RESTORED_LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    install, prior = (load(p/'slot-delta/install-plan.json') for p in (BASE,P368))
    require({name for name in install['rows'] if install['rows'][name]['new_file_sha256']!=
        prior['rows'][name]['new_file_sha256']}=={'c4','admission'},'unrelated userspace changes')
    model,host,slots = (load(BASE/name) for name in
        ('restore-model/result.json','frame-host/result.json','slot-capture/result.json'))
    require(model['all_model_IO_writes_memory_only'] and model['install_ranges']==12 and
        model['all_restore_partial_write_points']>=17 and
        model['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
        model['maximum_actual_model_restore_bytes']<=plan['maximum_restore_userdata_bytes'] and
        'split-tail-became-unallocated-refused-before-write' in model['checks'] and
        host['state']=='0369-swap-timing-and-replay-passed' and host['patch_sha256']==sha(PATCH) and
        len(slots['reused_original_data'])==6 and slots['baseline_sha256']==sha(REFERENCE) and
        not (slots['device_writes'] or slots['device_boots']), '0369 rollback, trace or slot evidence is incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P368,HEADER,plan)


def pins():
    report_input = RESCUE/'score'
    extra = [C4, RETIREMENT, REFERENCE, RESCUE/'independent-restore.json', RESCUE/'scoped-scan-audit.json']
    extra += [report_input/name for name in ('result.json','kernel.log','frame-scanout-analysis.json','frame-pacing-0365-0368.json')]
    artifacts = [BASE/name for name in ('native-kernel/build-manifest.json','frame369-image.json','edr-native/result.json',
                                      'core-native/result.json','c4-native/result.json','frame-host/result.json','restore-model/result.json')]
    return shared.pins(base=BASE,prior=P368,doc=DOC,patch=PATCH,reference=P366/'execution',trial=TRIAL,
        extra=extra,artifacts=artifacts)


def freeze():
    return shared.freeze(base=BASE,prior=P368,expected=expected_plan,validate=criteria,storage_bound=storage,
        pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
        preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=steps)
    print(json.dumps(steps[cli.parse_args().step](),indent=2))
