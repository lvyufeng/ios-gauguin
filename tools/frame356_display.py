"""Measure the Core, submit, and copy timing of the 0356 comparison."""

from collections import Counter

import frame344_log as trace

FOCUS_COPY_STROKE = 10


def matched_latencies(core, identity, kernel):
    ids = lambda row: (row['queue'],row['ticket'],row['job'])
    trace.require(core['coverage_qualified'] and identity['coverage_qualified'] and kernel['coverage_qualified'],
                  'Core, submit identity or kernel phase capture is incomplete')
    core_rows = trace.indexed(core['rows'],ids,'Core job')
    native_rows = trace.indexed((r for r in kernel['rows'] if r['selector']==0x46),
                                lambda r:r['token'],'kernel submit')
    phase_index = kernel['phase_names'][str(0x46)].index('runtime_issue')
    samples = []
    for join in identity['submits']:
        old = core_rows[ids(join)]
        native = native_rows[join['kernel_token']]
        phase = native['phases'][phase_index]
        trace.require(phase and (join['driver_queue'],join['driver_fence'])==(native['queue'],native['fence']) and
                      0<=phase['CPU_lower_ns']<=phase['CPU_upper_ns']<=phase['wall_ns'] and
                      old['enq_ns']<=old['start_ns'],'runtime issue or Core FIFO identity differs')
        samples.append(dict(queue=old['queue'],ticket=old['ticket'],job=old['job'],kernel_token=join['kernel_token'],
            native_fence=join['driver_fence'],core_queue_ns=old['start_ns']-old['enq_ns'],
            runtime_issue_wall_ns=phase['wall_ns'],runtime_issue_cpu_lower_ns=phase['CPU_lower_ns'],
            runtime_issue_cpu_upper_ns=phase['CPU_upper_ns']))
    trace.require(len(samples)==identity['complete_submit_count'] and len(samples)>0,'missing timed submissions')
    fields=('core_queue_ns','runtime_issue_wall_ns','runtime_issue_cpu_lower_ns','runtime_issue_cpu_upper_ns')
    summary={}
    for field in fields:
        values=[row[field] for row in samples]
        summary[field]=dict(p50=trace.quantile(values,.5),p95=trace.quantile(values,.95),maximum=max(values))
    return dict(matched_submits=len(samples),summary=summary,submissions=samples)


def focus_copy(aligned, stroke=FOCUS_COPY_STROKE):
    attempts = trace.indexed(aligned['attempts'],lambda r:r['attempt'],'present attempt')
    selected = [w for w in aligned['windows'] if w['stroke']==stroke]
    trace.require(len(selected)==2 and {w['phase'] for w in selected}=={'active','release'},
                  'missing copy-boundary windows for the focus stroke')
    report={}
    for window in selected:
        rows=[]
        counts=Counter()
        timed=set()
        uncertified=set()
        for interval in window['intervals']:
            key=interval['after_copy_boundary_check']
            step=(interval['frame']-interval['previous_frame'])&0xffffffff
            counts[key]+=step
            copies=[]
            bounded={p['attempt'] for p in interval['certified_blanking_overlaps']}
            for entry in interval['copies_between_samples']:
                attempt=attempts.get(entry['attempt'])
                proofs=[p for p in attempt['blanking_proofs'] if p['surface']==entry['surface']] if attempt else []
                verdict='independently-bounded' if entry['attempt'] in bounded else 'not-used-to-resolve-overlap'
                if key=='unknown' and interval['copy_overlap'] and entry['attempt'] not in bounded:
                    uncertified.add(entry['attempt'])
                    verdict='copy-boundary-unknown'
                copies.append(dict(entry,verdict=verdict,scanline_receipts=proofs,
                    generation=attempt['generation'] if attempt else None,
                    source_writer=next((layer.get('native_fence') for layer in attempt['layers']
                                        if layer['surface']==entry['surface']),None) if attempt else None))
            rows.append(dict(frame=interval['frame'],previous_frame=interval['previous_frame'],
                edge_ticks=interval['edge_ticks'],crc_relation=interval['crc_relation'],
                classification=key,copies=copies))
            timed.update(interval['present_attempts'])
        copy_times=[layer['copy_ns'] for identifier in timed for layer in attempts[identifier]['layers']]
        report[window['phase']]=dict(counts={kind:counts[kind] for kind in ('changed','repeated','unknown')},
            present_attempts=len(timed),copy_p95_ns=trace.quantile(copy_times,.95),copy_max_ns=max(copy_times,default=None),
            copy_boundary_unknown_attempts=sorted(n for n in uncertified if n is not None),hardware_intervals=rows)
    return dict(stroke=stroke,phases=report)
