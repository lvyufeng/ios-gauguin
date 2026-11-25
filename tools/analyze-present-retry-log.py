#!/usr/bin/env python3
"""Validate bounded held-frame retry counters; never infer physical FPS."""
import argparse
import json
import re
from pathlib import Path

HOLD = re.compile(r'^SWEET FB HOLD: submitted=(\d+) replaced=(\d+) consumed=(\d+) retired=(\d+) canceled=(\d+) rejected=(\d+) pending=([0-4]) active=([01])$')
RETRY = re.compile(r'^SWEET FB RETRY332: requeued=(\d+) newer=(\d+) canceled=(\d+) exhausted=(\d+); max_retries=8$')
ENABLE = 'SWEET FB RETRY332: enabled max_retries=8; GPU read guards retained'


def analyze(text, *, pending_limit=2):
    if type(pending_limit) is not int or pending_limit not in (2, 4):
        raise ValueError('unknown held-frame slot layout')
    rows, errors, enabled, pending = [], [], 0, None
    for line_number, line in enumerate(text.splitlines(), 1):
        if line == ENABLE:
            enabled += 1
            continue
        hold = HOLD.fullmatch(line)
        if hold and int(hold[7]) <= pending_limit:
            if pending is not None:
                errors.append(dict(line=line_number, reason='unpaired-hold-record'))
            pending = dict(zip(('submitted', 'replaced', 'consumed', 'retired', 'canceled', 'rejected', 'pending', 'active'), map(int, hold.groups())))
            pending['hold_line'] = line_number
            continue
        retry = RETRY.fullmatch(line)
        if retry:
            if pending is None:
                errors.append(dict(line=line_number, reason='retry-without-hold'))
                continue
            row = dict(pending, **dict(zip(('requeued', 'newer', 'retry_canceled', 'exhausted'), map(int, retry.groups()))), retry_line=line_number)
            pending = None
            counts = {k:v for k,v in row.items() if not k.endswith('_line')}
            valid = all(0 <= value < 2**64 for value in counts.values())
            valid = valid and row['submitted'] + row['requeued'] == row['replaced'] + row['consumed'] + row['canceled'] + row['pending']
            valid = valid and row['consumed'] == row['retired'] + row['requeued'] + row['active']
            valid = valid and row['requeued'] <= 8 * row['submitted']
            valid = valid and 8 * row['exhausted'] <= row['requeued']
            valid = valid and row['newer'] + row['retry_canceled'] + row['exhausted'] <= row['retired']
            if not valid:
                errors.append(dict(line=line_number, reason='counter-invariant'))
            if rows and any(row[k] < rows[-1][k] for k in counts if k not in ('pending', 'active')):
                errors.append(dict(line=line_number, reason='counter-regression'))
            rows.append(row)
        elif line.startswith('SWEET FB RETRY332:'):
            errors.append(dict(line=line_number, reason='malformed-retry-record'))
        elif line.startswith('SWEET FB HOLD:') and line != 'SWEET FB HOLD: enabled pending=1 active=1; original surfaces, prompt retirement':
            errors.append(dict(line=line_number, reason='malformed-hold-record'))
    if pending is not None:
        errors.append(dict(line=pending['hold_line'], reason='trailing-unpaired-hold'))
    last = rows[-1] if rows else None
    quiescent = bool(last is not None and last['pending'] == last['active'] == 0)
    exercised = bool(last is not None and last['requeued'] > 0)
    qualified = enabled == 1 and len(rows) >= 2 and not errors
    return dict(active=qualified and quiescent and exercised, policy_qualified=qualified,
        enabled_markers=enabled, snapshots=len(rows), maximum_additional_attempts_per_frame=8,
        retry_exercised=exercised, final_snapshot_quiescent=quiescent, last=last, rows=rows, errors=errors,
        physical_fps_qualified=False,
        scope='Counter snapshots under the framebuffer lock. Requeues preserve the same held frame; newer/canceled/exhausted are terminal retry outcomes. Valid accounting does not establish panel latch, physical FPS or uninterrupted 60Hz delivery.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--pending-limit', type=int, choices=(2, 4), default=2)
    args = parser.parse_args()
    print(json.dumps(analyze(args.log.read_text(errors='replace'), pending_limit=args.pending_limit), indent=2))


if __name__ == '__main__':
    main()
