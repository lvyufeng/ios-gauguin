#!/usr/bin/env python3
"""Parse bounded SpringBoard register/frame snapshots without inferring FPS."""
import argparse
import collections
import json
from pathlib import Path
import re

PREFIX = 'GAUGUIN SB STACK: '
CONFIG = dict(version=315, start_us=220000000, end_us=270000000, period_us=1000000,
              min_turn_us=250000, budget_us=2000, max_samples=64, depth=16)
SAMPLE_KEYS = ('sample requested_us us held_us resumed_us watch stopped_watch suspend state read resume stop frames valid pc lr sp fp').split()
SIGNED = {'suspend', 'state', 'read', 'resume'}
HEX = {'pc', 'lr', 'sp', 'fp', 'address'}
NOT_CALLED = -(1 << 31)


def fields(text, names):
    tokens = text.split(' ')
    if any(token.count('=') != 1 for token in tokens): raise ValueError('malformed stack fields')
    pairs = [token.split('=', 1) for token in tokens]
    if len(pairs) != len(names) or [key for key,_ in pairs] != list(names):
        raise ValueError('missing, duplicate or reordered stack field')
    result = {}
    for key,value in pairs:
        if key == 'image':
            if not value or len(value)>79 or not all(33<=ord(c)<=126 for c in value):
                raise ValueError('invalid image label')
            result[key] = value; continue
        pattern = r'[0-9a-f]+' if key in HEX else r'-?[0-9]+' if key in SIGNED else r'[0-9]+'
        if not re.fullmatch(pattern, value): raise ValueError('invalid stack integer')
        number = int(value, 16 if key in HEX else 10)
        if key in SIGNED:
            if not -(1<<31)<=number<(1<<31): raise ValueError('stack result code overflow')
        elif not 0<=number<(1<<64): raise ValueError('stack integer overflow')
        result[key] = number
    return result


def parse(text):
    configurations, samples, unavailable, resume_failures = [], {}, [], 0
    last = 0
    for line in text.splitlines():
        where = line.find(PREFIX)
        if where < 0: continue
        body = line[where+len(PREFIX):]
        if body.startswith('active '):
            config = fields(body[7:], CONFIG)
            if config != CONFIG: raise ValueError('unexpected stack probe configuration')
            configurations.append(config)
            if len(configurations)>1: raise ValueError('multiple stack activations or mixed boots')
        elif body == 'unavailable=mach-context': unavailable.append('mach-context')
        elif body == 'stopped=resume-failure': resume_failures += 1
        elif body.startswith('sample='):
            row = fields(body, SAMPLE_KEYS); ident = row['sample']
            if not last<ident<=CONFIG['max_samples'] or row['frames']>CONFIG['depth'] or row['valid'] not in (0,1) or row['stop']>10:
                raise ValueError('invalid sample ID, depth, validity or stop reason')
            row['frame_rows'] = []; samples[ident] = row; last = ident
        elif body.startswith('frame '):
            row = fields(body[6:], ('sample','index','address','image'))
            owner = samples.get(row['sample'])
            if owner is None or row['index']!=len(owner['frame_rows']) or row['index']>=owner['frames']+2:
                raise ValueError('orphan, duplicate or unordered stack frame')
            if not owner['valid'] or owner['resume']!=0: raise ValueError('frames after invalid snapshot or failed resume')
            if row['index']<2 and row['address']!=owner['pc' if row['index']==0 else 'lr']:
                raise ValueError('register/frame address mismatch')
            owner['frame_rows'].append(row)
        else: raise ValueError('malformed stack probe line')
    return dict(configurations=configurations, samples=list(samples.values()),
                unavailable=unavailable, resume_failures=resume_failures)


def summarize(parsed):
    rows = parsed['samples']; last_requested = None; missing = []
    ids = {row['sample'] for row in rows}
    if ids: missing = [i for i in range(1, max(ids)+1) if i not in ids]
    usable, incomplete, policy_errors, clock_errors, over_budget = [], [], [], [], []
    durations = []
    for row in rows:
        ident = row['sample']; requested = row['requested_us']; began = row['watch']>>2
        eligible = (CONFIG['start_us']<=requested<CONFIG['end_us'] and (row['watch']&3) in (1,2)
                    and 0<began<=requested and requested-began>=CONFIG['min_turn_us']
                    and (last_requested is None or requested-last_requested>=CONFIG['period_us']))
        last_requested = requested
        if not eligible: policy_errors.append(ident)
        expected_frames = row['frames']+2 if row['valid'] and row['resume']==0 else 0
        complete = len(row['frame_rows'])==expected_frames
        if not complete: incomplete.append(ident)
        good_clock = requested<=row['us']<=row['held_us']<=row['resumed_us']
        if row['suspend']==0:
            if not good_clock: clock_errors.append(ident)
            else:
                duration = row['resumed_us']-row['us']; durations.append(duration)
                if duration>=CONFIG['budget_us']: over_budget.append(ident)
        plausible_registers = (row['pc']>0 and row['sp']>0 and not row['sp']&15 and
                               row['fp']>=row['sp'] and not row['fp']&15 and row['fp']-row['sp']<=65536-16)
        good = (len(parsed['configurations'])==1 and eligible and complete and good_clock and
                plausible_registers and row['suspend']==row['state']==row['resume']==0 and
                row['valid']==1 and row['stopped_watch']==row['watch'] and row['frames']>0)
        if good: usable.append(row)
    image_counts = collections.Counter(frame['image'] for row in usable for frame in row['frame_rows'])
    return dict(scope='Same-process main-thread register/frame snapshots. Sampling perturbs scheduling; no GPU, physical FPS or gesture qualification.',
                active=len(parsed['configurations'])==1, sample_count=len(rows), usable_stack_samples=len(usable),
                missing_sample_ids=missing, incomplete_frame_samples=incomplete,
                policy_error_samples=policy_errors, clock_error_samples=clock_errors,
                resume_failures=parsed['resume_failures']+sum(r['suspend']==0 and r['resume']!=0 for r in rows),
                suspend_failures=sum(r['suspend'] not in (0,NOT_CALLED) for r in rows),
                state_failures=sum(r['state'] not in (0,NOT_CALLED) for r in rows),
                stale_watch_samples=[r['sample'] for r in rows if r['stop']==2],
                over_budget_samples=over_budget, maximum_capture_elapsed_us=max(durations,default=None),
                unavailable=parsed['unavailable'], image_offset_counts=dict(image_counts), samples=rows,
                hard_realtime_pause_limit=False, root_cause_proven=False, physical_fps_qualified=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('log',type=Path); ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args(); result=summarize(parse(args.log.read_text(errors='replace')))
    with args.out.open('x') as stream: json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('samples','image_offset_counts')},indent=2))


if __name__=='__main__': main()
