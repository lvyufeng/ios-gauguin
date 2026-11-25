#!/usr/bin/env python3
"""Prepare a one-shot SpringBoard to BackBoard producer transport capture."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import shlex
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame370')
shared = parent.shared
save = shared.stage.save
TRIAL = '0371'
BASE = WORK/'research/tmp/frame-371'
P370 = MAIN/'research/tmp/gauguin-swap-wait-worktree-20261121/research/tmp/frame-370'
P368 = MAIN/'research/tmp/gauguin-route-lifetime-worktree-20261121/research/tmp/frame-368'
REFERENCE = P370/'execution'
PATCH = WORK/'xnu/patches/0282-gauguin-observe-producer-transport.patch'
DOC = WORK/'docs/gauguin-frame-371-trial-20261121.md'
HOST = WORK/'research/tmp/frame-371-host/result.json'
RETIREMENT = MAIN/'research/tmp/0371-storage-retirement/verified-retirement-manifest.json'
HEADER = '837f1d5733e2e9115d3ef9c927abd1fada9402af6d2ff7c5f7080720e057fd53'
LOG_BYTES = 184_294_769
BATCH = 425_000_000
PAIR_RECORDS = 1536
MAX_SOURCE_SENDS = 16384
C4_EXTENTS = parent.parent.C4_EXTENTS
ORIGIN = MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/.deps-cache/p0-20261105'
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0370')],
    'allow_0371_one_60Hz_boot_with_bounded_producer_transport_capture')
SUCCESS = '0371-producer-transport-measured-root-restored'


def check_budget():
    review = load(BASE/'build-storage-admission.json')
    require(review['admitted'] and review['planned_batch_bytes']==BATCH and
        review['current_accounted_bytes']+BATCH<=review['limit_bytes'],'0371 whole batch not admitted')


def check_reference():
    r = load(REFERENCE/'result.json')
    proof = load(REFERENCE/'independent-restore.json')
    original = load(REFERENCE/'restored-capture/result.json')
    require(sha(REFERENCE/'result.json')=='b9677ba4516c59c4c7f6ec05f8cdc8916616b6400c2adc2d96823829d7318478' and
        sha(REFERENCE/'independent-restore.json')=='8f1c3a72cfeebfa8465532f11dbcf3006080bd638fa5703c9ce762aeb4e36aca' and
        sha(REFERENCE/'scoped-swap-timing-0370.json')=='6dbe6ccbbfc3ec17d870e6a03ce3cb1b2377c432ef7783c8148f7218fdc37d4a' and
        r['restored'] and r['static_root_comparison_passed'] and r['independent_restore_verified'] and
        all(r['other_log_prefix_preserved'].values()) and not r['stable_60_fps_observed'] and
        proof['root_header_sha256']==original['root_header_sha256']==HEADER and
        original['combined_log_bytes']==LOG_BYTES, '0370 verified baseline differs')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
        len(current['files'])==31 and not current['device_writes'],'0371 read-only baseline differs')
    return current


def build():
    check_budget()
    prior = P370/'native-kernel/build-manifest.json'
    board = P368/'native-kernel/build-manifest.json'
    source = ORIGIN/'source301-causal-trace/osfmk/ipc/ipc_kmsg.c'
    recipe = ipc_recipe(source, prior)
    import_module('build-frame347').link_scanout(prior,BASE/'native-kernel',parent_trial='0370',trial=TRIAL,
        patches=(PATCH,),recompile_scanout=False,extra_sources={'osfmk/ipc/ipc_kmsg.c':source},
        extra_units=(('SweetFramebuffer',prior,'compile-SweetFramebuffer'),
                     ('gauguin_ui_trace_board',board,'compile-gauguin_ui_trace_board'),
                     ('ipc_kmsg',recipe,'compile-ipc_kmsg')))


def ipc_recipe(source, prior):
    out = BASE/'ipc-origin'
    cwd = ORIGIN/'build301-causal-trace/obj-gauguin-macos/DEVELOPMENT_ARM64_GAUGUIN/osfmk/DEVELOPMENT'
    flags = cwd/'.CFLAGS'
    original = cwd/'ipc_kmsg.o'
    require(load(prior)['input_pins'][str(original)]==sha(original), 'IPC baseline object differs')
    flag_text = flags.read_text().rstrip('\0')
    # replacecontents stores the original argv with spaces inside this value.
    macro = '-DCONFIG_NMBCLUSTERS=((1024 * 512) / MCLBYTES)'
    require(flag_text.count(macro)==1, 'IPC macro provenance differs')
    arguments = shlex.split(flag_text.replace(macro,shlex.quote(macro)))
    compiler = Path('/Library/Developer/CommandLineTools/usr/bin/clang')
    require('-DGAUGUIN' in arguments and '-mkernel' in arguments and
        arguments[arguments.index('-arch')+1]=='arm64', 'IPC compiler scope differs')
    argv = [str(compiler),'-c',*arguments[1:],'-Wno-conditional-uninitialized',
        '-Wno-shorten-64-to-32','-Wno-sign-conversion','-MD','-MP','-MF',
        str(cwd/'ipc_kmsg.d'),'-o',str(original),str(source)]
    out.mkdir()
    replay = out/'original-ipc_kmsg.o'
    replay_argv = [str(replay) if arg==str(original) else
        str(replay.with_suffix('.d')) if arg==str(cwd/'ipc_kmsg.d') else arg for arg in argv]
    subprocess.run(replay_argv,cwd=cwd,check=True,capture_output=True,timeout=90)
    def code(obj):
        return subprocess.check_output(['xcrun','otool','-s','__TEXT','__text',str(obj)]).splitlines()[2:]
    text = code(original)
    require(text and text==code(replay), 'pinned IPC instructions failed reproduction')
    path = out/'result.json'
    save(path,dict(state='0370-IPC-machine-code-reproduced',steps=[
        dict(name='compile-ipc_kmsg',argv=argv,cwd=str(cwd),exit=0)],baseline_machine_code_matches=True,
        input_pins={str(item):sha(item) for item in
            (source,original,compiler,flags,cwd/'meta_features.h',cwd/'ipc_kmsg.d',replay)}))
    return path


def package():
    check_budget()
    pack = import_module('package-frame344')
    manifest = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(manifest),base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P370/'trial-plan.json')['boot_command'],'0371 boot arguments differ')
    image['kernel_manifest'] = str(manifest)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P370/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P370/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame371-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P370/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
        max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',str(REFERENCE/'restored-capture/result.json'),
        '--out',str(BASE/'slot-capture'),'--reuse-data-from',str(P370/'slot-capture')],
        check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
        maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P370,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    r = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in r.items() if k not in ('input_pins','checks')} | {'checks':len(r['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P370/'trial-plan.json'
    original = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame371-image.json',
        'edr-native/result.json'))
    install = BASE/'slot-delta/install-plan.json'
    slots = load(install)
    require(native['state']=='0371-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
        native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
        {Path(p).name for p in (*native['object_replacements'],*native['object_replacements'].values())}=={'SweetFramebuffer.o','gauguin_ui_trace_board.o','ipc_kmsg.o'} and
        sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
        native['identity']==image['build_identity']==edr['kernel_identity'],'0371 linked changes differ')
    require(image['command']==original['boot_command'] and sha(image['image'])==image['image_sha256'] and
        image['image_bytes']==Path(image['image']).stat().st_size and slots['trial']==TRIAL and
        slots['changed_ranges']==12 and slots['core_sha256']==original['owned_core_sha256'] and
        slots['rows']['eagl']['new_file_sha256']==original['SB_sha256'] and
        slots['rows']['c4']['new_file_sha256']==original['C4_sha256'] and
        slots['rows']['c4']['data_extents']==C4_EXTENTS and
        slots['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
        sha(BASE/'metadata-snapshot/misc-original.bin')==original['misc_before_sha256'],
        '0371 kernel, helper or userspace baseline differs')
    files = {k:current['files'][k]['bytes'] for k in original['log_capture']['sizes']}
    raw = load(REFERENCE/'kernel-IO-analysis.json')['ring']['total_bytes']
    require(sum(files.values())==LOG_BYTES and raw+PAIR_RECORDS*144+1024<4_194_304 and
        19_900<original['frame_capture']['records'], '0371 capture reserve too small')
    capture = dict(original['log_capture'],measured_baseline_bytes=LOG_BYTES,max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,
        sizes=files,reference_kernel_log_bytes=raw,reserved_frame_console_bytes=4_194_304-raw,
        previous_verified_suffix_bytes=LOG_BYTES-original['log_capture']['measured_baseline_bytes'])
    del original['swap_wait']
    return dict(original,state='prepared-frame371-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(install),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],log_capture=capture,
        optimization='Localize time to first SwapBegin with exact kernel message transit receipts.',
        performance_comparison='Keep the 0370 Core, C4, workload and physical CRC scoring.',
        producer_transport=dict(maximum_pairs=PAIR_RECORDS,maximum_tagged_sends=MAX_SOURCE_SENDS,
            key='authenticated process generation and live kernel message',
            source='SpringBoard',receiver='backboardd',window_seconds=45,
            sends_injected=0,extra_GPU_calls=0,records_payload=False,
            blocking_lock=False,changes_dispatch_or_return=False))


def storage(plan):
    prior = load(P370/'storage-bound-370.json')
    parts = {k:v for k,v in prior['components'].items() if k!='swap_wait_summary'}
    parts['producer_transport_summary'] = 1_000_000
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
        '0371 runtime exceeds reservation')
    return dict(prior,state='bounded0371-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
        fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    prior,install = (load(p/'slot-delta/install-plan.json') for p in (P370,BASE))
    require({n for n in install['rows'] if install['rows'][n]['new_file_sha256']!=
        prior['rows'][n]['new_file_sha256']}=={'admission'}, '0371 userspace change outside EDR identity')
    model = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(model['all_model_IO_writes_memory_only'] and model['install_ranges']==12 and
        model['all_restore_partial_write_points']==17 and
        model['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
        'split-tail-became-unallocated-refused-before-write' in model['checks'] and
        host['patch_sha256']==sha(PATCH) and host['projection_passed'] and
        host['state']=='0371-producer-transport-cross-compiled-and-modeled' and
        not (host['device_writes'] or host['device_boots']),'0371 frame or restore model incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P370,HEADER,plan)


def pins():
    extra = [RETIREMENT,REFERENCE/'scoped-swap-timing-0370.json',
        REFERENCE/'frame-pacing-0369-0370.json']
    names = ('ipc-origin/result.json','native-kernel/build-manifest.json','frame371-image.json','edr-native/result.json',
        'core-native/result.json','c4-native/result.json','restore-model/result.json')
    return shared.pins(base=BASE,prior=P370,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,extra=extra,
        artifacts=[HOST, *(BASE/name for name in names)])


def freeze():
    return shared.freeze(base=BASE,prior=P370,expected=expected_plan,validate=criteria,storage_bound=storage,
        pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
        preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {f.__name__:f for f in (build,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=steps)
    print(json.dumps(steps[cli.parse_args().step](),indent=2))
