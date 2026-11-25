#!/usr/bin/env python3
"""Prepare a one-shot SpringBoard to BackBoard producer transport capture."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame371')
shared = parent.shared
save = shared.stage.save
TRIAL = '0372'
BASE = WORK/'research/tmp/frame-372'
P371 = MAIN/'research/tmp/gauguin-producer-handoff-worktree-20261121/research/tmp/frame-371'
REFERENCE = P371/'execution'
PATCH = WORK/'xnu/patches/0283-gauguin-compact-producer-transport.patch'
DOC = WORK/'docs/gauguin-frame-372-trial-20261121.md'
HOST = WORK/'research/tmp/frame-372-host/result.json'
RETIREMENT = MAIN/'research/tmp/0372-storage-retirement/verified-retirement-manifest.json'
HEADER = '151eb049127101882f6225310b0ca9865bf0da69d42601c7a22ddf4f30d57ae3'
LOG_BYTES = 188_341_485
BATCH = 435_000_000
PAIR_RECORDS = 10240
MAX_SOURCE_SENDS = 16384
C4_EXTENTS = parent.C4_EXTENTS
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0371')],
    'allow_0372_one_60Hz_boot_with_bounded_compact_transport')
SUCCESS = '0372-producer-transport-measured-root-restored'


def check_budget():
    review = load(BASE/'build-storage-admission.json')
    require(review['admitted'] and review['planned_batch_bytes']==BATCH and
        review['current_accounted_bytes']+BATCH<=review['limit_bytes'],'0372 whole batch not admitted')


def check_reference():
    r = load(REFERENCE/'result.json')
    proof = load(REFERENCE/'independent-restore.json')
    original = load(REFERENCE/'restored-capture/result.json')
    require(sha(REFERENCE/'result.json')=='09db5db99e8e2c9f3cc99915844c1073fb896d74c1298562d8388c0edaa33209' and
        sha(REFERENCE/'independent-restore.json')=='0ea399b84c1d10c96358ada539cbc43d95c77f3c17c1edd0e3098452fab8bee9' and
        sha(REFERENCE/'scoped-swap-timing-0371.json')=='c8775b8e589132129e57d28ea82aea5904bfcc00ace427e4efb800fd350d527b' and
        r['restored'] and r['static_root_comparison_passed'] and r['independent_restore_verified'] and
        all(r['other_log_prefix_preserved'].values()) and not r['stable_60_fps_observed'] and
        proof['root_header_sha256']==original['root_header_sha256']==HEADER and
        original['combined_log_bytes']==LOG_BYTES, '0371 verified baseline differs')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
        len(current['files'])==31 and not current['device_writes'],'0372 read-only baseline differs')
    return current


def build():
    check_budget()
    previous = P371/'native-kernel/build-manifest.json'
    units = ('gauguin_ui_trace_board','ipc_kmsg')
    source = Path(next(step['cwd'] for step in load(previous)['steps']
                       if step['name']=='compile-ipc_kmsg')).parents[4]/'source301-causal-trace/osfmk/kern/exception.c'
    sample = sample_recipe(source,previous)
    import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',
        parent_trial='0371',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_sources={'osfmk/kern/exception.c':source},
        extra_units=(*( (name,previous,'compile-'+name) for name in units),
                     ('exception',sample,'compile-exception')))


def sample_recipe(source, previous):
    baseline = load(previous)
    compile_ipc = next(step for step in baseline['steps'] if step['name']=='compile-ipc_kmsg')
    cwd = Path(compile_ipc['cwd'])
    origin = cwd/'exception.o'
    require(source.is_file() and baseline['input_pins'][str(origin)]==sha(origin),
            'original saved register sampler differs')
    out = BASE/'sampler-origin'
    receipt = out/'result.json'
    if receipt.is_file():
        proof = load(receipt)
        require(proof['baseline_machine_code_matches'] and
            all(sha(path)==digest for path,digest in proof['input_pins'].items()),
            'existing sampler machine-code proof differs')
        return receipt
    out.mkdir()
    argv = list(compile_ipc['argv'])
    argv[argv.index('-MF')+1] = str(cwd/'exception.d')
    argv[argv.index('-o')+1] = str(origin)
    argv[-1] = str(source)
    replay = out/'original-exception.o'
    replay_argv = [str(replay) if arg==str(origin) else
        str(replay.with_suffix('.d')) if arg==str(cwd/'exception.d') else arg for arg in argv]
    subprocess.run(replay_argv,cwd=cwd,check=True,capture_output=True,timeout=90)
    def text(obj):
        return subprocess.check_output(['xcrun','otool','-s','__TEXT','__text',str(obj)]).splitlines()[2:]
    require(text(origin) and text(origin)==text(replay),'sampler baseline machine code did not reproduce')
    save(receipt,dict(state='0371-register-sampler-machine-code-reproduced',steps=[
        dict(name='compile-exception',argv=argv,cwd=str(cwd),exit=0)],baseline_machine_code_matches=True,
        input_pins={str(item):sha(item) for item in (source,origin,cwd/'exception.d',replay)}))
    return receipt


def package():
    check_budget()
    pack = import_module('package-frame344')
    manifest = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(manifest),base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P371/'trial-plan.json')['boot_command'],'0372 boot arguments differ')
    image['kernel_manifest'] = str(manifest)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P371/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P371/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame372-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P371/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
        max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',str(REFERENCE/'restored-capture/result.json'),
        '--out',str(BASE/'slot-capture'),'--reuse-data-from',str(P371/'slot-capture')],
        check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
        maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P371,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    r = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in r.items() if k not in ('input_pins','checks')} | {'checks':len(r['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P371/'trial-plan.json'
    original = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame372-image.json',
        'edr-native/result.json'))
    install = BASE/'slot-delta/install-plan.json'
    slots = load(install)
    require(native['state']=='0372-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
        native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
        {Path(p).name for p in (*native['object_replacements'],*native['object_replacements'].values())}==
        {'gauguin_ui_trace_board.o','ipc_kmsg.o','exception.o'} and
        sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
        native['identity']==image['build_identity']==edr['kernel_identity'],'0372 linked changes differ')
    require(image['command']==original['boot_command'] and sha(image['image'])==image['image_sha256'] and
        image['image_bytes']==Path(image['image']).stat().st_size and slots['trial']==TRIAL and
        slots['changed_ranges']==12 and slots['core_sha256']==original['owned_core_sha256'] and
        slots['rows']['eagl']['new_file_sha256']==original['SB_sha256'] and
        slots['rows']['c4']['new_file_sha256']==original['C4_sha256'] and
        slots['rows']['c4']['data_extents']==C4_EXTENTS and
        slots['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
        sha(BASE/'metadata-snapshot/misc-original.bin')==original['misc_before_sha256'],
        '0372 kernel, helper or userspace baseline differs')
    files = {k:current['files'][k]['bytes'] for k in original['log_capture']['sizes']}
    raw = load(REFERENCE/'kernel-IO-analysis.json')['ring']['total_bytes']
    host = load(HOST)
    require(sum(files.values())==LOG_BYTES and host['reference_raw_bytes']==raw and
        host['projected_ring_bound']<4_194_304 and
        host['full_scope_export_bound']<=330_000 and
        19_539<original['frame_capture']['records'], '0372 capture reserve too small')
    capture = dict(original['log_capture'],measured_baseline_bytes=LOG_BYTES,max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,
        sizes=files,reference_kernel_log_bytes=raw,reserved_frame_console_bytes=4_194_304-raw,
        previous_verified_suffix_bytes=LOG_BYTES-original['log_capture']['measured_baseline_bytes'])
    return dict(original,state='prepared-frame372-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(install),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],log_capture=capture,
        optimization='Preserve transport identities for the complete original workload before tracing the remaining CA handoff.',
        performance_comparison='Keep the 0371 Core, C4, workload and physical CRC scoring.',
        producer_transport=dict(maximum_pairs=PAIR_RECORDS,maximum_tagged_sends=MAX_SOURCE_SENDS,
            key='authenticated process generation and live kernel message',
            source='SpringBoard',receiver='backboardd',window_seconds=45,record_bytes=20,block_records=64,
            thread_dictionary_capacity=256,miss_timestamps_cap=64,
            receive_stamp_slots=512,maximum_stamped_samples=64,extra_thread_suspensions=0,
            sends_injected=0,extra_GPU_calls=0,records_payload=False,
            blocking_lock=False,changes_dispatch_or_return=False))


def storage(plan):
    prior = load(P371/'storage-bound-371.json')
    parts = dict(prior['components'],producer_transport_summary=4_000_000)
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
        '0372 runtime exceeds reservation')
    return dict(prior,state='bounded0372-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
        fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    prior,install = (load(p/'slot-delta/install-plan.json') for p in (P371,BASE))
    require({n for n in install['rows'] if install['rows'][n]['new_file_sha256']!=
        prior['rows'][n]['new_file_sha256']}=={'admission'}, '0372 userspace change outside EDR identity')
    model = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(model['all_model_IO_writes_memory_only'] and model['install_ranges']==12 and
        model['all_restore_partial_write_points']==17 and
        model['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
        'split-tail-became-unallocated-refused-before-write' in model['checks'] and
        host['patch_sha256']==sha(PATCH) and host['projection_passed'] and
        host['state']=='0372-compact-transport-cross-compiled-and-modeled' and
        not (host['device_writes'] or host['device_boots']),'0372 frame or restore model incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P371,HEADER,plan)


def pins():
    extra = [RETIREMENT,REFERENCE/'scoped-swap-timing-0371.json',
        REFERENCE/'frame-pacing-0370-0371.json']
    names = ('sampler-origin/result.json','native-kernel/build-manifest.json','frame372-image.json','edr-native/result.json',
        'core-native/result.json','c4-native/result.json','restore-model/result.json')
    return shared.pins(base=BASE,prior=P371,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,extra=extra,
        artifacts=[HOST, *(BASE/name for name in names)])


def freeze():
    return shared.freeze(base=BASE,prior=P371,expected=expected_plan,validate=criteria,storage_bound=storage,
        pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
        preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {f.__name__:f for f in (build,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=steps)
    print(json.dumps(steps[cli.parse_args().step](),indent=2))
