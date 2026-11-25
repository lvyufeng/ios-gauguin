#!/usr/bin/env python3
"""Replay display ownership and scan opportunities from restored 0355/0356."""

from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path

import frame344_log as trace
import frame349_log as misr
from frame354_display import KINDS, VALIDATE, order
from frame356_scope import MAIN, REF355, check_references, load, require, sha

P356 = MAIN/'research/tmp/gauguin-latency-worktree-20261120/research/tmp/frame-356'
REF356 = P356/'execution'
RESULT_356 = '33427c7e9b16abf9a0ef4f0023d2b2f536c84a5617b9c4b813bd29d3d48c94be'
PROOF_356 = '1ae043c6e6450727f38e74621ebe8d28a50f78d0f155ee8db6f1d1dd410d90d8'
INPUTS = ('kernel.log', 'result.json', 'independent-restore.json', 'frame-scanout-analysis.json',
          'ready-selection-analysis.json', 'kernel-IO-analysis.json')
TOTAL_LINES, OPEN_LINE, END_LINE, START_BUDGET = 4910, 2480, 4878, 5_500_000
FIRST_FORBIDDEN_LINE = END_LINE - (START_BUDGET + 2999)//3000 + 1


@dataclass(frozen=True)
class Write:
    fence: int
    surface: int
    version: int
    generation: int
    first_ns: int
    bound_by_ns: int
    issue_ns: int
    visible_ns: int


@dataclass(frozen=True)
class Scan:
    frame: int
    opening: int
    deadline: int
    end: int


class Busy:
    def __init__(self, intervals):
        self.spans = []
        for start, end in sorted(intervals):
            require(0 < start < end, 'invalid GPU lock envelope')
            if self.spans and start <= self.spans[-1][1]:
                self.spans[-1][1] = max(end, self.spans[-1][1])
            else:
                self.spans.append([start, end])
        self.ends = [end for _, end in self.spans]

    def first_free(self, start, length, deadline):
        i = bisect_right(self.ends, start)
        for i in range(i, len(self.spans)):
            begin, end = self.spans[i]
            if start + length <= begin or start >= deadline:
                break
            start = end
        return start if start < deadline else None


class Display:
    """A descriptor owns one display reference until moved or retired."""

    def __init__(self, retain_issued):
        self.retain_issued = retain_issued
        self.waiting = self.issued = self.ready = self.copying = None
        self.surfaces = {}
        self.latest_taken = 0
        self.references = set()
        self.counts = Counter()

    @staticmethod
    def generation(descriptor):
        if isinstance(descriptor, Write):
            return descriptor.generation
        return descriptor.id if descriptor else 0

    def check(self):
        slots = (self.waiting, self.ready, self.copying)
        if self.retain_issued:
            slots += (self.issued,)
        ids = [self.generation(item) for item in slots if item]
        require(len(ids) == len(set(ids)) and self.references == set(ids), 'aliased or leaked display reference')

    def retire(self, descriptor):
        if descriptor:
            self.references.remove(self.generation(descriptor))

    def event(self, kind, value):
        if kind == 'swap':
            self.retire(self.waiting)
            self.waiting = value
            self.references.add(value.id)
        elif kind == 'writer':
            self.surfaces[value.surface] = value
        elif kind == 'bind':
            if self.waiting and value.generation == self.waiting.id:
                if self.issued and self.retain_issued:
                    self.counts['binding_slot_busy'] += 1
                else:
                    self.issued = value
                    if self.retain_issued:
                        self.waiting = None
                    self.counts['bound'] += 1
        elif kind == 'visible' and self.issued and value == self.issued.fence:
            writer, self.issued = self.issued, None
            owned = self.retain_issued or bool(self.waiting and self.waiting.id == writer.generation)
            if owned:
                if not self.retain_issued:
                    self.waiting = None
                if self.live(writer) and writer.generation > max(self.latest_taken, self.generation(self.ready)):
                    self.retire(self.ready)
                    self.ready = writer
                    self.counts['promoted'] += 1
                else:
                    self.retire(writer)
                    self.counts['retired_stale_or_older'] += 1
        elif kind == 'ordinary' and self.waiting and self.waiting.id == value:
            self.latest_taken = max(self.latest_taken, value)
            self.retire(self.waiting)
            self.waiting = None
            if self.ready and self.ready.generation <= self.latest_taken:
                self.retire(self.ready)
                self.ready = None
        self.check()

    def live(self, writer):
        return self.surfaces.get(writer.surface) == writer

    def take(self, writer, start, scan, copy_ns, busy):
        require(self.ready == writer and self.live(writer) and writer.visible_ns <= start and
                self.latest_taken < writer.generation and scan.opening <= start < scan.deadline and
                start+copy_ns <= scan.end and busy.first_free(start, copy_ns, start+1) == start,
                'copy without current version, monotonic order, lock availability or scan budget')
        require(self.copying is None, 'overlapping display copies')
        self.copying, self.ready = self.ready, None
        self.latest_taken = writer.generation
        self.check()

    def finish(self):
        self.retire(self.copying)
        self.copying = None
        self.check()

    def stop(self):
        self.retire(self.waiting)
        self.retire(self.ready)
        self.retire(self.copying)
        if self.retain_issued:
            self.retire(self.issued)
        self.waiting = self.issued = self.ready = self.copying = None
        self.check()


def scan_windows(edges, ns, scale, *, bracketed, copy_budget_ns=START_BUDGET):
    cutoff_line = END_LINE - (copy_budget_ns+2999)//3000 + 1

    def at(left, right, line, bound):
        return ((TOTAL_LINES-line)*ns(getattr(left,bound)) + line*ns(getattr(right,bound)))//TOTAL_LINES

    for left, right in zip(edges, edges[1:]):
        if left.flags != 1 or not misr.consecutive((left,right), scale):
            continue
        if bracketed:
            opening = at(left,right,OPEN_LINE,'b')+1
            close = at(left,right,cutoff_line,'a')
            end = at(left,right,END_LINE,'a')
        else:
            opening, close, end = ((at(left,right,line,'a')+at(left,right,line,'b'))//2
                                   for line in (OPEN_LINE,cutoff_line,END_LINE))
        if opening < close and opening+copy_budget_ns <= end:
            yield Scan(left.id, opening, close, end)


def schedule(events, scans, busy, copy_ns, overhead_ns, *, retain):
    state = Display(retain)
    selected = {}
    position = 0

    def advance(time):
        nonlocal position
        while position < len(events) and events[position][0] <= time:
            _, _, kind, value = events[position]
            state.event(kind, value)
            position += 1

    for scan in scans:
        start = scan.opening
        deadline = min(scan.deadline, scan.end-copy_ns+1)
        advance(start)
        while start < deadline:
            writer = state.ready
            if writer and state.live(writer):
                start = max(start, writer.visible_ns+overhead_ns)
                free = busy.first_free(start, copy_ns, deadline)
                if free is None:
                    break
                advance(free)
                start = free
                if state.ready != writer or not state.live(writer):
                    continue
                state.take(writer, start, scan, copy_ns, busy)
                selected[scan.frame] = dict(generation=writer.generation, fence=writer.fence,
                    surface=writer.surface, version=writer.version, start_ns=start, end_ns=start+copy_ns)
                advance(start+copy_ns)
                state.finish()
                break
            if position == len(events) or events[position][0] >= deadline:
                break
            start = max(start, events[position][0])
            advance(start)
    advance(2**63-1)
    state.stop()
    return selected, dict(state.counts)


def replay(path):
    proof, result, frame, kernel, receipt = (load(path/name) for name in
        ('independent-restore.json', 'result.json', 'frame-scanout-analysis.json',
         'kernel-IO-analysis.json', 'ready-selection-analysis.json'))
    require(result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            result['frame_trace_complete'] and len(proof['files']) == 6 and proof['journal_empty'] and
            kernel['coverage_qualified'], 'missing restore, root or I/O proof')
    rows, strokes, numer, denom = trace.parse((path/'kernel.log').read_text(), extra_kinds=(52,53,*KINDS))

    def ns(tick):
        return tick*numer//denom

    edges = rows[trace.VBLANK]
    timing, = rows[trace.TIMING]
    require((timing.a,timing.b,timing.c) == (TOTAL_LINES,32,2431) and edges and
            all((p.c >> 32 if p.flags else p.c) == END_LINE for p in rows[52]),
            'observed copy geometry differs')
    submits = trace.indexed((r for r in kernel['rows'] if r['selector']==70), lambda r:r['token'], 'submit')
    issues = trace.indexed(rows[trace.ISSUE],lambda r:r.id,'native issue')
    completions = trace.indexed(rows[trace.READY],lambda r:r.id,'native visibility')
    eops = trace.indexed(rows[trace.EOP],lambda r:r.id,'native EOP')
    require(issues.keys()==completions.keys()==eops.keys() and all(
            order(issues[f]) < order(eops[f]) < order(completions[f])
            for f in issues) and all(a.id < b.id and order(completions[a.id]) < order(b)
            for a,b in zip(rows[trace.ISSUE],rows[trace.ISSUE][1:])), 'parallel, missing or out-of-order GPU fences')
    phases = kernel['phase_names']['70']
    escrow_end = phases.index('surface_cache_flush')
    swaps = trace.indexed((r for r in rows[trace.SWAP] if not r.flags),lambda r:r.id,'swap')
    require(len(swaps)==len(rows[trace.SWAP]) and len(strokes)==13,'power cancellation or incomplete workload')
    ranges = [(w['stroke']+1,w['window'],w['vblank_edges'][0]['edge_upper_tick'],
               w['vblank_edges'][-1]['edge_upper_tick']) for w in frame['hardware']['windows']]
    active = {g for g,s in swaps.items() if any(a<s.tick<=b for _,p,a,b in ranges if p=='active')}
    slots = {item['previous_frame']:(w['stroke']+1,w['window']) for w in frame['hardware']['windows']
             for item in w['outputs']}
    writes = []
    by_surface = defaultdict(list)
    victims = {}
    for row in rows[trace.WRITER]:
        issue = issues[row.id]
        submission = submits[issue.a]
        begin, end = submission['begin'][escrow_end], submission['end'][escrow_end]
        swap = swaps.get(row.b >> 32)
        exact = swap and swap.b==1 and (row.b&0xffffffff)==row.a and swap.c==((row.c<<32)|row.a)
        require((submission['queue'],submission['fence'])==(issue.b,issue.c) and
                0 < begin <= end <= ns(issue.tick) <= ns(row.tick), 'surface version lacks a matching issue interval')
        writer = Write(row.id,row.a,row.c,swap.id if exact else 0,begin,end,
                       ns(issue.tick),ns(completions[row.id].tick))
        previous = by_surface[writer.surface]
        require(not previous or previous[-1].version+4==writer.version,
                'missing intervening surface writer or reused surface id')
        previous.append(writer)
        writes.append(writer)
        successor = swaps.get(writer.generation+1)
        if exact and swap.id in active and successor and order(successor)<order(completions[row.id]):
            victims[swap.id] = dict(surface=writer.surface,version=writer.version,fence=writer.fence,
                bind_interval_ns=[begin,end],issue_ns=writer.issue_ns,visibility_ns=writer.visible_ns,
                successor_ns=ns(successor.tick),
                successor_phase=('after-issue' if order(issue)<order(successor) else
                                  'during-issue' if end<ns(successor.tick) else 'binding-uncertain'))

    # Exclude the entire recorded GPU-lock envelope, even when an internal
    # wait temporarily released it. An added copy cannot delay native work
    # in this fixed trace model. Include cache visibility when outside I/O.
    busy = Busy([(r['begin'][1],r['last_ns']+1) for r in kernel['rows'] if r['begin'][1]] +
                [(ns(eops[f].tick),ns(c.tick)+1) for f,c in completions.items()])
    attempts = trace.indexed(rows[trace.ATTEMPT],lambda r:r.id,'attempt')
    overheads = [ns(r.tick)-ns(attempts[r.id].tick) for r in rows[VALIDATE] if r.flags==1]
    overhead_ns = int(trace.quantile(overheads,.95))+1
    actual = {r['target_frame']:r['generation'] for r in receipt['joins'] if r['copied']}
    actual_attempts = {r['target_frame'] for r in receipt['joins']}
    source_durations = [ns(r.b)-ns(r.a) for r in rows[trace.COPY]]
    plain = [(ns(r.tick),r.seq,'ordinary',r.a) for r in rows[trace.ATTEMPT] if not swaps[r.a].c]
    common = [(ns(r.tick),r.seq,'swap',r) for r in swaps.values()] + plain + [
        (ns(r.tick),r.seq,'visible',r.id) for r in completions.values()] + [
        (w.first_ns,0,'writer',w) for w in writes]
    modes = {}
    for name, bracketed, copy_ns in (
            ('bracketed_5_5ms',True,START_BUDGET),
            ('bracketed_measured_max',True,max(source_durations)),
            ('midpoint_measured_p95',False,int(trace.quantile(source_durations,.95))+1)):
        scans = list(scan_windows(edges,ns,numer/denom,bracketed=bracketed))
        bound = [(w.bound_by_ns if bracketed else w.first_ns,1,'bind',w) for w in writes if w.generation]
        events = sorted(common+bound,key=lambda record:record[:2])
        baseline, before = schedule(events,scans,busy,copy_ns,overhead_ns,retain=False)
        retained, after = schedule(events,scans,busy,copy_ns,overhead_ns,retain=True)
        recovered = [dict(row,frame=i,stroke=slots[i][0],phase=slots[i][1],
                          actual_copy=actual.get(i),actual_attempt=i in actual_attempts,
                          replay_baseline_copy=baseline.get(i))
                     for i,row in retained.items() if i in slots and row['generation'] in victims]
        modes[name] = dict(copy_ns=copy_ns,prep_ns=overhead_ns, eligible_scan_windows=len(scans),
            baseline_events=before,retained_events=after,
            baseline_copy_counts=dict(Counter(slots[i][1] for i in baseline if i in slots)),
            retained_copy_counts=dict(Counter(slots[i][1] for i in retained if i in slots)),
            recovered_counts=dict(Counter(r['phase'] for r in recovered)),
            recovered_in_unattempted_slots=dict(Counter(r['phase'] for r in recovered if not r['actual_attempt'])),
            recovered_in_empty_slots=dict(Counter(r['phase'] for r in recovered if r['actual_copy'] is None)),
            recovered_in_both_baseline_empty_slots=dict(Counter(r['phase'] for r in recovered
                if r['actual_copy'] is None and r['replay_baseline_copy'] is None)),
            recovered=recovered)
    return dict(trial=result['trial'], crc_latch_qualified=frame['crc_frame_calibration']['qualified'],
        verified_fifo_fences=len(issues), observed_copy_counts=dict(Counter(slots[i][1] for i in actual if i in slots)),
        prematurely_replaced_counts=dict(Counter(v['successor_phase'] for v in victims.values())),
        prematurely_replaced=victims, scenarios=modes, input_sha256={name:sha(path/name) for name in INPUTS})


def report():
    check_references()
    require(sha(REF356/'result.json')==RESULT_356 and sha(REF356/'independent-restore.json')==PROOF_356,
            '0356 read-back receipt differs')
    trials = {tag:replay(path) for tag,path in (('0355',REF355),('0356',REF356))}
    return dict(state='0355-0356-fixed-trace-issued-retention-replay', trials=trials,
                measured_device_IO=0, counts_are_copy_opportunities_not_CRC_or_FPS=True)


if __name__ == '__main__':
    print(json.dumps(report(),indent=2))
