#!/usr/bin/env python3
"""Independent source-order, inherited gate, input, byte and budget review."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types
from core341_scope import MAIN,WORK,BASE,PRIOR,PARENT,CORE,C4,IMAGE,HEADER,expected_plan,load,sha


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def inherited_analysis_audit():
    old_tree=ast.parse((WORK/'tools/run-sb-cadence-trial.py').read_text())
    main=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    old_try=next(n for n in main.body if isinstance(n,ast.Try))
    new_tree=ast.parse((WORK/'tools/analyze-core341.py').read_text())
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
                item.value=item.value.replace('C4Q321-CPU-stages-observed','C4Q341-CPU-stages-observed').replace(
                    'C4Q321-stage-coverage-unqualified','C4Q341-stage-coverage-unqualified')
            if isinstance(item,ast.Call) and isinstance(item.func,ast.Attribute) and isinstance(item.func.value,ast.Name) and item.func.value.id=='queue_log':
                assert item.func.attr=='analyze';item.func=ast.Attribute(value=ast.Name(id='CORE',ctx=ast.Load()),attr='lifecycle',ctx=ast.Load())
        expected.append(node)
    assert ast.dump(ast.Module(body=expected,type_ignores=[]))==ast.dump(ast.Module(body=subset(fn.body),type_ignores=[]))
    return 'all-legacy-runtime-configuration-gates-identical-except-explicit341-wire-decoder-and-state-labels'


def inherited_decoder_bound_audit():
    import core341_log as decoder
    original=module('independent_pristine340_decoder',WORK/'tools/core340_log.py')
    def shape(code,replacements):
        constants=[]
        for item in code.co_consts:
            if isinstance(item,types.CodeType):item=shape(item,{})
            elif isinstance(item,int):item=replacements.get(item,item)
            constants.append(item)
        return (code.co_code,code.co_names,code.co_varnames,code.co_argcount,
            code.co_cellvars,code.co_freevars,tuple(constants))
    source=(WORK/'tools/core340_log.py').read_text()
    assert source.count('len(line.encode())+1>4096')==1 and source.count('total>4097*4096')==1
    expected=source.replace('len(line.encode())+1>4096','len(line.encode())+1>8192').replace('total>4097*4096','total>4097*8192')
    functions=[n for n in ast.parse(expected).body if isinstance(n,ast.FunctionDef) and n.name in ('parse_extra','analyze')]
    namespace=dict(original.__dict__)
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(WORK/'tools/core340_log.py'),'exec'),namespace)
    assert shape(namespace['parse_extra'].__code__,{})==shape(decoder.OLD.parse_extra.__code__,{})
    assert shape(namespace['analyze'].__code__,{})==shape(decoder.OLD.analyze.__code__,{})
    return 'inherited340-decoder-matches-exact-two-byte-bound-source-transform; record4096-preserved'



def main():
    assert not (BASE/'approval.json').exists() and not (BASE/'execution').exists() and not (BASE/'final-review.json').exists()
    ready=load(BASE/'ready.json');plan=load(BASE/'trial-plan.json');old=load(PARENT/'trial-plan.json')
    assert plan==expected_plan()
    assert ready['state']=='ready-core341-one-shot' and ready['pin_count']==len(ready['input_pins'])>23120
    assert ready['parent_340_pins_preserved']==23120
    assert ready['trial_plan_sha256']==sha(BASE/'trial-plan.json') and ready['install_plan_sha256']==sha(BASE/'slot-delta/install-plan.json')
    for p,h in ready['input_pins'].items():assert sha(p)==h,p
    parent=load(PARENT/'ready.json')
    assert all(ready['input_pins'].get(p)==h for p,h in parent['input_pins'].items())
    allowed={'state','root_header_sha256','install_plan_sha256','owned_core_sha256','C4_sha256',
        'diagnostic_only','performance_candidate','capture_log_limits','storage_reserve_bytes',
        'additional_GPU_calls_scope','core_wait_execution_trace','core_symbol_policy',
        'program_table_slab_trace','IO_calling_thread_CPU_accounting','parent_trial_plan_sha256'}
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
    assert plan['diagnostic_only'] and not plan['performance_candidate'] and not plan['physical_FPS_qualified']
    delta=load(BASE/'slot-delta/install-plan.json')
    assert delta['changed_ranges']==11 and delta['install_write_bytes']==plan['install_userdata_bytes']==10301440
    assert delta['restore_max_ranges']==18 and delta['restore_max_write_bytes']==plan['maximum_restore_userdata_bytes']==10330112
    assert 6*4096+4*4096+2*4096+10280960==10330112
    assert 10301440+10330112==plan['normal_userdata_write_bytes_max']==20631552
    assert 10301440+2*10330112==plan['maximum_userdata_write_bytes']==30961664
    assert plan['failed_restore_retry_limit']==0 and plan['restore_forward_attempts']==1 and plan['temporary_boots']==1 and plan['boot_retries']==0
    assert plan['maximum_host_misc_write_bytes']==26 and plan['misc_write_bytes']==13
    assert not plan['journal_home_replay_allowed'] and not plan['alternate_header_write_allowed']
    for leaf,state in [('restore-model-v1/result.json','0341-live-metadata-install-and-tail-journal-restore-models-passed'),
        ('pipeline-v1/result.json','0341-executor-analysis-collection-order-host-models-passed'),
        ('frontend-host-v1/result.json','0341-production-ObjC-methods-core-FakeGpu-lifetimes-passed')]:
        receipt=load(BASE/leaf);assert receipt['state']==state
        for p,h in receipt['input_pins'].items():assert sha(p)==h,p
    inherited=inherited_analysis_audit()
    decoder_audit=inherited_decoder_bound_audit()
    from core_program341_patch import patch,reverse
    prepared=load(BASE/'prepared-v2/result.json')
    for name in ('src/c_api.cpp','src/command.cpp','src/render.cpp','src/gpu.cpp','src/iokit_transport.cpp'):
        original=(Path(prepared['sources']['baseline'])/name).read_text()
        candidate=(Path(prepared['sources']['candidate'])/name).read_text()
        expected,edits=patch(original,name);assert expected==candidate
        reverse(original,candidate,edits)
    assert plan['core_category_submit_trace']['additional_CPU_jobs_per_commit']==0
    assert plan['core_symbol_policy']['possible_core_trim_tail_blocks']==105
    import core341_log as decoder
    assert plan['draw_submit_phase_trace']['draw_common_phases']==list(decoder.DRAW)
    assert plan['draw_submit_phase_trace']['render_body_phases']==list(decoder.RENDER)
    assert plan['draw_submit_phase_trace']['GPU_submit_phases']==list(decoder.GPU)
    reuse=plan['worker_CPU_scratch_reuse']
    assert (reuse['draw_retained_elements_per_vector'],reuse['draw_vectors'],reuse['submit_retained_BO_descriptors'],reuse['BO_index_buckets'])==(128,7,1024,2048)
    assert reuse['FIFO_turn_event_completion_and_notification_order_unchanged']
    assert reuse['GPU_buffer_mapping_and_BO_cache_policy_unchanged']
    assert plan['core_wait_execution_trace']['core_line_bytes']==8192
    assert plan['draw_submit_phase_trace']['actual_IO_begin_end_and_count']
    assert plan['program_table_slab_trace']['phases']=={k:list(v) for k,v in decoder.PARTS.items()}
    assert plan['program_table_slab_trace']['counters']==list(decoder.COUNTS)
    assert plan['IO_calling_thread_CPU_accounting']['CPU_clock_slop_ns']==decoder.CPU_SLOP_NS==2000
    assert plan['IO_calling_thread_CPU_accounting']['queries_per_traced_IO']==2
    frontend_baseline=Path(prepared['sources']['frontend-baseline'])
    frontend_candidate=Path(prepared['sources']['frontend-candidate'])
    for name in ('HakiosMetalCA.m','GauguinMetalProfile.m'):
        before=(frontend_baseline/name).read_text();after=(frontend_candidate/name).read_text()
        for tag in ('C4Q','Q','N'):before=before.replace('GAUGUIN '+tag+'340:','GAUGUIN '+tag+'341:')
        assert before==after


    source=(WORK/'tools/run-core341-trial.py').read_text();tree=ast.parse(source)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    restore=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='restore_and_verify')
    body=ast.unparse(restore)
    assert body.index("result['restore_attempted'] = True")<body.index('RESTORE.apply(')<body.index('independent.verify(')<body.index("result['independent_restore_verified'] = True")
    trial=next(n for n in main.body if isinstance(n,ast.Try) and any(isinstance(x,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='before' for t in x.targets) for x in n.body))
    actual=ast.unparse(trial)
    assert actual.index('restore_and_verify(io)')<actual.index('analyze(EXEC, plan, result, before, code)')
    assert "not result['restore_attempted']" in ast.unparse(trial.handlers)
    analysis=(WORK/'tools/analyze-core341.py').read_text()
    assert analysis.index("proof=load(EXEC/'independent-restore.json')")<analysis.index('CORE.lifecycle(backboard)')
    assert analysis.index('collection=COLLECTION.analyze(')<analysis.index("save(EXEC/'collection-analysis.json'")<analysis.index('backlog=interpret(')
    cap=module('independent_cap341',WORK/'tools/capture-core341-root.py')
    limits=sum(cap.BASE.FILE_LIMITS.get(p,1048576) for p in cap.BASE.PATHS)
    assert limits==190347824 and cap.RESULT_MAX==1048576
    try:cap.bounded_json({'oversize':'x'*1048576})
    except ValueError:pass
    else:raise AssertionError('capture metadata unbounded')
    # Recompute all allocations independently of the preparation function.
    total=3*(limits+1048576)+(48+64+8+8)*1048576+16781312+12587008+2*10330112+8*2*1048576
    total+=32*1048576+(8+8+64+8+2+4)*1048576+3*131072+3*65536+1572864
    bound=load(BASE/'storage-bound.json')
    assert total==sum(bound['components'].values())==bound['worst_case_bytes']==909495952<plan['storage_reserve_bytes']==950000000
    recipe_bound=load(BASE/'storage-recipe-bound.json')
    assert recipe_bound['maximum_home_hashes']==8388608//512==16384
    assert recipe_bound['inflated_serialized_recipe_bytes']+65536<=recipe_bound['reserved_bytes']==1572864
    budget=load(BASE/'storage-runtime-admission.json')
    assert budget['admitted'] and budget['current_accounted_bytes']+950000000<=500000000000
    # Recheck the COMPLETE runtime after the frozen ready file itself exists.
    current=subprocess.run([sys.executable,str(MAIN/'tools/storage-budget.py'),'--planned-bytes','950000000'],capture_output=True,text=True,timeout=600)
    assert current.returncode==0,current.stdout+current.stderr
    final_budget=json.loads(current.stdout);assert final_budget['admitted']
    budget_path=BASE/'storage-final-admission.json'
    with budget_path.open('x') as f:json.dump(final_budget,f,indent=2);f.write('\n')
    gate=subprocess.run([sys.executable,str(WORK/'tools/run-core341-trial.py'),'--check-gate'],capture_output=True,text=True,timeout=10)
    assert gate.returncode==2 and 'approval absent; zero device commands' in gate.stdout
    assert not (BASE/'execution').exists() and not (BASE/'approval.json').exists()
    gate_log=BASE/'gate-test.log'
    with gate_log.open('x') as f:f.write(gate.stdout+gate.stderr)
    paths=[Path(__file__),BASE/'ready.json',BASE/'trial-plan.json',BASE/'storage-bound.json',BASE/'storage-recipe-bound.json',gate_log,
        BASE/'pipeline-v1/result.json',BASE/'restore-model-v1/result.json',BASE/'frontend-host-v1/result.json',budget_path,
        WORK/'tools/run-core341-trial.py',WORK/'tools/analyze-core341.py',
        WORK/'docs/gauguin-program-io-341-trial-20261117.md']
    result=dict(state='reviewed-core341-one-shot',ready_sha256=sha(BASE/'ready.json'),
        all_pins_unchanged=True,pin_count=ready['pin_count'],parent_340_pins_preserved=23120,
        changed_plan_keys=sorted(changed),inherited_gate_source_audit=inherited,
        inherited_decoder_bound_audit=decoder_audit,
        restoration_precedes_analysis=True,collection_precedes_interpretation=True,
        independent_runtime_bound_bytes=total,reversible_core_source_audit=True,new_kernel_builds=0,new_images=0,
        approval_absent=True,execution_absent=True,device_commands=0,
        input_pins={str(p):sha(p) for p in paths})
    with (BASE/'final-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
