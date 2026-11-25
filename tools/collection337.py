"""Fail closed on collection integrity before interpreting per-queue latency."""
from pathlib import Path
import importlib.util

def module(name,leaf):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(leaf))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def assess(trace,springboard,c4,identity,allocation,prefix_ok,bounds):
    errors=[]
    if not prefix_ok:errors.append('log-prefix-not-preserved')
    h=trace.get('header',{})
    if h.get('version')!=2:errors.append('kernel-wire-version-not2')
    if not trace.get('clock_valid') or h.get('reason')!=1:errors.append('kernel-window-unqualified')
    if h.get('lost')!=0:errors.append('kernel-record-loss')
    if trace.get('truncated_by_capacity') or h.get('count',4096)>=4096:errors.append('kernel-capacity')
    if not allocation.get('coverage_qualified'):errors.append('allocation-phase-coverage')
    if not c4.get('coverage_qualified'):errors.append('independent-C4-coverage')
    if not identity.get('coverage_qualified'):errors.append('queue-identity-coverage')
    if any(q.get('unobserved_ticket_ranges')for q in identity.get('queues',[])):
        errors.append('unobserved-interior-queue-tickets')
    if identity.get('records')!=3*c4.get('complete_cb_count',0):errors.append('queue-record-count-mismatch')
    if springboard.get('lost_rows_in_log_tail')!=0:errors.append('SpringBoard-record-loss')
    inp=springboard.get('input',{})
    if not inp.get('hook_active') or not inp.get('watch_covers_window'):errors.append('SpringBoard-window-coverage')
    if inp.get('metadata_errors_in_tail')!=0 or inp.get('write_errors_in_tail')!=0:
        errors.append('SpringBoard-metadata-or-write-error')
    if inp.get('unpaired_entry_ids') or inp.get('unpaired_end_ids'):errors.append('SpringBoard-input-pairing')
    if inp.get('callbacks_with_original_exception',0):errors.append('SpringBoard-input-exception')
    if any(r['flags'] for r in inp.get('entries',[])):errors.append('SpringBoard-input-metadata-flags')
    if not inp.get('entries_in_window'):errors.append('SpringBoard-input-not-observed')
    if bounds is None or not 220000000<=bounds[0]<bounds[1]<=270000000:
        errors.append('script-outside-instrumented-window')
    return dict(state='Q337-collection-qualified'if not errors else'Q337-collection-unqualified',
        coverage_qualified=not errors,errors=errors,kernel_version=h.get('version'),
        kernel_lost=h.get('lost'),kernel_count=h.get('count'),
        SB_lost=springboard.get('lost_rows_in_log_tail'),script_window_us=bounds,
        C4_complete=c4.get('complete_cb_count'),queue_identity_records=identity.get('records'),
        allocation_complete=allocation.get('complete_count'),
        allocation_boundary_partials=allocation.get('partial_count'),
        physical_FPS_qualified=False,device_commands=0,
        scope='Configured kernel prefix and createdAt220..270s C4/queue records, whole SB tail and validated13-stroke window. Legitimate capture-boundary API partials remain explicit. This is not whole-boot loss-free recording or physical FPS.')

def analyze(kernel,backboard,sb,prefix_ok,allocation,c4,identity):
    ui=module('collector_ui337','ui_trace_log.py');rate=module('collector_sb337','analyze-sb-rate-log.py')
    runner=module('collector_workload337','run-sb-cadence-trial.py')
    try:
        trace=ui.parse(kernel);wake=runner.validate_wake_log(kernel);h=trace['header']
        us=lambda n:n*h['numer']//h['denom']//1000
        bounds=[us(wake['first_stroke_tick']),us(wake['last_release_tick'])+1]
        springboard=rate.summarize(rate.parse(sb),*bounds)
        result=assess(trace,springboard,c4,identity,allocation,prefix_ok,bounds)
        if sb.splitlines().count('GAUGUIN SB PROBE: constructor=337')!=1:
            result['errors'].append('SpringBoard-constructor-identity')
        result['coverage_qualified']=not result['errors']
        result['state']='Q337-collection-qualified'if result['coverage_qualified']else'Q337-collection-unqualified'
        return result
    except ValueError as error:
        return dict(state='Q337-collection-unqualified',coverage_qualified=False,
                    errors=['strict-decode-or-workload-rejected'],error=str(error),
                    physical_FPS_qualified=False,device_commands=0)
