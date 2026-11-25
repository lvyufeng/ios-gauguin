"""Qualify the dedicated latch witnesses and the issued-frame experiment."""

from collections import Counter
from itertools import zip_longest

import frame344_log as trace
import frame349_log as misr
import frame354_display as ready

BOUND, CALIBRATION = 58, 59
KINDS = (*ready.KINDS, BOUND, CALIBRATION)
MASK = 0xffffffff
CALIBRATION_OFFSET_NS = 750_000_000
CALIBRATION_LIMIT_NS = 1_500_000_000
CALIBRATION_GAP = 8
MARKERS = (0x00ff0000, 0x0000ff00, 0)


def calibration(rows, strokes, paired, copies, scale):
    try:
        edges = rows[trace.VBLANK]
        by_frame = trace.indexed(edges, lambda r:r.id, 'calibration hardware edge')
        events = rows[CALIBRATION]
        trace.require([r.id>>32 for r in events]==[0,1,2,3,4] and all(r.flags==1 for r in events),
                      'must pause, verify three isolated stores and resume without recovery')
        pause, *stores, resume = events
        end_script = strokes[-1][1]
        trace.require(CALIBRATION_OFFSET_NS<=(pause.tick-end_script)*scale and
                      (resume.tick-end_script)*scale<=CALIBRATION_LIMIT_NS+5_000_000 and
                      pause.a==pause.b==pause.c==resume.a==resume.b==resume.c==0 and
                      not misr.copy_overlap(copies,pause.tick,resume.tick) and
                      all(CALIBRATION_GAP<=((b.id-a.id)&MASK) for a,b in zip(events,events[1:])),
                      'calibration pause, cadence or copy isolation differs')
        original = stores[0].c>>32
        markers = []
        for step,(row,mask) in enumerate(zip(stores,MARKERS,strict=True),1):
            frame = row.id&MASK
            left,right = by_frame.get(frame),by_frame.get((frame+1)&MASK)
            pair = paired.get(frame)
            trace.require(left and right and left.flags==1 and misr.consecutive((left,right),scale) and
                          pair and pair['agrees'] and (row.c>>32)==original and (row.c&MASK)==(original^mask) and
                          left.b<=pair['ticks'][1][1]<row.a<row.b<=row.tick and
                          (right.a-row.b)*scale>=misr.COPY_GUARD_NS, 'marker lacks exact pixels or an independent blank boundary')
            markers.append(dict(seq=row.seq, surface=0, start_tick=row.a, end_tick=row.b,
                                calibration_step=step, marker_scan_frame=(frame+1)&MASK))
        phase = misr.calibrate(edges,paired,[*copies,*markers],scale)
        witnesses = [w for w in phase['witnesses'] if 'calibration_step' in w['copy']]
        trace.require(phase['qualified'] and sorted(w['copy']['calibration_step'] for w in witnesses)==[1,2,3] and
                      all(w['copy']['marker_scan_frame']==w['expected_scan_frame'] for w in witnesses) and
                      len({w['expected_scan_frame'] for w in witnesses})==3,
                      'three independent and agreeing marker latch witnesses are required')
        return dict(phase,dedicated_witnesses=witnesses,marker_pixel_restored=True,
                    pause_tick=pause.tick,resume_tick=resume.tick)
    except ValueError as error:
        return dict(qualified=False,lag_frames=None,witnesses=[],dedicated_witnesses=[],
                    calibration_error=str(error))


def retained_before_completion(rows, selection):
    swaps = trace.indexed((r for r in rows[trace.SWAP] if not r.flags),lambda r:r.id,'accepted generation')
    claims = trace.indexed(rows[BOUND],lambda r:r.id,'writer claim')
    visibility = trace.indexed(rows[trace.READY],lambda r:r.id,'visibility receipt')
    writers = trace.indexed((r for r in rows[trace.WRITER] if r.b),lambda r:r.b>>32,'bound writer')
    issues = trace.indexed(rows[trace.ISSUE],lambda r:r.id,'issue receipt')
    eops = trace.indexed(rows[trace.EOP],lambda r:r.id,'EOP receipt')
    trace.require(all(ready.order(a)<ready.order(eops[a.id])<ready.order(visibility[a.id])<ready.order(b)
                      for a,b in zip(rows[trace.ISSUE],rows[trace.ISSUE][1:])
                      if a.id in eops and a.id in visibility) and
                  all(a.id<b.id for a,b in zip(rows[trace.ISSUE],rows[trace.ISSUE][1:])),
                  'native submit or completion order changed')
    overtaken = set()
    for generation,writer in writers.items():
        claim,swap = claims.get(generation),swaps.get(generation)
        successor = swaps.get(generation+1)
        issue,fence,eop = issues.get(writer.id),visibility.get(writer.id),eops.get(writer.id)
        trace.require(claim and swap and issue and (claim.a,claim.b)==(writer.b,writer.c) and
                      swap.c==((writer.c<<32)|writer.a) and
                      ready.order(swap)<=ready.order(claim)<=ready.order(issue)<=ready.order(writer),
                      'issued frame lost its exact reservation')
        if fence:
            trace.require(eop and ready.order(writer)<=ready.order(eop)<ready.order(fence),
                          'writer completed before issue, EOP or surface visibility')
        if successor and fence and ready.order(claim)<ready.order(successor)<ready.order(fence):
            overtaken.add(generation)
    promoted = {r.id for r in rows[ready.PROMOTE]}
    hits = [r for r in selection['joins'] if r['generation'] in overtaken]
    bounded = [r for r in hits if r.get('following_hardware_frame')]
    classifications = Counter(r['following_hardware_frame']['classification'] for r in bounded)
    return dict(claims=len(claims),issued_with_exact_claim=len(writers),
                successors_before_visibility=len(overtaken),retained_promotions=len(overtaken&promoted),
                retained_selections=len(hits),guarded_copies=sum(r['copied'] and r['guarded'] for r in hits),
                independently_bounded_scored_copies=len(bounded),hardware_classifications=dict(classifications),
                verified_candidates=bounded)


def compare(displays, *, reference='0357'):
    """Align by gesture, phase and physical refresh ordinal, never raw tick."""
    lanes = {trial:{(w['stroke'],w['phase']):w['intervals'] for w in report['windows']}
             for trial,report in displays.items()}
    trace.require(all(len(windows)==26 and windows.keys()==lanes[reference].keys()
                      for windows in lanes.values()), 'missing matched gesture windows')
    alignment = []
    for (stroke,phase) in lanes[reference]:
        slots = zip_longest(*(windows[stroke,phase] for windows in lanes.values()))
        for ordinal, entries in enumerate(slots,1):
            alignment.append(dict(stroke=stroke,phase=phase,ordinal=ordinal,
                trials={trial:(dict(frame=e['frame'],kind=e.get('after_copy_boundary_check',e['full_frame']),crc=e['crc_relation'])
                               if e else None) for trial,e in zip(lanes,entries,strict=True)}))
    return dict(aligned_by='gesture, phase and hardware refresh ordinal',
                phases={trial:report['phases'] for trial,report in displays.items()},frames=alignment)
