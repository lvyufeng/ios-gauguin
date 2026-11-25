"""Decode accepted swap timing without assigning a producer by proximity."""

from collections import Counter

from frame344_log import ISSUE, READY, SWAP, SWAP_TIMING, WRITER, indexed, quantile, require
from frame357_display import BOUND

MAX_SAMPLES = 1024
WORD = (1 << 32) - 1
MAX_VERSION = WORD & ~3


def decode(rows, numer, denom, *, begin_threads=False):
    receipts = indexed(rows.get(SWAP_TIMING,()),lambda row:row.id,'swap timing generation')
    require(0<len(receipts)<=MAX_SAMPLES and numer>0 and denom>0,'missing or unbounded swap timing')
    accepted = indexed(rows[SWAP],lambda row:row.id,'accepted swap generation')
    exact_claims = indexed((row for row in rows.get(BOUND,()) if row.flags==2),
                           lambda row:row.id,'exact in-render producer')
    exact_writers = indexed((row for row in rows.get(WRITER,()) if row.b>>32 in exact_claims),
                            lambda row:row.b>>32,'exact in-render writer')
    issues = indexed(rows.get(ISSUE,()),lambda row:row.id,'native issue')
    result = []
    for g,row in receipts.items():
        swap = accepted.get(g)
        require(swap is not None and not swap.flags and swap.c and swap.c==row.c and
                swap.tick<=row.tick and swap.seq<row.seq and row.flags in (0,1) and
                (begin_threads or row.b<=WORD),
                'timing lacks its exact accepted swap')
        observed = row.b & MAX_VERSION
        predicted = min(observed+4,MAX_VERSION)
        wanted,surface = divmod(swap.c, 1 << 32)
        if claim := exact_claims.get(g):
            ticket = g<<32|surface
            writer = exact_writers.get(g)
            issue = issues.get(writer.id) if writer else None
            require(not row.flags and row.b&3==1 and wanted==observed>0 and claim.c and
                    (claim.a,claim.b)==(ticket,wanted) and writer and issue and
                    (writer.a,writer.b,writer.c)==(surface,ticket,wanted) and
                    swap.seq<claim.seq<issue.seq<writer.seq and
                    swap.tick<=claim.tick<=issue.tick<=writer.tick,
                    'busy swap timing lacks the exact observed version and ordered native writer')
        else:
            require((wanted==predicted and row.flags==0) or
                    (row.flags==1 and predicted<=wanted<=MAX_VERSION and wanted%4==0),
                    'swap timing contradicts the compiled version policy')
        require(not row.a or row.a<=swap.tick,'matched SwapBegin occurs after acceptance')
        result.append(dict(generation=g,client_swap_id=swap.a,surface=surface,
            accepted_tick=swap.tick,begin_tick=row.a or None,
            observed_source_version=observed,observed_source_status=row.b&3,
            selected_source_version=wanted,advanced_past_pending=bool(row.flags),
            begin_to_accept_ns=((swap.tick-row.a)*numer//denom if row.a else None)))
        if begin_threads:
            thread = row.b >> 32
            require(bool(thread)==bool(row.a),'matched SwapBegin thread or timestamp missing')
            result[-1]['begin_thread'] = thread or None
    return result


def observe(rows, numer, denom, deadline_audit, *, begin_threads=False):
    timing = decode(rows,numer,denom,begin_threads=begin_threads)
    eligible = sorted((row for row in rows[SWAP] if not row.flags and row.c),key=lambda r:r.seq)
    observed = {r['generation'] for r in timing}
    expected = {r.id for r in eligible[:MAX_SAMPLES]}
    require(observed == expected, 'swap timing does not cover the exact eligible prefix')
    writers = indexed(rows[WRITER],lambda row:(row.a,row.c),'surface version writer')
    claimed = indexed((r for r in rows[WRITER] if r.b),lambda row:row.b>>32,'claimed swap writer')
    issued = indexed(rows[ISSUE],lambda row:row.id,'issued swap writer')
    ready = indexed(rows[READY],lambda row:row.id,'visible swap writer')
    by_generation = {r['generation']:r for r in timing}
    for row in timing:
        surface = row['surface']
        version = row['selected_source_version']
        observed_writer = writers.get((surface,row['observed_source_version']))
        exact = claimed.get(row['generation'])
        if exact:
            require(exact == writers.get((surface,version)), 'accepted swap writer version differs')
        row['claimed_native_fence'] = exact.id if exact else None
        if observed_writer:
            issue,visible = issued.get(observed_writer.id),ready.get(observed_writer.id)
            row['observed_version_writer'] = dict(native_fence=observed_writer.id,
                claimed_generation=observed_writer.b>>32 or None,writer_tick=observed_writer.tick,
                issue_tick=issue.tick if issue else None,visible_tick=visible.tick if visible else None)
    no_swap = []
    for deadline in deadline_audit['details']:
        upcoming = deadline['next_swap']
        if not upcoming or not deadline['next_swap_within_stroke_tail']:
            continue
        trace = by_generation.get(upcoming['generation'])
        if not trace or not trace['begin_tick']:
            position = 'begin_unobserved'
        else:
            tick_ns = trace['begin_tick']*numer//denom
            position = 'begin_before_cutoff' if tick_ns<=deadline['deadline_ns'] else 'begin_after_cutoff'
        no_swap.append(dict(stroke=deadline['stroke'],scan=deadline['scan'],position=position,
            cutoff_ns=deadline['deadline_ns'],next_swap_generation=upcoming['generation']))
    early = [r for r in timing if not r['claimed_native_fence'] and r.get('observed_version_writer') and
        not r['observed_version_writer']['claimed_generation']]
    spans = [r['begin_to_accept_ns'] for r in timing if r['begin_to_accept_ns'] is not None]
    return dict(state='same-client-swap-timing-and-observed-version',records=len(timing),
        eligible=len(eligible),exact_begin=len(spans),begin_to_accept_p50_ns=quantile(spans,.5),
        begin_to_accept_p95_ns=quantile(spans,.95),advanced_past_pending=sum(r['advanced_past_pending'] for r in timing),
        accepted_without_claim=sum(not r['claimed_native_fence'] for r in timing),
        unclaimed_observed_writer=len(early),no_swap_cutoff_position=dict(Counter(r['position'] for r in no_swap)),
        no_swap_cutoff_position_warm=dict(Counter(r['position'] for r in no_swap if r['stroke']>=3)),
        no_swap_detail=no_swap,swap_timing=timing,
        interpretation='Earlier writer identity demonstrates the exact stored surface version. '
            'The intended CA transaction remains unobserved.')
