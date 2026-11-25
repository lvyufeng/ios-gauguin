#!/usr/bin/env python3
"""Score the bounded previous-swap trial after independent restoration."""

from importlib import import_module

import frame344_log as trace
from frame357_display import BOUND

scope = import_module('prepare-frame391')
previous = import_module('run-frame390-trial')
flip,stage = previous.flip,previous.stage


def previous_candidates(execution, measured):
    raw = (execution/'kernel.log').read_text()
    rows,_,_,_ = stage.staging.parse(raw)
    evidence = flip.latch_receipts(raw,rows)
    latches = stage.staging.verified_latches(rows,evidence['accepted_by_scan'])
    expected = trace.indexed((row for row in rows[trace.SWAP] if not row.flags and row.c),
                             lambda row:row.id,'accepted display update')
    writers = trace.indexed((row for row in rows[trace.WRITER] if row.b),
                            lambda row:row.b>>32,'claimed native writer')
    visible = trace.indexed(rows[trace.READY],lambda row:row.id,'visible GPU fence')
    claim = [row for row in rows[BOUND] if row.flags==1]
    retained = {}
    for row in claim:
        swap = expected[row.id]
        version, surface = divmod(swap.c,1<<32)
        trace.require(swap.tick<row.tick and row.a==((row.id<<32)|surface) and row.b==version,
            'previous swap lost the original surface-version identity')
        if writer := writers.get(row.id):
            trace.require((writer.b,writer.a,writer.c)==(row.a,surface,version) and row.tick<=writer.tick,
                'older descriptor does not match its exact writer')
            retained[row.id] = dict(generation=row.id,render_fence=writer.id,
                ready_tick=visible[writer.id].tick if writer.id in visible else None,latch=None)
    for scan,latch in latches.items():
        generation = latch['generation']
        if generation in retained:
            candidate = retained[generation]
            trace.require(candidate['render_fence']==latch['fence'] and candidate['ready_tick']==latch['visible_tick'],
                'older submitted frame latched without its exact ready fence')
            candidate['latch'] = scan
    warm = measured['moving_GPU']['ordinary']['windows']
    return dict(claimed=len(claim),exact_writers=len(retained),cache_visible=sum(r['ready_tick'] is not None for r in retained.values()),
        latched=sum(r['latch'] is not None for r in retained.values()),visible_warm=sum(
            r['latch'] is not None and any(w['first_scan']<=r['latch']<=w['last_scan'] for w in warm)
            for r in retained.values()),receipts=list(retained.values()))


def after_restore(execution, plan, result, before, code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'previous-swap scoring requires independent restore')
    flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        scored = previous.score_pair(execution,plan,trial=scope.TRIAL,measure_CA=False)
        scored['previous_swap_candidates'] = previous_candidates(execution,scored['measurements'][scope.TRIAL])
        out = 'scanout-comparison-0388-0391.json'
        stage.save_bounded(execution/out,scored,2_000_000)
    except (KeyError, OSError, ValueError) as error:
        result.update(state='0391-display-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=out,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=scored['stable_60_fps_observed'],
        previous_swap_latches=scored['previous_swap_candidates']['latched'])


if __name__=='__main__':
    raise SystemExit(previous.runner.main(scope,after_restore_fn=after_restore))
