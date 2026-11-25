#!/usr/bin/env python3
"""Verify producer-labelled writes and compare physical scanout after restore."""

from importlib import import_module

import frame344_log as trace
from frame357_display import BOUND

scope = import_module('prepare-frame401')
prior = import_module('run-frame400-trial')


def producer_receipts(rows,latches,motion):
    claims = [r for r in rows[BOUND] if r.flags==2]
    swaps = trace.indexed((r for r in rows[trace.SWAP] if not r.flags),lambda r:r.id,'accepted swap')
    writes = trace.indexed((r for r in rows[trace.WRITER] if r.b),lambda r:r.b,'bound writer')
    issued, eop, ready = (
        trace.indexed(rows[kind],lambda r:r.id,'native fence') for kind in (trace.ISSUE,trace.EOP,trace.READY))
    scan_by_generation = {r['generation']:frame for frame,r in latches.items()}
    windows = motion['ordinary']['windows']
    receipts = []
    trace.require(len({r.c for r in claims})==len(claims),'producer certificate reused across swaps')
    for claim in claims:
        swap = swaps[claim.id]
        surface = claim.a & 0xffffffff
        trace.require(claim.c and claim.a>>32==claim.id and swap.c==(claim.b<<32|surface) and
                     (swap.tick,swap.seq)<=(claim.tick,claim.seq),'qualified producer swap lost its version')
        row = dict(generation=claim.id,surface=surface,version=claim.b,cookie=claim.c,
                   accepted_tick=swap.tick,bound_tick=claim.tick)
        writer = writes.get(claim.a)
        if writer:
            fence = writer.id
            issue, completion, visibility = issued[fence],eop.get(fence),ready.get(fence)
            trace.require((writer.a,writer.c)==(surface,claim.b) and claim.tick<=issue.tick<=writer.tick and
                          (visibility is None or (completion and writer.tick<=completion.tick<=visibility.tick)),
                          'producer certificate differs from the ordered native write')
            scan = scan_by_generation.get(claim.id)
            row.update(fence=fence,issue_tick=issue.tick,visible_tick=visibility.tick if visibility else None,
                       scan=scan,ordinary_motion=bool(scan and any(w['first_scan']<=scan<=w['last_scan']
                                                                  for w in windows)))
        receipts.append(row)
    return dict(qualified_claims=len(claims),physical_latches=sum(bool(r.get('scan')) for r in receipts),
                warm_motion_latches=sum(bool(r.get('ordinary_motion')) for r in receipts),receipts=receipts)


def score(execution,plan):
    report = prior.score(execution,plan,trial=scope.TRIAL)
    audit = prior.common.audit
    old_plan = scope.load(scope.P400/'trial-plan.json')
    old_report = scope.load(scope.CONTROL)
    old_scans,old = audit.score_archive(scope.P400/'execution',old_plan['kernel_banner'],
        expected_pairs=None,require_first=False)
    scans,new = audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(old==old_report['measurements']['0400'] and new==report['measurements'][scope.TRIAL],
                  '0400/0401 independent physical replay differs')
    raw = (execution/'kernel.log').read_text()
    rows,_,_,_ = prior.stage.staging.parse(raw)
    latches = prior.stage.staging.verified_latches(rows,prior.flip.latch_receipts(raw,rows)['accepted_by_scan'])
    for key in ('measurements','moving_Core_IO','all_warm_GPU_writers'):
        report[key]['0400'] = old_report[key]['0400']
    report.update(per_scan_0400_0401=prior.flip.parent.parent.paired_ordinals({'0400':old_scans,'0401':scans}),
        native_render_producer=producer_receipts(rows,latches,new['moving_GPU']))
    return report


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'0401 requires independent restoration')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        report = score(execution,plan)
        name = 'scanout-comparison-0400-0401.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0401-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    counts = report['native_render_producer']
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        exact_producer_claims=counts['qualified_claims'],newly_bound_warm_latches=counts['warm_motion_latches'])


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
