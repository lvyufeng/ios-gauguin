"""Describe repeated warm swipes by the latest observed pipeline stage."""

from collections import Counter, defaultdict
from importlib import import_module
import json
from statistics import median

from frame364_analysis import motion_deadlines, score, trace

scope = import_module('prepare-frame367')
audit = import_module('audit-frame366-restored')
pacing = import_module('audit-frame-pacing')
feasible = import_module('audit-frame-supply').feasible


def furthest_phase(miss):
    if miss['same_CRC_copy']:
        return 'certified_copy_same_CRC'
    stages = {item['stage'] for item in miss['accepted_candidates']}
    if not stages:
        return 'no_new_eligible_swap'
    if 'ready_by_cutoff' in stages or 'visible_awaiting_ready_promotion' in stages:
        return 'cache_visibility_observed'
    if 'GPU_completion_to_cache_visibility' in stages or 'issued_awaiting_observed_GPU_completion' in stages:
        return 'native_issue_observed_writes_pending_or_not_visible'
    if any(item in ('before_Core_buffer','before_Core_commit_enqueue','Core_commit_queue','Core_submit_pre_IO') or
           item.startswith('submit_') for item in stages):
        return 'exact_Core_writer_before_native_issue'
    return 'swap_without_more_exact_readiness_evidence'


def supply_ceiling(windows, slots, rows, ns):
    started = {r.id:r.a for r in rows[trace.ATTEMPT]}
    copies = [(ns(r.tick),started[r.id]) for r in rows[trace.RESULT] if r.a]
    issued = {r.id:ns(r.tick) for r in rows[trace.ISSUE]}
    visible = {r.id:ns(r.tick) for r in rows[trace.READY]}
    accepted = {r.id:ns(r.tick) for r in rows[trace.SWAP] if not r.flags and r.c}
    writers = {r.b>>32:r.id for r in rows[trace.WRITER] if r.b}
    results = []
    for _,lane in windows:
        scans = [slots[r['previous_frame']] for r in lane['intervals'] if r['previous_frame'] in slots]
        missing = len(lane['intervals'])-len(scans)
        audit.require(scans,'no bracketed scan in a warm stroke')
        before = max((g for t,g in copies if t<scans[0].opening),default=0)
        accepted_in_window = [(g,t) for g,t in accepted.items() if g>before and t<=scans[-1].end]
        launch = [(g,issued[writers[g]]) for g,_ in accepted_in_window if g in writers]
        ready = [(g,visible[writers[g]]) for g,_ in accepted_in_window if g in writers and writers[g] in visible]
        rates = dict(accepted=accepted_in_window,native_issue=launch,observed_visible=ready)
        bounds = {name:feasible(scans,events,before)+missing for name,events in rates.items()}
        results.append(dict(stroke=lane['stroke'],scans=len(scans)+missing,unbracketed=missing,
            previous_copied_generation=before,upper_bound=bounds))
    return dict(scans=sum(w['scans'] for w in results),unbracketed=sum(w['unbracketed'] for w in results),
        upper_bound={key:sum(w['upper_bound'][key] for w in results) for key in results[0]['upper_bound']},
        windows=results,scope='Keep the observed swap and scan times. Permit indefinite valid retention and '
            'zero copy time. Count any unbracketed slot as an optimistic success.')


def prior_writer_replay(repeats, slots, rows, kernel, frame, ns):
    swaps = {r.id:r for r in rows[trace.SWAP]}
    issues = {r.id:r for r in rows[trace.ISSUE]}
    observed = {r.id:ns(r.tick) for r in rows[trace.READY]}
    io = {r['token']:r for r in kernel['rows'] if r['selector']==70}
    bound = {r.b>>32:r.id for r in rows[trace.WRITER] if r.b}
    source_versions = defaultdict(list)
    by_version = defaultdict(list)
    flush = kernel['phase_names']['70'].index('surface_cache_flush')
    for row in rows[trace.WRITER]:
        begin = io[issues[row.id].a]['begin'][flush]
        source_versions[row.a].append((row.c,begin))
        by_version[row.a,row.c].append(row)

    lost = [miss for miss in repeats if miss['phase']=='swap_without_more_exact_readiness_evidence']
    candidate_ids = {c['generation'] for miss in lost for c in miss['accepted_candidates']}
    prior = {}
    nearby = 0
    for generation in candidate_ids:
        swap = swaps[generation]
        version,surface = divmod(swap.c,1 << 32)
        earlier = by_version[surface,version-4]
        if len(earlier)==1 and not earlier[0].b:
            old = earlier[0]
            prior[generation] = old
            nearby += abs(ns(old.tick)-ns(swap.tick))<=5_000_000
    full = [layer['copy_ns'] for attempt in frame['attempts'] for layer in attempt['layers']
            if layer['bytes']==trace.FRAME_BYTES]
    copy = int(median(full))
    placements = []
    for miss in lost:
        last = bound.get(miss['previous_copied_generation'])
        slot = slots[miss['scan_slot']]
        for candidate in miss['accepted_candidates']:
            g = candidate['generation']
            writer = prior.get(g)
            if writer is None or writer.id not in observed or last is None or writer.id<=last:
                continue
            ready = observed[writer.id]
            end = max(slot.opening,ns(swaps[g].tick),ready)+copy
            overwritten = any(v>writer.c and t<=end for v,t in source_versions[writer.a])
            if end<=slot.end and not overwritten:
                placements.append(dict(scan=slot.frame,stroke=miss['stroke'],generation=g,preceding_fence=writer.id,
                    actual_preceding_display_fence=last,modeled_end_margin_ns=slot.end-end))
    return dict(affected_swaps=len(candidate_ids),preceding_versions_with_unclaimed_writer=len(prior),
        preceding_native_issues_within_5ms_of_swap=nearby,median_copy_ns=copy,
        candidate_scans=len({p['scan'] for p in placements}),
        distinct_candidate_preceding_writers=len({p['preceding_fence'] for p in placements}),
        placements=placements,scope='An accepted swap does not identify the preceding version as its producer. '
            'Replay counts opportunities only if that additional identity is established.')


def measure(execution):
    result = audit.check_restored(execution)
    proof = scope.load(scope.P366/'scoped-scan-audit.json')
    audit.require(proof['input_pins'][str(execution/'kernel.log')]==scope.sha(execution/'kernel.log'),
                  'trace differs from scoped 0366 review')
    frame = audit.load(execution/'frame-scanout-analysis.json')
    raw = (execution/'kernel.log').read_text()
    rows,_,num,den = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    display = score.copy.analyze(raw,frame,extra_kinds=score.KINDS)
    timing, = rows[trace.TIMING]
    edges,_ = audit.refine_post_copy_edges(rows,display,timing)
    corrected = rows | {trace.VBLANK:list(edges.values())}
    ns = lambda tick:tick*num//den
    slots = {item.frame:item for item in score.scan_windows(corrected[trace.VBLANK],ns,num/den,bracketed=True)}
    certificates = score.copy.copy_certificates(display['attempts'],edges,timing)
    paired = []
    for window,lane in zip(frame['hardware']['windows'],display['windows'],strict=True):
        if lane['phase']!='active' or lane['stroke']<3:
            continue
        for output,interval in zip(window['outputs'],lane['intervals'],strict=True):
            if interval['after_copy_boundary_check']=='unknown' and score.copy.resolve_overlap(output,certificates):
                interval.update(after_copy_boundary_check=interval['crc_relation'])
        paired.append((window,lane))
    report = pacing.cadence(paired,[r.tick for r in rows[trace.SWAP] if not r.flags and r.b],ns)
    strokes = {r['frame']:lane['stroke'] for _,lane in paired for r in lane['intervals']}
    lanes = [r for _,lane in paired for r in lane['intervals']]
    measured = [r for r in lanes if r['previous_frame'] in slots]
    unavailable = [dict(frame=r['frame'],stroke=strokes[r['frame']]) for r in lanes
                   if r['previous_frame'] not in slots and r['after_copy_boundary_check']=='repeated']
    core = audit.load(execution/'core-wait-execution-analysis.json')
    joined = audit.load(execution/'kernel-IO-identity-analysis.json')
    identities = motion_deadlines(corrected,dict(display,windows=[dict(intervals=measured)]),core,
        dict(joined,complete_submit_count=len(joined['submits']),full_script_bounds_us=None),ns,num/den)
    stage_counts = Counter()
    for miss in identities['repeats']:
        phase = furthest_phase(miss)
        stage_counts[phase]+=1
        miss.update(phase=phase,stroke=strokes[miss['frame']])
    audit.require(len(unavailable)+sum(stage_counts.values())==report['scans']['repeated'],
                  'warm repeat classification has incomplete coverage')
    return dict(trial=result['trial'],warm_active=report,stages_at_copy_start_cutoff=dict(stage_counts),
        repeated_with_no_bracketed_cutoff=unavailable,repeats=identities['repeats'],
        supply_ceiling=supply_ceiling(paired,slots,corrected,ns),
        preceding_writer=prior_writer_replay(identities['repeats'],slots,corrected,
            audit.load(execution/'kernel-IO-analysis.json'),frame,ns),
        scope='Furthest recorded pipeline evidence for an accepted generation newer than the last copied one. '
              'A late qualified cutoff or a cache-visible writer does not certify the version was still valid.')


if __name__=='__main__':
    print(json.dumps(measure(scope.REF366),indent=2))
