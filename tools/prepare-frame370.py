#!/usr/bin/env python3
"""Prepare the one-shot BackBoard SwapWait lifecycle capture."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame369')
shared = parent.shared
save = shared.stage.save
TRIAL = '0370'
BASE = WORK/'research/tmp/frame-370'
P369 = MAIN/'research/tmp/gauguin-swap-timing-worktree-20261121/research/tmp/frame-369'
REFERENCE = P369/'execution'
PATCH = WORK/'xnu/patches/0281-gauguin-observe-swap-wait-lifecycle.patch'
DOC = WORK/'docs/gauguin-frame-370-trial-20261121.md'
HOST = WORK/'research/tmp/frame-370-host/result.json'
RETIREMENT = MAIN/'research/tmp/0370-storage-retirement/verified-retirement-manifest.json'
HEADER = 'c3ef7870d6ab13a91806ffe63b07637cd364365b7089aca1b52cb37797e6879f'
LOG_BYTES = 180_270_273
BATCH = 405_000_000
WAIT_RECORDS = 384
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0369')],
    'allow_0370_one_60Hz_boot_with_bounded_read_only_SwapWait_capture')
SUCCESS = '0370-swap-wait-lifecycle-observed-root-restored'


def check_budget():
    review = load(BASE/'build-storage-admission.json')
    require(review['admitted'] and review['planned_batch_bytes']==BATCH and
        review['current_accounted_bytes']+BATCH<=review['limit_bytes'],'0370 whole batch not admitted')


def check_reference():
    r = load(REFERENCE/'result.json')
    proof = load(REFERENCE/'independent-restore.json')
    original = load(REFERENCE/'restored-capture/result.json')
    require(sha(REFERENCE/'result.json')=='c080d04232f6407c335f3fbec7171f7da91dafa0acbe92ce3b39cc9b5b74054d' and
        sha(REFERENCE/'independent-restore.json')=='ea0e1ae57f8955c5173f898d3250221bb01dfaf58c1381167576d1aafc1efd4b' and
        r['restored'] and r['static_root_comparison_passed'] and r['independent_restore_verified'] and
        all(r['other_log_prefix_preserved'].values()) and not r['stable_60_fps_observed'] and
        proof['root_header_sha256']==original['root_header_sha256']==HEADER and
        original['combined_log_bytes']==LOG_BYTES, '0369 verified baseline differs')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
        len(current['files'])==31 and not current['device_writes'],'0370 read-only baseline differs')
    return current


def build():
    check_budget()
    prior = P369/'native-kernel/build-manifest.json'
    import_module('build-frame347').link_scanout(prior,BASE/'native-kernel',parent_trial='0369',trial=TRIAL,
        patches=(PATCH,),recompile_scanout=False,extra_units=(('SweetFramebuffer',prior,'compile-SweetFramebuffer'),))


def package():
    check_budget()
    pack = import_module('package-frame344')
    manifest = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(manifest),base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P369/'trial-plan.json')['boot_command'],'0370 boot arguments differ')
    image['kernel_manifest'] = str(manifest)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P369/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P369/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame370-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P369/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
        max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',str(REFERENCE/'restored-capture/result.json'),
        '--out',str(BASE/'slot-capture'),'--reuse-data-from',str(P369/'slot-capture')],
        check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
        maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P369,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    r = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in r.items() if k not in ('input_pins','checks')} | {'checks':len(r['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P369/'trial-plan.json'
    original = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame370-image.json',
        'edr-native/result.json'))
    install = BASE/'slot-delta/install-plan.json'
    slots = load(install)
    require(native['state']=='0370-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
        native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
        {Path(p).name for p in (*native['object_replacements'],*native['object_replacements'].values())}=={'SweetFramebuffer.o'} and
        sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
        native['identity']==image['build_identity']==edr['kernel_identity'],'0370 linked changes differ')
    require(image['command']==original['boot_command'] and sha(image['image'])==image['image_sha256'] and
        image['image_bytes']==Path(image['image']).stat().st_size and slots['trial']==TRIAL and
        slots['changed_ranges']==12 and slots['core_sha256']==original['owned_core_sha256'] and
        slots['rows']['eagl']['new_file_sha256']==original['SB_sha256'] and
        slots['rows']['c4']['new_file_sha256']==original['C4_sha256'] and
        slots['rows']['c4']['data_extents']==parent.C4_EXTENTS and
        slots['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
        sha(BASE/'metadata-snapshot/misc-original.bin')==original['misc_before_sha256'],
        '0370 kernel, helper or userspace baseline differs')
    files = {k:current['files'][k]['bytes'] for k in original['log_capture']['sizes']}
    raw = load(REFERENCE/'kernel-IO-analysis.json')['ring']['total_bytes']
    require(sum(files.values())==LOG_BYTES and raw+WAIT_RECORDS*160<4_194_304 and
        19_461+WAIT_RECORDS<original['frame_capture']['records'], '0370 capture reserve too small')
    capture = dict(original['log_capture'],measured_baseline_bytes=LOG_BYTES,max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,
        sizes=files,reference_kernel_log_bytes=raw,reserved_frame_console_bytes=4_194_304-raw,
        previous_verified_suffix_bytes=LOG_BYTES-original['log_capture']['measured_baseline_bytes'])
    return dict(original,state='prepared-frame370-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(install),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],log_capture=capture,
        optimization='Observe the existing SwapWait return path alongside its exact retained-frame state.',
        performance_comparison='Keep the 0369 Core, C4, workload and physical CRC scoring.',
        swap_wait=dict(wire_kind=63,maximum_records=WAIT_RECORDS,requested_ID_modulus=4,
            blocking_lock=False,changes_return=False,extra_GPU_calls=0))


def storage(plan):
    prior = load(P369/'storage-bound-369.json')
    parts = dict(prior['components'],swap_wait_summary=1_000_000)
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
        '0370 runtime exceeds reservation')
    return dict(prior,state='bounded0370-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
        fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    prior,install = (load(p/'slot-delta/install-plan.json') for p in (P369,BASE))
    require({n for n in install['rows'] if install['rows'][n]['new_file_sha256']!=
        prior['rows'][n]['new_file_sha256']}=={'admission'}, '0370 userspace change outside EDR identity')
    model = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(model['all_model_IO_writes_memory_only'] and model['install_ranges']==12 and
        model['all_restore_partial_write_points']==17 and
        model['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
        'split-tail-became-unallocated-refused-before-write' in model['checks'] and
        host['patch_sha256']==sha(PATCH) and host['same_return_path'] and
        host['state']=='0370-read-only-swap-wait-cross-compiled-and-modeled' and
        not (host['device_writes'] or host['device_boots']),'0370 frame or restore model incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P369,HEADER,plan)


def pins():
    extra = [RETIREMENT,HOST,HOST.parent/'observer-projection.cpp',HOST.parent/'SweetFramebuffer.o',
        WORK/'tests/test_frame370_swap_wait.py',REFERENCE/'scoped-swap-timing-0369.json']
    names = ('native-kernel/build-manifest.json','frame370-image.json','edr-native/result.json',
        'core-native/result.json','c4-native/result.json','restore-model/result.json')
    return shared.pins(base=BASE,prior=P369,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,extra=extra,
        artifacts=[BASE/name for name in names])


def freeze():
    return shared.freeze(base=BASE,prior=P369,expected=expected_plan,validate=criteria,storage_bound=storage,
        pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
        preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {f.__name__:f for f in (build,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=steps)
    print(json.dumps(steps[cli.parse_args().step](),indent=2))
