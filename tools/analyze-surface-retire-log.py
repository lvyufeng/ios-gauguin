#!/usr/bin/env python3
"""Read bounded SURF334 lifecycle diagnostics; never infer panel FPS."""
import argparse
import json
import re
from pathlib import Path

PREFIX = 'GAUGUIN SURF334:'
ENABLED = PREFIX + ' enabled close-before-reimport=1'
LIMIT = PREFIX + ' limit=64 coverage=incomplete'
RECORD = re.compile(r'GAUGUIN SURF334: (wait|retired) seq=([0-9]+) handle=([0-9]+) surface=([0-9]+)')


def analyze(text, prefix_preserved=True):
    rows, issues = [], []
    enabled = limit = 0
    waiting, retired = {}, set()
    for line in text.splitlines():
        if not line.startswith(PREFIX):
            continue
        if len(line.encode()) + 1 > 128:
            raise ValueError('SURF334 record exceeds producer byte bound')
        if line == ENABLED:
            enabled += 1
            if rows or limit:
                issues.append('activation-after-events')
            continue
        if line == LIMIT:
            limit += 1
            if len(waiting) != 64:
                issues.append('limit-before-64-waits')
            continue
        match = RECORD.fullmatch(line)
        if match is None:
            raise ValueError('malformed SURF334 diagnostic')
        phase, seq, handle, surface = match.groups()
        seq, handle, surface = int(seq), int(handle), int(surface)
        if not 1 <= seq <= 64 or not 0 < handle <= 0xffffffff or not 0 <= surface <= 0xffffffff:
            raise ValueError('SURF334 field outside producer range')
        if enabled != 1:
            issues.append('event-without-unique-activation')
        if phase == 'wait':
            if seq in waiting or seq != len(waiting) + 1 or limit:
                issues.append('duplicate-or-unordered-wait')
            waiting[seq] = (handle, surface)
        else:
            if seq in retired or waiting.get(seq) != (handle, surface):
                issues.append('unmatched-or-duplicate-retirement')
            retired.add(seq)
        rows.append(dict(phase=phase, seq=seq, handle=handle, surface=surface))
        if len(rows) > 128:
            raise ValueError('SURF334 diagnostic record capacity exceeded')
    incomplete = sorted(set(waiting) - retired)
    if enabled != 1:
        issues.append('missing-or-duplicate-activation')
    if limit > 1:
        issues.append('duplicate-limit')
    if incomplete:
        issues.append('incomplete-retirement-pairs')
    qualified = prefix_preserved and not issues and limit == 0
    return dict(state='SURF334-lifecycle-diagnostics', active=prefix_preserved and enabled == 1,
                coverage_qualified=qualified, prefix_preserved=prefix_preserved,
                wait_pairs=len(waiting), completed_pairs=len(set(waiting) & retired),
                retire_path_observed=bool(waiting), incomplete_pairs=incomplete,
                capacity_limited=bool(limit), activation_count=enabled,
                issues=sorted(set(issues)), rows=rows,
                kernel_handle774_cause_proven=False, physical_FPS_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.log.read_text(errors='replace'))
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
