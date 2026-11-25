#!/usr/bin/env python3
"""One separately approved SpringBoard rate-observer boot and exact restoration."""

import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


WORK = Path(__file__).resolve().parents[1]
MAIN = Path('/Users/baai/Project/ios-gauguin')
STATE = WORK/'research/tmp/queue-loss-337'
EXEC = STATE/'execution'
LOG_PATHS = ('/private/var/tmp/gauguin-gles180.log',
             '/private/var/tmp/gauguin-gles180.stderr.log',
             '/private/var/log/backboardd.log',
             '/private/var/log/springboard.log')
SPRINGBOARD_LOG = '/private/var/log/springboard.log'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def require(ok,why):
    if not ok:
        raise ValueError(why)


def load(path):
    return json.loads(Path(path).read_bytes())


def save(path,data):
    with Path(path).open('x') as stream:
        json.dump(data,stream,indent=2)
        stream.write('\n')


def link_saved_log(source,target):
    """Alias an immutable local capture; fail rather than allocate another copy."""
    require(source.is_file() and not source.is_symlink(),'missing regular saved log')
    os.link(source,target)
    require(os.path.samefile(source,target),'saved log alias differs')


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def authorization(plan_path,ready_path,approval_path):
    """All checks here precede device IO and an execution directory claim."""
    plan,ready = load(plan_path),load(ready_path)
    require(ready['state']=='ready-q337-one-shot' and
            ready['trial_plan_sha256']==sha(plan_path) and
            ready['install_plan_sha256']==sha(STATE/'slot-delta/install-plan.json') and
            ready['image_sha256']==plan['image_sha256'], 'reviewed trial pins differ')
    require(approval_path.exists(), 'no individual SpringBoard trial approval; zero device IO')
    approval = load(approval_path)
    expected = ('approved','one_shot','allow_install','allow_restore','allow_rollback',
                'allow_misc_marker','allow_temporary_boot','allow_recovery_fallback',
                'allow_scripted_input','allow_wake_button','allow_main_thread_sampling','allow_process_sampling','allow_optional_edr_default','allow_explicit_C4_loader','allow_completed_once_generation','allow_C4_CPU_stage_trace','allow_owned_core_update','allow_fault_query_negative_cache','allow_compiler_cache_lock_change','allow_stage_cache_CPU_trace','allow_kernel_update','allow_unrelated_map_descriptor','allow_EDR_kernel_scope_update','allow_native_GPU_performance_profile','allow_native_GPU_bandwidth_profile','allow_submit_refusal_diagnostics','allow_absolute_uptime_sampling','allow_bounded_draw_scratch','allow_direct_constant_packets','allow_state_key_reuse','allow_bounded_present_retry','allow_BO_allocation_CPU_trace','allow_surface_retirement','allow_completed_owned_BO_cache','allow_cache_full_replacement','allow_concurrent_trace_collectors','allow_queue_identity_CPU_trace')
    require(all(approval.get(key) is True for key in expected) and
            approval.get('fixture_only') is not True and
            approval.get('plan_sha256')==ready['install_plan_sha256'] and
            approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
            approval.get('image_sha256')==plan['image_sha256'] and
            approval.get('source')=='actual-user-q337-trial-reply' and
            approval.get('provenance') in ('direct-user-message','async-question-reply') and
            (approval.get('provenance')!='async-question-reply' or
             (isinstance(approval.get('question_item_id'),str) and approval['question_item_id'])) and
            isinstance(approval.get('user_answer'),str) and approval['user_answer'].strip() and
            approval.get('user_answer_sha256')==hashlib.sha256(approval['user_answer'].encode()).hexdigest(),
            'separate user reply is not bound to this exact trial')
    require(plan['state']=='prepared-q337-one-shot' and
            plan['install_plan_sha256']==ready['install_plan_sha256'] and
            plan['image_sha256']==sha(plan['image']) and
            plan['observer_helper'] in ready['input_pins'] and
            plan['image'] in ready['input_pins'] and
            plan['temporary_boots']==1 and plan['boot_retries']==0 and
            plan['install_userdata_bytes']==10301440 and
            plan['maximum_restore_userdata_bytes']==10305536 and
            plan['normal_userdata_write_bytes_max']==20606976 and
            plan['maximum_userdata_write_bytes']==51523584 and
            plan['misc_write_bytes']==13 and plan['observer_seconds']==780 and
            plan['failed_restore_retry_limit']==1 and
            plan['maximum_fastboot_reboot_recovery_fallbacks']==1 and
            plan['storage_reserve_bytes']==671088640 and
            plan['no_new_files_or_HFSX_allocations'] is True and
            plan['diagnostic_only'] is True and plan['performance_candidate'] is False and plan['optional_EDR_default_pointer_bytes']==8 and
            plan['once_completed_generation_supported'] is True and plan['once_runtime_contract_function_count']==6 and
            plan['observed_busy_initializer_refused'] is True and plan['direct_once_predicate_writes']==0 and
            plan['initializer_retry_count']==0 and plan['additional_threads']==0 and
            plan['recursive_region_max_depth']==8 and plan['code_mismatch_log_max_bytes']==156 and plan['unchanged_318_C4'] is False and plan['unchanged_320_helper'] is False and plan['EDR_scope_only_update'] is True and
            plan['EDR_helper_sha256']=='6bc54af153975708b05107c51333aff545b0a4e595e048473c395551a11f735f' and
            plan['C4_CPU_stage_trace'] is True and plan['trace_phases']==10 and
            plan['trace_record_limit']==32768 and plan['trace_max_bytes']==4194432 and
            plan['trace_window_seconds']==[220,270] and plan['additional_GPU_calls']==0 and
            plan['unchanged_321_C4'] is False and plan['C4_sha256']=='d4e46b8e8541d3a674a6e814170b27d4d930b5d301f25dc016b5f7c9da34b6f3' and plan['SB_sha256']=='3f6dba175451498e190f17bd4043cba5a79c377127b0422c1111fe3ba38b0925' and plan['owned_core_updated'] is True and
            plan['owned_core_sha256']=='dc26b7b613345f84d2e8e2636a1948be75b3d400418291e3b2281176a4070954' and
            plan['fault_query_negative_cache'] is True and
            plan['fault_query_scope']=={'request':64,'pipe':16,'param':9,'value':0,'len':0,'pad':0} and
            plan['supported_queries_stay_live'] is True and plan['transient_errors_do_not_enable_cache'] is True and
            plan['cache_is_per_connection'] is True and plan['compiler_object_reused'] is False and
            plan['stage_cache_hit_outside_lock'] is True and plan['compiler_misses_serialized'] is True and
            plan['cache_key_and_serialization_unchanged'] is True and plan['stage_cache_trace_limit']==1024 and
            plan['stage_cache_trace_max_bytes']==1048576 and plan['stage_cache_analysis_max_bytes']==2097152 and
            plan['core_catalog_write'] is True and
            plan['fault_cache_object_sha256']=='75503992b3fc6bbc60efe1490ef745e9b16221c792cbd853a4afb75a602f04d3' and
            plan['cache_build_tag']=='8a71fe61aded108fa9ba5a22' and
            plan['EDR_launch_mode']=='edr-default318' and plan['unchanged_316_image'] is False and
            plan['image_sha256']=='765e7c7cc2efb84d24ee1404f94b3f866dcf98e04e6a755d53a808b35a3841f3' and
            plan['kernel_identity']=='xnu-local337-d846caeab5924ac49b8ac8802e070e95' and
            plan['command_bytes']==607 and plan['mapping_optin']=='sweetgpumap=1' and
            plan['unrelated_map_descriptor_fastpath'] is True and plan['unchanged_323_core'] is False and
            plan['mapping_noneligible_path_unchanged'] is True and
            plan['unchanged_324_mapping_policy'] is True and plan['unchanged_324_image'] is False and
            plan['unchanged_328_helper'] is False and plan['unchanged_328_image'] is False and
            plan['bounded_draw_scratch']=={'streams':4,'maximum_retained_bytes_per_CB':65536,'reset_on_scope_exit':True,'additional_GPU_commands':0,'additional_threads':0} and plan['all_core_TUs_recompiled'] is False and plan['unchanged_331_core'] is False and plan['unchanged_333_image'] is False and plan['unchanged_333_helper'] is False and plan['unchanged_334_core'] is True and plan['unchanged_335_core'] is True and plan['cache_full_replacement']=={'maximum_mappings_removed_per_return': 1, 'rotating_cursor': True, 'single_victim_must_satisfy_byte_limit': True, 'insufficient_single_victim_releases_new': True, 'cache_slots': 32, 'cache_bytes': 16777216, 'eligible_completed_owned_only': True, 'failure_keeps_DMA_escrow': True, 'new_GPU_commands': 0, 'new_threads': 0} and plan['completed_owned_BO_cache']=={'slots':32,'bytes':16777216,'max_bo_bytes':1048576,'exact_size_and_flags':True,'zero_before_new_handle':True,'no_IOSurface':True,'no_exported_alias':True,'completed_only':True,'residency_includes_cache':True,'allocator_retry_max':1,'reuse_event_kind':33,'maximum_records_per_BO_request':7,'new_GPU_commands':0,'new_threads':0} and plan['surface_retirement']=={'close_before_reimport':True,'wait_releases_cache_mutex':True,'weak_owner_identity_checked':True,'exception_safe_publication':True,'Buffer_layout_unchanged':True,'wait_pairs_max':64,'record_max_bytes':128,'analysis_max_bytes':131072,'result_copy_max_bytes':65536,'additional_threads':0,'additional_GPU_submissions':0,'hard_wait_limit':False} and
            plan['direct_constant_packets']=={'prefix_words':3,'maximum_packet_words':16383,'padding_words_max':3,'preflight_before_mutation':True,'reserve_before_append':True,'additional_GPU_commands':0,'additional_threads':0} and
            plan['GPU_native_profile']=={'argument':'gpf=4','frequency_hz':565000000,'perf_index':4,'bw_index':9,'bandwidth_bytes_per_second':5412000000,'ARC_virtual_level':256,'GX_index':4,'MX_index':5} and
            plan['state_key_reuse']=={'stack_key_bytes':325,'compile_time_bytes_limit':1024,'reuse_pass_storage':True,'contents_and_comparison_unchanged':True,'additional_GPU_commands':0,'additional_threads':0} and
            plan['additional_GPU_calls_scope']=='C4 CPU instrumentation only' and
            plan['display_retry']=={'maximum_additional_attempts_per_frame':8,'maximum_total_attempts_per_frame':9,'one_pending_one_active':True,'newer_pending_preferred':True,'owner_power_epoch_checked':True,'epoch_wrap_disables_retry':True,'GPU_read_guards_retained':True,'additional_GPU_submissions':0,'additional_threads':0,'readiness_reported_in_present_end_flag':1} and
            plan['BO_allocation_diagnostics']=={'event_kind': 32, 'maximum_records_per_new_BO': 6, 'capture_capacity': 4096, 'capture_window_seconds': 4, 'numeric_thread_id': True, 'new_GPU_calls': 0, 'new_MMIO_reads': 0, 'original_validators_waits_ownership_preserved': True, 'analysis_max_bytes': 4194304, 'result_copy_max_bytes': 65536} and
            plan['submission_refusal_diagnostics']=={'records_max':64,'record_bytes_max':235,'serial_payload_bytes':255,'fixed_hex_fields':22,'limit_markers_max':1,'analysis_max_bytes':131072,'new_GPU_calls':0,'new_MMIO_reads':0,'return_values_and_ownership_unchanged':True} and
            plan['dynamic_frequency_governor'] is False and plan['GPU_frequency_measured'] is False and plan['explicit_C4_loader_after_completion'] is True and plan['loader_first_call_pool'] is True and plan['wake_button_pairs_max']==1 and
            plan['scripted_strokes']==13 and plan['require_display_on'] is True and
            plan['async_compositor'] is True and plan['observer_python_utf8'] is True and
            plan['main_thread_sampling']=={'version':315,'start_us':220000000,'end_us':270000000,'period_us':1000000,'min_turn_us':250000,'budget_us':2000,'max_samples':64,'depth':16,'stack_window_bytes':65536,'hard_realtime_pause_limit':False} and
            plan['process_sampling']=={'profile':328,'targets':['SpringBoard','backboardd'],'first_uptime_seconds':220,'interval_seconds':6,'rounds':8,'max_tasks_per_round':2,'max_threads_per_task':64,'max_register_samples':1024,'max_frames':16,'frame_walks_coherent':False,'hard_realtime_pause_limit':False,'maximum_start_lateness_us':1000000,'maximum_sleep_attempts_per_deadline':8} and
            plan['process_sampling_time_origin']=='mach_absolute_time-boot-uptime' and
            plan['physical_FPS_qualified'] is False and
            plan['collector_changes']=={'kernel_wire_version':2,'kernel_capacity':4096,'kernel_writers':'atomic-reservation','freeze_waits_for_admitted_writers':True,'late_close_errors_retained':True,'SB_slots':1024,'SB_producer_mutex':False,'new_threads':0} and
            plan['queue_identity_trace']=={'stages':3,'record_limit':32768,'line_max_bytes':192,'trace_max_bytes':6291648,'per_lifetime_queue_id':True,'admission_ticket':True,'retire_after_explicit_release':True,'retire_excludes_final_logging_and_block_destruction':True,'unobserved_interior_tickets_refused':True} and
            plan['capture_log_limits']=={'backboard':23068672,'springboard':41943040} and
            plan['collection_before_backlog_interpretation'] is True and plan['unchanged_336_GPU_and_cache'] is True and
            plan['retry_only_after_verified_rollback'] is True,
            'unexpected SpringBoard trial scope')
    require(not EXEC.exists(), 'one-shot execution already claimed')
    for path,digest in ready['input_pins'].items():
        require(sha(path)==digest,'reviewed input changed: '+path)
    budget = subprocess.run([sys.executable,str(MAIN/'tools/storage-budget.py'),
                             '--planned-bytes',str(plan['storage_reserve_bytes'])],
                            capture_output=True,text=True,timeout=600)
    require(budget.returncode==0 and json.loads(budget.stdout)['admitted'] is True,
            'trial storage reserve no longer admitted')
    return plan,ready,approval,json.loads(budget.stdout)


def static_compare(before,after):
    require(set(before['files'])==set(after['files']) and
            before['directories']==after['directories'], 'root file/directory set changed')
    for path,old in before['files'].items():
        new = after['files'][path]
        require(old['present'] and new['present'] and
                all(old[key]==new[key] for key in ('uid','gid','mode')),
                'root file metadata changed: '+path)
        if path not in LOG_PATHS:
            require(all(old[key]==new[key] for key in ('bytes','sha256','fork')),
                    'static root file changed: '+path)


def capture_as(name,phase,header,capture):
    profile = load(STATE/'capture-profile.json')
    profile['out'] = str((EXEC/name).relative_to(MAIN))
    profile['phase'] = phase
    profile['expected_header_sha256'] = header
    return capture(profile)


def recovery_for_rollback(RecoveryIO,approval,state):
    try:
        return RecoveryIO()
    except Exception as original:
        require(approval.get('allow_recovery_fallback') is True and state['attempts']==0,
                'recovery fallback not approved or already used')
        found = subprocess.run(['fastboot','devices'],capture_output=True,text=True,timeout=5)
        rows = [line.split() for line in found.stdout.splitlines() if line.strip()]
        require(len(rows)==1 and len(rows[0])>=2 and rows[0][1]=='fastboot',
                'neither recovery nor one fastboot device available')
        serial = rows[0][0]
        product = subprocess.run(['fastboot','-s',serial,'getvar','product'],
                                 capture_output=True,text=True,timeout=5)
        require(product.returncode==0 and 'product: gauguinpro' in product.stdout+product.stderr,
                'rollback fastboot product differs')
        state['attempts'] += 1
        reboot = subprocess.run(['fastboot','-s',serial,'reboot','recovery'],
                                capture_output=True,text=True,timeout=10)
        require(reboot.returncode==0,'fastboot recovery fallback failed')
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            try:return RecoveryIO()
            except Exception:time.sleep(2)
        raise RuntimeError('recovery did not return after bounded fallback') from original


def fastboot_identity():
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        found=subprocess.run(['fastboot','devices'],capture_output=True,text=True,timeout=5)
        rows=[line.split() for line in found.stdout.splitlines() if line.strip()]
        if rows:
            require(len(rows)==1 and len(rows[0])>=2 and rows[0][1]=='fastboot',
                    'ambiguous fastboot devices')
            serial=rows[0][0]
            product=subprocess.run(['fastboot','-s',serial,'getvar','product'],
                                   capture_output=True,text=True,timeout=5)
            require(product.returncode==0 and 'product: gauguinpro' in product.stdout+product.stderr,
                    'wrong fastboot product')
            return serial
        time.sleep(1)
    raise RuntimeError('fastboot did not become ready; no boot retry')


def marker_rollback(io,before,READ,WRITE,MARKER):
    actual=io.run(io.adb+['exec-out',READ]).stdout
    require(actual==MARKER+before[len(MARKER):],
            'misc changed since marker write; no stale rollback')
    io.run(io.adb+['exec-in',WRITE],data=before[:len(MARKER)])
    require(io.run(io.adb+['exec-out',READ]).stdout==before,
            'preboot misc marker restoration readback failed')


def validate_wake_log(kernel):
    wake=re.findall(r'SWEET UI WAKE: display-on confirmed tick=(\d+); begin workload',kernel)
    begins=re.findall(r'SWEET UI SCRIPT: begin stroke=(\d+) tick=(\d+) origin=synthetic',kernel)
    ends=re.findall(r'SWEET UI SCRIPT: end stroke=(\d+) tick=(\d+) events=34;',kernel)
    power=[(int(tick),int(state)) for state,tick in re.findall(r'SWEET FB POWER: state=(\d+) tick=(\d+);',kernel)]
    presses=re.findall(r'SWEET UI WAKE: power press tick=(\d+) state=off',kernel)
    releases=re.findall(r'SWEET UI WAKE: power release tick=(\d+); one pair only',kernel)
    require([int(n)for n,_ in begins]==list(range(13)) and [int(n)for n,_ in ends]==list(range(13)),
         'stroke IDs missing, duplicated or reordered')
    require(all(int(b)<=int(e) for (_,b),(_,e) in zip(begins,ends)) and
         all(int(ends[i][1])<int(begins[i+1][1]) for i in range(12)),
         'stroke intervals overlap or reverse')
    require(len(wake)==1 and len(begins)==len(ends)==13 and int(wake[0])<=int(begins[0][1]),
         'display-on workload gate did not qualify')
    require(len(presses)==len(releases) and len(presses)<=1,'wake button pair missing or repeated')
    if presses:require(int(presses[0])<=int(releases[0])<=int(wake[0]),'wake button timing invalid')
    before=sorted((tick,state)for tick,state in power if tick<=int(begins[0][1]))
    require(before and before[-1][1]==1 and not any(state!=1 for tick,state in power
         if int(begins[0][1])<=tick<=int(ends[-1][1])), 'display off/unknown during workload')
    return {'button_pairs':len(presses),'first_stroke_tick':int(begins[0][1]),'last_release_tick':int(ends[-1][1])}


def classify_observer(analysis,prefix_preserved):
    if not prefix_preserved:
        return 'SpringBoard-log-tail-ambiguous-root-restored'
    if not analysis['observer_seen']:
        return 'SpringBoard-observer-not-seen-root-restored'
    if not analysis['records_in_window']:
        return 'SpringBoard-observer-active-no-samples-root-restored'
    if not analysis['input']['hook_active']:
        return 'SpringBoard-input-hook-not-active-root-restored'
    return 'SpringBoard-cadence-observed-root-restored'


def classify_stacks(stacks,constructor_seen):
    if not constructor_seen:return 'SpringBoard-stack-constructor-missing-root-restored'
    if not stacks['active'] or stacks['unavailable']:return 'SpringBoard-stack-probe-unavailable-root-restored'
    if stacks['resume_failures']:return 'SpringBoard-stack-resume-failure-root-restored'
    if any(stacks[key] for key in ('missing_sample_ids','incomplete_frame_samples','policy_error_samples','clock_error_samples')):
        return 'SpringBoard-stack-log-unqualified-root-restored'
    if stacks['suspend_failures'] or stacks['state_failures']:
        return 'SpringBoard-stack-capture-error-root-restored'
    if stacks['sample_count']==0:return 'SpringBoard-stack-active-no-long-turn-sample-root-restored'
    if stacks.get('version')==359 and not stacks['usable_stack_samples']:
        return 'SpringBoard-stack-active-no-long-turn-sample-root-restored'
    if not stacks['usable_stack_samples']:return 'SpringBoard-no-qualified-stack-root-restored'
    return 'SpringBoard-stack-observed-root-restored'


def classify_process_samples(prior,processes):
    if prior not in ('SpringBoard-stack-observed-root-restored','SpringBoard-stack-active-no-long-turn-sample-root-restored'):return prior
    if not processes['complete'] or processes['state']!='bounded-process-samples-observed':
        return 'receiver-process-samples-unqualified-root-restored'
    return 'receiver-process-samples-observed-root-restored'


def inspect_edr_activation(backboard,prefix_preserved):
    helper_prefix='GAUGUIN EDR320: ';loader_prefix='GAUGUIN EDR318 LOADER: '
    helpers=[(i,line[line.index(helper_prefix):]) for i,line in enumerate(backboard.splitlines()) if helper_prefix in line]
    loaders=[(i,line[line.index(loader_prefix):]) for i,line in enumerate(backboard.splitlines()) if loader_prefix in line]
    expected_entry=helper_prefix+'entry os_read=1 kernel_read=1 args_read=1 scope=1'
    expected_success=helper_prefix+'optional-query result=1 slot_null=1 bytes=8 code_writes=0'
    hashes=(('initializer','a5c01abf3fd26dce1209234ee6786e53339c5b74df917ccc32d08f16afbe78f7'),
            ('callback','57a8089a33acefd10a675e6ad7b947a8cc452bc76dfef2bbea6b516bdaa72dba'))
    checks=[]
    if len(helpers)>=3:
        for (_,line),(name,digest) in zip(helpers[1:3],hashes):
            match=re.fullmatch(re.escape(helper_prefix+'code-check name='+name)+
                r' region=1 kr=0 count=12 depth=([0-8]) protection=(\d+) hashed=1 hash=1 sha256='+digest,line)
            checks.append(bool(match and int(match[2]) & 5 == 5))
    code_ok=len(checks)==2 and all(checks)
    abi_ok=len(helpers)>=4 and helpers[3][1]==helper_prefix+'once-abi checks=6 passed=1'
    once_before=once_after=None
    if len(helpers)>=6:
        once_before=re.fullmatch(re.escape(helper_prefix)+r'once before=0x([0-9a-f]{16}) eligible=1',helpers[4][1])
        once_after=re.fullmatch(re.escape(helper_prefix)+r'once after=0x([0-9a-f]{16}) complete=1',helpers[5][1])
    completed=lambda value:value==(1<<64)-1 or value&3==2
    once_ok=bool(once_before and once_after and
                 (int(once_before[1],16)==0 or completed(int(once_before[1],16))) and completed(int(once_after[1],16)))
    legacy=[line for line in backboard.splitlines() if 'GAUGUIN GPU PILOT' in line]
    begin=end=None
    if len(loaders)==2:
        begin=re.fullmatch(re.escape(loader_prefix)+r'entry us=(\d+) identity=1 mode=1',loaders[0][1])
        end=re.fullmatch(re.escape(loader_prefix)+r'result=opened us=(\d+)',loaders[1][1])
    ordered=(len(helpers)==7 and len(loaders)==2 and
             loaders[0][0]<helpers[0][0]<helpers[-1][0]<loaders[1][0])
    clock_ok=bool(begin and end and 0<int(begin[1])<=int(end[1])<1<<64)
    active=(prefix_preserved and ordered and code_ok and abi_ok and once_ok and helpers[0][1]==expected_entry and
            helpers[-1][1]==expected_success and clock_ok and not legacy)
    return dict(active=active,code_checks_qualified=code_ok,once_abi_qualified=abi_ok,once_state_checks_qualified=once_ok,
        once_before='0x'+once_before[1]if once_before else None,once_after='0x'+once_after[1]if once_after else None,activation_lines=[line for _i,line in helpers],
        loader_lines=[line for _i,line in loaders],loader_duration_us=int(end[1])-int(begin[1])if clock_ok else None,
        legacy_pilot_lines=legacy,log_prefix_preserved=prefix_preserved,physical_fps_qualified=False)


def classify_edr(edr,analysis):
    if not edr['active']:return 'EDR320-activation-unqualified-root-restored'
    inputs=analysis['input']
    if (not inputs['watch_covers_window'] or analysis['lost_rows_in_log_tail'] or
        inputs['metadata_errors_in_tail'] or inputs['write_errors_in_tail']):
        return 'EDR320-active-cadence-coverage-unqualified-root-restored'
    return 'EDR320-default-active-cadence-observed-root-restored'


def inspect_fault_query_cache(backboard,kernel,prefix_preserved):
    """Activation evidence and aggregate counters, never a claimed FPS result."""
    lines=[line for line in backboard.splitlines() if line.startswith('GAUGUIN FQ322:')]
    expected='GAUGUIN FQ322: unsupported_cached=1 request=64 param=9'
    headers=re.findall(r'^SWEET GPU API PERF: valid=(\d+) pending=(\d+) selector=[0-9a-f]+ .*$',kernel,re.M)
    api=re.findall(r'^SWEET GPU API PERF: selector=40 calls=(\d+) failures=(\d+) queue_ns=(\d+) held_ns=(\d+) max_held_ns=(\d+) wait_ns=(\d+); held excludes unlocked wait$',kernel,re.M)
    service=re.findall(r'^SWEET GPU SERVICE: final renewals=(\d+) submitted=(\d+) completed=(\d+) shadow=\d+; quarantined, no further refresh$',kernel,re.M)
    counters=None
    if headers==[('1','0')] and len(api)==len(service)==1:
        calls,failures,queued,held,peak,wait=map(int,api[0])
        renewals,submitted,completed=map(int,service[0])
        if 0<failures<=calls and peak<=held and 0<submitted==completed:
            counters=dict(get_param_calls=calls,get_param_failures=failures,
                get_param_queue_ns=queued,get_param_held_ns=held,
                get_param_max_held_ns=peak,get_param_unlocked_wait_ns=wait,
                submitted=submitted,completed=completed,renewals=renewals,
                get_param_failures_per_submission=failures/submitted)
    return dict(active=prefix_preserved and lines==[expected] and counters is not None,
        transition_lines=lines,log_prefix_preserved=prefix_preserved,counters=counters,
        counter_scope='whole-service aggregate GET_PARAM counts, not per-frame fault-query attribution',
        physical_fps_qualified=False)


def main():
    plan_path,ready_path,approval_path=(STATE/'trial-plan.json',STATE/'ready.json',
                                        STATE/'approval.json')
    plan,ready,approval,budget=authorization(plan_path,ready_path,approval_path)
    sys.path[:0]=[str(MAIN/'research/tmp/dsh-0175'),
                 str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112'),
                 str(MAIN/'research/tmp/metal-hardware-repeat2-20261112'),str(MAIN/'tools')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote
    capture=module('cadence_capture',WORK/'tools/capture-sb-cadence-root.py').capture
    from recovery_marker import READ,WRITE,MARKER,set_recovery_marker
    install_core=module('sb_install',WORK/'tools/sb-cadence-slot-install-io.py')
    restore_build=module('sb_restore_build',WORK/'tools/build-sb-cadence-restore.py')
    restore_core=module('sb_restore_io',WORK/'tools/sb-cadence-slot-restore-io.py')
    rate_log=module('sb_rate_log',WORK/'tools/analyze-sb-rate-log.py')
    ui_log=module('ui_trace_log',WORK/'tools/ui_trace_log.py')
    joint_log=module('joint_cadence',WORK/'tools/analyze-sb-cadence.py')
    stack_log=module('stack_log',WORK/'tools/analyze-sb-stack-log.py')
    process_log=module('process_log',WORK/'tools/analyze-process-samples328.py')
    EXEC.mkdir(exist_ok=False)
    save(EXEC/'claim.json',{'pid':os.getpid(),'started':time.time(),
                            'trial_plan_sha256':ready['trial_plan_sha256'],
                            'approval_sha256':sha(approval_path)})
    save(EXEC/'storage-preflight.json',budget)
    def report(row):
        with (EXEC/'progress.jsonl').open('a') as stream:
            json.dump(row,stream);stream.write('\n')
            stream.flush();os.fsync(stream.fileno())
    result={'state':'preflight','boot_attempts':0,'partition_write_phase':'none'}
    installed=marker_written=boot_started=restored=restore_attempted=False
    fallback={'attempts':0}
    before_misc=None
    base_plan=STATE/'slot-delta'
    capture_dir=STATE/'slot-capture'
    try:
        before=capture_as('fresh-before','before-boot',plan['root_header_sha256'],capture)
        static_compare(load(STATE/'expected-baseline.json'),before)
        io=RecoveryIO()
        before_sb=(EXEC/'fresh-before'/before['files'][SPRINGBOARD_LOG]['output']).read_bytes()
        link_saved_log(EXEC/'fresh-before'/before['files'][SPRINGBOARD_LOG]['output'],EXEC/'springboard-before.log')
        before_misc=(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112/device-candidate/misc-before.bin').read_bytes()
        require(len(before_misc)==4096 and hashlib.sha256(before_misc).hexdigest()==plan['misc_before_sha256'] and
                io.run(io.adb+['exec-out',READ]).stdout==before_misc,
                'misc preimage changed')
        installed_result=install_core.install(base_plan,capture_dir,approval,io,HFS,Remote,report)
        installed=installed_result['state']=='install-applied-and-HFSX-verified'
        save(EXEC/'install-result.json',installed_result)
        require(installed_result['state']=='install-applied-and-HFSX-verified',
                'installation failed or rolled back')
        result['partition_write_phase']='observer-installed'
        marker=set_recovery_marker(io,{'misc_recovery_marker_approved':True,
                                       'allow_rollback':True,
                                       'misc_backup_sha256':plan['misc_before_sha256']},before_misc)
        marker_written=True
        save(EXEC/'marker-result.json',marker)
        io.run(io.adb+['reboot','bootloader'])
        fastboot_identity()
        with (EXEC/'observer.log').open('x') as log:
            child=subprocess.Popen(['bash',plan['observer_helper'],plan['image'],
                                    str(EXEC/'kernel.log'),str(plan['observer_seconds'])],
                                   stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONUTF8='1'))
            boot_started=True
            result['boot_attempts']=1
            save(EXEC/'observer-process.json',{'pid':child.pid,'pgid':child.pid,
                                               'image_sha256':plan['image_sha256'],
                                               'boot_attempts':1})
            try:code=child.wait(timeout=plan['observer_seconds']+80)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGTERM)
                child.wait(timeout=10)
                raise RuntimeError('observer timed out; no boot retry')
        result['observer_exit']=code
        if code==5:
            boot_started=False
        require(code!=5,'fastboot boot failed before temporary launch')
        ps=subprocess.run(['ps','-axo','pid=,pgid=,comm='],capture_output=True,text=True,check=True)
        require(not [line for line in ps.stdout.splitlines()
                     if len(line.split(None,2))==3 and line.split(None,2)[1]==str(child.pid)],
                'observer process group remains live')
        io=recovery_for_rollback(RecoveryIO,approval,fallback)
        after_boot=capture_as('post-capture','after-boot',None,capture)
        after_sb=(EXEC/'post-capture'/after_boot['files'][SPRINGBOARD_LOG]['output']).read_bytes()
        link_saved_log(EXEC/'post-capture'/after_boot['files'][SPRINGBOARD_LOG]['output'],EXEC/'springboard-after.log')
        result['springboard_log_prefix_preserved']=after_sb.startswith(before_sb)
        (EXEC/'springboard-new.log').write_bytes(
            after_sb[len(before_sb):] if result['springboard_log_prefix_preserved'] else after_sb)
        for path in LOG_PATHS:
            old_file=(EXEC/'fresh-before'/before['files'][path]['output']).read_bytes()
            new_file=(EXEC/'post-capture'/after_boot['files'][path]['output']).read_bytes()
            preserved=new_file.startswith(old_file)
            result.setdefault('other_log_prefix_preserved',{})[path]=preserved
            tail=EXEC/(before['files'][path]['output']+'.current')
            if path==SPRINGBOARD_LOG:
                link_saved_log(EXEC/'springboard-new.log',tail)
            else:
                tail.write_bytes(new_file[len(old_file):] if preserved else new_file)
        dynamic=restore_build.prepare(base_plan,capture_dir,io,HFS,Remote,
                                      EXEC/'restore-inputs')
        restored_result=restore_core.restore(base_plan,EXEC/'restore-inputs',approval,
                                             io,HFS,Remote,report)
        restore_attempted=True
        save(EXEC/'restore-result.json',restored_result)
        if restored_result['state']=='restore-failed-rollback-verified':
            io=recovery_for_rollback(RecoveryIO,approval,fallback)
            dynamic=restore_build.prepare(base_plan,capture_dir,io,HFS,Remote,
                                          EXEC/'retry-restore-inputs')
            restored_result=restore_core.restore(base_plan,EXEC/'retry-restore-inputs',approval,
                                                 io,HFS,Remote,report)
            save(EXEC/'retry-restore-result.json',restored_result)
        require(restored_result['state']=='restore-applied-and-readback-verified',
                'postboot restoration failed or rolled back')
        restored=True;result['partition_write_phase']='original-files-restored'
        final=capture_as('restored-capture','after-boot',after_boot['root_header_sha256'],capture)
        static_compare(before,final)
        require(code==0 and (EXEC/'kernel.log').is_file(),
                'observer failed or kernel log absent')
        kernel=(EXEC/'kernel.log').read_text(errors='replace')
        require(plan['kernel_banner'] in kernel,'kernel banner not from pinned observer image')
        native_perf_log=module('native_perf_log',WORK/'tools/analyze-native-perf-log.py')
        native_perf=native_perf_log.analyze(kernel)
        require(len((json.dumps(native_perf,indent=2)+'\n').encode())<=65536,
                'native performance analysis exceeds reserved bytes; originals already restored')
        save(EXEC/'native-perf-analysis.json',native_perf)
        result['native_performance_profile']=native_perf
        retry_log=module('present_retry_log',WORK/'tools/analyze-present-retry-log.py')
        present_retry=retry_log.analyze(kernel)
        require(len((json.dumps(present_retry,indent=2)+'\n').encode())<=65536,
                'display retry analysis exceeds reserved bytes; originals already restored')
        save(EXEC/'present-retry-analysis.json',present_retry)
        result['display_retry_analysis']={key:value for key,value in present_retry.items() if key!='rows'}
        allocation_log=module('bo_reuse_log',WORK/'tools/analyze-bo-reuse-log.py')
        try:
            allocation=allocation_log.analyze(kernel,ui_log)
        except ValueError as error:
            allocation={'state':'BC336-reuse-parser-rejected','coverage_qualified':False,
                        'error':str(error),'device_commands':0,'physical_FPS_qualified':False}
        require(len((json.dumps(allocation,indent=2)+'\n').encode())<=4194304,
                'allocation analysis exceeds reserved bytes; originals already restored')
        save(EXEC/'bo-allocation-analysis.json',allocation)
        result['BO_allocation_analysis']={key:value for key,value in allocation.items()
                                        if key not in ('rows','partial','missing_metadata_tokens')}
        require(len((json.dumps(result['BO_allocation_analysis'],indent=2)+'\n').encode())<=65536,
                'allocation summary exceeds reserved bytes; originals already restored')
        submit_log=module('submit_reject_log',WORK/'tools/analyze-submit-reject-log.py')
        submit_diagnostics=submit_log.analyze(kernel)
        require(len((json.dumps(submit_diagnostics,indent=2)+'\n').encode())<=131072,
                'submit diagnostics exceed reserved analysis bytes; originals already restored')
        save(EXEC/'submit-reject-analysis.json',submit_diagnostics)
        result['submit_reject_analysis']={key:value for key,value in submit_diagnostics.items() if key!='rows'}
        sb_text=(EXEC/'springboard-new.log').read_text(errors='replace')
        result['loader_initialization_lines']=[line for line in sb_text.splitlines() if line.startswith('GAUGUIN SB PROBE:')]
        result['kernel_insertion_lines']=[line for line in kernel.splitlines() if line.startswith('SWEET SB INJECT:')]
        parsed=rate_log.parse(sb_text)
        trace=None
        try:
            trace=ui_log.parse(kernel)
            save(EXEC/'ui-trace.json',trace)
            bounds=rate_log.window_from_kernel(kernel)
        except ValueError as problem:
            result['ui_trace_error']=repr(problem)
            bounds=(None,None)
        timebase=trace['header'] if trace is not None and trace['clock_valid'] else None
        numer,denom=(timebase['numer'],timebase['denom']) if timebase else (None,None)
        try:
            processes=process_log.summarize(process_log.parse(kernel),numer,denom)
        except ValueError as problem:
            processes=process_log.summarize({'active_markers':0,'legacy_markers':0,
                'refused':['parse-error'],'cycles':[]},numer,denom)
            processes['parse_error']=repr(problem)
        save(EXEC/'process-sample-analysis.json',processes)
        result['process_analysis']={key:value for key,value in processes.items() if key!='cycles'}
        wake_validation=validate_wake_log(kernel)
        save(EXEC/'wake-validation.json',wake_validation)
        analysis=rate_log.summarize(parsed,*bounds)
        save(EXEC/'springboard-rate-analysis.json',analysis)
        backboard=(EXEC/(before['files']['/private/var/log/backboardd.log']['output']+'.current')).read_text(errors='replace')
        qualified=result['springboard_log_prefix_preserved'] and all(result['other_log_prefix_preserved'].values())
        surface_log=module('surface_retire_log',WORK/'tools/analyze-surface-retire-log.py')
        surface=surface_log.analyze(backboard,qualified)
        require(len((json.dumps(surface,indent=2)+'\n').encode())<=131072,
                'surface diagnostics exceed reserved bytes; originals already restored')
        save(EXEC/'surface-retire-analysis.json',surface)
        result['surface_retirement_analysis']={key:value for key,value in surface.items() if key!='rows'}
        joint_error=None
        if bounds!=(None,None):
            backboard=(EXEC/(before['files']['/private/var/log/backboardd.log']['output']+'.current')).read_text(errors='replace')
            try:
                joint=joint_log.analyze(kernel,backboard,sb_text)
                save(EXEC/'cadence-analysis.json',joint)
            except ValueError as problem:
                # Keep the strict analyzer's rejection and continue saving the
                # other observations. Failure remains the final trial verdict.
                joint_error=repr(problem)
                result['cadence_analysis_error']=joint_error
                save(EXEC/'cadence-analysis-rejected.json',{'state':'strict-cadence-analysis-rejected',
                     'error':joint_error,'physical_FPS_qualified':False})
        result['analysis']={'observer_seen':analysis['observer_seen'],
                            'animation_requests':analysis['animation']['count'],
                            'main_turns':analysis['turns']['count'],
                            'lost_rows':analysis['lost_rows_in_log_tail'],
                            'log_tail_qualified':result['springboard_log_prefix_preserved'],
                            'physical_fps_qualified':False,
                            'touch_entries':analysis['input']['entries_in_window'],
                            'touch_hook_active':analysis['input']['hook_active']}
        qualified=result['springboard_log_prefix_preserved'] and all(result['other_log_prefix_preserved'].values())
        result['state']=classify_observer(analysis,qualified)
        stacks=stack_log.summarize(stack_log.parse(sb_text))
        save(EXEC/'springboard-stack-analysis.json',stacks)
        result['stack_analysis']={key:stacks[key] for key in ('active','sample_count','usable_stack_samples','resume_failures','suspend_failures','state_failures','maximum_capture_elapsed_us','over_budget_samples','missing_sample_ids','incomplete_frame_samples','policy_error_samples','clock_error_samples','unavailable')}
        if result['state']=='SpringBoard-cadence-observed-root-restored':
            result['state']=classify_stacks(stacks,'GAUGUIN SB PROBE: constructor=337' in sb_text.splitlines())
        result['state']=classify_process_samples(result['state'],processes)
        backboard=(EXEC/(before['files']['/private/var/log/backboardd.log']['output']+'.current')).read_text(errors='replace')
        edr=inspect_edr_activation(backboard,qualified)
        save(EXEC/'edr-activation.json',edr)
        result['edr_activation']=edr
        result['cadence_observation_state']=result['state']
        if result['state']=='receiver-process-samples-observed-root-restored':
            result['state']=classify_edr(edr,analysis)
        queue_log=module('queue_log',WORK/'tools/analyze-c4-queue-log.py')
        queue_analysis=queue_log.analyze(backboard)
        require(len((json.dumps(queue_analysis,indent=2)+'\n').encode())<=8388608,
                'queue analysis exceeds its reserved 8 MiB; originals already restored')
        save(EXEC/'c4-queue-analysis.json',queue_analysis)
        result['queue_analysis']={key:value for key,value in queue_analysis.items()
                                  if key not in ('buffers','incomplete','compiler_spans')}
        result['edr_cadence_state']=result['state']
        if result['state']=='EDR320-default-active-cadence-observed-root-restored':
            result['state']=('C4Q321-CPU-stages-observed-root-restored' if queue_analysis['coverage_qualified']
                             else 'C4Q321-stage-coverage-unqualified-root-restored')
        fault_cache=inspect_fault_query_cache(backboard,kernel,qualified)
        save(EXEC/'fault-cache-activation.json',fault_cache)
        result['fault_cache_activation']=fault_cache
        result['C4_stage_observation_state']=result['state']
        if result['state']=='C4Q321-CPU-stages-observed-root-restored':
            result['state']=('FQ322-cache-active-CPU-stages-observed-root-restored' if fault_cache['active']
                             else 'FQ322-cache-activation-unqualified-root-restored')
        stage_log=module('stage_log',WORK/'tools/analyze-stage-cache-log.py')
        stages=stage_log.analyze(backboard,qualified)
        require(len((json.dumps(stages,indent=2)+'\n').encode())<=plan['stage_cache_analysis_max_bytes'],
                'stage analysis exceeds reserved bytes; originals already restored')
        save(EXEC/'stage-cache-analysis.json',stages)
        result['stage_cache_analysis']={key:value for key,value in stages.items() if key!='rows'}
        result['fault_cache_observation_state']=result['state']
        if result['state']=='FQ322-cache-active-CPU-stages-observed-root-restored':
            result['state']=('SC323-cache-stages-observed-root-restored' if stages['coverage_qualified'] and stages['fast_hits']>0
                             else 'SC323-cache-trace-unqualified-root-restored')
        map_log=module('map_log',WORK/'tools/analyze-map-query-log.py')
        mapping=map_log.analyze(kernel)
        require(len((json.dumps(mapping,indent=2)+'\n').encode())<=65536,
                'mapping analysis exceeds reserved bytes; originals already restored')
        save(EXEC/'map-query-analysis.json',mapping)
        result['map_query_analysis']=mapping
        result['stage_cache_observation_state']=result['state']
        if result['state']=='SC323-cache-stages-observed-root-restored':
            result['state']=('MAP324-descriptor-fastpath-active-root-restored' if mapping['active']
                             else 'MAP324-descriptor-fastpath-unqualified-root-restored')
        result['mapping_observation_state']=result['state']
        if result['state']=='MAP324-descriptor-fastpath-active-root-restored':
            result['state']=('BO333-native565-request-active-root-restored' if native_perf['active']
                             else 'BO333-native565-request-unqualified-root-restored')
        if result['state']=='BO333-native565-request-active-root-restored':
            result['state']=('BO333-diagnostics-observed-root-restored' if submit_diagnostics['diagnostic_coverage_qualified'] else 'BO333-diagnostics-coverage-unqualified-root-restored')
        if result['state']=='BO333-diagnostics-observed-root-restored':
            result['state']=('BO333-display-retry-observed-root-restored' if present_retry['active']
                             else 'BO333-display-retry-unqualified-root-restored')
        if result['state']=='BO333-display-retry-observed-root-restored':
            result['state']=('BO333-allocation-phases-observed-root-restored' if allocation['coverage_qualified']
                             else 'BO333-allocation-phases-unqualified-root-restored')
        if result['state']=='BO333-allocation-phases-observed-root-restored':
            result['state']=('BC336-cache-reuse-observed-root-restored' if surface['coverage_qualified'] and allocation.get('cache_hits',0)>0
                             else 'BC336-cache-reuse-unqualified-root-restored')
        result['legacy_observation_state']=result['state']
        identity_log=module('queue_identity337',WORK/'tools/analyze-queue337.py')
        identity=identity_log.analyze(backboard)
        require(len((json.dumps(identity,indent=2)+'\n').encode())<=8388608,
                'identity analysis exceeds reserved bytes; originals already restored')
        save(EXEC/'queue-identity-analysis.json',identity)
        result['queue_identity_analysis']={k:v for k,v in identity.items()if k not in ('buffers','queues')}
        collector=module('collection337',WORK/'tools/collection337.py')
        collection=collector.analyze(kernel,backboard,sb_text,qualified,allocation,queue_analysis,identity)
        require(len((json.dumps(collection,indent=2)+'\n').encode())<=131072,
                'collection analysis exceeds reserved bytes; originals already restored')
        save(EXEC/'collection-analysis.json',collection)
        result['collection_analysis']=collection
        if not collection['coverage_qualified']:
            result['state']='Q337-collection-unqualified-root-restored'
        backlog_log=module('queue_backlog337',WORK/'tools/queue337_backlog.py')
        if not collection['coverage_qualified']:
            backlog=backlog_log.analyze(collection,None,None)
        elif result['legacy_observation_state']!='BC336-cache-reuse-observed-root-restored':
            backlog={'state':'Q337-backlog-interpretation-withheld','reason':'legacy-configuration-unqualified',
                     'physical_FPS_qualified':False,'device_commands':0}
        else:
            try:
                backlog=backlog_log.analyze(collection,queue_analysis,identity)
                result['state']='Q337-lossless-queue-CPU-observed-root-restored'
            except ValueError as problem:
                backlog={'state':'Q337-backlog-analysis-rejected','error':str(problem),'physical_FPS_qualified':False,'device_commands':0}
                result['state']='Q337-backlog-analysis-unqualified-root-restored'
        require(len((json.dumps(backlog,indent=2)+'\n').encode())<=8388608,
                'backlog analysis exceeds reserved bytes; originals already restored')
        save(EXEC/'queue-backlog-analysis.json',backlog)
        result['queue_backlog_analysis']={k:v for k,v in backlog.items()if k!='queues'}
        for key in ('queue_identity_analysis','queue_backlog_analysis'):
            require(len((json.dumps(result[key],indent=2)+'\n').encode())<=65536,
                    'queue summary exceeds reserved bytes; originals already restored')
        if bounds==(None,None):result['state']='SpringBoard-cadence-window-missing-root-restored'
        require(joint_error is None,'strict cadence analysis rejected: '+str(joint_error))
    except (Exception,KeyboardInterrupt) as error:
        result.update(state='trial-incomplete-or-failed',error=repr(error))
        if installed and not restored and not restore_attempted:
            try:
                io=recovery_for_rollback(RecoveryIO,approval,fallback)
                restore_attempted=True
                restore_build.prepare(base_plan,capture_dir,io,HFS,Remote,
                                      EXEC/'fallback-restore-inputs')
                fallback_result=restore_core.restore(base_plan,EXEC/'fallback-restore-inputs',
                                                     approval,io,HFS,Remote,report)
                save(EXEC/'fallback-restore-result.json',fallback_result)
                restored=fallback_result['state']=='restore-applied-and-readback-verified'
                if restored:result['partition_write_phase']='original-files-restored-after-failure'
            except (Exception,KeyboardInterrupt) as problem:
                result['fallback_restore_error']=repr(problem)
        if marker_written and not boot_started and before_misc is not None:
            try:
                io=recovery_for_rollback(RecoveryIO,approval,fallback)
                marker_rollback(io,before_misc,READ,WRITE,MARKER)
                result['preboot_misc_marker_restored']=True
            except (Exception,KeyboardInterrupt) as problem:
                result['preboot_misc_restore_error']=repr(problem)
    result.update(installed=installed,restored=restored,
                  restore_attempted=restore_attempted,
                  recovery_fallbacks=fallback['attempts'],
                  misc_marker_written=marker_written,
                  boot_started=boot_started,
                  finished=time.time())
    save(EXEC/'result.json',result)
    print(json.dumps(result,indent=2),flush=True)
    return 0 if result['state']=='Q337-lossless-queue-CPU-observed-root-restored' else 1


if __name__=='__main__':
    raise SystemExit(main())
