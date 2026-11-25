#!/usr/bin/env python3
"""Align input consumption, SpringBoard turns and C4 production observations."""
import argparse
import importlib.util
import json
from pathlib import Path


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


UI = module('ui_trace_log')
SB = module('analyze-sb-rate-log')
TL = module('analyze-ui-timeline')


def analyze(kernel, backboard, springboard):
    capture = UI.parse(kernel)
    timeline = TL.analyze(kernel, backboard)
    start, end = SB.window_from_kernel(kernel)
    parsed = SB.parse(springboard)
    sb = SB.summarize(parsed, start, end)
    metal = sorted(TL.parse_metal(backboard), key=lambda row: row['made_us'])
    gaps = [(b['made_us']-a['made_us'], a['made_us'], b['made_us'])
            for a,b in zip(metal, metal[1:])]
    # Bound detail to the largest 20 gaps. Include a callback spanning the
    # whole gap; selecting only callbacks whose entry falls inside hides stalls.
    detailed = []
    for duration, before, after in sorted(gaps, reverse=True)[:20]:
        if duration < 1000000:
            continue
        observed = SB.summarize(parsed, before, after)
        detailed.append(dict(start_us=before, end_us=after, duration_us=duration,
                             input=observed['input'], turns=observed['turns'],
                             animation_requests=observed['animation']['count']))
    return {
        'scope': 'CPU timestamps in the mach_absolute_time domain. Use boot-qualified '
                 'log tails from one trial. Queue progress, public sendEvent entry and '
                 'C4 creation are separate observations, not causal frame identities.',
        'window': {'start_us':start, 'end_us':end},
        'kernel_and_c4': timeline,
        'queues': capture['queue_state_summary'],
        'springboard': sb,
        'full_tail_c4': {
            'records':len(metal),
            'creation_gaps':SB.gap_summary([gap[0] for gap in gaps]),
            'gaps_4900000_to_5300000_us':sum(4900000<=gap[0]<=5300000 for gap in gaps),
            'largest_gaps_with_springboard_observations':detailed,
        },
        'physical_fps_qualified':False,
        'gesture_acceptance_qualified':False,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel_log','backboardd_log','springboard_log'):
        ap.add_argument(name, type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = analyze(*(getattr(args,name).read_text(errors='replace')
                       for name in ('kernel_log','backboardd_log','springboard_log')))
    with args.out.open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
