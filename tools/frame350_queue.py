"""Trace the waits in swipes 3 and 11 to observed predecessor jobs and native IO."""

from collections import defaultdict

import frame344_log as frames


FOCUS_STROKES = (3, 11)
TAIL_PER_STROKE = 4


def identity(row):
    return row['queue'], row['ticket'], row['job']


def intersection(start, end, left, right):
    return max(0,min(end,right)-max(start,left))


def clipped_phases(submit, phase_names, start, end):
    if submit is None:
        return []
    phases = submit['phases']
    names = phase_names[str(submit['kernel_selector'])]
    frames.require(len(names)==len(phases),'kernel IO phase names differ')
    measured = []
    for name,phase in zip(names,phases):
        overlap = intersection(start,end,phase['begin_ns'],phase['end_ns'])
        if overlap:
            outside = phase['wall_ns']-overlap
            measured.append(dict(phase=name,overlap_ns=overlap,
                cpu_lower_ns=max(0,phase['CPU_lower_ns']-outside),
                cpu_upper_ns=min(overlap,phase['CPU_upper_ns']),
                off_cpu_lower_ns=max(0,phase['off_CPU_lower_ns']-outside),
                off_cpu_upper_ns=min(overlap,phase['off_CPU_upper_ns'])))
    return measured


def predecessors(row, queue_rows, submissions, kernel_names, categories, draw_names, render_names):
    start,end = row['enq_ns'],row['start_ns']
    commits, draws = [], []
    for other in queue_rows:
        if other['ticket']>=row['ticket']:
            break
        overlap = intersection(start,end,other['start_ns'],other['end_ns'])
        if overlap:
            joined = submissions.get(identity(other))
            commits.append(dict(queue=other['queue'],ticket=other['ticket'],job=other['job'],
                commit_overlap_ns=overlap,native_submit_overlap_ns=intersection(
                    start,end,other['io_begin_ns'],other['io_end_ns']),
                whole_predecessor_render_ns=dict(zip(render_names,other['render_ns'])),
                predecessor_draw_calls=other['draw_calls'],
                kernel_token=joined['kernel_token'] if joined else None,
                kernel_IO_within_wait=clipped_phases(joined,kernel_names,start,end)))
        overlap = intersection(start,end,other['draw_max_start_ns'],other['draw_max_end_ns'])
        if other['draw_calls'] and overlap and other['draw_max_job']<row['job']:
            # The fine phases describe this one draw's whole span. The draw
            # overlap separately bounds how much of that span can delay this CB.
            draws.append(dict(queue=other['queue'],ticket=other['ticket'],job=other['draw_max_job'],
                draw_overlap_ns=overlap,whole_draw_ns=dict(zip(draw_names,other['draw_max_phases']))))
    waited = row['start_ns']-row['enq_ns']
    frames.require(sum(row['wait_ns'])==row['busy_wait_ns']<=waited,'Core wait categories do not reconcile')
    frames.require(sum(item['commit_overlap_ns'] for item in commits)<=row['wait_ns'][categories.index('commit')],
                   'joined predecessor commit exceeds measured commit residence')
    return dict(queue=row['queue'],ticket=row['ticket'],job=row['job'],made_us=row['made_us'],
                enq_ns=start,start_ns=end,wait_ns=waited,observed_worker_ns=row['busy_wait_ns'],
                uncovered_ns=waited-row['busy_wait_ns'],wait_by_category_ns=dict(zip(categories,row['wait_ns'])),
                exact_predecessor_commits=commits,overlapping_maximum_draws=draws)


def analyze(core, joined, kernel, frame, *, strokes=FOCUS_STROKES, release_bounds_ns=None):
    frames.require(core['coverage_qualified'] and joined['coverage_qualified'] and kernel['coverage_qualified']
                   and frame['frame_trace_complete'] and len(frame['strokes'])==13,
                   'focused queue comparison requires the qualified script and identities')
    rows = frames.indexed(core['rows'],identity,'Core queue ticket/job')
    submits = frames.indexed(joined['submits'],identity,'native queue ticket/job')
    frames.require(set(submits)<=set(rows),'native submissions lack Core identities')
    queues = defaultdict(list)
    for row in rows.values():
        queues[row['queue']].append(row)
    for lane in queues.values():
        lane.sort(key=lambda row:row['ticket'])
    layers = defaultdict(list)
    for attempt in frame['attempts']:
        for layer in attempt['layers']:
            if 'ticket' in layer:
                layers[identity(layer)].append(dict(generation=attempt['generation'],attempt=attempt['attempt'],
                    surface=layer['surface'],native_fence=layer['native_fence'],gpu_complete_tick=layer['eop_observed_tick'],
                    read_lock_wait_ns=layer['lock_wait_ns'],
                    copy_start_tick=layer['copy_start_tick'],copy_end_tick=layer['copy_end_tick']))
    numer,denom = frame['tick_numer'],frame['tick_denom']
    focus = []
    for i,(start,end) in enumerate(frame['strokes']):
        if i+1 not in strokes:
            continue
        if release_bounds_ns is not None:
            lower,upper = release_bounds_ns
            start,end = end+lower*denom//numer,end+upper*denom//numer
        active = [rows[key] for key in submits if start*numer<=rows[key]['made_us']*1000*denom<end*numer]
        ranks = sorted(active,key=lambda row:(row['start_ns']-row['enq_ns'],row['ticket']),reverse=True)
        tail = []
        for row in ranks[:TAIL_PER_STROKE]:
            item = predecessors(row,queues[row['queue']],submits,kernel['phase_names'],
                                core['category_order'],core['draw_phase_order'],core['render_phase_order'])
            item.update(kernel_token=submits[identity(row)]['kernel_token'],
                        linked_present_layers=layers[identity(row)])
            tail.append(item)
        focus.append(dict(stroke=i+1,matched_submits=len(active),
            wait_p95_ns=frames.quantile([row['start_ns']-row['enq_ns'] for row in active],.95),
            wait_max_ns=max((row['start_ns']-row['enq_ns'] for row in active),default=None),tail=tail))
    categories = core['category_order']
    totals = {name:sum(row['wait_by_category_ns'][name] for stroke in focus for row in stroke['tail'])
              for name in categories}
    return dict(focus=focus,wait_category_sum_ns=totals,matched_submits=len(submits),
                scope='Waits can overlap across queued buffers. Predecessor commits and kernel phases are time-clipped. Fine draw phases describe whole observed maximum draws.')
