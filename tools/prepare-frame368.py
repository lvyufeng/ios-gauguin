#!/usr/bin/env python3
"""Build and freeze the Gauguin read-only inherited-display route trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import BATCH, CHANGES, FLAGS as PRIOR_FLAGS, LOG_SUFFIX, MAIN, METADATA_CAP
from frame366_scope import REPORT_BYTES, RESERVE, WORK, load, require, sha


TRIAL = '0368'
BASE = WORK/'research/tmp/frame-368'
P366 = MAIN/'research/tmp/gauguin-issued-probe-worktree-20261121/research/tmp/frame-366'
REF366 = P366/'execution'
P367 = MAIN/'research/tmp/gauguin-source-route-worktree-20261121/research/tmp/frame-367'
REF367 = P367/'execution'
REFERENCE = REF367/'restored-capture/result.json'
DOC = WORK/'docs/gauguin-frame-368-trial-20261121.md'
PATCH = WORK/'xnu/patches/0279-gauguin-keep-permanent-scanout-read-mappings.patch'
SOURCE = 'bsd/dev/gauguin_ui_trace_board.c'
HEADER = '7368627599fe8ac48ee497f78d6061c8f43059cde3bda29dd7bee61b226af53d'
RESTORED_LOG_BYTES = 172_210_511
RETIREMENT = MAIN/'research/tmp/0368-storage-retirement/verified-retirement-manifest.json'
BATCH_BYTES = BATCH + 45_000_000
SUCCESS = '0368-inherited-source-route-observed-root-restored'
FLAGS = tuple(flag for flag in PRIOR_FLAGS if not flag.startswith('allow_0366')) + (
    'allow_0368_one_same_60Hz_boot_and_read_only_route',)
shared = import_module('prepare-frame349')
save = shared.stage.save


def check_budget():
    r = load(BASE/'build-storage-admission.json')
    require(r['admitted'] and r['planned_batch_bytes']==BATCH_BYTES and
        r['current_accounted_bytes']+BATCH_BYTES<=r['limit_bytes'], '0368 whole batch not admitted')


def check_baseline():
    terminal,proof = (REF367/name for name in ('result.json','independent-restore.json'))
    require(sha(terminal)=='cd4945dcc95c2dce11dcbab62a748d2e0b9b4747ff5a0145bd5d6dd5609bd0bf' and
        sha(proof)=='02954ae1375a1a290fa2cffb8e180ceea19fc7f56d038d80dfca19fbd64a85d3',
        '0367 terminal provenance differs')
    result = load(terminal)
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
        all(result['other_log_prefix_preserved'].values()), '0367 independent recovery incomplete')
    current,previous = load(BASE/'current-root-capture/result.json'),load(REFERENCE)
    require(current['files']==previous['files'] and current['directories']==previous['directories'] and
        current['root_header_sha256']==previous['root_header_sha256']==HEADER and len(current['files'])==31 and
        current['combined_log_bytes']==previous['combined_log_bytes']==RESTORED_LOG_BYTES and
        not current['device_writes'], '0368 live read-only baseline differs')
    return current


def build():
    check_budget()
    unit = 'gauguin_ui_trace_board'
    extra = ((unit,P367/'native-kernel/build-manifest.json','compile-'+unit),)
    import_module('build-frame347').link_scanout(P367/'native-kernel/build-manifest.json',BASE/'native-kernel',
        parent_trial='0367',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,extra_units=extra)
    applied = (BASE/'native-kernel/source'/SOURCE).read_text()
    require('scan367_poll(frame)' in applied and 'ml_io_unmap' not in applied,
        '0368 route and permanent mapping change did not apply')
    r = load(BASE/'native-kernel/build-manifest.json')
    return {key:r[key] for key in ('state','identity','kernel_bytes','kernel_sha256','object_replacements')}


def package():
    check_budget()
    pack = import_module('package-frame344')
    build = load(BASE/'native-kernel/build-manifest.json')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),build,base=BASE,trial=TRIAL,
                             frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P367/'trial-plan.json')['boot_command'],'0368 boot arguments changed')
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P367/'edr-native/result.json')
    save(BASE/'edr-native/result.json',edr)
    (BASE/'core-native').mkdir()
    shutil.copyfile(P367/'core-native/result.json',BASE/'core-native/result.json')
    save(BASE/'frame368-image.json',image)
    return dict(image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],EDR_identity_only=edr['identity_only_retarget'])


def capture():
    check_budget()
    previous = load(P367/'capture-profile.json')
    path = BASE/'current-root-capture'
    profile = dict(previous,out=str(path.relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=RESTORED_LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    current = check_baseline()
    slots = BASE/'slot-capture'
    prior_slots = P367/'slot-capture'
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',str(REFERENCE),
        '--out',str(slots),'--reuse-data-from',str(prior_slots)],check=True,capture_output=True,timeout=300)
    snapshot = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
        maximum_compressed_bytes=METADATA_CAP)
    require(snapshot['root_header_sha256']==HEADER and not (snapshot['device_writes'] or snapshot['device_boots']),
        '0368 read-only snapshot differs')
    return dict(files=len(current['files']),log_bytes=current['combined_log_bytes'],
        metadata_bytes=snapshot['compressed_bytes'],device_writes=0)


def delta():
    check_budget()
    check_baseline()
    return shared.stage.delta(BASE,P367,trial=TRIAL,header=HEADER,baseline=REFERENCE)


def model():
    check_budget()
    r = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(r['checks']),failure_points=r['all_restore_partial_write_points'],device_writes=0)


def expected_plan():
    current = check_baseline()
    prior = P367/'trial-plan.json'
    original = load(prior)
    plan = dict(original)
    image, build, edr = (load(BASE/name) for name in ('frame368-image.json','native-kernel/build-manifest.json',
                                                    'edr-native/result.json'))
    install = BASE/'slot-delta/install-plan.json'
    delta = load(install)
    files = {name:current['files'][name]['bytes'] for name in original['log_capture']['sizes']}
    require(build['state']=='0368-native-ARM64-linked' and build['baseline_reproduced_except_uuid'] and
        build['inputs_unchanged'] and build['input_pins'][str(PATCH)]==sha(PATCH) and
        sha(build['kernel'])==build['kernel_sha256']==image['kernel_sha256'] and
        {Path(name).name for name in (*build['object_replacements'],*build['object_replacements'].values())}
            =={'gauguin_ui_trace_board.o'} and
        build['identity']==image['build_identity']==edr['kernel_identity'], '0368 kernel replacement scope differs')
    require(image['command']==original['boot_command'] and image['image_sha256']==sha(image['image']) and
        image['image_bytes']==Path(image['image']).stat().st_size and
        image['kernel_banner']==build['kernel_banner'] and delta['trial']==TRIAL and
        delta['core_sha256']==original['owned_core_sha256'] and
        delta['rows']['eagl']['new_file_sha256']==original['SB_sha256'] and
        delta['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
        sha(BASE/'metadata-snapshot/misc-original.bin')==original['misc_before_sha256'],
        '0368 image, Core, CA or original misc identity differs')
    raw_bytes = load(REF366/'kernel-IO-analysis.json')['ring']['total_bytes']
    require(sum(files.values())==RESTORED_LOG_BYTES and raw_bytes+4096<4_194_304,'0368 capture reserve differs')
    capture = dict(original['log_capture'],measured_baseline_bytes=RESTORED_LOG_BYTES,
        max_combined_log_bytes=RESTORED_LOG_BYTES+LOG_SUFFIX,sizes=files,
        previous_verified_suffix_bytes=RESTORED_LOG_BYTES-original['log_capture']['measured_baseline_bytes'],
        reference_kernel_log_bytes=raw_bytes)
    plan.update(state='prepared-frame368-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(install),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=build['identity'],kernel_banner=build['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        optimization='Keep the three permanent read-only route mappings until temporary reset.',
        performance_comparison='Use the same 0366 workload as a control, retaining independent score verdicts.',
        scanout_route=dict(read_only=True,attempts=8,stable_samples=3,additional_pages=3,register_writes=0,
            scanout_buffer_changes=0,extra_probe_ns_limit=1_000_000,per_snapshot_raw_words=80,
            mapping_lifetime='temporary-boot'),
        log_capture=capture)
    require({key for key in plan if plan[key]!=original.get(key)}<=CHANGES|{'scanout_route'},
        '0368 changes an unrelated execution capability')
    return plan


def storage(plan):
    prior = load(P367/'storage-bound-367.json')
    require(sum(prior['components'].values())==prior['worst_case_bytes']<=RESERVE and
        plan['log_capture']['measured_baseline_bytes']==RESTORED_LOG_BYTES and
        plan['log_capture']['max_combined_log_bytes']==RESTORED_LOG_BYTES+LOG_SUFFIX,
        '0368 measurement reserve differs')
    return dict(prior,state='bounded0368-runtime-batch',fresh_log_bytes=RESTORED_LOG_BYTES,
        log_cap_bytes=RESTORED_LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    install, prior = (load(folder/'slot-delta/install-plan.json') for folder in (BASE,P367))
    require({name for name,row in install['rows'].items() if row['new_file_sha256']!=prior['rows'][name]['new_file_sha256']}
        =={'admission'}, '0368 changes a user file outside the kernel identity retarget')
    model, host, slots = (load(BASE/name) for name in
        ('restore-model/result.json','frame-host/result.json','slot-capture/result.json'))
    require(model['all_model_IO_writes_memory_only'] and len(model['checks'])==47 and
        model['all_restore_partial_write_points']==17 and
        model['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
        model['maximum_actual_model_restore_bytes']<=plan['maximum_restore_userdata_bytes'] and
        host['boot_lifetime_readonly_mapping'] and host['native_sample_cases']>=5 and host['decoder_cases']>=6 and host['patch_sha256']==sha(PATCH) and
        len(slots['reused_original_data'])==6 and slots['baseline_sha256']==sha(REFERENCE) and
        not slots['device_writes'] and not slots['device_boots'], '0368 host or restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P367,HEADER,plan)


def pins():
    extra = [RETIREMENT,P366/'scoped-scan-audit.json',P366/'scoped-supply-audit.json',
        REF367/'independent-restore.json',REF367/'result.json',REF367/'kernel.log',
        REF367/'observer.log',REFERENCE,P367/'slot-delta/install-plan.json']
    extra += [path for path in (BASE/'frame-host').iterdir() if path.is_file()]
    extra += [Path(path) for path in load(BASE/'slot-capture/result.json')['reused_original_data'].values()]
    return shared.pins(base=BASE,prior=P367,doc=DOC,patch=PATCH,reference=REF366,trial=TRIAL,extra=extra)


def freeze():
    return shared.freeze(base=BASE,prior=P367,expected=expected_plan,validate=criteria,
                         storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
