"""Align boot-local output signatures with framebuffer attempts and readiness."""

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
import re

import frame344_log as trace

PRESENT = 52
OPEN_LINE = 2480
COPY_NS = 6_000_000
MIN_LINE_NS = 3_000


def correspond_attempts(rows, frame, *, copy_budget_ns=COPY_NS, allow_paired_copy=False):
    """Keep the exact swap/fence joins from the qualified software analysis."""
    locks = rows[trace.LOCK]
    stamps = [row.tick for row in locks]
    ready = trace.indexed(rows[trace.READY],lambda row:row.id,'surface readiness')
    complete = trace.indexed(rows[trace.EOP],lambda row:row.id,'GPU completion')
    writers = defaultdict(list)
    for row in rows[trace.WRITER]:
        writers[row.a].append(row)
    writer_ticks = {s:[row.tick for row in lane] for s,lane in writers.items()}
    raw_copies = rows[trace.COPY]
    proof_rows = rows[PRESENT]
    for a in frame['attempts']:
        begin,end = a['attempt_tick'],a['result_tick']
        interval = locks[bisect_left(stamps,begin):bisect_right(stamps,end)]
        reasons = []
        for lock in interval:
            matched = bisect_right(writer_ticks.get(lock.id,[]),lock.b)-1
            w = writers[lock.id][matched] if matched>=0 else None
            fence = w.id if w else None
            eop = complete.get(fence)
            available = ready.get(fence)
            guard = dict(surface=lock.id,queued_tick=lock.a,locked_tick=lock.b,
                resolved_tick=lock.c,accepted=lock.flags in trace.LOCK_ACCEPTED,fence=fence,
                gpu_complete_tick=eop.tick if eop else None,surface_ready_tick=available.tick if available else None)
            if lock.flags==trace.LOCK_SURFACE_RESERVATION:
                trace.require(w and eop and available and w.tick<=eop.tick<=available.tick<=lock.b,
                              'surface reservation precedes its producer or cache visibility')
                guard['surface_reservation'] = True
            reasons.append(guard)
        proofs = []
        for pos in proof_rows:
            if not begin<=pos.tick<=end:
                continue
            finish,end_line = pos.c>>32,pos.c&0xffffffff
            copies=[row for row in raw_copies if begin<=row.tick<=pos.tick and row.id==pos.a]
            paired = allow_paired_copy and bool(pos.flags & 4)
            disposition = pos.flags & ~4 if allow_paired_copy else pos.flags
            trace.require(disposition in (0,1,2) and ((disposition==0)==(not copies)) and
                          (not paired or len(copies)==1 and copies[0].c==trace.FRAME_BYTES),
                          'blanking proof disagrees with copy records')
            if disposition==1:
                trace.require(OPEN_LINE<=pos.b<=end_line<finish<=4910 and
                              (finish-pos.b)*MIN_LINE_NS>=copy_budget_ns, 'blanking copy endpoints invalid')
            proof = dict(frame=pos.id,surface=pos.a,disposition={0:'deferred',1:'verified-blank',2:'end-unverified'}[disposition],
                         begin_line=pos.b,finish_line=end_line if disposition else None,
                         end_guard_line=finish if disposition else pos.c)
            if allow_paired_copy:
                proof['paired_copy'] = paired
            proofs.append(proof)
        yield dict(a,read_guards=reasons,blanking_proofs=proofs)


def analyze(text, frame, *, copy_budget_ns=COPY_NS, allow_paired_copy=False, extra_kinds=()):
    rows,_,_,_ = trace.parse(text,extra_kinds=(PRESENT,*extra_kinds))
    hardware = frame['hardware']
    pairs = trace.indexed(frame['raw_crc_pairs'],lambda row:row['frame'],'paired CRC')
    lag = frame['crc_frame_calibration']['lag_frames']
    enabled = bool(frame['misr']['qualified'] and frame['crc_frame_calibration']['qualified'])
    attempts = list(correspond_attempts(rows,frame,copy_budget_ns=copy_budget_ns,allow_paired_copy=allow_paired_copy))
    ticks = [a['attempt_tick'] for a in attempts]
    accepted_swaps = [row for row in rows[trace.SWAP] if row.flags==0]
    swap_ticks = [row.tick for row in accepted_swaps]
    copy_owners = {(layer['surface'],layer['copy_start_tick'],layer['copy_end_tick']):a['attempt']
                   for a in attempts for layer in a['layers']}
    windows = []
    for window in hardware['windows']:
        edges={e['frame']:e for e in window['vblank_edges']}
        intervals = []
        counts = Counter()
        for out in window['outputs']:
            left,right = (edges[out[k]] for k in ('previous_frame','frame'))
            begin,end = left['edge_upper_tick'],right['edge_upper_tick']
            used = attempts[bisect_right(ticks,begin):bisect_right(ticks,end)]
            relation = 'unknown'
            before = after = None
            if enabled and out['step']==1:
                before,after=(pairs.get((q['frame']+lag)&0xffffffff) for q in (left,right))
                if before and after and before['agrees'] and after['agrees']:
                    relation = 'changed' if before['signatures'][0]!=after['signatures'][0] else 'repeated'
            counts[relation]+=out['step']
            if relation=='repeated':
                if not used:
                    counts['repeat_without_present_attempt']+=1
                    if bisect_right(swap_ticks,begin)!=bisect_right(swap_ticks,end):
                        counts['repeat_without_attempt_but_new_swap']+=1
                elif any(a['layers'] for a in used):
                    counts['repeat_with_copy_by_attempt_time']+=1
                elif any(a['refused_guards'] for a in used):
                    counts['repeat_with_refused_read_guard']+=1
                else:
                    counts['repeat_with_other_attempt_outcome']+=1
            crc = None
            related = []
            if before and after:
                crc = [before['signatures'][0],after['signatures'][0]]
                previous_sample,current_sample=before['ticks'][0][1],after['ticks'][0][1]
                related = [dict(surface=ev.id,begin_tick=ev.a,end_tick=ev.b,
                                attempt=copy_owners.get((ev.id,ev.a,ev.b)))
                           for ev in rows[trace.COPY] if ev.a<current_sample and previous_sample<ev.b]
            intervals.append(dict(previous_frame=left['frame'],frame=right['frame'],crc_relation=relation,
                                  signatures=crc,edge_ticks=[[left['edge_lower_tick'],begin],[right['edge_lower_tick'],end]],
                                  full_frame=out['classification'],copy_overlap=out.get('reason')=='possible-mid-scan-copy',
                                  present_attempts=[a['attempt'] for a in used],copies_between_samples=related))
        windows.append(dict(stroke=window['stroke']+1,phase=window['window'],counts=dict(counts),
                            elapsed_ns_low=window['elapsed_ns_low'],elapsed_ns_high=window['elapsed_ns_high'],
                            intervals=intervals))
    summary={}
    for phase in ('active','release'):
        selected=[w for w in windows if w['phase']==phase]
        counts=Counter()
        for w in selected: counts.update(w['counts'])
        lower,upper=(sum(w[f'elapsed_ns_{name}'] for w in selected) for name in ('low','high'))
        same_ranges_complete=bool(enabled and len(selected)==13 and all(w['elapsed_ns_low']>0 for w in selected))
        reference=hardware if phase=='active' else hardware['release_cadence']
        summary[phase]=dict(signature_counts=dict(counts),
            output_updates_per_second=([counts['changed']*1e9/upper,
                 (counts['changed']+counts['unknown'])*1e9/lower] if same_ranges_complete else None),
            full_frame_counts={key:reference[key] for key in ('changed','repeated','unknown')})
    opening=re.findall(r'^SWEET F351 WINDOW: available=([01]) frame=(\d+) end=(\d+)$',text,re.M)
    trace.require(len(opening)<=2,'too many opening receipts')
    proof=Counter(p['disposition'] for a in attempts for p in a['blanking_proofs'])
    return dict(phases=summary,windows=windows,attempts=attempts,mode_receipts=opening,
                measured_attempt_proofs=dict(proof),
                pair_scope='Hardware edges bound attempt attribution. A matching signature means the output hash repeated. Stable whole-frame counts retain the frozen possible-overlap guard.')
