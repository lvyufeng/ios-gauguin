#!/usr/bin/env python3
"""Validate offline flip ordering and bound what it could change in 0380."""

from importlib import import_module

import frame381_page_flip as flip

scope = import_module('prepare-frame381')
candidate = import_module('run-frame381-trial')
parent = candidate.parent
load, require = scope.load, scope.require


def test_route_decode():
    def sample(s2cr, cbar, sctlr):
        header = 'SWEET F381 APPS: id0=48016647 id1=60430040 id2=00007511 control=00000000 secure=00000000 groups=71'
        stream = (f'SWEET F381 STREAM: sid={{sid}} matches=1 index=3 smr=80020800 '
                  f's2cr={s2cr:08x} cbar={cbar:08x} sctlr={sctlr:08x}')
        footer = 'SWEET F381 DMA: status=stable attempts=3 samples=3 first=4294967294 last=0 extra_mmio_writes=0'
        return '\n'.join((header,stream.format(sid='800'),stream.format(sid='802'),footer))

    direct = sample(1<<16,0xffffffff,0xffffffff)
    assert candidate.dma_route(direct)['address_translation_bypassed_for_both']
    context = sample(3,1<<16,0)
    assert candidate.dma_route(context)['address_translation_bypassed_for_both']
    for raw in (sample(3,1<<16,1),sample(3,0,0),
                context.replace('matches=1','matches=2'),context.replace('control=00000000','control=00000001')):
        assert not candidate.dma_route(raw)['address_translation_bypassed_for_both']
    for raw in (direct.replace('80020800','80000800'),direct.replace('attempts=3','attempts=9'),
                direct.replace('groups=71','groups=70'),direct+'\n'+direct):
        try:
            candidate.dma_route(raw)
        except ValueError:
            continue
        raise AssertionError('accepted inconsistent hardware report')
    return 10


def replay():
    scope.check_reference()
    report = load(scope.REFERENCE/'scanout-comparison-0375-0379-0380.json')
    frame = load(scope.REFERENCE/'frame-scanout-analysis.json')
    raw = (scope.REFERENCE/'kernel.log').read_text()
    rows,strokes,n,d = parent.trace.parse(raw,extra_kinds=(parent.score.PRESENT,parent.score.copy.WAKE,*parent.score.KINDS))
    require(len(strokes)==13 and (n,d)==(625,12),'0380 trace changed')
    edges = {row.id:row for row in rows[parent.trace.VBLANK] if row.flags==1}
    ns = lambda tick: tick*n//d

    retest = report['segments']['retest']['stroke_4_release']
    crossing, = retest['crossed']
    attempt, = [a for a in frame['attempts'] if a['attempt']==crossing['attempt']]
    layer, = attempt['layers']
    start, done = layer['copy_start_tick'], layer['copy_end_tick']
    eop, visible = layer['eop_observed_tick'],layer['surface_ready_tick']
    next_edge = edges[crossing['frame']+1]
    require(layer['bytes']==flip.FRAME_BYTES and eop<=visible<start<next_edge.a<next_edge.b<done,
            '0380 release boundary or GPU visibility order changed')
    release = dict(attempt=attempt['attempt'],generation=attempt['generation'],scan_before=crossing['frame'],
        bytes=layer['bytes'],fence=layer['native_fence'],core={k:layer[k] for k in ('queue','ticket','job')},
        earliest_edge_ns=ns(next_edge.a),latest_edge_ns=ns(next_edge.b),
        observed_cache_visible_to_copy_begin_ns=ns(start)-ns(visible),
        copy_duration_ns=ns(done)-ns(start),late_by_next_edge_ns=[ns(done)-ns(next_edge.b),ns(done)-ns(next_edge.a)],
        modeled_margin_if_read_lease_available_at_cache_visibility_ns=[
            ns(next_edge.a)-ns(visible+done-start),ns(next_edge.b)-ns(visible+done-start)],
        same_timing_can_latch_on_original_target=False)

    repeats = []
    for miss in report['slow_drag']['repeats']:
        edge = edges[miss['frame']]
        cutoff = miss['cutoff_ns']
        require(cutoff < ns(edge.a), 'old deadline is not before the target edge')
        witnesses = []
        for writer in miss['accepted_candidates']:
            relative = writer.get('relative_ns',{})
            observed = relative.get('observed_GPU_completion')
            ready = relative.get('cache_visible')
            if observed is None or ready is None:
                continue
            require(writer['native_fence'] and observed <= ready,'unbound or unordered cache receipt')
            visible_ns = cutoff+ready
            witnesses.append(dict(generation=writer['generation'],fence=writer['native_fence'],
                eop_after_old_cutoff_ns=observed,visible_after_old_cutoff_ns=ready,
                margin_from_visible_to_target_edge_ns=[ns(edge.a)-visible_ns,ns(edge.b)-visible_ns]))
        repeats.append(dict(frame=miss['frame'],candidates=witnesses,
            cache_visible_by_earliest_edge=any(w['margin_from_visible_to_target_edge_ns'][0]>0 for w in witnesses),
            cache_visible_by_latest_edge=any(w['margin_from_visible_to_target_edge_ns'][1]>0 for w in witnesses)))
    require(len(repeats)==7 and all(w['visible_after_old_cutoff_ns']>0
            for row in repeats for w in row['candidates']),'0380 slow drag receipt differs')
    return dict(stroke_4_release=release,slow_drag_repeats=repeats,
        slow_repeats_with_visibility_before_earliest_target_edge=sum(x['cache_visible_by_earliest_edge'] for x in repeats),
        slow_repeats_with_visibility_before_latest_target_edge=sum(x['cache_visible_by_latest_edge'] for x in repeats),
        assumptions='Fixed observed GPU and CPU timing. The DPU may fetch before the edge. '
            'Availability of an earlier read lease, transfer time and a real hardware latch are unverified.')


def check():
    old = import_module('model-scanout-buffers').exercise()
    return dict(state='0381-offline-ordering-and-timing-verified',device_commands=0,
        patch_sha256=scope.sha(scope.PATCH),lifetime=flip.exercise(),state_space=old,
        route_decoder_cases=test_route_decode(),replayed_0380=replay())


if __name__=='__main__':
    out = check()
    scope.save(scope.BASE/'host-verification.json',out)
    release = out['replayed_0380']['stroke_4_release']
    print('0380 replay, release lateness in ns',release['late_by_next_edge_ns'])
    print('Cache visibility before earliest edge on slow drag repeats',
          out['replayed_0380']['slow_repeats_with_visibility_before_earliest_target_edge'])
