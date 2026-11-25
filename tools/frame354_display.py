"""Measure retention of ready swaps and verify writer, fence and read identity."""

from bisect import bisect_right
from collections import Counter

import frame344_log as trace
import frame351_display as present
import frame352_display as copy
from frame353_display import READY, TAKE, UNKNOWN_FRAME, MASK32

PROMOTE, VALIDATE = 56,57
KINDS = (READY,TAKE,PROMOTE,VALIDATE)


def order(row):
    return row.tick,row.seq


def ready_joins(rows, attempts, *, binding_kind=None):
    swaps = trace.indexed(rows[trace.SWAP],lambda r:r.id,'swap generation')
    marks = trace.indexed(rows[READY],lambda r:r.id,'ready observation')
    advances = trace.indexed(rows[PROMOTE],lambda r:r.id,'ready promotion')
    completes = trace.indexed(rows[trace.READY],lambda r:r.id,'GPU completion')
    writers = trace.indexed((r for r in rows[trace.WRITER] if r.b),lambda r:(r.id,r.b),'bound GPU writer')
    takes = trace.indexed(rows[TAKE],lambda r:r.id,'ready selection')
    validates = trace.indexed(rows[VALIDATE],lambda r:r.id,'fresh read version validation')
    edges = trace.indexed(rows[trace.VBLANK],lambda r:r.id,'hardware frame edge')
    accepted = [r for r in rows[trace.SWAP] if r.flags==0]
    accepted_order = [order(r) for r in accepted]
    bindings = ({} if binding_kind is None else
                trace.indexed(rows[binding_kind],lambda r:r.id,'issued writer claim'))
    promotions = list(advances.values())
    promotion_order = [order(r) for r in promotions]
    previous = None
    for advance in promotions:
        mark = marks.get(advance.id)
        swap = swaps.get(advance.id)
        fence = completes.get(mark.b) if mark else None
        ticket = (advance.id<<32)|advance.c
        writer = writers.get((mark.b,ticket)) if mark else None
        binding = bindings.get(advance.id)
        if binding_kind is not None:
            trace.require(binding and binding.flags==binding.c==0 and (binding.a,binding.b)==(ticket,advance.b) and
                          swap and writer and order(swap)<=order(binding)<=order(writer),
                          'promotion has no exact pre-issue claim')
        latest = bisect_right(accepted_order,order(binding or advance))-1
        trace.require(swap and latest>=0 and swap==accepted[latest] and swap.b==1 and
            mark and mark.flags in (0,1) and advance.flags==0 and advance.c==mark.a and
            ((advance.b<<32)|advance.c)==swap.c and advance.b>0 and advance.b%4==0 and advance.b<0xfffffffc and
            writer and writer.a==advance.c and writer.c==advance.b and fence and
            order(swap)<=order(writer)<=order(fence)<=order(mark)<=order(advance),
            'ready replaced without its accepted swap and completed watched writer')
        trace.require((not previous or previous.id<advance.id) and
            (not advance.a or (previous and previous.id==advance.a)), 'previous ready generation differs at replacement')
        previous = advance

    seen_frames = set()
    joined = []
    last_attempt = None
    for attempt in attempts:
        if last_attempt:
            trace.require(attempt['generation']>last_attempt['generation'] or
                (attempt['generation']==last_attempt['generation'] and not last_attempt['ready'] and
                 attempt['retry']==last_attempt['retry']+1), 'present generation regressed or duplicated')
        last_attempt = attempt
        take = takes.get(attempt['attempt'])
        receipts = attempt['blanking_proofs']
        reservations = [g for g in attempt['read_guards'] if g.get('surface_reservation')]
        trace.require(not receipts or take is not None,'blanking copy has no ready selection')
        if not take:
            trace.require(not reservations,'surface reservation has no ready selection')
            continue
        latest_ready = bisect_right(promotion_order,order(take))-1
        latest_swap = bisect_right(accepted_order,order(take))-1
        edge = edges.get(take.c)
        trace.require(latest_ready>=0 and latest_swap>=0 and
            promotions[latest_ready].id==take.a==attempt['generation']<=accepted[latest_swap].id and
            order(promotions[latest_ready])<=order(take) and take.tick<=attempt['attempt_tick'] and
            edge and edge.flags==1 and take.c not in seen_frames, 'selection lacks latest qualified ready frame or a unique scan')
        mark, advance = marks[take.a],advances[take.a]
        trace.require(take.b==mark.c and (take.b==UNKNOWN_FRAME or 0<=take.b<=MASK32),
                      'readiness frame differs from its selection')
        delta = None if take.b==UNKNOWN_FRAME else (take.c-take.b)&MASK32
        trace.require((delta is None or delta<(1<<31)) and take.flags==int(bool(delta)), 'invalid cross-frame selection')
        guards = attempt['read_guards']
        observed = validates.get(take.id)
        trace.require(not guards or observed,'read guard without a writer-version validation receipt')
        trace.require(not reservations or (len(guards)==len(reservations)==1 and observed and
            observed.flags==1 and (reservations[0]['surface'],reservations[0]['fence'])==(mark.a,mark.b)),
            'surface reservation differs from the selected, validated writer')
        if observed:
            accepted_guard = any(g['accepted'] and g['surface']==mark.a and g['resolved_tick']<=observed.tick for g in guards)
            trace.require(attempt['attempt_tick']<=observed.tick<=attempt['result_tick'] and
                observed.a==mark.a and observed.b==advance.b and observed.flags in (0,1,2) and
                (observed.b!=observed.c)==(observed.flags==2) and
                (observed.flags in (0,2) or accepted_guard), 'guard did not validate the selected writer version')
        trace.require(all(p['frame']==take.c and p['surface']==mark.a for p in receipts) and
            all(observed and observed.flags==1 and layer['surface']==mark.a and
                observed.tick<=layer['copy_start_tick'] and layer.get('native_fence')==mark.b for layer in attempt['layers']),
            'copy lacks exact writer, target slot or fresh read evidence')
        seen_frames.add(take.c)
        joined.append(dict(attempt=take.id,generation=take.a,surface=mark.a,fence=mark.b,version=advance.b,
            newest_swap_at_select=accepted[latest_swap].id,waiting_newer_swap=accepted[latest_swap].id>take.a,
            observation='probe' if mark.flags else 'GPU-completion',target_frame=take.c,frame_delay=delta,
            ready_tick=mark.tick,take_tick=take.tick,stale=bool(observed and observed.flags==2),
            guarded=bool(observed and observed.flags==1),copied=bool(attempt['layers']),
            verified_blank=any(p['disposition']=='verified-blank' for p in receipts)))
    return joined,accepted,promotions


def analyze(text, aligned, *, binding_kind=None, extra_kinds=()):
    bindings = () if binding_kind is None else (binding_kind,)
    rows,_,numer,denom = trace.parse(text,extra_kinds=(present.PRESENT,copy.WAKE,*KINDS,*bindings,*extra_kinds))
    trace.require(not rows[copy.WAKE],'same-slot wake receipt in held-ready mode')
    joined,swaps,advances = ready_joins(rows,aligned['attempts'],binding_kind=binding_kind)
    swap_ticks = [r.tick for r in swaps]
    advances_by_generation = {r.id:r for r in advances}
    missed = []
    certified = set()
    following = {}
    for window in aligned['windows']:
        for out in window['intervals']:
            certified.update(p['attempt'] for p in out['certified_blanking_overlaps'])
            following[out['previous_frame']] = (window['stroke'],window['phase'],out)
            if out['crc_relation']!='repeated' or out['present_attempts']:
                continue
            begin,end = (edge[1] for edge in out['edge_ticks'])
            arrived = swaps[bisect_right(swap_ticks,begin):bisect_right(swap_ticks,end)]
            if arrived:
                missed.append(dict(stroke=window['stroke'],phase=window['phase'],hardware_frame=out['frame'],
                    new_generations=[r.id for r in arrived],
                    new_generations_ready_by_edge=[r.id for r in arrived if r.id in advances_by_generation and
                                                   advances_by_generation[r.id].tick<=end]))
    for row in joined:
        next_interval = following.get(row['target_frame'])
        if row['attempt'] in certified and next_interval:
            stroke,phase,out = next_interval
            row['following_hardware_frame'] = dict(stroke=stroke,phase=phase,frame=out['frame'],
                classification=out['after_copy_boundary_check'])
    summary = {}
    for phase in ('active','release','all'):
        ids = {i for w in aligned['windows'] if w['phase']==phase
               for item in w['intervals'] for i in item['present_attempts']}
        sample = joined if phase=='all' else [r for r in joined if r['attempt'] in ids]
        retained = [r for r in sample if r['waiting_newer_swap']]
        relevant_misses = [r for r in missed if phase=='all' or r['phase']==phase]
        summary[phase] = dict(selections=len(sample),cross_frame_selections=sum(bool(r['frame_delay']) for r in sample),
            stale_generation_refusals=sum(r['stale'] for r in sample),
            newer_swap_waiting_at_selection=len(retained),older_ready_with_newer_swap_guarded=sum(r['guarded'] for r in retained),
            older_ready_with_newer_swap_verified_copies=sum(r['attempt'] in certified for r in retained),
            older_ready_with_newer_swap_followed_by_new_CRC=sum(
                r.get('following_hardware_frame',{}).get('classification')=='changed' for r in retained),
            repeat_without_attempt_but_new_swap=len(relevant_misses),
            repeat_without_attempt_but_new_swap_ready_by_edge=sum(bool(r['new_generations_ready_by_edge']) for r in relevant_misses),
            ready_to_selection_p95_ns=trace.quantile([(r['take_tick']-r['ready_tick'])*numer/denom for r in sample],.95))
    return dict(phases=summary,ready_promotions=len(advances),
        replacement_on_completed_write=sum(bool(r.a) for r in advances),joins=joined,unpresented_new_swaps=missed)
