"""Join the pre-blank fence checks to exact completions and scanout."""

from collections import Counter

import frame344_log as trace
from frame354_display import READY, order
from frame357_display import BOUND, KINDS as RETAINED
from frame358_audit import PROBE, PROBE_LIMIT

LOCK_RETRY = 61
RAW_PROBE = 64
KINDS = (*RETAINED, PROBE, LOCK_RETRY, RAW_PROBE)
RESULTS = {1:'lock_busy',2:'stale',3:'pending',4:'published'}


def probe_joins(rows, display, selection):
    notices = trace.indexed(rows[PROBE],lambda r:r.id,'probe hardware scan')
    trace.require(len(notices)<=PROBE_LIMIT,'extra readiness checks exceed the frozen limit')
    claims = trace.indexed(rows[BOUND],lambda r:r.id,'bound writer reservation')
    writers = trace.indexed((r for r in rows[trace.WRITER] if r.b),lambda r:r.b,'bound native writer')
    issue = trace.indexed(rows[trace.ISSUE],lambda r:r.id,'native issue')
    eop = trace.indexed(rows[trace.EOP],lambda r:r.id,'observed EOP')
    visible = trace.indexed(rows[trace.READY],lambda r:r.id,'fence publication')
    marks = trace.indexed(rows[READY],lambda r:r.id,'ready promotion')
    edges = trace.indexed(rows[trace.VBLANK],lambda r:r.id,'hardware edge')
    selected = {r['generation']:r for r in selection['joins'] if r['copied']}
    scored = {row['previous_frame']:window['phase'] for window in display['windows'] for row in window['intervals']}
    detail = []
    for rec in notices.values():
        generation, surface = rec.a>>32, rec.a&0xffffffff
        version, fence = rec.b>>32, rec.b&0xffffffff
        claim, edge = claims.get(generation), edges.get(rec.id)
        trace.require(rec.flags in RESULTS and claim and claim.a==rec.a and claim.b==version and
                      bool(fence)==(rec.flags==4) and edge and edge.b<=rec.c<=rec.tick and
                      order(claim)<=(rec.c,rec.seq),'probe lacks qualified slot, bound version or start tick')
        item = dict(hardware_frame=rec.id,phase=scored.get(rec.id),generation=generation,
                    surface=surface,version=version,started_tick=rec.c,finished_tick=rec.tick,result=RESULTS[rec.flags])
        if rec.flags in (3,4):
            writer = writers.get(rec.a)
            trace.require(writer and writer.id in issue and (writer.a,writer.c)==(surface,version) and
                          order(issue[writer.id])<=order(writer)<=order(rec),'probe did not name an issued writer')
        if rec.flags==4:
            finished, memory_ready, promoted = eop.get(fence), visible.get(fence), marks.get(generation)
            trace.require(writer.id==fence and finished and memory_ready and
                          (rec.c,0)<=order(finished)<order(memory_ready)<=order(rec) and
                          (not promoted or (promoted.b==fence and order(rec)<=order(promoted))),
                          'early fence publication fails the exact issue/EOP/visibility join')
            item.update(fence=fence,eop_tick=finished.tick,visible_tick=memory_ready.tick,
                        promoted=bool(promoted))
            copied = selected.get(generation)
            if copied:
                trace.require(copied['guarded'] and copied['fence']==fence,'probe copy lacks its exact guarded writer')
                image = copied.get('following_hardware_frame')
                item.update(selected_frame=copied['target_frame'],same_scan=copied['target_frame']==rec.id,
                            accepted_full_frame=image if image and image['classification']=='changed' else None)
        detail.append(item)
    counts = {phase:dict(Counter(r['result'] for r in detail if phase=='all' or r['phase']==phase))
              for phase in ('all','active','release')}
    classified = Counter(r['accepted_full_frame']['phase'] for r in detail
                         if r.get('same_scan') and r.get('accepted_full_frame'))
    return dict(checks=counts,exact_same_scan_new_images_by_phase=dict(classified),probes=detail)
