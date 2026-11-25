#!/usr/bin/env python3
"""Prepare and review the one-shot 0359 first-frame observation."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import frame352_display
from frame358_display import KINDS
from frame359_frontend import analyze, PREFIX, RATE, STACK
from frame359_scope import BASE, DOC, HEADER, LOG_SUFFIX, MAIN, P358, REF358, RESERVE, WORK
from frame359_scope import check_0358, expected_plan, load, require, sha, SUCCESS

shared = import_module('prepare-frame349')
save = shared.stage.save


def capture():
    check_0358()
    reference = REF358/'restored-capture/result.json'
    restored = load(reference)
    current_path = BASE/'current-root-capture/result.json'
    profile = load(P358/'capture-profile.json')
    profile.update(out=str(current_path.parent),phase='before-boot',expected_header_sha256=HEADER,
                   max_combined_log_bytes=restored['combined_log_bytes']+LOG_SUFFIX)
    current = load(current_path) if current_path.exists() else import_module('capture-core342-root').capture(
        profile,save_files=False)
    require(current['root_header_sha256']==restored['root_header_sha256']==HEADER and
            current['files']==restored['files'] and current['directories']==restored['directories'] and
            not current['device_writes'],'0359 read-only TWRP baseline differs')
    slots = BASE/'slot-capture/result.json'
    if not slots.exists():
        subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
                        '--baseline',str(reference),'--out',str(slots.parent)],check=True,
                       capture_output=True,timeout=300)
    require(load(slots)['baseline_sha256']==sha(reference),'0359 six-slot baseline differs')
    metadata = BASE/'metadata-snapshot/result.json'
    snapshot = load(metadata) if metadata.exists() else import_module('capture-core342-metadata').capture(
        metadata.parent,HEADER,trial='0359')
    require(snapshot['root_header_sha256']==HEADER and not snapshot['device_writes'],'0359 metadata differs')
    return dict(reference_files=len(current['files']),log_bytes=current['combined_log_bytes'],
                metadata_bytes=snapshot['compressed_bytes'],device_writes=0)


def delta():
    for name in ('core-native','edr-native'):
        dest = BASE/name
        dest.mkdir()
        save(dest/'result.json',load(P358/name/'result.json'))
    return shared.stage.delta(BASE,P358,trial='0359',header=HEADER,
        baseline=REF358/'restored-capture/result.json',core_logical=7_992_224,
        sb_receipt=BASE/'sb-native/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0359')
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')}


def host():
    check_0358()
    out = BASE/'frame-host'
    out.mkdir()
    stack = load(BASE/'stack-host/result.json')
    require(stack['state']=='passed-bounded-collector-and-live-own-process-Mach' and stack['inputs_unchanged'] and
            all(sha(name)==digest for name,digest in stack['input_pins'].items()),'stack policy was not qualified')
    tests = ('test_frame359_frontend.py','test_sb_stack_log.py','test_sb_rate_log.py')
    for name in tests:
        result = subprocess.run([sys.executable,str(WORK/'tests'/name)],check=True,capture_output=True,text=True)
        (out/(name+'.log')).write_text(result.stdout+result.stderr)
    primary = frame352_display.analyze((REF358/'kernel.log').read_text(),
        load(REF358/'frame-scanout-analysis.json'),extra_kinds=KINDS)
    reference = analyze(REF358,display=primary)
    second = reference['strokes'][1]
    require(len(reference['strokes'])==13 and second['active_swaps']==second['active_Core_enqueues']==0 and
            second['longest_touch']['duration_us']==258_289 and second['first_CRC_new_output']['phase']=='release' and
            second['first_guarded_swap_linked_CRC']['edge_bounds_ns']==second['first_CRC_new_output']['edge_bounds_ns'],
            '0358 first-frame replay differs')
    save(out/'reference-first-frame.json',reference)
    save(out/'reference-display.json',primary)
    report = dict(first_frame_observer_tests=5,legacy_observer_and_sampler_checks=True,
                  exact_0358_trace_reproduced=True,active_strokes=13,second_swipe=second,
                  device_commands=0)
    save(out/'result.json',report)
    return {k:v for k,v in report.items() if k!='second_swipe'}


def controls():
    plan = expected_plan()
    path = BASE/'frame-host'
    runner = import_module('run-frame359-trial')
    try:
        runner.after_restore(path,plan,dict(restored=True,independent_restore_verified=False,
            static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'wrong before-readback failure')
    else:
        raise ValueError('first-frame analysis started before independent readback')
    fixture = import_module('check-core342-pipeline')
    scenarios = []
    for scenario in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                     'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        fixture.control_fixture(path,plan,scenario,scenarios)
    save(path/'control-models.json',dict(scenarios=scenarios,analysis_requires_independent_readback=True))
    return dict(scenarios=len(scenarios),analysis_requires_independent_readback=True)


def replay():
    """Exercise the restored analyzer on the saved 0358 streams with modeled observer rows."""
    plan = expected_plan()
    runner = import_module('run-frame359-trial')
    text = '\n'.join(line for line in (REF358/'springboard-new.log').read_text().splitlines() if STACK.PREFIX not in line)
    parsed = RATE.parse(text)
    starts = {r['id']:r for r in parsed['rows'] if r['kind']=='input-begin'}
    rows = [PREFIX+'active input=1 ca_commit=1 ca_flush=1 max_rows=8192',
            STACK.PREFIX+'active '+' '.join(f'{k}={v}' for k,v in STACK.CALLBACK_CONFIG.items())]
    for row in parsed['rows']:
        if row['kind']!='input-end':
            continue
        entry = starts[row['id']]
        if not entry['flags']&8 and 220_000_000<=entry['us']<270_000_000:
            rows.append(f"{PREFIX}input id={row['id']} entered_us={entry['us']} left_us={row['us']} returned={int(row['returned'])}")
    with TemporaryDirectory(prefix='0359-host-analysis-',dir=BASE) as temporary:
        path = Path(temporary)
        for name in ('kernel.log','kernel.log.bin','backboardd.log.current'):
            (path/name).symlink_to(REF358/name)
        (path/'springboard-new.log').write_text(text+'\n'+'\n'.join(rows)+'\n')
        prior = load(REF358/'result.json')
        result = {key:prior[key] for key in ('restored','independent_restore_verified','static_root_comparison_passed',
                                            'springboard_log_prefix_preserved','other_log_prefix_preserved')}
        proof = load(REF358/'independent-restore.json')
        save(path/'independent-restore.json',dict(proof,install_plan_sha256=plan['install_plan_sha256']))
        runner.after_restore(path,plan,result,load(REF358/'fresh-before/result.json'),0)
        require(result['state']==SUCCESS,'restored analyzer fixture failed: '+str({
            k:result.get(k) for k in ('state','first_frame_error','frame_capture_error','frame_measurement','stack_analysis')}))
        second = result['second_swipe']
        require(result['dpu_new_content_FPS_qualified'] and result['strict_new_frame_rate_bounds']==prior['strict_new_frame_rate_bounds']
                and second['active_swaps']==second['active_Core_enqueues']==0 and
                second['longest_touch_original']['left_us']-second['longest_touch_original']['entered_us']==258_289 and
                result['first_frame']['targeted_stack_attempts']==0,'modeled observer changed the saved output comparison')
    report = dict(state='0359-full-restored-analysis-host-pass',synthetic_observer_rows=True,
                  device_commands=0,verified_after_restore_state=SUCCESS)
    save(BASE/'frame-host/full-analysis-fixture.json',report)
    return report


def storage(plan):
    bound = load(P358/'storage-bound-358.json')
    bound['components']['first_frame_comparison'] = 1_000_000
    worst = sum(bound['components'].values())
    require(worst<=RESERVE and plan['log_capture']['maximum_suffix_bytes']==LOG_SUFFIX,
            '0359 total runtime output exceeds reserve')
    return dict(bound,state='bounded0359-runtime-batch',worst_case_bytes=worst,
                fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'])


def criteria(plan):
    previous = load(P358/'trial-plan.json')
    allowed = {'state','trial','parent_trial_plan_sha256','root_header_sha256','install_plan_sha256',
               'misc_before_sha256','SB_sha256','unchanged_337_SB','new_kernel_builds','new_boot_images',
               'diagnostic_only','performance_candidate','main_thread_sampling','first_frame_observation',
               'optimization','performance_comparison','log_capture'}
    require({k for k in plan.keys()|previous.keys() if plan.get(k)!=previous.get(k)}<=allowed and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442 and
            plan['main_thread_sampling']['max_samples']==8 and plan['process_sampling']['max_register_samples']==1024,
            '0359 changed an unrelated trial effect')
    receipt = load(BASE/'frame-host/result.json')
    controls = load(BASE/'frame-host/control-models.json')
    replayed = load(BASE/'frame-host/full-analysis-fixture.json')
    rollback = load(BASE/'restore-model/result.json')
    require(receipt['active_strokes']==13 and receipt['first_frame_observer_tests']==5 and
            receipt['exact_0358_trace_reproduced'] and len(controls['scenarios'])==9 and
            replayed['state']=='0359-full-restored-analysis-host-pass' and replayed['synthetic_observer_rows'] and
            controls['analysis_requires_independent_readback'] and rollback['all_model_IO_writes_memory_only'] and
            len(rollback['checks'])==47 and rollback['all_restore_partial_write_points']==17 and
            rollback['maximum_actual_model_restore_bytes']<=10_330_112,'0359 host or rollback checks incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P358,HEADER,plan)


def pins():
    ready = P358/'ready.json'
    pinned = dict(load(ready)['input_pins'])
    files = [WORK/name for name in subprocess.check_output(
        ['git','ls-files','tools/*.py','tools/*.sh','graphics/gauguin-sb-rate-trace/*','tests/*sb*','tests/*359*'],
        cwd=WORK,text=True).splitlines()]
    files += [ready,DOC,Path(__file__),MAIN/'tools/storage-budget.py',
              P358/'trial-plan.json',P358/'storage-bound-358.json',P358/'slot-delta/install-plan.json']
    files += [REF358/name for name in ('kernel.log','springboard-new.log','result.json',
              'independent-restore.json','restored-capture/result.json','frame-scanout-analysis.json',
              'core-wait-execution-analysis.json')]
    files += [BASE/name for name in ('current-root-capture/result.json','build-storage-admission.json',
              'core-native/result.json','edr-native/result.json')]
    for folder in ('slot-delta','slot-capture','metadata-snapshot','restore-model','frame-host','sb-native','stack-host'):
        files.extend(path for path in (BASE/folder).rglob('*') if path.is_file())
    for manifest in (BASE/'sb-native/result.json',BASE/'stack-host/result.json'):
        for name,digest in load(manifest)['input_pins'].items():
            require(pinned.setdefault(name,digest)==digest,'conflicting source pin '+name)
    for path in files:
        digest = sha(path)
        require(pinned.setdefault(str(path),digest)==digest,'inherited pin changed '+str(path))
    for name,digest in pinned.items():
        require(sha(name)==digest,'pinned artifact differs '+name)
    return pinned


def freeze():
    return shared.freeze(base=BASE,prior=P358,expected=expected_plan,validate=criteria,
                         storage_bound=storage,pin_inputs=pins)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__))


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (capture,delta,model,host,controls,replay,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
