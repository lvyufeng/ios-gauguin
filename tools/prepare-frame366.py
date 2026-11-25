#!/usr/bin/env python3
"""Build and freeze the issued-writer and lock-only retry candidate."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import (BASE, DOC, HEADER, LOG_SUFFIX, MAIN, METADATA_CAP, MODEL, P360, P363, P365,
    PATCH, REF365, REFERENCE, REPORT_BYTES, RESERVE, SAVED_SLOTS, TRIAL, WORK,
    check_archive, check_baseline, check_budget, expected_plan, load, require, sha)

shared = import_module('prepare-frame349')
save = shared.stage.save


def build():
    check_budget()
    origin = P360/'native-kernel/build-manifest.json'
    terms = tuple((name,origin,'compile-'+name) for name in ('GauguinGPU','SweetFramebuffer'))
    import_module('build-frame347').link_scanout(P363/'native-kernel/build-manifest.json',BASE/'native-kernel',
        parent_trial='0363',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,extra_units=terms)
    manifest = load(BASE/'native-kernel/build-manifest.json')
    return {key:manifest[key] for key in ('state','identity','kernel_bytes','kernel_sha256','object_replacements')}


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = load(BASE/'native-kernel/build-manifest.json')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=BASE,trial=TRIAL,
                            frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P365/'trial-plan.json')['boot_command'],'0366 boot flags changed')
    image['kernel_manifest'] = str(BASE/'native-kernel/build-manifest.json')
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P365/'edr-native/result.json')
    save(BASE/'edr-native/result.json',edr)
    (BASE/'core-native').mkdir()
    shutil.copyfile(P365/'core-native/result.json',BASE/'core-native/result.json')
    save(BASE/'frame366-image.json',image)
    return dict(image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
                CA_and_Core_identities_unchanged=True,EDR_identity_only=edr['identity_only_retarget'])


def capture():
    check_budget()
    current = check_baseline()
    slots = BASE/'slot-capture'
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',str(REFERENCE),
        '--out',str(slots),'--reuse-data-from',str(SAVED_SLOTS)],check=True,capture_output=True,timeout=300)
    metadata = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
        maximum_compressed_bytes=METADATA_CAP)
    require(metadata['root_header_sha256']==HEADER and not (metadata['device_writes'] or metadata['device_boots']),
            '0366 read-only snapshot differs')
    return dict(files=len(current['files']),log_bytes=current['combined_log_bytes'],
        metadata_bytes=metadata['compressed_bytes'],device_writes=0)


def delta():
    check_budget()
    result = shared.stage.delta(BASE,P365,trial=TRIAL,header=HEADER,baseline=REFERENCE)
    expected_plan()
    return result


def model():
    check_budget()
    r = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(r['checks']),failure_points=r['all_restore_partial_write_points'],device_writes=0)


def host():
    from frame364_analysis import measure, score, trace
    from frame366_retry import analyze, LOCK_RETRY, PROBE, exact_writer_tables, issued_probe
    from dataclasses import replace

    check_archive()
    archive = load(REF365/'CA-timing-0364-0365.json')['current_0365']
    replay = measure(REF365)
    require(json.loads(json.dumps(replay))==archive,'0366 analyzer changed the 0365 control')
    raw = (REF365/'kernel.log').read_text()
    rows,_,_,_ = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    writers = exact_writer_tables(rows)
    lock_busy = next(row for row in rows[PROBE] if row.flags==1 and
                     row.a in writers[1] and writers[1][row.a].tick<=row.c)
    early = replace(lock_busy,kind=LOCK_RETRY)
    issued_probe(early,*writers)
    modeled = rows | {LOCK_RETRY:[early],PROBE:[]}
    expiry = analyze(modeled,{}, {})
    require(expiry['actual_query_count']==0 and expiry['lock_only_rearm_count']==1 and
            expiry['reserved_rearms_without_following_probe']==1,'expired lock try was counted as a query')
    candidate = import_module('run-frame366-trial')
    try:
        candidate.after_restore(BASE,expected_plan(),dict(restored=True,independent_restore_verified=False,
            static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'wrong 0366 restore gate')
    else:
        raise ValueError('0366 analysis accepted no independent proof')
    host_model = subprocess.run([str(MODEL.parent/'probe-model')],capture_output=True,text=True,check=True,timeout=60)
    require('bounded workloop probe' in host_model.stdout and load(MODEL)['patch_sha256']==sha(PATCH),
            'native probe model or patch changed')
    out=BASE/'frame-host'
    out.mkdir()
    report=dict(state='0366-exact-writer-lock-retry-and-restore-gate-modeled',
        probe_model_sha256=sha(MODEL.parent/'probe-model'),patch_sha256=sha(PATCH),
        baseline_slow_new_and_repeated=[71,6],expired_lock_only_try_kept_separate=True,
        restore_precedes_analysis=True,device_commands=0)
    save(out/'result.json',report)
    return report


def storage(plan):
    prior = load(P365/'storage-bound-365.json')
    require(sum(prior['components'].values())==prior['worst_case_bytes']<=RESERVE and
            prior['components']['matched_producer_and_motion_comparison']==REPORT_BYTES and
            plan['log_capture']['max_combined_log_bytes']==plan['log_capture']['measured_baseline_bytes']+LOG_SUFFIX,
            '0366 bounded comparison or log reserve differs')
    return dict(prior,state='bounded0366-runtime-batch',
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def criteria(plan):
    check_budget()
    install = load(BASE/'slot-delta/install-plan.json')
    prior = load(P365/'slot-delta/install-plan.json')
    require({name for name,row in install['rows'].items() if row['new_file_sha256']!=prior['rows'][name]['new_file_sha256']}
            =={'admission'},'0366 changes a user file besides the kernel identity retarget')
    model,host,slots,snapshot = (load(BASE/name) for name in
        ('restore-model/result.json','frame-host/result.json','slot-capture/result.json','metadata-snapshot/result.json'))
    require(model['all_model_IO_writes_memory_only'] and len(model['checks'])==47 and
            model['all_restore_partial_write_points']==17 and
            model['maximum_actual_model_restore_bytes']<=plan['maximum_restore_userdata_bytes'] and
            model['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            host['state']=='0366-exact-writer-lock-retry-and-restore-gate-modeled' and host['restore_precedes_analysis'] and
            len(slots['reused_original_data'])==6 and slots['baseline_sha256']==sha(REFERENCE) and
            snapshot['root_header_sha256']==HEADER and snapshot['compressed_bytes']<=METADATA_CAP and
            not any(r['device_writes'] or r['device_boots'] for r in (slots,snapshot)),
            '0366 signatures, aperture or recovery models differ')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P365,HEADER,plan)


def pins():
    artifacts = tuple(BASE/name for name in ('native-kernel/build-manifest.json','frame366-image.json',
        'core-native/result.json','edr-native/result.json','frame-host/result.json','restore-model/result.json'))
    extra = [REF365/name for name in ('frame-pacing-0364-0365.json','CA-timing-0364-0365.json',
        'kernel-IO-analysis.json','springboard-new.log')]
    extra += [P365/'slot-delta/install-plan.json',MODEL,MODEL.parent/'probe-model',
        MAIN/'research/tmp/0366-storage-retirement/verified-retirement-manifest.json']
    extra.extend(Path(path) for path in load(BASE/'slot-capture/result.json')['reused_original_data'].values())
    return shared.pins(base=BASE,prior=P365,doc=DOC,patch=PATCH,reference=REF365,trial=TRIAL,
        extra=extra,artifacts=artifacts)


def freeze():
    return shared.freeze(base=BASE,prior=P365,expected=expected_plan,validate=criteria,
                         storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,host,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
