"""Tie first-frame timing to exact input samples and qualified scanout."""

from importlib import import_module
import re

import frame344_log as trace
import frame352_display as boundary
from frame355_scope import load
from frame358_display import KINDS

RATE = import_module('analyze-sb-rate-log')
STACK = import_module('analyze-sb-stack-log')
PREFIX = 'SWEET SB FIRST359: '
ACTIVE = re.compile(r'active input=1 ca_commit=([01]) ca_flush=([01]) max_rows=8192')
INPUT = re.compile(r'input id=([1-9][0-9]{0,9}) entered_us=([0-9]{9}) left_us=([0-9]{9}) returned=([01])')
CA = re.compile(r'ca method=(commit|flush) entered_us=([0-9]{9}) left_us=([0-9]{9}) returned=([01])')


def callback_trace(text, parsed):
    begin = {r['id']:r for r in parsed['rows'] if r['kind']=='input-begin'}
    end = {r['id']:r for r in parsed['rows'] if r['kind']=='input-end'}
    configuration, calls, ca = None, {}, []
    config = STACK.CALLBACK_CONFIG

    def valid_span(entered, left):
        return config['start_us']<=entered<config['end_us'] and entered<=left

    for line in text.splitlines():
        where = line.find(PREFIX)
        if where<0:
            continue
        body = line[where+len(PREFIX):]
        active, call, transaction = ACTIVE.fullmatch(body), INPUT.fullmatch(body), CA.fullmatch(body)
        if active:
            trace.require(configuration is None,'multiple first-frame observer activations')
            configuration = dict(zip(('commit','flush'),(v=='1' for v in active.groups())))
            continue
        trace.require(configuration is not None and len(calls)+len(ca)<8192,
                      'first-frame observer lacks activation or exceeded its record budget')
        if call:
            ident, entered, left, returned = (int(value) for value in call.groups())
            a, b = begin.get(ident), end.get(ident)
            trace.require(ident<=0xffffffff and ident not in calls and a and b and not a['flags']&8 and
                          valid_span(entered,left) and a['us']<=entered<=left==b['us'] and
                          bool(returned)==b['returned'],'input call does not match its wrapper identity and endpoints')
            calls[ident] = dict(id=ident, entered_us=entered,left_us=left,returned=bool(returned),
                               wrapper_to_call_us=entered-a['us'])
        elif transaction:
            method = transaction[1]
            entered, left, returned = (int(value) for value in transaction.groups()[1:])
            trace.require(configuration[method] and valid_span(entered,left),'CA API entry outside its active observation')
            ca.append(dict(method=method,entered_us=entered,left_us=left,returned=bool(returned)))
        else:
            raise ValueError('malformed first-frame observation')
    trace.require(configuration is not None and any(configuration.values()) and calls,
                  'input or explicit CA API observer unavailable')

    stacks = STACK.summarize(STACK.parse(text))
    trace.require(stacks['active'] and stacks['version']==359 and not any(stacks[key] for key in (
        'unavailable','resume_failures','suspend_failures','state_failures','missing_sample_ids',
        'incomplete_frame_samples','policy_error_samples','clock_error_samples')),
        'targeted stack capture is incomplete')
    snapshots = []
    for sample in stacks['samples']:
        watch = sample['watch']
        ident, entered = watch>>32, watch&0xffffffff
        call = calls.get(ident)
        trace.require(call and call['entered_us']==entered,'stack does not name an observed input invocation')
        if sample['sample'] in stacks['usable_sample_ids'] and entered<=sample['held_us']<call['left_us']:
            snapshots.append(dict(input_id=ident, sample=sample['sample'],held_us=sample['held_us'],
                                  capture_elapsed_us=sample['resumed_us']-sample['us'],
                                  frames=[frame['image'] for frame in sample['frame_rows']]))
    return dict(CA_API_active=configuration,calls=calls,CA_API_calls=ca,stack_attempts=stacks['sample_count'],
                stale_stack_attempts=len(stacks['stale_watch_samples']),linked_stacks=snapshots)


def frame_points(windows, edges, attempts, swaps, first, last, to_ns):
    first_changed = None
    linked = None
    changes = []
    for window in windows:
        for interval in window['intervals']:
            if interval['after_copy_boundary_check']!='changed':
                continue
            edge = edges[interval['frame']]
            if edge.a<first or edge.b>last:
                continue
            point = dict(phase=window['phase'],frame=edge.id,edge_bounds_ns=[to_ns(edge.a),to_ns(edge.b)])
            changes.append(point)
            first_changed = first_changed or point
            if linked is not None:
                continue
            copies = []
            for proof in interval['certified_blanking_overlaps']:
                if proof['frame']!=interval['previous_frame']:
                    continue
                attempt = attempts[proof['attempt']]
                swap = swaps.get(attempt['generation'])
                if swap is None:
                    continue
                for layer in attempt['layers']:
                    if layer['surface']==proof['surface'] and layer['bytes']==trace.FRAME_BYTES:
                        copies.append((swap,layer))
            if not copies:
                continue
            swap, layer = max(copies,key=lambda item:item[1]['copy_end_tick'])
            if first<=swap.tick<=last:
                linked = dict(point,swap_generation=swap.id,swap_ns=to_ns(swap.tick),
                              copy_start_ns=to_ns(layer['copy_start_tick']),copy_finish_ns=to_ns(layer['copy_end_tick']),
                              **{k:layer[k] for k in ('queue','ticket','job','native_fence') if k in layer})
    return first_changed, linked, changes


def analyze(execution, *, targeted=False, display=None):
    proof = load(execution/'independent-restore.json')
    trace.require(proof['state']=='independently-verified-six-original-files-misc-and-empty-journal' and
                  len(proof['files'])==6 and proof['all_original_slot_bits_allocated'] and
                  proof['journal_empty'] and proof['misc_original_4096_bytes_match'],
                  'independent restoration must precede first-frame analysis')
    kernel = (execution/'kernel.log').read_text()
    text = (execution/'springboard-new.log').read_text()
    frame = load(execution/'frame-scanout-analysis.json')
    core = load(execution/'core-wait-execution-analysis.json')
    trace.require(frame['frame_trace_complete'] and frame['crc_frame_calibration']['qualified'] and
                  core['coverage_qualified'],'first-frame analysis requires qualified Core and hardware capture')
    rows,strokes,n,d = trace.parse(kernel,extra_kinds=(52,53,*KINDS))
    def ns(tick):
        return tick*n//d

    if display is None:
        display = boundary.analyze(kernel,frame,extra_kinds=KINDS)
    sw = trace.indexed((r for r in rows[trace.SWAP] if not r.flags and r.c),lambda r:r.id,'eligible swap')
    edges = trace.indexed(rows[trace.VBLANK],lambda r:r.id,'hardware edge')
    attempts = trace.indexed(display['attempts'],lambda r:r['attempt'],'present attempt')
    parsed = RATE.parse(text)
    observed = RATE.summarize(parsed,ns(strokes[0][0])//1000,ns(strokes[-1][1])//1000+250_000)
    inp = observed['input']
    trace.require(observed['lost_rows_in_log_tail']==0 and inp['hook_active'] and inp['watch_covers_window'] and
                  not any(inp[k] for k in ('unpaired_entry_ids','unpaired_end_ids','metadata_errors_in_tail',
                                          'write_errors_in_tail','callbacks_with_original_exception')),
                  'first-frame SpringBoard window is not lossless and closed')
    focused = callback_trace(text,parsed) if targeted else None
    if focused is not None:
        trace.require(all(row['id'] in focused['calls'] for row in inp['entries'] if not row['flags']&8),
                      'missing original call span inside scripted workload')
    output = []
    for ordinal,(first,release) in enumerate(strokes,1):
        start, up = ns(first), ns(release)
        limit = up+250_000_000
        last = ((limit+1)*d-1)//n
        windows = [w for w in display['windows'] if w['stroke']==ordinal]
        trace.require([w['phase'] for w in windows]==['active','release'],'missing stroke score windows')
        changed,linked,changes = frame_points(windows,edges,attempts,sw,first,last,ns)
        active_changed = [row for row in changes if row['phase']=='active']
        touches = [row for row in inp['callback_spans'] if start//1000<=row['entered_us']<=up//1000]
        active_swaps = [r for r in sw.values() if first<=r.tick<=release]
        enqueues = sorted((r for r in core['rows'] if start<=r['enq_ns']<=up),key=lambda r:r['enq_ns'])
        first_swap = next((r for r in sw.values() if first<=r.tick<=last),None)
        first_core = min((r for r in core['rows'] if start<=r['enq_ns']<=limit),key=lambda r:r['enq_ns'],default=None)
        longest = max(touches,key=lambda r:r['duration_us'],default=None)
        ca = [r for r in focused['CA_API_calls'] if start//1000<=r['entered_us']<=limit//1000] if focused else []
        turns = [r for r in observed['turns']['rows'] if r['observer_order_valid'] and
                 start//1000<=r['after_ca_us']<=limit//1000]
        output.append(dict(stroke=ordinal,HID_begin_ns=start,HID_release_ns=up,active_swaps=len(active_swaps),
            active_Core_enqueues=len(enqueues),active_new_CRC_frames=len(active_changed),active_touch_entries=len(touches),
            first_touch=min(touches,key=lambda r:r['entered_us'],default=None),longest_touch=longest,
            longest_touch_original=focused['calls'].get(longest['id']) if focused and longest else None,
            first_observed_CA_API=min(ca,key=lambda r:r['entered_us'],default=None),
            first_CA_observer_bracket=min(turns,key=lambda r:r['after_ca_us'],default=None),
            first_swap=dict(generation=first_swap.id,ns=ns(first_swap.tick)) if first_swap else None,
            first_Core_enqueue={k:first_core[k] for k in ('queue','ticket','job','enq_ns')} if first_core else None,
            first_CRC_new_output=changed,first_guarded_swap_linked_CRC=linked,
            longest_active_new_output_gap_upper_ns=max((b['edge_bounds_ns'][1]-a['edge_bounds_ns'][0]
                for a,b in zip(active_changed,active_changed[1:])),default=None),
            targeted_stacks=[r for r in focused['linked_stacks'] if any(r['input_id']==a['id'] for a in touches)]
                if focused else []))
    return dict(state='first-frame-observation-qualified',strokes=output,
                first_CRC_scope='DPU new complete output, with optional exact blanking copy and swap identity.',
                CA_scope='Public commit/flush calls and run-loop brackets are separate milestones. The shared clock does not prove touch-to-transaction causality.',
                targeted_stack_attempts=focused['stack_attempts'] if focused else None,
                stale_targeted_stacks=focused['stale_stack_attempts'] if focused else None,
                linked_targeted_stacks=len(focused['linked_stacks']) if focused else None,
                explicit_CA_calls=len(focused['CA_API_calls']) if focused else None)
