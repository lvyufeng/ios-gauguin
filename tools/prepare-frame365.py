#!/usr/bin/env python3
"""Build, model and freeze the bounded 0365 CA timing candidate."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame365_scope import (BASE, DOC, HEADER, LOG_SUFFIX, MAIN, METADATA_CAP, P364, PATCH, REF364,
    REFERENCE, REPORT_BYTES, RESERVE, SAVED_SLOTS, TRIAL, WORK, check_archive, check_baseline, check_budget,
    expected_plan, load, require, sha)

shared = import_module('prepare-frame349')
save = shared.stage.save


def build():
    check_budget()
    compiler = import_module('build-first-frame359')
    source = WORK/'graphics/gauguin-sb-rate-trace/SBRateTrace.m'
    install = P364/'slot-delta/install-plan.json'
    baseline = load(install)['rows']['eagl']
    pins = {str(path):sha(path) for path in (source,*sorted(source.parent.glob('SB*.h')),
        compiler.SDK/'SDKSettings.json',compiler.CLANG,install,Path(compiler.__file__))}
    out = BASE/'sb-native'
    out.mkdir()
    binary = out/'libGauguinSBRateTrace.dylib'
    args = [str(compiler.CLANG),'-target','arm64-apple-ios16.0','-isysroot',str(compiler.SDK),
        '-DGAUGUIN_SB_CA_TIMING=1','-std=gnu11','-O2','-fno-objc-arc','-Wall','-Wextra','-Werror',
        '-dynamiclib','-framework','Foundation','-framework','QuartzCore','-framework','UIKit','-lobjc',
        '-Wl,-install_name,'+baseline['path'],str(source),'-o',str(binary)]
    for name,command in [('compile',args),('sign',['codesign','--force','--sign','-',str(binary)]),
            ('verify',['codesign','--verify','--strict',str(binary)]),('loads',['otool','-L',str(binary)])]:
        with (out/(name+'.log')).open('x') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
    require(baseline['path'] in (out/'loads.log').read_text() and
            binary.stat().st_size<=min(94_208,baseline['data_blocks']*4096) and
            b'GAUGUIN SB STACK: active version=315' in binary.read_bytes() and
            b'SWEET SB CA365: active' in binary.read_bytes(), '0365 slot size or collector flags differ')
    imports,abi_pins = compiler.verify_imports(binary,
        additional_imports={('_class_getClassMethod','/usr/lib/libobjc.A.dylib',False)})
    require(all(sha(path)==digest for path,digest in pins.items()),'0365 sources or compiler changed')
    result = dict(state='0365-passthrough-CA-timing-signed',binary=str(binary),binary_sha256=sha(binary),
        bytes=binary.stat().st_size,platform=import_module('build-hakios-metal').ios_version(binary),
        signature_verified=True,runtime_imports_qualified=True,stack_sampling_version=315,
        install_name=baseline['path'],input_pins=pins|abi_pins,imports=imports,compiler_argv=args,device_commands=0)
    save(out/'result.json',result)
    return {k:v for k,v in result.items() if k not in ('input_pins','imports','compiler_argv')}


def capture():
    check_budget()
    current = check_baseline()
    slots = BASE/'slot-capture'
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',str(REFERENCE),
        '--out',str(slots),'--reuse-data-from',str(SAVED_SLOTS)],check=True,capture_output=True,timeout=300)
    metadata = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
        maximum_compressed_bytes=METADATA_CAP)
    require(metadata['root_header_sha256']==HEADER and not (metadata['device_writes'] or metadata['device_boots']),
            '0365 read-only snapshot differs')
    return dict(files=len(current['files']),log_bytes=current['combined_log_bytes'],
        metadata_bytes=metadata['compressed_bytes'],device_writes=0)


def delta():
    check_budget()
    for directory in ('core-native','edr-native'):
        (BASE/directory).mkdir()
        receipt = Path(directory)/'result.json'
        shutil.copyfile(P364/receipt,BASE/receipt)
    result = shared.stage.delta(BASE,P364,trial=TRIAL,header=HEADER,baseline=REFERENCE,
        sb_receipt=BASE/'sb-native/result.json')
    expected_plan()
    return result


def model():
    check_budget()
    r = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(r['checks']),failure_points=r['all_restore_partial_write_points'],device_writes=0)


def host():
    from frame365_analysis import attribute, parse
    from frame364_analysis import measure

    check_archive()
    runner = import_module('run-frame365-trial')
    archive = load(REF364/'motion-identity-0363-0364.json')['current_0364']
    replay = measure(REF364)
    require(json.loads(json.dumps(replay))==archive,'0365 host replay changed the 0364 baseline')
    placement = load(P364/'deadline-budget-0363-0364.json')['0364']
    miss = next(row for row in replay['frontend']['details'] if
        row['stroke']>=3 and row['returned_main_callback'] and row['next_swap_within_stroke_tail'])
    begin = miss['returned_main_callback']['returned_us']
    end = miss['deadline_ns']//1000+1
    active = 'SWEET SB CA365: active commit=1 flush=1 max_rows=8192\n'
    call = f'SWEET SB CA365: method=flush entered_us={begin} left_us={end} returned=1 depth=1 caller=UIKitCore+0x1\n'
    result = attribute(parse(active+call),replay['frontend'],placement)
    require(result['warm']['CA_spanning_cutoff']>=1 and result['call_counts']=={'flush':1} and
            not parse(active)['calls'],'0365 phase or empty-observation handling differs')
    for bad in (active+active,active+call.replace('returned=1','returned=0'),call):
        try:
            parse(bad)
        except ValueError:
            pass
        else:
            raise ValueError('invalid CA timing passed')
    try:
        runner.after_restore(BASE,expected_plan(),dict(restored=True,independent_restore_verified=False,
            static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'wrong 0365 restore gate')
    else:
        raise ValueError('0365 accepted analysis before readback')
    out = BASE/'frame-host'
    out.mkdir()
    report = dict(state='0365-reference-and-CA-timing-model-qualified',modeled_trace_only=True,
        original_strokes=13,slow_reference_copies=75,invalid_CAs_rejected=3,
        readback_gate_checked=True,device_commands=0)
    save(out/'result.json',report)
    return report


def storage(plan):
    prior = load(P364/'storage-bound-364.json')
    require(sum(prior['components'].values())==prior['worst_case_bytes']<=RESERVE and
            prior['components']['matched_producer_and_motion_comparison']==REPORT_BYTES and
            plan['log_capture']['maximum_additional_CA_log_bytes']+plan['log_capture']['previous_verified_suffix_bytes']<LOG_SUFFIX,
            '0365 bounded comparison or CA log reserve differs')
    return dict(prior,state='bounded0365-runtime-batch',
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def criteria(plan):
    check_budget()
    delta = load(BASE/'slot-delta/install-plan.json')
    prior = load(P364/'slot-delta/install-plan.json')
    require({name for name,row in delta['rows'].items() if row['new_file_sha256']!=prior['rows'][name]['new_file_sha256']}
            =={'eagl'},'0365 changes a file besides the timing probe')
    model,host,slots,snapshot = (load(BASE/name) for name in
        ('restore-model/result.json','frame-host/result.json','slot-capture/result.json','metadata-snapshot/result.json'))
    require(model['all_model_IO_writes_memory_only'] and len(model['checks'])==47 and
            model['all_restore_partial_write_points']==17 and
            model['maximum_actual_model_restore_bytes']<=plan['maximum_restore_userdata_bytes'] and
            model['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            host['state']=='0365-reference-and-CA-timing-model-qualified' and host['readback_gate_checked'] and
            len(slots['reused_original_data'])==6 and slots['baseline_sha256']==sha(REFERENCE) and
            snapshot['root_header_sha256']==HEADER and snapshot['compressed_bytes']<=METADATA_CAP and
            not any(r['device_writes'] or r['device_boots'] for r in (slots,snapshot)),
            '0365 archive replay, signature or restore model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P364,HEADER,plan)


def pins():
    artifacts = tuple(BASE/name for name in ('sb-native/result.json','core-native/result.json',
        'edr-native/result.json','frame-host/result.json','restore-model/result.json'))
    extra = [REF364/name for name in ('frame-pacing-0363-0364.json','motion-identity-0363-0364.json',
        'kernel-IO-analysis.json','springboard-new.log')]
    extra += [P364/'slot-delta/install-plan.json',P364/'deadline-budget-0363-0364.json',
        MAIN/'research/tmp/0365-storage-retirement/verified-retirement-manifest.json']
    extra.extend(Path(path) for path in load(BASE/'slot-capture/result.json')['reused_original_data'].values())
    return shared.pins(base=BASE,prior=P364,doc=DOC,patch=PATCH,reference=REF364,trial=TRIAL,
        extra=extra,artifacts=artifacts)


def freeze():
    return shared.freeze(base=BASE,prior=P364,expected=expected_plan,validate=criteria,
                         storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,capture,delta,model,host,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
