"""Offline, loss-preserving queue analysis of the frozen 0335/0336 captures."""
from pathlib import Path
import hashlib
import argparse
import importlib.util
import json
import math
import re
import statistics

ROOT = Path('/Users/baai/Project/ios-gauguin')
BASE = Path(__file__).resolve().parents[1]/'research/tmp/queue-loss-337'
PINS = {}
_spec=importlib.util.spec_from_file_location('backlog_c4',Path(__file__).with_name('analyze-c4-queue-log.py'))
C4=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(C4)


def read(p):
    raw = p.read_bytes()
    PINS[str(p)] = hashlib.sha256(raw).hexdigest()
    return raw.decode('utf-8', 'replace')


def stats(v):
    v = sorted(v)
    return dict(n=len(v), median=statistics.median(v) if v else None,
                p95=v[math.ceil(len(v)*.95)-1] if v else None, max=max(v) if v else None)


def union(spans, lo, hi):
    total, end = 0, lo
    for a, b in sorted(spans):
        a, b = max(lo, a), min(hi, b)
        if a < b:
            total += max(0, b-max(end, a))
            end = max(end, b)
    return total


def one(n, checkout):
    e = ROOT/'research/tmp'/checkout/'research/tmp'/f'bo-reuse-{n}'/'execution'
    q = json.loads(read(e/'c4-queue-analysis.json'))
    assert q['coverage_qualified'] and not q['errors'] and not q['incomplete']
    assert json.loads(json.dumps(C4.analyze(read(e/'backboardd.log.current'))))==q
    supplement = json.loads(read(e/f'supplemental-analysis{n}.json'))['after']
    script = supplement['script']
    lo, hi = script['start_us'], script['end_us']
    allrows = q['buffers']
    rows = [r for r in allrows if lo <= r['made_us'] < hi]
    workers = [(r['times_us']['1'], r['times_us']['4']) for r in allrows]
    ordered = sorted(allrows, key=lambda r:r['times_us']['1'])
    inversions = sum(a['times_us']['0'] > b['times_us']['0'] for a,b in zip(ordered,ordered[1:]))
    overlaps = [(a['made_us'],b['made_us']) for a,b in zip(ordered,ordered[1:])
                if a['times_us']['4'] > b['times_us']['1']]
    details = []
    for r in rows:
        t = {int(k):v for k,v in r['times_us'].items()}
        wait = t[1]-t[0]
        covered = union(workers,t[0],t[1])
        prior = [p for p in ordered if p['times_us']['1'] < t[1] and p['times_us']['4'] > t[0]]
        waiting = [p for p in allrows if p['times_us']['0'] <= t[0] < p['times_us']['1']]
        d = dict(made_us=r['made_us'], commit_us=t[0], worker_us=t[1],
                 done_us=r['existing_timeline']['done_us'],
                 commit_done_us=r['existing_timeline']['done_us']-t[0],
                 queue_us=wait, turn_us=t[2]-t[1], core_callback_us=t[5]-t[2],
                 timing_tail_us=r['existing_timeline']['done_us']-t[5],
                 observed_worker_union_in_wait_us=covered,
                 uncovered_wait_us=wait-covered,
                 preceding_observed_workers=len(prior), aggregate_waiters_at_commit=len(waiting))
        assert d['commit_done_us'] == d['queue_us']+d['turn_us']+d['core_callback_us']+d['timing_tail_us']
        details.append(d)
    ranked = sorted(details,key=lambda d:d['commit_done_us'])
    tail = ranked[math.ceil(.95*len(ranked))-1:]
    allstats = {k:stats([r[k] for r in details]) for k in details[0] if k.endswith('_us') or k in ('preceding_observed_workers','aggregate_waiters_at_commit')}
    contact = []
    for stroke, observed in enumerate(supplement['strokes']):
        a=observed['start_us']; b=supplement['strokes'][stroke+1]['start_us'] if stroke+1<13 else hi
        part=[r for r in details if a<=r['commit_us']<b]
        contact.append(dict(index=stroke+1, count=len(part), queue_us=stats([r['queue_us'] for r in part]),
                            commit_done_us=stats([r['commit_done_us'] for r in part])))
    batches=[]; batch=[]; lost=0
    for line in read(e/'springboard-new.log').splitlines():
        if any(p in line for p in ('SWEET SB TURN:','SWEET SB INPUT:','SWEET SB RATE: us=')):batch.append(line)
        if m:=re.fullmatch(r'SWEET SB RATE: lost=(\d+)',line):lost+=int(m[1])
        if m:=re.search(r'SWEET SB WATCH: us=(\d+)',line):
            batches.append(dict(watch_us=int(m[1]),rows=len(batch),lost=lost));batch=[];lost=0
    return dict(script=script, complete_script_buffers=len(rows), metrics=allstats,
                global_worker_overlap_pairs=overlaps, global_admission_order_inversions=inversions,
                queue_wait_over_250ms=sum(r['queue_us']>250000 for r in details),
                queue_wait_over_300ms=sum(r['queue_us']>300000 for r in details),
                p95_ranked_cb=ranked[math.ceil(.95*len(ranked))-1],
                top5percent_count=len(tail), top5percent_totals={k:sum(r[k] for r in tail) for k in
                  ('commit_done_us','queue_us','turn_us','core_callback_us','timing_tail_us','observed_worker_union_in_wait_us','uncovered_wait_us')},
                longest_queues=sorted(details,key=lambda r:r['queue_us'],reverse=True)[:12],
                observed_stroke_cycles=contact,
                sb_batch_row_counts=stats([r['rows'] for r in batches]),
                sb_loss_batches=[batches[max(0,i-1):i+2] for i,r in enumerate(batches) if r['lost']],
                details=details)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=dict(before=one(335,'gauguin-bo-reuse-worktree-20261116'),
             after=one(336,'gauguin-cache-adapt-worktree-20261116'),
             scope='CPU elapsed; queue identity not recorded. Worker unions include all observed queues and give an upper bound on same-queue occupancy. Phase4 precedes worker logging, scheduling notification and release; uncovered wait includes untraced tail and scheduling. Stroke cycles extend from each observed stroke start to the next start, including the release gap; no physical FPS or cache-change causality is established. Paired tail components sum; marginal percentiles do not.',
             physical_FPS_qualified=False,device_commands=0)
    read(Path(__file__))
    read(Path(__file__).with_name('analyze-c4-queue-log.py'))
    out['input_pins']=PINS
    with args.out.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    for side in ('before','after'):
        print(side,json.dumps({k:v for k,v in out[side].items() if k not in ('details','longest_queues','observed_stroke_cycles')},indent=2))
