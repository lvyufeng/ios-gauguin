"""Join private-buffer staging, exact GPU writes and first visible frames."""

from bisect import bisect_right
from collections import Counter, defaultdict
from importlib import import_module
import re

import frame344_log as trace
import frame354_display as ready
from frame357_display import BOUND
from frame357_replay import OPEN_LINE, TOTAL_LINES, scan_windows
from frame364_analysis import score
import frame374_native_ca as native

EARLY = re.compile(r'^SWEET F384 P (\d+) ([12]) (\d+)$', re.M)


def parse(raw):
    return trace.parse(raw, extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))


def verified_latches(rows, latches):
    swaps = trace.indexed(rows[trace.SWAP],lambda r:r.id,'accepted swap')
    attempts = trace.indexed(rows[trace.ATTEMPT],lambda r:r.id,'present attempt')
    validations = trace.indexed(rows[ready.VALIDATE],lambda r:r.id,'version check')
    promotions = trace.indexed(rows[ready.PROMOTE],lambda r:r.id,'ready promotion')
    marks = trace.indexed(rows[ready.READY],lambda r:r.id,'ready observation')
    bindings = trace.indexed(rows[BOUND],lambda r:r.id,'bound display write')
    issues = trace.indexed(rows[trace.ISSUE],lambda r:r.id,'native issue')
    writers = trace.indexed((r for r in rows[trace.WRITER] if r.b),
                            lambda r:(r.id,r.b),'exact writer')
    eops = trace.indexed(rows[trace.EOP],lambda r:r.id,'EOP')
    visible = trace.indexed(rows[trace.READY],lambda r:r.id,'GPU cache visible')
    lock_ticks = [r.tick for r in rows[trace.LOCK]]
    output = {}
    for scan, receipt in sorted(latches.items()):
        generation = receipt['generation']
        swap, attempt, promotion, mark, binding, validation = (
            swaps[generation],attempts[receipt['attempt']],promotions[generation],
            marks[generation],bindings[generation],validations[receipt['attempt']])
        surface, version, fence = promotion.c,promotion.b,mark.b
        ticket = generation<<32|surface
        issue, writer, eop, visibility = issues[fence],writers[fence,ticket],eops[fence],visible[fence]
        before_copy = bisect_right(lock_ticks,receipt['begin'])
        lock = rows[trace.LOCK][before_copy-1] if before_copy else None
        trace.require(swap.a==attempt.b==receipt['swap'] and swap.b==attempt.c==1 and not swap.flags and
            swap.c==(version<<32|surface) and (binding.a,binding.b)==(ticket,version) and
            (writer.a,writer.c)==(surface,version) and mark.a==surface and validation.flags==1 and
            (validation.a,validation.b,validation.c)==(surface,version,version) and lock and lock.id==surface and
            lock.flags in trace.LOCK_ACCEPTED and
            swap.tick<=binding.tick<=issue.tick<=writer.tick<=eop.tick<=visibility.tick<=mark.tick<=promotion.tick<=
            attempt.tick<=lock.a<=lock.b<=lock.c<=lock.tick<=validation.tick<=receipt['begin']<receipt['tick'],
            'latched frame lacks the exact completed and cache-visible writer or read protection')
        output[scan] = receipt | dict(surface=surface, version=version, fence=fence, swap_tick=swap.tick,
            issue_tick=issue.tick, eop_tick=eop.tick, visible_tick=visibility.tick, ready_tick=promotion.tick,
            attempt_tick=attempt.tick, lease_tick=lock.b)
    return output


def replay(rows, latches, n, d):
    """Check earlier staging on recorded writer lifetimes with prior latches fixed."""
    ns = lambda tick: tick*n//d
    windows = {w.frame:w for w in scan_windows(rows[trace.VBLANK],ns,n/d,bracketed=True,
                                               copy_budget_ns=192*3000)}
    later_writes = defaultdict(list)
    issues = {r.id:r.tick for r in rows[trace.ISSUE]}
    for r in rows[trace.WRITER]:
        if r.id in issues:
            later_writes[r.a].append(issues[r.id])
    previous = 0
    earlier = possible_earlier_display = 0
    for scan, row in latches.items():
        begin = max(previous,row['ready_tick'],row['visible_tick'])
        end = begin+row['tick']-row['attempt_tick']
        trace.require(begin<=row['attempt_tick'] and end<=row['tick'],
                      'recorded readiness or slot release is later than the accepted copy')
        writer_starts = later_writes[row['surface']]
        safe = not any(begin<=tick<=end for tick in writer_starts)
        if safe and begin<row['attempt_tick']:
            earlier += 1
            # This is an opportunity for one recorded frame with all other
            # activity fixed. Multiple opportunities need not be compatible.
            window = windows.get((scan-2)&0xffffffff)
            if window and max(ns(end), window.opening)<window.deadline:
                possible_earlier_display += 1
        previous = row['confirmed_tick']
    return dict(exact_baseline_latches=len(latches),earlier_stage_candidates=earlier,
        possible_individual_one_scan_advance=possible_earlier_display,
        scope='Replay charges the recorded attempt-to-barrier duration and holds other latches and writers fixed.')


def trial_rows(comparison, trial):
    return [dict(record['scans'][trial],workload=record['workload'],stroke=record['stroke'],phase=record['phase'])
            for record in comparison['scans'] if record['scans'][trial] is not None]


def early_timing(raw, rows, latches, n, d):
    trace.one(r'^SWEET F384 WORKER: separate=1 copies=(1024)$', raw, 'bounded staging worker')
    staged = {int(attempt): (int(slot),int(tick)) for attempt,slot,tick in EARLY.findall(raw)}
    trace.require(staged and len(staged)<=1024, 'early staging did not activate or exceeded its bound')
    early = [r for r in latches.values() if staged.get(r['attempt'])==(r['slot'],r['tick'])]
    trace.require(early, 'no verified early staging latch')
    edges = rows[trace.VBLANK]
    edge_ticks = [e.b for e in edges]
    active = 0
    for r in early:
        i = bisect_right(edge_ticks,r['begin'])-1
        if i<0 or i+1>=len(edges):
            continue
        left,right = edges[i:i+2]
        earliest_open = ((TOTAL_LINES-OPEN_LINE)*left.a+OPEN_LINE*right.a)//TOTAL_LINES
        if left.flags==right.flags==1 and right.id==left.id+1 and r['begin']<earliest_open:
            active += 1
    trace.require(active, 'no guarded private staging started before the old blanking opening')
    duration = lambda key_a, key_b: trace.quantile(
        [(r[key_b]-r[key_a])*n//d for r in early],.95)
    return dict(early_latched=len(early),completed_early_stages=len(staged),started_during_active_scan=active,
        ready_to_stage_start_p95_ns=duration('ready_tick','begin'),
        stage_p95_ns=duration('begin','tick'),stage_to_latch_p95_ns=duration('tick','confirmed_tick'))


def first_frames(execution, raw, rows, strokes, n, d, scans, latches):
    start,end,*_ = native.envelope(raw)
    events = native.decode(raw,start,end)
    swaps = trace.indexed(rows[trace.SWAP],lambda r:r.id,'input comparison swap')
    timing = {row.id:row for row in rows[trace.SWAP_TIMING] if row.a and row.b>>32 and
              swaps[row.id].c==row.c and row.a<=swaps[row.id].tick<=row.tick}
    native_swaps = [dict(generation=g,client_swap_id=swaps[g].a,
                        begin_thread=r.b>>32,begin_tick=r.a) for g,r in timing.items()]
    renders = native.link_swaps(events,native_swaps,start,end,n,d)
    rate = import_module('analyze-sb-rate-log')
    touch = rate.parse((execution/'springboard-new.log').read_text())

    def ns(tick):
        return tick*n//d

    output, stages = [], Counter()
    after_return_before_render = 0
    for stroke,(down,up) in enumerate(strokes,1):
        lane = [r for r in scans if r['stroke']==stroke and r['phase']=='active' and r['workload']=='ordinary']
        first = next((scan for scan in lane if scan['crc']=='changed'),None)
        if not first:
            output.append(dict(stroke=stroke,first_scan=None,unknown_before_onset=sum(
                scan['crc']=='unknown' for scan in lane)))
            continue
        receipt = latches[first['frame']]
        generation = receipt['generation']
        render = renders.get(generation,{}).get('render')
        callback = next((c for c in rate.summarize_input(touch,ns(down)//1000,ns(up)//1000)['callback_spans']
                         if not c['flags']&8 and c['returned'] and c['entered_us']*1000>=ns(down)),None)
        cuts = [(name,t) for name,t in (
            ('CA_render',render['begin_tick'] if render else None),
            ('SwapBegin',timing[generation].a if generation in timing else None),
            ('swap_accept',receipt['swap_tick']),('native_issue',receipt['issue_tick']),
            ('GPU_EOP',receipt['eop_tick']),('cache_visible',receipt['visible_tick']),
            ('start_staging',receipt['begin']),('stage_barrier',receipt['tick']),
            ('flip_request',receipt['issued_tick'])) if t is not None]
        trace.require(all(a<=b for (_,a),(_,b) in zip(cuts,cuts[1:])),
                      'first visible frame has contradictory stage order')
        stage_counts = Counter()
        for scan in lane[:lane.index(first)]:
            if scan['crc']!='repeated':
                continue
            lo, hi = scan['vblank_ticks']
            phase = ('stage_overlaps_edge_bracket' if any(lo<=t<=hi for _,t in cuts) else
                     next((name for name,t in cuts if hi<t),'latch'))
            if phase=='swap_accept' and generation not in timing:
                phase = 'before_accept_upstream_unresolved'
            if stroke>=3:
                stages[phase] += 1
                if phase=='CA_render' and callback and callback['returned_us']*1000<ns(lo):
                    after_return_before_render += 1
            stage_counts[phase] += 1
        output.append(dict(stroke=stroke,first_scan=first['frame'],generation=generation,
            first_change_from_touch_ns_bounds=[ns(t)-ns(down) for t in first['vblank_ticks']],
            first_main_callback_id=callback['id'] if callback else None,
            touch_to_first_callback_return_ns=callback['returned_us']*1000-ns(down) if callback else None,
            first_callback_return_to_first_visible_render_ns=ns(render['begin_tick'])-callback['returned_us']*1000
                if callback and render else None,
            cutoffs_for_eventual_first_frame=dict(stage_counts),
            timeline_from_touch_ns={name:ns(t)-ns(down) for name,t in cuts}))
    return dict(strokes=output,warm_pre_onset_repeat_stage=dict(stages),
        warm_after_first_callback_return_before_linked_render=after_return_before_render,
        scope='Exact visible swap and optional native render join. First main callback is a temporal reference within the gesture.')
