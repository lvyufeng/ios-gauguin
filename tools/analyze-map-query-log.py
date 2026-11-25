#!/usr/bin/env python3
"""Qualify descriptor fast-path counters against the complete API prefix."""
import re


def analyze(kernel):
    lines = kernel.splitlines()
    markers = [line for line in lines if 'SWEET GPU MAP324:' in line]
    initial = 'SWEET GPU MAP324: enabled=1 service=1 ordinary-unsubmitted-owner-only'
    final = re.compile(r'SWEET GPU MAP324: calls=(\d+) fast=(\d+) waited=(\d+) failures=(\d+) valid=1; descriptor-only')
    headers = re.findall(r'^SWEET GPU API PERF: valid=(\d+) pending=(\d+) selector=[0-9a-f]+ .*$', kernel, re.M)
    api = re.findall(r'^SWEET GPU API PERF: selector=100 calls=(\d+) failures=(\d+) queue_ns=(\d+) held_ns=(\d+) max_held_ns=(\d+) wait_ns=(\d+); held excludes unlocked wait$', kernel, re.M)
    match = final.fullmatch(markers[1]) if len(markers) == 2 and markers[0] == initial else None
    counters = None
    if match and headers == [('1', '0')] and len(api) == 1:
        calls, fast, waited, failures = map(int, match.groups())
        api_calls, api_failures, queued, held, peak, wait = map(int, api[0])
        if (all(0 <= v < 1 << 64 for v in (calls, fast, waited, failures, api_calls, api_failures, queued, held, peak, wait))
                and 0 < calls == api_calls and failures == api_failures <= calls
                and fast + waited <= calls and fast <= calls - failures and peak <= held):
            counters = dict(calls=calls, fast=fast, waited=waited, failures=failures,
                            api_queue_ns=queued, api_held_ns=held,
                            api_max_held_ns=peak, api_unlocked_wait_ns=wait)
    return dict(active=counters is not None and counters['fast'] > 0,
                counters_qualified=counters is not None, counters=counters,
                marker_lines=markers,
                counter_scope='whole-service mapping descriptor queries; includes map and unmap callbacks',
                physical_fps_qualified=False)
