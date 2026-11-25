"""Locate 0357 repeat causes at the actual preceding blanking deadline."""

from bisect import bisect_right
from collections import Counter
import json

import frame344_log as trace
from frame354_display import PROMOTE, READY as PROMOTED, TAKE, order
from frame355_scope import MAIN, WORK, load, require, sha
from frame357_display import KINDS
from frame357_replay import Busy, TOTAL_LINES, scan_windows

P357 = MAIN/'research/tmp/gauguin-issued-frame-worktree-20261120/research/tmp/frame-357'
REF357 = P357/'execution'
BASE = WORK/'research/tmp/frame-358'
SUMMARY_357 = REF357/'analysis-after-readback/pacing-0357.json'
RESULT_357 = 'f8090d4948b8fdf8b09baedba54ee4e682dd4805a42e4e90710267b1e0312bca'
PROOF_357 = '2866df49c6f7867f008f2b5703d40af2b5b349891101999d9a8c4cd6a42a339b'
SUMMARY_SHA_357 = '7f53031ed318b8e7efe19e1eb03e087ed3fe77bc50dcb2d068176389e63304f1'
FIRST_PROBE_LINE = 1728
PROBE_LIMIT = 1024
FRAME_CAPACITY = 20480
PROBE = 60


def check_0357():
    result, proof = (load(REF357/name) for name in ('result.json','independent-restore.json'))
    require(sha(REF357/'result.json')==RESULT_357 and sha(REF357/'independent-restore.json')==PROOF_357 and
        sha(SUMMARY_357)==SUMMARY_SHA_357 and result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'] and result['frame_trace_complete'] and
        result['crc_frame_calibration']['qualified'] and proof['journal_empty'] and
        proof['misc_original_4096_bytes_match'] and len(proof['files'])==6,'0357 restoration or capture differs')


def audit():
    check_0357()
    raw = REF357/'kernel.log'
    rows,_,n,d = trace.parse(raw.read_text(),extra_kinds=(52,53,*KINDS))
    scale = n/d

    def ns(tick):
        return tick*n//d

    edges = rows[trace.VBLANK]
    slots = {row.frame:row for row in scan_windows(edges,ns,scale,bracketed=True)}
    brackets = trace.indexed(edges,lambda row:row.id,'hardware scan')
    issue = trace.indexed(rows[trace.ISSUE],lambda r:r.id,'native issue')
    eop = trace.indexed(rows[trace.EOP],lambda r:r.id,'observed EOP')
    visible = trace.indexed(rows[trace.READY],lambda r:r.id,'visible fence')
    promotion = trace.indexed(rows[PROMOTED],lambda r:r.id,'ready promotion')
    require(issue.keys()==eop.keys()==visible.keys() and all(
        order(issue[key])<order(eop[key])<order(visible[key]) for key in issue), 'missing native fence stages')
    attempts = trace.indexed(rows[trace.ATTEMPT],lambda r:r.id,'attempt')
    takes = trace.indexed(rows[TAKE],lambda r:r.c,'timed scan')
    ends = sorted((ns(r.tick),attempts[r.id].a) for r in rows[trace.RESULT] if r.a)
    end_stamps = [tick for tick,_ in ends]
    swaps = [r for r in rows[trace.SWAP] if not r.flags]
    swap_stamps = [ns(r.tick) for r in swaps]
    writers = {(r.b>>32,r.a,r.c):r for r in rows[trace.WRITER] if r.b}
    writers_by_generation = sorted((gen,writer) for (gen,_,_),writer in writers.items())
    io_path = REF357/'kernel-IO-analysis.json'
    io = load(io_path)
    lock_envelope = Busy([(r['begin'][1],r['last_ns']+1) for r in io['rows'] if r['begin'][1]]+
                         [(ns(r.a),ns(r.b)) for r in rows[trace.COPY]])
    lane_path = REF357/'frame-scanout-analysis.json'
    lane = load(lane_path)
    import frame352_display as output
    qualified = output.analyze(raw.read_text(),lane,extra_kinds=KINDS)
    linked = trace.indexed(qualified['attempts'],lambda r:r['attempt'],'qualified copy attempt')
    promotion_p95 = int(trace.quantile(
        [ns(row.tick)-ns(visible[row.b].tick) for row in promotion.values()],.95))
    sample_p95 = int(trace.quantile([ns(r.b)-ns(r.a) for r in edges if r.flags==1],.95))
    score = load(SUMMARY_357)['scored_crc_comparison']

    detail = {}
    for phase in ('active','release'):
        events = []
        for entry in score['frames']:
            scored = entry['trials']['0357']
            if entry['phase']!=phase or not scored or scored['kind']!='repeated':
                continue
            frame = (scored['frame']-1)&0xffffffff
            base = dict(stroke=entry['stroke'],hardware_frame=scored['frame'],blanking_frame=frame)
            slot = slots.get(frame)
            if not slot:
                events.append(dict(base,stage='unqualified_admission_window'))
                continue
            last_index = bisect_right(end_stamps,slot.opening)-1
            swap_index = bisect_right(swap_stamps,slot.deadline-1)-1
            if swap_index < 0:
                events.append(dict(base,stage='no_new_surface_swap_before_cutoff'))
                continue
            last = ends[last_index][1] if last_index>=0 else 0
            latest = swaps[swap_index]
            take = takes.get(frame)
            if take and take.id in linked:
                attempt = linked[take.id]
                proof, = attempt['blanking_proofs']
                guard, = attempt['read_guards']
                events.append(dict(base,stage='take_'+proof['disposition'],generation=take.a,
                    copy_check_line=proof['begin_line'],GPU_lock_wait_ns=ns(guard['locked_tick'])-ns(guard['queued_tick'])))
                continue
            promoted = [r for r in rows[PROMOTE] if r.id>last and ns(r.tick)<slot.deadline]
            if promoted:
                events.append(dict(base,stage='promoted_without_take',generation=promoted[-1].id))
                continue
            if latest.id<=last or not latest.c:
                events.append(dict(base,stage='no_new_surface_swap_before_cutoff'))
                continue
            ready_later = [r for gen,r in writers_by_generation if last<gen<=latest.id and
                           ns(issue[r.id].tick)<slot.deadline<=ns(visible[r.id].tick)]
            if not ready_later:
                writer = writers.get((latest.id,latest.c&0xffffffff,latest.c>>32))
                events.append(dict(base,stage='new_swap_without_exact_issue_by_cutoff',
                    generation=latest.id,eventual_native_fence=writer.id if writer else None,
                    issue_after_cutoff_ns=ns(issue[writer.id].tick)-slot.deadline if writer else None))
                continue
            writer = ready_later[-1]
            left,right = brackets[frame],brackets[scored['frame']]
            # Use the upper edge bracket at both ends to place the earliest
            # credible lead-line sighting. The measured observer cadence and
            # publication envelope are sensitivity parameters, not a proof
            # of when the GPU first signalled the EOP in memory.
            lead = ((TOTAL_LINES-FIRST_PROBE_LINE)*ns(left.b)+FIRST_PROBE_LINE*ns(right.b))//TOTAL_LINES
            visibility_cost = ns(visible[writer.id].tick)-ns(eop[writer.id].tick)
            modeled = {}
            for name,jitter in (('lead_line_only',0),('with_p95_scan_observer_spacing',sample_p95)):
                start = max(lead+jitter,ns(issue[writer.id].tick))
                finish = start+visibility_cost+promotion_p95
                modeled[name] = start<slot.deadline and finish<slot.deadline and (
                    lock_envelope.first_free(start,max(1,visibility_cost),start+1)==start)
            first_probe = max(lead,ns(issue[writer.id].tick))
            latest_probe = max(lead+sample_p95,ns(issue[writer.id].tick))
            modeled['whole_p95_observer_band'] = latest_probe+visibility_cost+promotion_p95<slot.deadline and (
                lock_envelope.first_free(first_probe,max(1,latest_probe-first_probe+visibility_cost),
                                         first_probe+1)==first_probe)
            events.append(dict(base,stage='exact_issue_waiting_for_visibility',generation=writer.b>>32,
                native_fence=writer.id,issue_ns=ns(issue[writer.id].tick),deadline_ns=slot.deadline,
                eop_observed_ns=ns(eop[writer.id].tick),visible_ns=ns(visible[writer.id].tick),
                modeled_probe_has_time_if_already_complete=modeled))
        late = [v['GPU_lock_wait_ns'] for v in events if v['stage']=='take_deferred']
        opportunities = [v for v in events if v['stage']=='exact_issue_waiting_for_visibility']
        detail[phase] = dict(stages=dict(Counter(v['stage'] for v in events)),
            probe_timing_opportunities={k:sum(r['modeled_probe_has_time_if_already_complete'][k] for r in opportunities)
                for k in ('lead_line_only','with_p95_scan_observer_spacing','whole_p95_observer_band')},
            eop_observed_before_deadline_but_not_visible=sum(v['eop_observed_ns']<v['deadline_ns'] for v in opportunities),
            late_guard_wait_p50_ns=trace.quantile(late,.5),late_guard_wait_p95_ns=trace.quantile(late,.95),
            per_repeated_frame=events)
    require(sum(detail['active']['stages'].values())==164 and sum(detail['release']['stages'].values())==71,
            'repeat accounting differs from qualified 0357')
    return dict(state='0357-repeat-at-blanking-deadline-audit',lanes=detail,device_commands=0,first_probe_line=FIRST_PROBE_LINE,
        sample_spacing_p95_ns=sample_p95,promotion_latency_p95_ns=promotion_p95,
        source_sha256={str(p):sha(p) for p in (raw,lane_path,io_path,SUMMARY_357,REF357/'independent-restore.json')})


if __name__=='__main__':
    print(json.dumps(audit(),indent=2))
