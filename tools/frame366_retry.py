"""Check one hardware readiness probe per scan despite one no-query lock retry."""

from collections import Counter

import frame344_log as trace
from frame357_display import BOUND
from frame358_display import LOCK_RETRY, PROBE, PROBE_LIMIT, RESULTS
from frame354_display import order


def exact_writer_tables(rows):
    return (
        trace.indexed(rows[BOUND],lambda r:r.id,'probe reservation'),
        trace.indexed((r for r in rows[trace.WRITER] if r.b),lambda r:r.b,'probe writer'),
        trace.indexed(rows[trace.ISSUE],lambda r:r.id,'probe issue'),
        trace.indexed(rows[trace.VBLANK],lambda r:r.id,'probe scan edge'),
    )


def issued_probe(row, claims, writers, issues, edges):
    gen = row.a>>32
    claim,writer,edge = claims.get(gen),writers.get(row.a),edges.get(row.id)
    issue = issues.get(writer.id) if writer else None
    trace.require(claim and writer and issue and edge and
        claim.a==row.a==writer.b and claim.b==row.b>>32==writer.c and
        order(claim)<=order(issue)<=order(writer)<=(row.c,row.seq) and
        edge.b<=row.c<=row.tick,'probe spent before exact native issue or on a different writer')
    return writer


def analyze(rows, scan_phases, qualified_copies):
    """Include only observed receipts. A rearmed lock attempt may expire."""
    early = trace.indexed(rows.get(LOCK_RETRY,()),lambda r:r.id,'lock-only retry opportunity')
    final = trace.indexed(rows[PROBE],lambda r:r.id,'final probe by scan')
    trace.require(len(early)+len(final)<=PROBE_LIMIT,'probe request budget exceeded')
    tables = exact_writer_tables(rows)
    outcomes = Counter()
    receipts = []
    for row in (*early.values(),*final.values()):
        writer = issued_probe(row,*tables)
        trace.require(row.flags in RESULTS and (row.kind!=LOCK_RETRY or
            (row.flags==1 and not row.b&0xffffffff)),'lock retry followed an actual query')
        if row.kind==LOCK_RETRY:
            continue
        first = early.get(row.id)
        if first is None:
            continue
        trace.require((first.a,first.b>>32)==(row.a,row.b>>32) and order(first)<(row.c,row.seq),
                      'retry crossed versions, frames or request order')
        image = qualified_copies.get((row.id,writer.id))
        recovered = row.flags==4 and image=='changed'
        phase = scan_phases.get(row.id,'other')
        outcomes[(phase,RESULTS[row.flags])] += 1
        receipts.append(dict(scan=row.id,phase=phase,generation=row.a>>32,native_fence=writer.id,
            first_lock_busy_tick=first.tick,second_probe_tick=row.c,result=RESULTS[row.flags],
            same_scan_certified_change=recovered))
    return dict(lock_only_rearm_count=len(early),retries_observed=len(receipts),
        reserved_rearms_without_following_probe=len(early)-len(receipts),
        actual_query_count=sum(row.flags in (3,4) for row in final.values()),
        outcomes={phase:{result:n for (p,result),n in outcomes.items() if p==phase}
                  for phase in sorted({p for p,_ in outcomes})},
        changed_in_same_scan_after_retry=sum(row['same_scan_certified_change'] for row in receipts),
        receipts=receipts)
