#!/usr/bin/env python3
"""Independent source-order, inherited gate, input, byte and budget review."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from core338_scope import MAIN,WORK,BASE,PRIOR,CORE,C4,IMAGE,HEADER,load,sha


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def inherited_analysis_audit():
    old_tree=ast.parse((WORK/'tools/run-sb-cadence-trial.py').read_text())
    main=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    old_try=next(n for n in main.body if isinstance(n,ast.Try))
    new_tree=ast.parse((WORK/'tools/analyze-core338.py').read_text())
    fn=next(n for n in new_tree.body if isinstance(n,ast.FunctionDef) and n.name=='analyze_saved')
    def subset(nodes):
        start=next(i for i,n in enumerate(nodes) if 'observer failed or kernel log absent' in ast.unparse(n))
        end=next(i for i,n in enumerate(nodes) if isinstance(n,ast.Assign) and
            any(isinstance(t,ast.Subscript) and ast.unparse(t)=="result['legacy_observation_state']" for t in n.targets))
        return copy.deepcopy(nodes[start:end+1])
    expected=[]
    for node in subset(old_try.body):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='queue_log' for t in node.targets):continue
        for item in ast.walk(node):
            if isinstance(item,ast.Constant) and isinstance(item.value,str):
                item.value=item.value.replace('C4Q321-CPU-stages-observed','C4Q338-CPU-stages-observed').replace(
                    'C4Q321-stage-coverage-unqualified','C4Q338-stage-coverage-unqualified')
            if isinstance(item,ast.Call) and isinstance(item.func,ast.Attribute) and isinstance(item.func.value,ast.Name) and item.func.value.id=='queue_log':
                assert item.func.attr=='analyze';item.func=ast.Attribute(value=ast.Name(id='CORE',ctx=ast.Load()),attr='lifecycle',ctx=ast.Load())
        expected.append(node)
    assert ast.dump(ast.Module(body=expected,type_ignores=[]))==ast.dump(ast.Module(body=subset(fn.body),type_ignores=[]))
    return 'all-legacy-runtime-configuration-gates-identical-except-explicit338-wire-decoder-and-state-labels'


def main():
    assert not (BASE/'approval.json').exists() and not (BASE/'execution').exists() and not (BASE/'final-review.json').exists()
    ready=load(BASE/'ready.json');plan=load(BASE/'trial-plan.json');old=load(PRIOR/'trial-plan.json')
    assert ready['state']=='ready-core338-one-shot' and ready['pin_count']==len(ready['input_pins'])>18389
    assert ready['parent_337_pins_preserved']==18389
    assert ready['trial_plan_sha256']==sha(BASE/'trial-plan.json') and ready['install_plan_sha256']==sha(BASE/'slot-delta/install-plan.json')
    for p,h in ready['input_pins'].items():assert sha(p)==h,p
    parent=load(PRIOR/'ready.json')
    assert all(ready['input_pins'].get(p)==h for p,h in parent['input_pins'].items())
    allowed={'state','root_header_sha256','install_plan_sha256','owned_core_sha256','C4_sha256','unchanged_334_core',
        'unchanged_335_core','diagnostic_only','performance_candidate','unchanged_337_kernel_helper_SB','new_kernel_builds',
        'new_boot_images','maximum_restore_userdata_bytes','normal_userdata_write_bytes_max','maximum_userdata_write_bytes',
        'failed_restore_retry_limit','retry_only_after_verified_rollback','restore_forward_attempts','no_new_files_or_HFSX_allocations',
        'install_has_no_new_allocation','restore_reclaims_original_free_unowned_tails_only','restore_journal_policy',
        'restore_max_ranges','restore_max_bitmap_blocks','alternate_header_write_allowed','journal_home_replay_allowed',
        'unsupported_restore_state','capture_log_limits','storage_reserve_bytes','additional_GPU_calls_scope',
        'async_recording_notification','core_wait_execution_trace','restoration_and_independent_readback_before_analysis',
        'parent_trial_plan_sha256'}
    changed={k for k in plan.keys()|old.keys() if plan.get(k)!=old.get(k)}
    assert changed==allowed,(changed-allowed,allowed-changed)
    assert plan['boot_command']==old['boot_command'] and len(plan['boot_command'].encode())==607
    for k in ('image','image_sha256','kernel_banner','kernel_identity','EDR_helper_sha256','SB_sha256',
        'GPU_native_profile','completed_owned_BO_cache','cache_full_replacement','surface_retirement','collector_changes',
        'queue_identity_trace','main_thread_sampling','process_sampling','observer_helper'):
        assert plan[k]==old[k],k
    assert plan['image_sha256']==IMAGE==sha(plan['image']) and Path(plan['image']).stat().st_size==20054016
    assert plan['new_kernel_builds']==plan['new_boot_images']==0 and plan['unchanged_337_kernel_helper_SB']
    assert plan['owned_core_sha256']==CORE and plan['C4_sha256']==C4 and plan['root_header_sha256']==HEADER
    assert plan['performance_candidate'] and not plan['physical_FPS_qualified']
    delta=load(BASE/'slot-delta/install-plan.json')
    assert delta['changed_ranges']==11 and delta['install_write_bytes']==plan['install_userdata_bytes']==10301440
    assert delta['restore_max_ranges']==18 and delta['restore_max_write_bytes']==plan['maximum_restore_userdata_bytes']==10330112
    assert 6*4096+4*4096+2*4096+10280960==10330112
    assert 10301440+10330112==plan['normal_userdata_write_bytes_max']==20631552
    assert 10301440+2*10330112==plan['maximum_userdata_write_bytes']==30961664
    assert plan['failed_restore_retry_limit']==0 and plan['restore_forward_attempts']==1 and plan['temporary_boots']==1 and plan['boot_retries']==0
    assert plan['maximum_host_misc_write_bytes']==26 and plan['misc_write_bytes']==13
    assert not plan['journal_home_replay_allowed'] and not plan['alternate_header_write_allowed']
    for leaf,state in [('restore-model-v5/result.json','0338-live-metadata-install-and-tail-journal-restore-models-passed'),
        ('pipeline-v3/result.json','0338-executor-analysis-collection-order-host-models-passed'),
        ('frontend-host-v9/result.json','0338-production-ObjC-methods-core-FakeGpu-lifetimes-passed')]:
        receipt=load(BASE/leaf);assert receipt['state']==state
        for p,h in receipt['input_pins'].items():assert sha(p)==h,p
    inherited=inherited_analysis_audit()
    source=(WORK/'tools/run-core338-trial.py').read_text();tree=ast.parse(source)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    restore=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='restore_and_verify')
    body=ast.unparse(restore)
    assert body.index("result['restore_attempted'] = True")<body.index('RESTORE.apply(')<body.index('independent.verify(')<body.index("result['independent_restore_verified'] = True")
    trial=next(n for n in main.body if isinstance(n,ast.Try) and any(isinstance(x,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='before' for t in x.targets) for x in n.body))
    actual=ast.unparse(trial)
    assert actual.index('restore_and_verify(io)')<actual.index('analyze(EXEC, plan, result, before, code)')
    assert "not result['restore_attempted']" in ast.unparse(trial.handlers)
    analysis=(WORK/'tools/analyze-core338.py').read_text()
    assert analysis.index("proof=load(EXEC/'independent-restore.json')")<analysis.index('CORE.lifecycle(backboard)')
    assert analysis.index('collection=COLLECTION.analyze(')<analysis.index("save(EXEC/'collection-analysis.json'")<analysis.index('backlog=interpret(')
    cap=module('independent_cap338',WORK/'tools/capture-core338-root.py')
    limits=sum(cap.BASE.FILE_LIMITS.get(p,1048576) for p in cap.BASE.PATHS)
    assert limits==146307632 and cap.RESULT_MAX==1048576
    try:cap.bounded_json({'oversize':'x'*1048576})
    except ValueError:pass
    else:raise AssertionError('capture metadata unbounded')
    # Recompute all allocations independently of the preparation function.
    total=3*(limits+1048576)+(48+22+8+8)*1048576+16781312+12587008+2*10330112+8*2*1048576
    total+=32*1048576+(8+8+32+8+2+4)*1048576+3*131072+3*65536+1572864
    bound=load(BASE/'storage-bound.json')
    assert total==sum(bound['components'].values())==bound['worst_case_bytes']==699780752<plan['storage_reserve_bytes']==700000000
    recipe_bound=load(BASE/'storage-recipe-bound.json')
    assert recipe_bound['maximum_home_hashes']==8388608//512==16384
    assert recipe_bound['inflated_serialized_recipe_bytes']+65536<=recipe_bound['reserved_bytes']==1572864
    budget=load(BASE/'storage-runtime-admission.json')
    assert budget['admitted'] and budget['current_accounted_bytes']+700000000<=500000000000
    gate=subprocess.run([sys.executable,str(WORK/'tools/run-core338-trial.py'),'--check-gate'],capture_output=True,text=True,timeout=10)
    assert gate.returncode==2 and 'approval absent; zero device commands' in gate.stdout
    assert not (BASE/'execution').exists() and not (BASE/'approval.json').exists()
    gate_log=BASE/'gate-test.log'
    with gate_log.open('x') as f:f.write(gate.stdout+gate.stderr)
    paths=[Path(__file__),BASE/'ready.json',BASE/'trial-plan.json',BASE/'storage-bound.json',BASE/'storage-recipe-bound.json',gate_log,
        BASE/'pipeline-v3/result.json',BASE/'restore-model-v5/result.json',BASE/'frontend-host-v9/result.json',
        WORK/'tools/run-core338-trial.py',WORK/'tools/analyze-core338.py',
        WORK/'docs/gauguin-core-async-338-trial-20261117.md']
    result=dict(state='reviewed-core338-one-shot',ready_sha256=sha(BASE/'ready.json'),
        all_pins_unchanged=True,pin_count=ready['pin_count'],parent_337_pins_preserved=18389,
        changed_plan_keys=sorted(changed),inherited_gate_source_audit=inherited,
        restoration_precedes_analysis=True,collection_precedes_interpretation=True,
        independent_runtime_bound_bytes=total,new_kernel_builds=0,new_images=0,
        approval_absent=True,execution_absent=True,device_commands=0,
        input_pins={str(p):sha(p) for p in paths})
    with (BASE/'final-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
