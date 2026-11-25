"""Validate sampled SwapWait snapshots against accepted swap IDs."""

from collections import Counter

from frame344_log import ISSUE, SWAP, SWAP_WAIT, WRITER, indexed, require

MAX_SAMPLES = 384
STATES = ('outside_retained_slots', 'pending', 'issued', 'ready', 'copying', 'lock_busy')


def decode(rows):
    wait = rows.get(SWAP_WAIT, ())
    require(0 < len(wait) <= MAX_SAMPLES, 'missing or unbounded SwapWait trace')
    by_id = indexed(rows[SWAP], lambda r: r.a, 'accepted client swap ID')
    require(bool(by_id), 'missing accepted swaps')
    first_generation = min(r.id for r in by_id.values())
    report = []
    for event in wait:
        require(0 < event.id < (1 << 32) and not event.id & 3 and
                0 <= event.flags < len(STATES), 'invalid SwapWait sample')
        accepted = by_id.get(event.id)
        if event.flags == 5:
            require(event.b == event.c == 0, 'lock-busy SwapWait has no snapshot')
        elif event.flags == 0:
            require(event.b == 0, 'outside-slot SwapWait has a retained generation')
        else:
            require(0 < event.b <= event.c, 'retained SwapWait generation exceeds accepts')
            if accepted is not None:
                require(accepted.id == event.b and not accepted.flags and accepted.seq < event.seq and
                        accepted.tick <= event.tick, 'retained SwapWait disagrees with exact accepted ID')
            else:
                require(event.b < first_generation, 'retained SwapWait lacks a captured accept')
        report.append(dict(requested_swap_id=event.id, timeout_scalar=event.a,
            state=STATES[event.flags], sample_tick=event.tick, snapshot_generation=event.b or None,
            latest_accepted_generation=event.c or None, sample_sequence=event.seq,
            accepted_before_sample=(accepted.seq < event.seq if accepted is not None else None)))
    return dict(total=len(wait), states=dict(Counter(row['state'] for row in report)),
        timeout_scalars=dict(Counter(row['timeout_scalar'] for row in report)), samples=report)


def join_issue(report, rows):
    bound = indexed((r for r in rows[WRITER] if r.b), lambda r: r.b>>32, 'bound swap writer')
    issued = indexed(rows[ISSUE], lambda r: r.id, 'native issue')
    coverage = Counter()
    for row in report['samples']:
        if row['state'] not in ('pending', 'issued', 'ready', 'copying'):
            continue
        writer = bound.get(row['snapshot_generation'])
        issue = issued.get(writer.id) if writer else None
        position = 'no_exact_issue'
        if issue:
            position = 'before_native_issue' if issue.seq > row['sample_sequence'] else 'after_native_issue'
            row['native_fence'] = issue.id
            row['native_issue_tick'] = issue.tick
        row['issue_position'] = position
        coverage[row['state'],position] += 1
    return {'issue_positions':{state:{position:n for (lane,position),n in coverage.items() if lane==state}
        for state in ('pending','issued','ready','copying')}, **report}
