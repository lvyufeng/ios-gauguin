#!/usr/bin/env python3
"""Read-only0342 analysis, gated by independent restoration and collection.

Legacy native565/cache/EDR/workload/stack gates are retained explicitly.
Wire340 phase4 and core timings are decoded only with the0342 semantics.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import core342_log as CORE
import collection342 as COLLECTION
import kernel342_log as KERNEL

WORK=Path(__file__).resolve().parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


LEGACY=module('unchanged_runtime_classifiers340',WORK/'tools/run-sb-cadence-trial.py')
require=LEGACY.require
load=LEGACY.load
validate_wake_log=LEGACY.validate_wake_log
classify_observer=LEGACY.classify_observer
classify_stacks=LEGACY.classify_stacks
classify_process_samples=LEGACY.classify_process_samples
inspect_edr_activation=LEGACY.inspect_edr_activation
classify_edr=LEGACY.classify_edr
inspect_fault_query_cache=LEGACY.inspect_fault_query_cache


def interpret(collection,legacy_state,core,bounds,capture_bounds=None):
    reason=None
    if not collection['coverage_qualified']:reason='collection-incomplete'
    elif legacy_state!='BC336-cache-reuse-observed-root-restored':reason='legacy-configuration-unqualified'
    if reason:
        return dict(state='CR342-interpretation-withheld',reason=reason,physical_FPS_qualified=False,device_commands=0)
    require(core['coverage_qualified'],'strict core/notice join is not qualified')
    start,end=bounds
    require(start is not None and end is not None,'workload window missing')
    rows=[r for r in core['rows'] if start<=r['made_us']<end]
    metrics=tuple(core['metrics'])
    narrow=[] if capture_bounds is None else [r for r in core['rows'] if capture_bounds[0]<=r['made_us']<capture_bounds[1]]
    # Prefix-category sums add only within a CB. They overlap across CB waits.
    waited=sum(r['core_queue_wait_us'] for r in rows)
    busy=sum(r['busy_wait_ns'] for r in rows)/1000
    by_category={k:sum(r['wait_ns'][i] for r in rows)/1000 for i,k in enumerate(CORE.CATEGORIES)}
    require(abs(sum(by_category.values())-busy)<.001,'category wait sum mismatch')
    ranked=sorted(rows,key=lambda r:(r['core_queue_wait_us'],r['ticket']),reverse=True)
    episodes=[]
    for row in ranked[:20]:
        overlapping=[]
        for other in core['rows']:
            if other['queue']!=row['queue'] or other['max_job']>=row['job']:continue
            overlap=max(0,min(row['start_ns'],other['max_end_ns'])-max(row['enq_ns'],other['max_start_ns']))
            if overlap:overlapping.append(dict(queue=other['queue'],ticket=other['ticket'],job=other['max_job'],
                category=CORE.CATEGORIES[other['max_class']],start_ns=other['max_start_ns'],end_ns=other['max_end_ns'],overlap_us=overlap/1000))
        draws=[]
        for other in core['rows']:
            if other['queue']!=row['queue'] or not other['draw_calls'] or other['draw_max_job']>=row['job']:continue
            overlap=max(0,min(row['start_ns'],other['draw_max_end_ns'])-max(row['enq_ns'],other['draw_max_start_ns']))
            if overlap:draws.append(dict(queue=other['queue'],ticket=other['ticket'],job=other['draw_max_job'],
                start_ns=other['draw_max_start_ns'],end_ns=other['draw_max_end_ns'],overlap_us=overlap/1000,
                common_phases_us={k:other['draw_max_phases'][i]/1000 for i,k in enumerate(CORE.DRAW)}))
        episodes.append(dict(queue=row['queue'],ticket=row['ticket'],wait_us=row['core_queue_wait_us'],
            wait_category_us={k:row['wait_ns'][i]/1000 for i,k in enumerate(CORE.CATEGORIES)},
            uncovered_us=row['core_uncovered_queue_wait_us'],known_worst_jobs_overlapping=overlapping,
            known_worst_draws_overlapping=draws,known_jobs_are_partial_evidence=True))
    lifecycle={(r['object'],r['made_us']):r for r in core['lifecycle']['buffers']}
    paths=[]
    for row in rows:
        b=lifecycle[row['object'],row['made_us']];t={int(k):v for k,v in b['times_us'].items()}
        done=b['existing_timeline']['done_us']
        parts=dict(frontend_queue=t[1]-t[0],turn_event=t[2]-t[1],core_admission=row['enq_ns']/1000-t[2],
            core_queue=row['core_queue_wait_us'],core_commit=row['core_commit_execution_us'],
            body_end_to_timeline=done-row['end_ns']/1000)
        require(abs(sum(parts.values())-row['commit_done_us'])<.001,'per-buffer critical path does not add up')
        paths.append(dict(queue=row['queue'],ticket=row['ticket'],made_us=row['made_us'],done_us=row['commit_done_us'],
            components_us=parts,wait_category_us={k:row['wait_ns'][i]/1000 for i,k in enumerate(CORE.CATEGORIES)},
            submit_phase_us={k:row['submit_ns'][i]/1000 for i,k in enumerate(CORE.STAGES)},
            commit_outside_submit_us=row['commit_outside_submit_us'],
            fine_draw_us={k:row['draw_ns'][i]/1000 for i,k in enumerate(CORE.DRAW)},
            fine_render_us={k:row['render_ns'][i]/1000 for i,k in enumerate(CORE.RENDER)},
            fine_GPU_us={k:row['gpu_ns'][i]/1000 for i,k in enumerate(CORE.GPU)},
            IO_elapsed_us=row['io_ns']/1000,BO_uses=row['bo_uses'],BO_unique=row['bo_unique'],
            draw_growths=row['draw_reuse'][2],submit_growths=row['submit_reuse'][2]))
    ordered=sorted(paths,key=lambda r:(r['done_us'],r['ticket']));rank=math.ceil(.95*len(ordered))-1
    require(rank>=0,'no CBs in qualified fullscript')
    tail=ordered[rank:];total=sum(r['done_us'] for r in tail)
    sums={k:sum(r['components_us'][k] for r in tail) for k in tail[0]['components_us']}
    require(abs(sum(sums.values())-total)<.001,'tail critical components do not add up')
    return dict(state='CR342-qualified-core-wait-execution-observation',
        completion_tail=dict(p95_buffer=ordered[rank],count=len(tail),CB_elapsed_sum_us=total,
            component_sums_us=sums,component_shares={k:v/total if total else None for k,v in sums.items()},
            wait_category_sums_us={k:sum(r['wait_category_us'][k] for r in tail) for k in CORE.CATEGORIES},
            submit_phase_sums_us={k:sum(r['submit_phase_us'][k] for r in tail) for k in CORE.STAGES},
            own_commit_outside_submit_sum_us=sum(r['commit_outside_submit_us'] for r in tail),
            fine_scopes=dict(draw_common_sums_us={k:sum(r['fine_draw_us'][k] for r in tail) for k in CORE.DRAW},
                render_body_sums_us={k:sum(r['fine_render_us'][k] for r in tail) for k in CORE.RENDER},
                GPU_submit_sums_us={k:sum(r['fine_GPU_us'][k] for r in tail) for k in CORE.GPU},
                actual_IO_elapsed_sum_us=sum(r['IO_elapsed_us'] for r in tail),
                nested_scopes_not_additive=True,draws_may_precede_frontend_commit=True),
            CPU_utilization_claim=False,independent_percentiles_not_additive=True),
        BO_capture_window=dict(bounds_us=capture_bounds,count=len(narrow),
            metrics={k:CORE.stats([CORE.value(r,k) for r in narrow]) for k in metrics}),
        overlapping_wait_sum_us=dict(total=waited,observed_body=busy,by_category=by_category,
            uncovered=waited-busy,CPU_utilization_claim=False),
        longest_wait_predecessor_evidence=episodes,
        full_window_metrics=core['metrics'],
        full_script_window=dict(start_us=start,end_us=end,count=len(rows),
            metrics={k:CORE.stats([CORE.value(r,k) for r in rows]) for k in metrics}),
        longest_scripted_core_wait=sorted(rows,key=lambda r:r['core_queue_wait_us'],reverse=True)[:20],
        longest_scripted_frontend_wait=sorted(rows,key=lambda r:r['frontend_queue_us'],reverse=True)[:20],
        fine_scope_hotspots={k:sorted(rows,key=lambda r:CORE.value(r,k),reverse=True)[:10] for k in
            ('gpu_BO_list_us','io_connect_us','draw_vertex_bindings_us','draw_fragment_bindings_us','render_encode_us')},
        program_IO_hotspots={k:sorted(rows,key=lambda r:CORE.value(r,k),reverse=True)[:10] for k in
            ('address_program_buffer_us','resident_new_BO_us','resident_upload_publish_us','table_piece_us','pool_reused_zero_us','IO_CPU_lower_us','IO_off_CPU_lower_us')},
        CPU_accounting=core['CPU_accounting'],program_detail=core['program_detail'],
        worker_reuse_observed=core['worker_reuse'],
        phase4_semantics='notification admission return; no synchronous status drain',
        scope=core['scope'],physical_FPS_qualified=False,device_commands=0)


def analyze_saved(EXEC,plan,result,before,code):
    proof=load(EXEC/'independent-restore.json')
    require(result.get('restored') is True and result.get('independent_restore_verified') is True and
        proof['state']=='independently-verified-six-original-files-misc-and-empty-journal' and
        proof['install_plan_sha256']==plan['install_plan_sha256'] and
        proof['misc_original_4096_bytes_match'] and proof['journal_empty'] and
        proof['all_original_slot_bits_allocated'],'independent restoration must precede every analysis')
    limits={'c4-queue-analysis.json':8388608,'queue-identity-analysis.json':8388608,
        'core-wait-execution-analysis.json':67108864,'queue-backlog-analysis.json':8388608,
        'stage-cache-analysis.json':2097152,'bo-allocation-analysis.json':4194304,
        'surface-retire-analysis.json':131072,'submit-reject-analysis.json':131072,
        'native-perf-analysis.json':65536,'present-retry-analysis.json':65536,
        'map-query-analysis.json':65536,'collection-analysis.json':131072,
        'kernel-IO-analysis.json':33554432,'kernel-IO-identity-analysis.json':8388608,
        'kernel-IO-backlog-analysis.json':8388608}
    metadata_bytes=0
    aggregate_max=plan.get('max_analysis_bytes')
    analysis_bytes=0
    def save(path,value):
        nonlocal metadata_bytes,analysis_bytes
        options=dict(separators=(',',':')) if aggregate_max is not None else dict(indent=2)
        raw=(json.dumps(value,**options)+'\n').encode()
        require(path.parent==EXEC and not path.exists(),'fresh analysis file required')
        if path.name in limits:require(len(raw)<=limits[path.name],'analysis file exceeds reserved bound: '+path.name)
        else:
            metadata_bytes+=len(raw);require(metadata_bytes<=33554432,'analysis metadata exceeds reserved32MiB')
        if aggregate_max is not None:
            analysis_bytes+=(len(raw)+4095)//4096*4096
            require(analysis_bytes<=aggregate_max,'analysis exceeds aggregate storage reservation')
        with path.open('xb') as f:f.write(raw)
    rate_log=module('rate340',WORK/'tools/analyze-sb-rate-log.py')
    ui_log=module('ui340',WORK/'tools/ui_trace_log.py')
    joint_log=module('cadence340',WORK/'tools/analyze-sb-cadence.py')
    stack_log=module('stack340',WORK/'tools/analyze-sb-stack-log.py')
    process_log=module('process340',WORK/'tools/analyze-process-samples328.py')
    require(code == 0 and (EXEC / 'kernel.log').is_file(), 'observer failed or kernel log absent')
    kernel = (EXEC / 'kernel.log').read_text(errors='replace')
    require(plan['kernel_banner'] in kernel, 'kernel banner not from pinned observer image')
    native_perf_log = module('native_perf_log', WORK / 'tools/analyze-native-perf-log.py')
    native_perf = native_perf_log.analyze(kernel)
    require(len((json.dumps(native_perf, indent=2) + '\n').encode()) <= 65536, 'native performance analysis exceeds reserved bytes; originals already restored')
    save(EXEC / 'native-perf-analysis.json', native_perf)
    result['native_performance_profile'] = native_perf
    retry_log = module('present_retry_log', WORK / 'tools/analyze-present-retry-log.py')
    pending_limit = plan.get('display_retry', {}).get('held_pending_limit', 2)
    if pending_limit == 4:
        retention = plan.get('issued_retention', {})
        slots = tuple(retention.get(name) for name in ('waiting_candidates','ready_candidates','issued_mailbox_cells'))
        require(slots == (1,1,2), 'four-slot diagnostic requires the issued-retention layout')
    present_retry = retry_log.analyze(kernel, pending_limit=pending_limit)
    require(len((json.dumps(present_retry, indent=2) + '\n').encode()) <= 65536, 'display retry analysis exceeds reserved bytes; originals already restored')
    save(EXEC / 'present-retry-analysis.json', present_retry)
    result['display_retry_analysis'] = {key: value for key, value in present_retry.items() if key != 'rows'}
    allocation_log = module('bo_reuse_log', WORK / 'tools/analyze-bo-reuse-log.py')
    try:
        allocation = allocation_log.analyze(kernel, ui_log)
    except ValueError as error:
        allocation = {'state': 'BC336-reuse-parser-rejected', 'coverage_qualified': False, 'error': str(error), 'device_commands': 0, 'physical_FPS_qualified': False}
    require(len((json.dumps(allocation, indent=2) + '\n').encode()) <= 4194304, 'allocation analysis exceeds reserved bytes; originals already restored')
    save(EXEC / 'bo-allocation-analysis.json', allocation)
    result['BO_allocation_analysis'] = {key: value for key, value in allocation.items() if key not in ('rows', 'partial', 'missing_metadata_tokens')}
    require(len((json.dumps(result['BO_allocation_analysis'], indent=2) + '\n').encode()) <= 65536, 'allocation summary exceeds reserved bytes; originals already restored')
    submit_log = module('submit_reject_log', WORK / 'tools/analyze-submit-reject-log.py')
    submit_diagnostics = submit_log.analyze(kernel)
    require(len((json.dumps(submit_diagnostics, indent=2) + '\n').encode()) <= 131072, 'submit diagnostics exceed reserved analysis bytes; originals already restored')
    save(EXEC / 'submit-reject-analysis.json', submit_diagnostics)
    result['submit_reject_analysis'] = {key: value for key, value in submit_diagnostics.items() if key != 'rows'}
    sb_text = (EXEC / 'springboard-new.log').read_text(errors='replace')
    result['loader_initialization_lines'] = [line for line in sb_text.splitlines() if line.startswith('GAUGUIN SB PROBE:')]
    result['kernel_insertion_lines'] = [line for line in kernel.splitlines() if line.startswith('SWEET SB INJECT:')]
    parsed = rate_log.parse(sb_text)
    trace = None
    try:
        trace = ui_log.parse(kernel)
        save(EXEC / 'ui-trace.json', trace)
        bounds = rate_log.window_from_kernel(kernel)
    except ValueError as problem:
        result['ui_trace_error'] = repr(problem)
        bounds = (None, None)
    timebase = trace['header'] if trace is not None and trace['clock_valid'] else None
    numer, denom = (timebase['numer'], timebase['denom']) if timebase else (None, None)
    try:
        processes = process_log.summarize(process_log.parse(kernel), numer, denom)
    except ValueError as problem:
        processes = process_log.summarize({'active_markers': 0, 'legacy_markers': 0, 'refused': ['parse-error'], 'cycles': []}, numer, denom)
        processes['parse_error'] = repr(problem)
    save(EXEC / 'process-sample-analysis.json', processes)
    result['process_analysis'] = {key: value for key, value in processes.items() if key != 'cycles'}
    wake_validation = validate_wake_log(kernel)
    save(EXEC / 'wake-validation.json', wake_validation)
    analysis = rate_log.summarize(parsed, *bounds)
    save(EXEC / 'springboard-rate-analysis.json', analysis)
    backboard = (EXEC / (before['files']['/private/var/log/backboardd.log']['output'] + '.current')).read_text(errors='replace')
    qualified = result['springboard_log_prefix_preserved'] and all(result['other_log_prefix_preserved'].values())
    surface_log = module('surface_retire_log', WORK / 'tools/analyze-surface-retire-log.py')
    surface = surface_log.analyze(backboard, qualified)
    require(len((json.dumps(surface, indent=2) + '\n').encode()) <= 131072, 'surface diagnostics exceed reserved bytes; originals already restored')
    save(EXEC / 'surface-retire-analysis.json', surface)
    result['surface_retirement_analysis'] = {key: value for key, value in surface.items() if key != 'rows'}
    joint_error = None
    if bounds != (None, None):
        backboard = (EXEC / (before['files']['/private/var/log/backboardd.log']['output'] + '.current')).read_text(errors='replace')
        try:
            joint = joint_log.analyze(kernel, backboard, sb_text)
            save(EXEC / 'cadence-analysis.json', joint)
        except ValueError as problem:
            joint_error = repr(problem)
            result['cadence_analysis_error'] = joint_error
            save(EXEC / 'cadence-analysis-rejected.json', {'state': 'strict-cadence-analysis-rejected', 'error': joint_error, 'physical_FPS_qualified': False})
    result['analysis'] = {'observer_seen': analysis['observer_seen'], 'animation_requests': analysis['animation']['count'], 'main_turns': analysis['turns']['count'], 'lost_rows': analysis['lost_rows_in_log_tail'], 'log_tail_qualified': result['springboard_log_prefix_preserved'], 'physical_fps_qualified': False, 'touch_entries': analysis['input']['entries_in_window'], 'touch_hook_active': analysis['input']['hook_active']}
    qualified = result['springboard_log_prefix_preserved'] and all(result['other_log_prefix_preserved'].values())
    result['state'] = classify_observer(analysis, qualified)
    stacks = stack_log.summarize(stack_log.parse(sb_text))
    save(EXEC / 'springboard-stack-analysis.json', stacks)
    result['stack_analysis'] = {key: stacks[key] for key in ('active', 'sample_count', 'usable_stack_samples', 'resume_failures', 'suspend_failures', 'state_failures', 'maximum_capture_elapsed_us', 'over_budget_samples', 'missing_sample_ids', 'incomplete_frame_samples', 'policy_error_samples', 'clock_error_samples', 'unavailable')}
    if result['state'] == 'SpringBoard-cadence-observed-root-restored':
        result['state'] = classify_stacks(stacks, 'GAUGUIN SB PROBE: constructor=337' in sb_text.splitlines())
    result['state'] = classify_process_samples(result['state'], processes)
    backboard = (EXEC / (before['files']['/private/var/log/backboardd.log']['output'] + '.current')).read_text(errors='replace')
    edr = inspect_edr_activation(backboard, qualified)
    save(EXEC / 'edr-activation.json', edr)
    result['edr_activation'] = edr
    result['cadence_observation_state'] = result['state']
    if result['state'] == 'receiver-process-samples-observed-root-restored':
        result['state'] = classify_edr(edr, analysis)
    queue_analysis = CORE.lifecycle(backboard)
    require(len((json.dumps(queue_analysis, indent=2) + '\n').encode()) <= 8388608, 'queue analysis exceeds its reserved 8 MiB; originals already restored')
    save(EXEC / 'c4-queue-analysis.json', queue_analysis)
    result['queue_analysis'] = {key: value for key, value in queue_analysis.items() if key not in ('buffers', 'incomplete', 'compiler_spans')}
    result['edr_cadence_state'] = result['state']
    if result['state'] == 'EDR320-default-active-cadence-observed-root-restored':
        result['state'] = 'C4Q342-CPU-stages-observed-root-restored' if queue_analysis['coverage_qualified'] else 'C4Q342-stage-coverage-unqualified-root-restored'
    fault_cache = inspect_fault_query_cache(backboard, kernel, qualified)
    save(EXEC / 'fault-cache-activation.json', fault_cache)
    result['fault_cache_activation'] = fault_cache
    result['C4_stage_observation_state'] = result['state']
    if result['state'] == 'C4Q342-CPU-stages-observed-root-restored':
        result['state'] = 'FQ322-cache-active-CPU-stages-observed-root-restored' if fault_cache['active'] else 'FQ322-cache-activation-unqualified-root-restored'
    stage_log = module('stage_log', WORK / 'tools/analyze-stage-cache-log.py')
    stages = stage_log.analyze(backboard, qualified)
    require(len((json.dumps(stages, indent=2) + '\n').encode()) <= plan['stage_cache_analysis_max_bytes'], 'stage analysis exceeds reserved bytes; originals already restored')
    save(EXEC / 'stage-cache-analysis.json', stages)
    result['stage_cache_analysis'] = {key: value for key, value in stages.items() if key != 'rows'}
    result['fault_cache_observation_state'] = result['state']
    if result['state'] == 'FQ322-cache-active-CPU-stages-observed-root-restored':
        result['state'] = 'SC323-cache-stages-observed-root-restored' if stages['coverage_qualified'] and stages['fast_hits'] > 0 else 'SC323-cache-trace-unqualified-root-restored'
    map_log = module('map_log', WORK / 'tools/analyze-map-query-log.py')
    mapping = map_log.analyze(kernel)
    require(len((json.dumps(mapping, indent=2) + '\n').encode()) <= 65536, 'mapping analysis exceeds reserved bytes; originals already restored')
    save(EXEC / 'map-query-analysis.json', mapping)
    result['map_query_analysis'] = mapping
    result['stage_cache_observation_state'] = result['state']
    if result['state'] == 'SC323-cache-stages-observed-root-restored':
        result['state'] = 'MAP324-descriptor-fastpath-active-root-restored' if mapping['active'] else 'MAP324-descriptor-fastpath-unqualified-root-restored'
    result['mapping_observation_state'] = result['state']
    if result['state'] == 'MAP324-descriptor-fastpath-active-root-restored':
        result['state'] = 'BO333-native565-request-active-root-restored' if native_perf['active'] else 'BO333-native565-request-unqualified-root-restored'
    if result['state'] == 'BO333-native565-request-active-root-restored':
        result['state'] = 'BO333-diagnostics-observed-root-restored' if submit_diagnostics['diagnostic_coverage_qualified'] else 'BO333-diagnostics-coverage-unqualified-root-restored'
    if result['state'] == 'BO333-diagnostics-observed-root-restored':
        result['state'] = 'BO333-display-retry-observed-root-restored' if present_retry['active'] else 'BO333-display-retry-unqualified-root-restored'
    if result['state'] == 'BO333-display-retry-observed-root-restored':
        result['state'] = 'BO333-allocation-phases-observed-root-restored' if allocation['coverage_qualified'] else 'BO333-allocation-phases-unqualified-root-restored'
    if result['state'] == 'BO333-allocation-phases-observed-root-restored':
        result['state'] = 'BC336-cache-reuse-observed-root-restored' if surface['coverage_qualified'] and allocation.get('cache_hits', 0) > 0 else 'BC336-cache-reuse-unqualified-root-restored'
    result['legacy_observation_state'] = result['state']

    identity=CORE.identity(backboard)
    save(EXEC/'queue-identity-analysis.json',identity)
    result['queue_identity_analysis']={k:v for k,v in identity.items() if k not in ('buffers','queues')}
    program_slabs=plan.get('program_storage')=='immutable-program-slabs-346'
    core=CORE.analyze(backboard,program_slabs=program_slabs)
    initial_collection=COLLECTION.BASE.analyze(kernel,backboard,sb_text,qualified,allocation,queue_analysis,identity)
    kernel_stream=KERNEL.parse(kernel,(EXEC/'kernel.log.bin').read_bytes() if (EXEC/'kernel.log.bin').is_file() else None)
    kernel_join=KERNEL.join(kernel_stream,core,initial_collection.get('script_window_us',(None,None)))
    save(EXEC/'kernel-IO-analysis.json',kernel_stream)
    save(EXEC/'kernel-IO-identity-analysis.json',kernel_join)
    collection=COLLECTION.analyze(kernel,backboard,sb_text,qualified,allocation,queue_analysis,identity,core,
                                  kernel_stream,kernel_join,program_slabs=program_slabs)
    result['kernel_IO_analysis']={k:v for k,v in kernel_stream.items() if k not in ('rows','phase_names')}
    result['kernel_IO_identity_analysis']={k:v for k,v in kernel_join.items() if k not in ('submits','program_maxima')}

    save(EXEC/'collection-analysis.json',collection)
    result['collection_analysis']=collection
    # Save decoding and rejected coverage too. Interpret only after the strict
    # collector gate and unchanged configuration gates above have qualified.
    save(EXEC/'core-wait-execution-analysis.json',{k:v for k,v in core.items() if k not in ('lifecycle','identity')})
    result['core_wait_execution_analysis']={k:v for k,v in core.items() if k not in ('rows','lifecycle','identity')}
    backlog=interpret(collection,result['legacy_observation_state'],core,collection.get('script_window_us',(None,None)),capture_bounds=bounds)
    kernel_backlog=KERNEL.summarize(kernel_join,core) if collection['coverage_qualified'] and result['legacy_observation_state']=='BC336-cache-reuse-observed-root-restored' else dict(state='IO342-backlog-interpretation-withheld',physical_FPS_qualified=False)
    save(EXEC/'kernel-IO-backlog-analysis.json',kernel_backlog)
    result['kernel_IO_backlog_analysis']={k:v for k,v in kernel_backlog.items() if k not in ('longest_wait_predecessor_phases','sustained_windows','longest_submit_calls','program_maxima')}
    save(EXEC/'queue-backlog-analysis.json',backlog)
    result['queue_backlog_analysis']={k:v for k,v in backlog.items() if k not in ('longest_scripted_core_wait','longest_scripted_frontend_wait','longest_wait_predecessor_evidence','fine_scope_hotspots','full_window_metrics','program_IO_hotspots')}
    result['state']=('CR342-lossless-wait-execution-observed-root-restored'
        if backlog['state']=='CR342-qualified-core-wait-execution-observation'
        else 'CR342-observation-unqualified-root-restored')
    for key in ('queue_identity_analysis','core_wait_execution_analysis','queue_backlog_analysis'):
        require(len((json.dumps(result[key],indent=2)+'\n').encode())<=65536,'analysis summary exceeds64KiB')
    if bounds==(None,None):result['state']='SpringBoard-cadence-window-missing-root-restored'
    require(joint_error is None,'strict cadence analysis rejected: '+str(joint_error))
    result['physical_FPS_qualified']=False
    return result
