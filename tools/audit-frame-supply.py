#!/usr/bin/env python3
"""Replay slow-drag availability at accepted swap, issue and observed readiness."""

import argparse
from importlib import import_module
import json

from frame364_analysis import score, trace
from frame364_scope import REF363
from frame365_scope import P364, REF364
from frame366_scope import BASE, REF365, load, pacing, sha


def feasible(slots, events, previous_generation):
    """Upper bound with zero copy time and arbitrary safe retention of old versions."""
    best = {previous_generation:0}
    for slot in slots:
        before = tuple(best.items())
        for generation,tick in events:
            if tick>slot.end:
                continue
            predecessors = [count for earlier,count in before if earlier<generation]
            if predecessors:
                best[generation] = max(best.get(generation,0),1+max(predecessors))
    return max(best.values())


def examine(execution, metrics, verdict):
    rows,_,num,den = trace.parse((execution/'kernel.log').read_text(),
        extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    ns = lambda tick:tick*num//den
    phase = metrics['slow_drag']
    scored = {(f['frame']-1)&0xffffffff for f in phase['identity']['frames']}
    slots = [x for x in score.scan_windows(rows[trace.VBLANK],ns,num/den,bracketed=True) if x.frame in scored]
    trace.require(slots and len(slots)==phase['known_scans'],'slow-drag bracket coverage differs')
    attempts = trace.indexed(rows[trace.ATTEMPT],lambda r:r.id,'attempt')
    previous = max((attempts[r.id].a for r in rows[trace.RESULT] if r.a and ns(r.tick)<slots[0].opening),default=0)
    accepted = {r.id:ns(r.tick) for r in rows[trace.SWAP] if not r.flags and r.c and r.id>previous}
    issues = trace.indexed(rows[trace.ISSUE],lambda r:r.id,'native issue')
    ready = trace.indexed(rows[trace.READY],lambda r:r.id,'native visibility')
    issued,visible = {},{}
    for r in rows[trace.WRITER]:
        generation = r.b>>32
        if generation not in accepted:
            continue
        issued[generation] = ns(issues[r.id].tick)
        receipt = ready.get(r.id)
        if receipt:
            visible[generation] = ns(receipt.tick)
    bounds = {name:feasible(slots,list(events.items()),previous) for name,events in
        (('accepted',accepted),('native_issue',issued),('observed_visibility',visible))}
    trace.require(len(slots)>=bounds['accepted']>=bounds['native_issue']>=bounds['observed_visibility']>=
                  phase['completed_copies'],'staged supply bounds disagree with actual copies')
    return dict(trial=verdict['trial'],scored_scans=len(slots),bounds=bounds,actual_copies=phase['completed_copies'],
                actual_new_images=phase['scans']['changed'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-0366',action='store_true')
    args = parser.parse_args()
    early = load(P364/'execution/motion-identity-0363-0364.json')
    later = load(REF365/'CA-timing-0364-0365.json')
    cases = [(REF363,early['reference_0363']),(REF364,early['current_0364']),(REF365,later['current_0365'])]
    if args.include_0366:
        execution = BASE/'execution'
        audited = import_module('audit-frame366-restored')
        verdict = audited.check_restored(execution)
        scoped = load(BASE/'scoped-scan-audit.json')
        trace.require(scoped['state']=='0366-scoped-scan-audit-root-restored' and
            not scoped['slow_drag']['scans']['unknown'] and
            all(scoped['input_pins'][str(execution/name)]==sha(execution/name)
                for name in ('result.json','independent-restore.json','kernel.log')),
            '0366 slow-drag scope or pins differ')
    trials = [examine(folder,metrics,pacing.check_restored(folder)) for folder,metrics in cases]
    if args.include_0366:
        trials.append(examine(execution,scoped,verdict))
    result = dict(trials=trials,
        scope='Keep recorded timing and the last preceding displayed generation fixed. '
              'Allow eventual accepted swaps to be distinct and hold their versions without copy cost. '
              'The counts are upper bounds for these traces, not measured output or hardware completion times.')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
