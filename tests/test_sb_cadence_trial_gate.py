#!/usr/bin/env python3
"""An absent individual approval must stop before ADB, fastboot or a claim."""

import os
import ast
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


WORK = Path(__file__).resolve().parents[1]
STATE = WORK/'research/tmp/queue-loss-337'
RUNNER = WORK/'tools/run-sb-cadence-trial.py'


def check_edr_classification(runner):
    marker=('GAUGUIN EDR318 LOADER: entry us=100 identity=1 mode=1\n'
            'GAUGUIN EDR320: entry os_read=1 kernel_read=1 args_read=1 scope=1\n'
            'GAUGUIN EDR320: code-check name=initializer region=1 kr=0 count=12 depth=1 protection=5 hashed=1 hash=1 sha256=a5c01abf3fd26dce1209234ee6786e53339c5b74df917ccc32d08f16afbe78f7\n'
            'GAUGUIN EDR320: code-check name=callback region=1 kr=0 count=12 depth=1 protection=5 hashed=1 hash=1 sha256=57a8089a33acefd10a675e6ad7b947a8cc452bc76dfef2bbea6b516bdaa72dba\n'
            'GAUGUIN EDR320: once-abi checks=6 passed=1\n'
            'GAUGUIN EDR320: once before=0x0000000019f31e02 eligible=1\n'
            'GAUGUIN EDR320: once after=0x0000000019f31e02 complete=1\n'
            'GAUGUIN EDR320: optional-query result=1 slot_null=1 bytes=8 code_writes=0\n'
            'GAUGUIN EDR318 LOADER: result=opened us=110\n')
    good=runner.inspect_edr_activation(marker,True)
    assert good['active'] and not good['physical_fps_qualified']
    for value in ('0000000000000000','ffffffffffffffff'):
        assert runner.inspect_edr_activation(marker.replace('before=0x0000000019f31e02','before=0x'+value),True)['active']
    assert runner.inspect_edr_activation(marker.replace('after=0x0000000019f31e02','after=0xffffffffffffffff'),True)['active']
    for text in (marker.replace('checks=6','checks=5'),marker.replace('passed=1','passed=0'),
                 marker.replace('eligible=1','eligible=0'),marker.replace('complete=1','complete=0'),
                 marker.replace('before=0x0000000019f31e02','before=0x0000000000012341'),
                 marker.replace('after=0x0000000019f31e02','after=0x0000000000000000'),
                 marker.replace('after=0x0000000019f31e02','after=0x0000000000012340'),
                 '',marker+marker,marker.replace('result=1','result=-1'),
                 marker+'GAUGUIN EDR320: refused=scope\n',marker+'GAUGUIN GPU PILOT begin\n',
                 marker.replace('hash=1','hash=0'),marker.replace('depth=1','depth=9'),
                 marker.replace('protection=5','protection=1'),marker.replace('count=12','count=19'),
                 marker.replace('name=callback','name=initializer'),
                 marker.replace('result=opened','result=failed'),marker.replace('scope=1','scope=0'),
                 marker.replace('us=110','us=99'),marker.replace('mode=1','mode=0'),
                 marker.replace('GAUGUIN EDR318 LOADER: result=opened us=110\n',''),
                 marker.splitlines()[3]+'\n'+'\n'.join(marker.splitlines()[:3])):
        assert not runner.inspect_edr_activation(text,True)['active']
    assert not runner.inspect_edr_activation(marker,False)['active']
    analysis={'lost_rows_in_log_tail':0,'input':{'watch_covers_window':True,
        'metadata_errors_in_tail':0,'write_errors_in_tail':0}}
    assert runner.classify_edr(good,analysis)=='EDR320-default-active-cadence-observed-root-restored'
    assert runner.classify_edr({**good,'active':False},analysis)=='EDR320-activation-unqualified-root-restored'
    for key,value in [('watch_covers_window',False),('metadata_errors_in_tail',1),('write_errors_in_tail',1)]:
        bad=copy.deepcopy(analysis);bad['input'][key]=value
        assert runner.classify_edr(good,bad)=='EDR320-active-cadence-coverage-unqualified-root-restored'
    assert runner.classify_edr(good,{**analysis,'lost_rows_in_log_tail':1})=='EDR320-active-cadence-coverage-unqualified-root-restored'
    empty={'active':True,'unavailable':[],'resume_failures':0,'suspend_failures':0,
        'state_failures':0,'missing_sample_ids':[],'incomplete_frame_samples':[],
        'policy_error_samples':[],'clock_error_samples':[], 'usable_stack_samples':0,'sample_count':0}
    state=runner.classify_stacks(empty,True)
    assert state=='SpringBoard-stack-active-no-long-turn-sample-root-restored'
    assert runner.classify_process_samples(state,{'complete':True,'state':'bounded-process-samples-observed'})=='receiver-process-samples-observed-root-restored'
    for key in ('suspend_failures','state_failures'):
        assert runner.classify_stacks({**empty,key:1},True)=='SpringBoard-stack-capture-error-root-restored'


def main():
    assert (STATE/'ready.json').is_file()
    assert not (STATE/'approval.json').exists()
    assert not (STATE/'execution').exists()
    with tempfile.TemporaryDirectory(prefix='sb-trial-gate-') as temporary:
        root=Path(temporary)
        marker=root/'device-command-called'
        for command in ('adb','fastboot'):
            path=root/command
            path.write_text('#!/bin/sh\n: > '+str(marker)+'\nexit 97\n')
            path.chmod(0o700)
        env=dict(os.environ,PATH=str(root)+os.pathsep+os.environ['PATH'])
        result=subprocess.run([sys.executable,str(RUNNER)],env=env,
                              capture_output=True,text=True,timeout=10)
        assert result.returncode != 0
        assert 'no individual SpringBoard trial approval; zero device IO' in result.stderr
        assert not marker.exists() and not (STATE/'execution').exists()
    spec=importlib.util.spec_from_file_location('sb_trial',RUNNER)
    runner=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    # Evaluate the actual policy expressions in memory. These dictionaries never
    # become approval files, and neither authorization() nor device IO is called.
    function=next(n for n in ast.parse(RUNNER.read_text()).body
                  if isinstance(n,ast.FunctionDef) and n.name=='authorization')
    conditions={n.value.args[1].value:n.value.args[0] for n in function.body
                if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
                and isinstance(n.value.func,ast.Name) and n.value.func.id=='require'
                and isinstance(n.value.args[1],ast.Constant)}
    policy=compile(ast.Expression(conditions['separate user reply is not bound to this exact trial']),str(RUNNER),'eval')
    expected=ast.literal_eval(next(n.value for n in function.body
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name)and t.id=='expected'for t in n.targets)))
    answer='IN-MEMORY POLICY TEST ONLY'
    example={key:True for key in expected}
    example.update(plan_sha256='install',trial_plan_sha256='trial',image_sha256='image',
                   source='actual-user-q337-trial-reply',provenance='direct-user-message',
                   user_answer=answer,user_answer_sha256=hashlib.sha256(answer.encode()).hexdigest())
    def permits(value):
        return eval(policy,{'approval':value,'expected':expected,'hashlib':hashlib,
                            'ready':{'install_plan_sha256':'install','trial_plan_sha256':'trial'},
                            'plan':{'image_sha256':'image'}})
    assert permits(example)
    assert not permits({**example,'source':'actual-user-bo333-trial-reply'})
    assert not permits({**example,'source':'actual-user-bcreuse335-trial-reply'})
    assert not permits({**example,'source':'actual-user-bcreuse336-trial-reply'})
    assert not permits({**example,'source':'actual-user-draw329-trial-reply'})
    assert not permits({**example,'source':'actual-user-direct330-trial-reply'})
    assert not permits({**example,'source':'actual-user-keyperf331-trial-reply'})
    for field in expected:
        assert not permits({**example,field:False})
        missing=example.copy();missing.pop(field);assert not permits(missing)
    for bad in ({'source':'actual-user-submit327-trial-reply'},{'source':'actual-user-perf326-trial-reply'},{'source':'actual-user-perf325-trial-reply'},{'source':'actual-user-map324-trial-reply'},{'source':'actual-user-sc323-trial-reply'},{'source':'actual-user-fq322-trial-reply'},{'source':'actual-user-c4q321-trial-reply'},{'source':'actual-user-edr320-trial-reply'},{'source':'actual-user-edr319-trial-reply'},{'source':'actual-user-edr318-trial-reply'},
                {'fixture_only':True},{'trial_plan_sha256':'old'},
                {'provenance':'async-question-reply','question_item_id':''},
                {'user_answer_sha256':'bad'}):
        assert not permits({**example,**bad})
    scope=compile(ast.Expression(conditions['unexpected SpringBoard trial scope']),str(RUNNER),'eval')
    plan=json.loads((STATE/'trial-plan.json').read_text())
    ready=json.loads((STATE/'ready.json').read_text())
    assert eval(scope,{'plan':plan,'ready':ready,'sha':runner.sha})
    for key,value in {'profile':315,'rounds':9,'max_tasks_per_round':3,
                      'max_threads_per_task':65,'max_register_samples':1025,
                      'max_frames':17,'targets':['SpringBoard'],
                      'first_uptime_seconds':0,'maximum_start_lateness_us':1000001,'maximum_sleep_attempts_per_deadline':9,'interval_seconds':0,
                      'frame_walks_coherent':True,'hard_realtime_pause_limit':True}.items():
        changed=copy.deepcopy(plan);changed['process_sampling'][key]=value
        assert not eval(scope,{'plan':changed,'ready':ready,'sha':runner.sha})
    for key,value in {'install_userdata_bytes':10297345,'maximum_restore_userdata_bytes':10301441,
                      'normal_userdata_write_bytes_max':20598785,'maximum_userdata_write_bytes':51503105,
                      'optional_EDR_default_pointer_bytes':16,'EDR_launch_mode':'admission',
                      'once_completed_generation_supported':False,'once_runtime_contract_function_count':5,
                      'observed_busy_initializer_refused':False,'direct_once_predicate_writes':8,'additional_threads':1,'initializer_retry_count':1,
                      'recursive_region_max_depth':9,'code_mismatch_log_max_bytes':157,'unchanged_318_C4':True,'unchanged_320_helper':True,'EDR_scope_only_update':False,'EDR_helper_sha256':'old',
                      'C4_CPU_stage_trace':False,'trace_phases':9,'trace_record_limit':32769,
                      'trace_max_bytes':4194433,'trace_window_seconds':[0,900],
                      'additional_GPU_calls':1,'collector_changes':{},'queue_identity_trace':{},'capture_log_limits':{},'collection_before_backlog_interpretation':False,'unchanged_336_GPU_and_cache':False,'C4_sha256':'old','SB_sha256':'old','diagnostic_only':False,'performance_candidate':True,'BO_allocation_diagnostics':{},
                      'unchanged_321_C4':True,'owned_core_updated':False,'owned_core_sha256':'old',
                      'fault_query_negative_cache':False,'fault_query_scope':{},
                      'supported_queries_stay_live':False,'transient_errors_do_not_enable_cache':False,
                      'cache_is_per_connection':False,'compiler_object_reused':True,'stage_cache_hit_outside_lock':False,
                      'compiler_misses_serialized':False,'cache_key_and_serialization_unchanged':False,
                      'stage_cache_trace_limit':1025,'stage_cache_trace_max_bytes':1048577,
                      'stage_cache_analysis_max_bytes':2097153,'core_catalog_write':False,'fault_cache_object_sha256':'bad','cache_build_tag':'different',
                      'storage_reserve_bytes':419430400,'submission_refusal_diagnostics':{},
                      'unchanged_316_image':True,'image_sha256':'old','kernel_identity':'old','command_bytes':587,'mapping_optin':'sweetgpumap=0','unrelated_map_descriptor_fastpath':False,'unchanged_323_core':True,'mapping_noneligible_path_unchanged':False,'unchanged_324_mapping_policy':False,'unchanged_324_image':True,'unchanged_328_helper':True,'unchanged_328_image':True,'all_core_TUs_recompiled':True,'unchanged_331_core':True,'surface_retirement':{},'unchanged_333_image':True,'unchanged_333_helper':True,'unchanged_334_core':False,'completed_owned_BO_cache':{},'cache_full_replacement':{},'unchanged_335_core':False,'display_retry':{},'additional_GPU_calls_scope':'unrestricted','bounded_draw_scratch':{},'direct_constant_packets':{},'state_key_reuse':{},'process_sampling_time_origin':'thread-start-delay','GPU_native_profile':{},'dynamic_frequency_governor':True,'GPU_frequency_measured':True,'explicit_C4_loader_after_completion':False,'loader_first_call_pool':False}.items():
        changed=copy.deepcopy(plan);changed[key]=value
        assert not eval(scope,{'plan':changed,'ready':ready,'sha':runner.sha})
    assert runner.classify_observer({'observer_seen':True,'records_in_window':1,'input':{'hook_active':True}},False) == \
        'SpringBoard-log-tail-ambiguous-root-restored'
    assert runner.classify_observer({'observer_seen':False,'records_in_window':0},True) == \
        'SpringBoard-observer-not-seen-root-restored'
    assert runner.classify_observer({'observer_seen':True,'records_in_window':0},True) == \
        'SpringBoard-observer-active-no-samples-root-restored'
    assert runner.classify_observer({'observer_seen':True,'records_in_window':1,'input':{'hook_active':True}},True) == \
        'SpringBoard-cadence-observed-root-restored'
    assert runner.classify_observer({'observer_seen':True,'records_in_window':1,'input':{'hook_active':False}},True)=='SpringBoard-input-hook-not-active-root-restored'
    stack={'active':True,'unavailable':[],'resume_failures':0,'missing_sample_ids':[],
           'incomplete_frame_samples':[],'policy_error_samples':[],'clock_error_samples':[],
           'usable_stack_samples':1,'sample_count':1,'suspend_failures':0,'state_failures':0}
    assert runner.classify_stacks(stack,True)=='SpringBoard-stack-observed-root-restored'
    assert runner.classify_stacks(stack,False)=='SpringBoard-stack-constructor-missing-root-restored'
    assert runner.classify_stacks({**stack,'active':False},True)=='SpringBoard-stack-probe-unavailable-root-restored'
    assert runner.classify_stacks({**stack,'unavailable':['mach-context']},True)=='SpringBoard-stack-probe-unavailable-root-restored'
    assert runner.classify_stacks({**stack,'resume_failures':1},True)=='SpringBoard-stack-resume-failure-root-restored'
    for key in ('missing_sample_ids','incomplete_frame_samples','policy_error_samples','clock_error_samples'):
        assert runner.classify_stacks({**stack,key:[1]},True)=='SpringBoard-stack-log-unqualified-root-restored'
    assert runner.classify_stacks({**stack,'usable_stack_samples':0},True)=='SpringBoard-no-qualified-stack-root-restored'
    qualified={'complete':True,'state':'bounded-process-samples-observed'}
    assert runner.classify_process_samples('SpringBoard-stack-observed-root-restored',qualified)=='receiver-process-samples-observed-root-restored'
    for bad in ({'complete':False,'state':'bounded-process-samples-observed'},{'complete':True,'state':'process-samples-incomplete-or-unqualified'}):
        assert runner.classify_process_samples('SpringBoard-stack-observed-root-restored',bad)=='receiver-process-samples-unqualified-root-restored'
    assert runner.classify_process_samples('SpringBoard-stack-resume-failure-root-restored',qualified)=='SpringBoard-stack-resume-failure-root-restored'
    check_edr_classification(runner)
    print('Q 0337 gate refused before any device command; observation classification checked')


if __name__=='__main__':
    main()
