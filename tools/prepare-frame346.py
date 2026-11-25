#!/usr/bin/env python3
"""Freeze reviewed 0346 effects and inputs before asking for device authorization."""
import argparse
from importlib import import_module
import json
from pathlib import Path
import re
import subprocess
import sys

from frame346_scope import ANALYSIS, BASE, DOC, HEADER, LOG_PATHS, MAIN, P345, POST_LOG_BYTES, RESERVE, WORK
from frame346_scope import expected_plan, load, require, sha

save = import_module('prepare-frame344').save


def recovery_probe():
    mode=(BASE/'dpu-readonly/recovery-kms-stdout.txt').read_text()
    rows=re.findall(r'^seq=(\d+) timestamp_us=(\d+)$',mode,re.M)
    require(len(rows)==14 and all(int(b[0])==int(a[0])+1 and int(b[1])>int(a[1]) for a,b in zip(rows,rows[1:])) and
            'dsi=1 crtc=0 active=1 width=1080 height=2400' in mode and 'htotal=1182 vtotal=4910 refresh=60' in mode,
            'recovery DPU scan differs')
    frequency=13_000_000/(int(rows[-1][1])-int(rows[0][1]))
    clocks=(BASE/'dpu-readonly/recovery-clock-status.txt').read_text()
    require(59<=frequency<=61 and clocks.splitlines()[:3]==['1700c: 8000000b','0104c: 00000001','01010: 00000221'],
            'recovery clock snapshots differ')
    return dict(hardware_vblank_hz=frequency,read_only_device_state='recovery',
                gcc='0x8000000b',disp_ahb='0x00000001',disp_mdp='0x00000221')


def storage(current):
    components=dict(load(P345/'storage-bound-345.json')['components'])
    baseline=sum(current['files'][p]['bytes'] for p in LOG_PATHS)
    require(0<baseline<=POST_LOG_BYTES,'baseline log bytes out of scope')
    components['verified_log_suffixes']=POST_LOG_BYTES-baseline+4*4096
    total=sum(components.values())
    require(components['compact_analysis']==ANALYSIS and total<=RESERVE,'runtime storage exceeds reservation')
    return dict(state='bounded0346-runtime-batch',components=components,worst_case_bytes=total,reserve_bytes=RESERVE,
                fresh_log_bytes=baseline,new_log_data_stored_once=True)


def criteria(plan):
    prior=load(P345/'trial-plan.json')
    allowed={'state','trial','image','image_sha256','image_bytes','kernel_identity','kernel_banner',
             'EDR_helper_sha256','owned_core_sha256','owned_core_logical_bytes','root_header_sha256',
             'install_plan_sha256','misc_before_sha256','parent_trial_plan_sha256','all_core_TUs_recompiled',
             'program_storage','optimization','performance_comparison','frame_capture','program_new_BO_CPU_phase_trace'}
    require({k for k in set(plan)|set(prior) if plan.get(k)!=prior.get(k)}<=allowed,'unreviewed trial effect')
    frame=plan['frame_capture']
    require(frame['volatile_crc_register_address']=='0x0ae6b980' and frame['maximum_volatile_crc_register_writes']==4 and
            frame['zero_control_preimage_required'] and frame['modesets']==0 and frame['target_refresh_hz']==60 and
            plan['scripted_reports']==442 and plan['scripted_strokes']==13 and
            plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            'clock, CRC, input or task sample bound differs')
    model=load(BASE/'restore-model/result.json')
    host=load(BASE/'frame-host/result.json')
    runtime=(BASE/'ring-host/result.log').read_text()
    require(model['all_model_IO_writes_memory_only'] and len(model['checks'])==47 and
            model['all_restore_partial_write_points']==17 and model['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['unit_tests']==21 and host['baseline_script_jobs']==725 and
            host['independent_readback_precedes_analysis'] and
            'actual-executor-control-suffix-prefix-mismatch' in host['model_controls'] and
            'actual-executor-control-suffix-success' in host['model_controls'] and
            '57897 additional ring-span assertions' in runtime,'0346 host review incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P345,HEADER,plan)
    return recovery_probe()


def gather_pins():
    prior=P345/'ready.json'
    pins=dict(load(prior)['input_pins'])
    sources=subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files=[WORK/name for name in sources]
    files += [Path(__file__),DOC,prior,P345/'trial-plan.json',P345/'storage-bound-345.json',MAIN/'tools/storage-budget.py']
    files += [WORK/name for name in (
        'xnu/patches/series','xnu/patches/0255-gauguin-display-ahb-hardware-gating.patch',
        'xnu/patches/0256-gauguin-join-ring-and-doorbell-guards.patch',
        'graphics/gauguin-program-io/0346-program-slabs.patch','tests/fixtures/dpu345_status.c',
        'tests/fixtures/gpu-user/runtime_host.c','tests/fixtures/gpu-user/ring_span_host.c',
        'tests/fixtures/core344_encoding.cpp','tests/fixtures/core346_program_slabs.cpp',
        'tests/test_core342_log.py','tests/test_frame345_log.py','tests/test_frame344_log.py',
        'tests/test_gpu_ring_span.py','tools/build-frame346.py','tools/frame346_scope.py','tools/run-frame346-trial.py')]
    files += [P345/'execution'/name for name in ('result.json','independent-restore.json','restored-capture/result.json',
        'collection-analysis.json','kernel.log','kernel-IO-identity-analysis.json','core-wait-execution-analysis.json',
        'queue-identity-analysis.json','frame-scanout-analysis.json','comparison-0344.json')]
    files += [BASE/name for name in ('frame346-image.json','frame346-image.img','native-kernel/build-manifest.json',
        'core-native/result.json','edr-native/result.json','core-host-reviewed/result.json','core-host-reviewed/program-slabs.log',
        'frame-host/result.json','ring-host/result.log','ring-host/control.log','build-prototype-retirement.json',
        'temporary-build-retirement.json','dpu-readonly/recovery-kms-stdout.txt','dpu-readonly/recovery-clock-status.txt')]
    files += [Path(load(BASE/name)['binary']) for name in ('core-native/result.json','edr-native/result.json')]
    files.append(Path(load(BASE/'native-kernel/build-manifest.json')['kernel']))
    for folder in ('slot-delta','slot-capture','metadata-snapshot','restore-model'):
        files.extend(p for p in (BASE/folder).rglob('*') if p.is_file())
    for path in files:
        value=sha(path)
        require(pins.setdefault(str(path),value)==value,'inherited pinned artifact differs: '+str(path))
    for name,digest in pins.items():
        require(sha(name)==digest,'pinned artifact differs: '+name)
    return pins


def freeze():
    require(not any((BASE/name).exists() for name in ('trial-plan.json','ready.json','approval.json','execution','final-review.json',
                                                      'capture-profile.json')),'0346 already prepared or claimed')
    plan=expected_plan()
    probe=criteria(plan)
    current=load(BASE/'current-root-capture/result.json')
    bound=storage(current)
    pins=gather_pins()
    manifest_bytes=len(json.dumps(pins,indent=2).encode())+1_048_576
    budget=json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
                      '--planned-bytes',str(RESERVE+manifest_bytes)],text=True,timeout=600))
    require(budget['admitted'],'frozen files and runtime reservation unavailable')
    profile=load(P345/'capture-profile.json')
    profile.update(out=str((BASE/'execution/fresh-before').relative_to(MAIN)),expected_header_sha256=HEADER)
    for name,value in (('trial-plan.json',plan),('capture-profile.json',profile),('expected-baseline.json',current),
                       ('storage-bound-346.json',bound),('storage-runtime-admission.json',budget),('recovery-DPU-checked.json',probe)):
        path=BASE/name
        save(path,value)
        pins[str(path)]=sha(path)
    ready=dict(state='ready-frame346-one-shot',trial_plan_sha256=sha(BASE/'trial-plan.json'),
               install_plan_sha256=plan['install_plan_sha256'],image_sha256=plan['image_sha256'],
               pin_count=len(pins),input_pins=pins,approval_pending=True,device_writes=0,boot_attempts=0)
    save(BASE/'ready.json',ready)
    return dict(ready_sha256=sha(BASE/'ready.json'),pin_count=len(pins),worst_case_bytes=bound['worst_case_bytes'],
                runtime_reserve=RESERVE)


def review():
    ready_path=BASE/'ready.json'
    plan_path=BASE/'trial-plan.json'
    ready,plan=load(ready_path),load(plan_path)
    require(not (BASE/'approval.json').exists() and not (BASE/'execution').exists() and
            ready['state']=='ready-frame346-one-shot' and plan==expected_plan() and
            ready['trial_plan_sha256']==sha(plan_path) and ready['pin_count']==len(ready['input_pins']) and
            plan['install_plan_sha256']==ready['install_plan_sha256'] and plan['image_sha256']==ready['image_sha256'],
            'frozen scope differs')
    require(criteria(plan)==load(BASE/'recovery-DPU-checked.json'),'recovery probe review differs')
    budget=load(BASE/'storage-runtime-admission.json')
    require(load(BASE/'storage-bound-346.json')==storage(load(BASE/'expected-baseline.json')) and
            budget['admitted'] and budget['planned_batch_bytes']>=RESERVE and
            budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'],'storage bound differs')
    for name,digest in ready['input_pins'].items():
        require(sha(name)==digest,'frozen input differs: '+name)
    report=dict(state='reviewed-frame346-one-shot',ready_sha256=sha(ready_path),trial_plan_sha256=sha(plan_path),
                image_sha256=ready['image_sha256'],install_plan_sha256=ready['install_plan_sha256'],
                no_device_mutation_during_preparation=True,restore_precedes_analysis=True,
                device_writes=0,boot_attempts=0,pin_count=ready['pin_count'],
                input_pins={str(p):sha(p) for p in (Path(__file__),DOC,WORK/'tools/run-frame346-trial.py')})
    save(BASE/'final-review.json',report)
    return {k:v for k,v in report.items() if k!='input_pins'}


if __name__=='__main__':
    steps={'freeze':freeze,'review':review}
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=steps)
    print(json.dumps(steps[parser.parse_args().stage](),indent=2))
