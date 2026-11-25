#!/usr/bin/env python3
"""Independent frozen-source, byte-cap, collection and restore-order review."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from core342_scope import MAIN,WORK,BASE,PRIOR,PARENT,HEADER,CORE,C4,EDR,IMAGE,IDENTITY,expected_plan,load,sha


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def gate_audit():
    def subset(path):
        tree=ast.parse(path.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='analyze_saved')
        start=next(i for i,n in enumerate(fn.body) if 'observer failed or kernel log absent' in ast.unparse(n))
        end=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and
            any(isinstance(t,ast.Subscript) and ast.unparse(t)=="result['legacy_observation_state']" for t in n.targets))
        return copy.deepcopy(fn.body[start:end+1])
    old=subset(WORK/'tools/analyze-core341.py');new=subset(WORK/'tools/analyze-core342.py')
    for node in old:
        for item in ast.walk(node):
            if isinstance(item,ast.Constant) and isinstance(item.value,str):item.value=item.value.replace('341','342')
    assert ast.dump(ast.Module(body=old,type_ignores=[]))==ast.dump(ast.Module(body=new,type_ignores=[]))
    prior_review=module('unchanged341_independent_audit',WORK/'tools/review-core341-trial.py')
    # The341 audit separately compares that inherited block to the original
    # legacy parser, and checks the exact two340 byte-bound transformations.
    return dict(legacy=prior_review.inherited_analysis_audit(),decoder=prior_review.inherited_decoder_bound_audit(),
        actual342_block_identical_except_wire_labels=True)


def source_order_audit():
    source=(WORK/'tools/run-core342-trial.py').read_text();tree=ast.parse(source)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    restore=next(n for n in fn.body if isinstance(n,ast.FunctionDef) and n.name=='restore_and_verify')
    body=ast.unparse(restore)
    assert body.index("result['restore_attempted'] = True")<body.index('RESTORE.apply(')<body.index('independent.verify(')<body.index("result['independent_restore_verified'] = True")
    trial=next(n for n in fn.body if isinstance(n,ast.Try) and any(isinstance(x,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='before' for t in x.targets) for x in n.body))
    actual=ast.unparse(trial)
    assert actual.index('restore_and_verify(io)')<actual.index('analyze(EXEC, plan, result, before, code)')
    assert "not result['restore_attempted']" in ast.unparse(trial.handlers)
    auth=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='authorization')
    assert 'RecoveryIO' not in ast.unparse(auth) and 'check_consent(' in ast.unparse(auth)
    analysis=(WORK/'tools/analyze-core342.py').read_text()
    assert analysis.index("proof=load(EXEC/'independent-restore.json')")<analysis.index('CORE.lifecycle(backboard)')
    assert analysis.index('kernel_join=KERNEL.join(')<analysis.index('collection=COLLECTION.analyze(')<analysis.index('backlog=interpret(')
    assert analysis.index("save(EXEC/'collection-analysis.json'")<analysis.index('backlog=interpret(')<analysis.index('KERNEL.summarize(')
    return True


def reversible_sources():
    from core_io342_patch import patch,reverse
    p=load(BASE/'prepared-v3/result.json')
    for name in ('src/c_api.cpp','src/command.cpp','src/render.cpp','src/gpu.cpp','src/iokit_transport.cpp'):
        before=(Path(p['sources']['baseline'])/name).read_text();after=(Path(p['sources']['candidate'])/name).read_text()
        expected,edits=patch(before,name);assert expected==after;reverse(before,after,edits)
    for name in ('HakiosMetalCA.m','GauguinMetalProfile.m'):
        before=(Path(p['sources']['frontend-baseline'])/name).read_text();after=(Path(p['sources']['frontend-candidate'])/name).read_text()
        for tag in ('C4Q','Q','N'):before=before.replace('GAUGUIN '+tag+'341:','GAUGUIN '+tag+'342:')
        assert before==after
    import kernel_io342_patch as driver
    parent=load(PRIOR/'local-link/build-manifest.json');old=Path(parent['source_union']['overlay'])
    kernel=load(BASE/'kernel-prepared-v8/result.json');new=Path(kernel['source'])
    name='iokit/Kernel/arm/GauguinGPU.cpp';before=(old/name).read_text();after=(new/name).read_text()
    expected,edits=driver.patch(before);assert expected==after;driver.reverse(before,after,edits)
    for name in ('Phase342.hpp','Kernel342.hpp'):
        assert (new/'iokit/Kernel/arm'/name).read_bytes()==(WORK/'graphics/gauguin-io-path'/name).read_bytes()
    ui='bsd/dev/gauguin_ui_trace.h'
    assert (new/ui).read_text()==(old/ui).read_text().replace(
        '    GUT_SYNTHETIC=30 /* explicit origin marker for a generated report ID */',
        '    GUT_SYNTHETIC=30 /* explicit origin marker for a generated report ID */,\n    GUT_BO_ALLOC333=31, GUT_BO_REUSE335=32')
    # Independently inspect the existing logger's atomic whole-span reservation.
    logger=Path(parent['source_union']['base'])/'bsd/dev/sweet_ufs.c'
    raw=logger.read_text();start=raw.index('sweet_log_append(const char *c, int size)\n{');end=raw.index('\n}',start)
    append=raw[start:end]
    assert 'os_atomic_add_orig(&sweet_log_total, (uint64_t)size, relaxed)' in append and 'sweet_log_ring[(at + (uint64_t)i) % SWEET_LOG_SIZE] = c[i]' in append
    head=(new/'iokit/Kernel/arm/Kernel342.hpp').read_text()
    assert 'frame(line.data,(int)line.used+2)' in head and "line.data[0]='\\n'" in head
    assert 'dumpByteLimit=2u*1024u*1024u' in head and 'rowBytes>dumpByteLimit-4096' in head
    assert 'io342::dump(record,sweet_log_append)' in after
    stop=after[after.index('extern "C" void GauguinGPUProfileDump'):after.index('extern "C" void GauguinGPUProfileDump')+1400]
    assert stop.index('io342::dump(')<stop.index('record(line)')
    assert 'sweet_log_flush_now' not in head and 'console_write(' not in head
    return dict(user_five_TUs_reversible=True,frontend_only_wire_label_changes=True,
        driver_reversible=True,existing_legacy_UI_events_only_same_numeric_enum_names_added=True,
        whole_line_RAM_ring_reservation_and_following_original_flush_verified=True,logger_source=str(logger))


def main():
    assert not any((BASE/n).exists() for n in ('approval.json','execution','final-review.json'))
    ready=load(BASE/'ready.json');plan=load(BASE/'trial-plan.json');old=load(PARENT/'trial-plan.json')
    assert plan==expected_plan() and ready['state']=='ready-core342-one-shot'
    assert ready['pin_count']==len(ready['input_pins'])>24906 and ready['parent_341_pins_preserved']==24906
    assert ready['trial_plan_sha256']==sha(BASE/'trial-plan.json') and ready['install_plan_sha256']==sha(BASE/'slot-delta/install-plan.json')
    for p,h in ready['input_pins'].items():assert sha(p)==h,p
    assert all(ready['input_pins'].get(p)==h for p,h in load(PARENT/'ready.json')['input_pins'].items())
    allowed={'C4_sha256','EDR_helper_sha256','additional_GPU_calls_scope','core_wait_execution_trace','image',
        'image_bytes','image_sha256','install_plan_sha256','kernel_IO_CPU_phase_trace','kernel_banner','kernel_identity',
        'new_boot_images','new_kernel_builds','owned_core_sha256','parent_trial_plan_sha256','program_new_BO_CPU_phase_trace',
        'root_header_sha256','state','storage_reserve_bytes','unchanged_337_SB','unchanged_337_kernel_helper_SB'}
    changed={k for k in plan.keys()|old.keys() if plan.get(k)!=old.get(k)};assert changed==allowed,(changed-allowed,allowed-changed)
    for k in ('boot_command','SB_sha256','GPU_native_profile','completed_owned_BO_cache','cache_full_replacement',
        'surface_retirement','collector_changes','queue_identity_trace','main_thread_sampling','process_sampling','observer_helper',
        'program_table_slab_trace','IO_calling_thread_CPU_accounting','worker_CPU_scratch_reuse','core_symbol_policy'):
        assert plan[k]==old[k],k
    assert len(plan['boot_command'].encode())==607 and plan['image_sha256']==IMAGE==sha(plan['image'])
    assert plan['image_bytes']==Path(plan['image']).stat().st_size==22183936 and plan['kernel_identity']==IDENTITY
    assert plan['new_kernel_builds']==plan['new_boot_images']==1 and plan['unchanged_337_SB'] and not plan['unchanged_337_kernel_helper_SB']
    assert plan['owned_core_sha256']==CORE and plan['C4_sha256']==C4 and plan['EDR_helper_sha256']==EDR and plan['root_header_sha256']==HEADER
    assert plan['diagnostic_only'] and not plan['performance_candidate'] and not plan['physical_FPS_qualified']
    d=load(BASE/'slot-delta/install-plan.json')
    assert d['changed_ranges']==11 and d['install_write_bytes']==plan['install_userdata_bytes']==10301440
    assert d['restore_max_ranges']==18 and d['restore_max_write_bytes']==plan['maximum_restore_userdata_bytes']==10330112
    assert 6*4096+4*4096+2*4096+10280960==10330112
    assert 10301440+10330112==plan['normal_userdata_write_bytes_max']==20631552
    assert 10301440+2*10330112==plan['maximum_userdata_write_bytes']==30961664
    assert plan['temporary_boots']==plan['restore_forward_attempts']==1 and plan['boot_retries']==plan['failed_restore_retry_limit']==0
    assert plan['misc_write_bytes']==13 and plan['maximum_host_misc_write_bytes']==26
    assert not plan['journal_home_replay_allowed'] and not plan['alternate_header_write_allowed']
    legacy=module('independent_readonly_parent_compare342',WORK/'tools/run-sb-cadence-trial.py')
    legacy.static_compare(load(PARENT/'execution/restored-capture/result.json'),load(BASE/'current-root-capture/result.json'))
    gates=gate_audit();ordering=source_order_audit();sources=reversible_sources()
    cap=module('independent_cap342',WORK/'tools/capture-core342-root.py')
    logical=sum(cap.BASE.FILE_LIMITS.get(p,1048576) for p in cap.BASE.PATHS)
    assert logical==190347824 and cap.RESULT_MAX==1048576
    try:cap.bounded_json({'oversize':'x'*1048576})
    except ValueError:pass
    else:raise AssertionError('capture metadata unbounded')
    # Independent arithmetic, without importing the preparation bound function.
    total=3*(logical+1048576)+(48+64+8+8)*1048576+16781312+12587008+2*10330112+8*2*1048576
    total+=32*1048576+(8+8+64+8+2+4)*1048576+3*131072+3*65536+1572864
    total+=(32+8+8)*1048576
    bound=load(BASE/'storage-bound.json')
    assert total==sum(bound['components'].values())==bound['worst_case_bytes']==959827600<plan['storage_reserve_bytes']==1000000000
    recipe=load(BASE/'storage-recipe-bound.json');assert recipe['maximum_home_hashes']==8388608//512==16384
    assert recipe['inflated_serialized_recipe_bytes']+65536<=recipe['reserved_bytes']==1572864
    budget=subprocess.run([sys.executable,str(MAIN/'tools/storage-budget.py'),'--planned-bytes','1000000000'],capture_output=True,text=True,timeout=600)
    assert budget.returncode==0,budget.stdout+budget.stderr
    current=json.loads(budget.stdout);assert current['admitted']
    whole=load(BASE/'storage-whole-batch-admission.json')
    assert current['current_accounted_bytes']-whole['current_accounted_bytes']+1000000000<=2400000000
    budget_path=BASE/'storage-final-admission.json'
    with budget_path.open('x') as f:json.dump(current,f,indent=2);f.write('\n')
    gate=subprocess.run([sys.executable,str(WORK/'tools/run-core342-trial.py'),'--check-gate'],capture_output=True,text=True,timeout=10)
    assert gate.returncode==2 and 'approval absent; zero device commands' in gate.stdout
    assert not (BASE/'execution').exists() and not (BASE/'approval.json').exists()
    gate_path=BASE/'gate-test.log';gate_path.write_text(gate.stdout+gate.stderr)
    paths=[Path(__file__),BASE/'ready.json',BASE/'trial-plan.json',BASE/'storage-bound.json',BASE/'storage-recipe-bound.json',
        budget_path,gate_path,BASE/'pipeline-v4/result.json',BASE/'restore-model-v3/result.json',
        BASE/'kernel-phase-host-v5/result.json',WORK/'tools/run-core342-trial.py',WORK/'tools/analyze-core342.py',Path(sources['logger_source']),
        WORK/'docs/gauguin-io-path-342-trial-20261117.md',WORK/'docs/gauguin-io-path342-design-20261117.md']
    result=dict(state='reviewed-core342-one-shot',ready_sha256=sha(BASE/'ready.json'),all_pins_unchanged=True,
        pin_count=ready['pin_count'],parent_341_pins_preserved=24906,changed_plan_keys=sorted(changed),
        inherited_gate_source_audit=gates,reversible_source_audit=sources,
        restoration_precedes_analysis=ordering,collection_precedes_interpretation=True,
        independent_runtime_bound_bytes=total,readonly_root_matches_parent_restoration=True,approval_absent=True,execution_absent=True,new_kernel_builds=1,new_images=1,
        device_commands=0,input_pins={str(p):sha(p) for p in paths})
    with (BASE/'final-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
