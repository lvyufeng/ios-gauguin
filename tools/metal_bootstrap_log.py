#!/usr/bin/env python3
"""Validate a 0298 bootstrap probe receipt and its METAL245/METAL279 lifecycle.

The eight offscreen jobs and the native first-eight handoff use the same strict
receipt checks as the legacy 0223 parser, with the current bootstrap-start
memory checkpoint. The METAL245/METAL279 records are then checked separately.

`METAL279 startup-open elapsed_ns` is the userspace bootstrap's recorded interval, not
total boot wall time. These checks do not establish full Metal, a discovered
MTLDevice, desktop correctness, physical FPS, high refresh or daily use.
"""
import re

from metal_probe_log import (
    GPU_OPEN, GPU_PROXY, GPU_SUBMIT, PHASES, _qualify_probe_receipt, need,
    records, single)

MEMORY_PHASES = ('bootstrap-start', 'compiled', 'completed')
STARTUP_BUDGET_SECONDS = 180
WORK_DEADLINE_SECONDS = 30
LIFECYCLE_245 = 'GAUGUIN METAL245'
STARTUP_279 = 'GAUGUIN METAL279'
NATIVE_245 = 'SWEET METAL245'
LIFECYCLE_245_PATTERNS = (
    ('begin', LIFECYCLE_245 + r' begin build=([0-9a-f]{24}) '
     r'startup_budget=(\d+) work_deadline=(\d+)'),
    ('armed', LIFECYCLE_245 + r' armed epoch=(\d+) jobs=(\d+) fence=(\d+) '
     r'ready=(\d+)'),
    ('result', LIFECYCLE_245 + r' RESULT PASS build=([0-9a-f]{24}) seed=(\d+) '
     r'arm=(\d+) teardown-requested=(\d+) stages=(\d+) ready=(\S+)'),
)
STARTUP_279_PATTERNS = (
    ('startup-open', STARTUP_279 + r' startup-open reason=(\d+) '
     r'attempts=(\d+) elapsed_ns=(\d+) connected=(\d+)'),
)
NATIVE_245_PATTERNS = (
    ('root armed', NATIVE_245 + r': root armed jobs=(\d+) fence=(\d+) '
     r'epoch=(\d+) ready=(\d+)'),
    ('root close', NATIVE_245 + r': root close ready=(\d+) jobs=(\d+) '
     r'fence=(\d+) epoch=(\d+) clean=(\d+)'),
)


def _lifecycle_records(text, token, patterns):
    """Classify every lifecycle-prefixed line, rejecting unknown forms."""
    compiled = [(label, re.compile(pattern)) for label, pattern in patterns]
    rows = []
    for at, line in enumerate(text.splitlines()):
        if token in line:
            matched = None
            if line.startswith(token):
                for label, pattern in compiled:
                    candidate = pattern.fullmatch(line)
                    if candidate is not None:
                        matched = (label, candidate.groups())
                        break
            need(matched is not None, 'malformed/interleaved ' + token)
            rows.append((at, matched[0], matched[1]))
    return rows


def _one_lifecycle(rows, label, name):
    return single([(at, groups) for at, current, groups in rows
                   if current == label], name)


def qualify_bootstrap_log(stdout, stderr, native, *, build, core):
    """Qualify the current 0298 bootstrap probe and owner lifecycle evidence.

    `stdout` carries the 0223 probe receipts and METAL245/METAL279 records;
    `stderr` must not carry lifecycle receipts; `native` carries the observer's
    submissions, METAL245 root lifecycle and compositor handoff. `build` is the
    expected 24-hex bootstrap build and `core` the linked 64-hex core SHA-256.

    Returns a strict receipt with the bootstrap memory profile and lifecycle
    counters; every broad qualification flag is false. Raises ValueError when any
    probe or lifecycle record is missing, duplicated, malformed, reordered or
    inconsistent with the pinned identity.
    """
    receipt, layout = _qualify_probe_receipt(
        stdout, stderr, native, build=build, core=core,
        memory_phases=MEMORY_PHASES)
    need(LIFECYCLE_245 not in stderr and STARTUP_279 not in stderr,
         'bootstrap lifecycle on unexpected stderr stream')

    lifecycle = _lifecycle_records(
        stdout, LIFECYCLE_245, LIFECYCLE_245_PATTERNS)
    startup_rows = _lifecycle_records(
        stdout, STARTUP_279, STARTUP_279_PATTERNS)
    begin = _one_lifecycle(lifecycle, 'begin', 'METAL245 begin')
    startup = _one_lifecycle(
        startup_rows, 'startup-open', 'METAL279 startup-open')
    armed = _one_lifecycle(lifecycle, 'armed', 'METAL245 armed')
    result = _one_lifecycle(lifecycle, 'result', 'METAL245 result')

    begin_build, startup_budget, work_deadline = begin[1]
    need(begin_build == build and
         int(startup_budget) == STARTUP_BUDGET_SECONDS and
         int(work_deadline) == WORK_DEADLINE_SECONDS,
         'METAL245 begin identity/budgets differ')

    reason, attempts, elapsed_ns, connected = map(int, startup[1])
    need(reason == 0 and 0 < attempts < 2**32 and connected == 1,
         'METAL279 startup result differs')
    need(0 < elapsed_ns <= STARTUP_BUDGET_SECONDS * 10**9,
         'METAL279 startup elapsed exceeds budget')

    epoch, jobs, fence, ready = map(int, armed[1])
    need((epoch, jobs, fence, ready) == (1, 8, 8, 0),
         'METAL245 armed lifecycle differs')

    result_build, result_seed, arm, teardown, stages, result_ready = result[1]
    need(result_build == build and result_seed == str(receipt['seed']) and
         int(arm) == 1 and int(teardown) == 1 and int(stages) == 8 and
         result_ready == 'kernel-close-required',
         'METAL245 result identity/lifecycle differs')

    # Probe begin, bootstrap-start memory, bootstrap begin, startup-open and
    # identity form one startup prefix. Arming follows the completed memory
    # checkpoint and precedes the final probe result.
    need(layout['begin'] < layout['memory'][0] < begin[0] < startup[0] <
         layout['identity'], 'bootstrap startup lifecycle order differs')
    need(layout['memory'][2] < armed[0] < result[0] < layout['result'],
         'bootstrap armed/result lifecycle order differs')

    native_submits = records(
        native, GPU_SUBMIT,
        GPU_SUBMIT + r'rc=(\d+) ibs=(\d+) submitted=(\d+) completed=(\d+) '
        r'shadow=(\d+) polls=(\d+)')
    need(len(native_submits) >= 8, 'eight native completions missing')
    native_lifecycle = _lifecycle_records(
        native, NATIVE_245, NATIVE_245_PATTERNS)
    native_armed = _one_lifecycle(
        native_lifecycle, 'root armed', 'native METAL245 root armed')
    native_close = _one_lifecycle(
        native_lifecycle, 'root close', 'native METAL245 root close')
    opened = records(native, GPU_OPEN, GPU_OPEN + r'pid=(\d+) root_fence=(\d+)')
    proxies = records(native, GPU_PROXY, GPU_PROXY + r'pid=(\d+)')
    need(len(opened) == 1 and len(proxies) == 1,
         'missing/duplicate compositor owner receipt')

    native_jobs, native_fence, native_epoch, native_ready = map(
        int, native_armed[1])
    need((native_jobs, native_fence, native_epoch, native_ready) == (8, 8, 1, 0),
         'native METAL245 root armed lifecycle differs')
    close_ready, close_jobs, close_fence, close_epoch, clean = map(
        int, native_close[1])
    need((close_ready, close_jobs, close_fence, close_epoch, clean) ==
         (1, 8, 8, 1, 1), 'native METAL245 root close lifecycle differs')

    open_pid, open_fence = map(int, opened[0][1])
    proxy_pid = int(proxies[0][1][0])
    need(native_submits[7][0] < native_armed[0] < native_close[0] <
         opened[0][0], 'native root/compositor lifecycle order differs')
    need(proxies[0][0] < opened[0][0] and proxy_pid == open_pid,
         'compositor opened without the same earlier launchd proxy')
    need(0 < open_pid < 2**32 and 0 < proxy_pid < 2**32 and open_fence == 8,
         'compositor root fence differs')

    return dict(
        state='qualified298-bootstrap-offscreen-readback-and-native-owner-handoff',
        build=build, core=core, seed=receipt['seed'],
        memory_profile=MEMORY_PHASES[0], phases=list(PHASES),
        output_words=receipt['output_words'], completed_root_fences=8,
        compositor_opens=len(opened), hashes=receipt['hashes'],
        startup=dict(reason=reason, attempts=attempts, elapsed_ns=elapsed_ns,
                     budget_ns=STARTUP_BUDGET_SECONDS * 10**9, connected=connected,
                     clock='userspace-bootstrap-recorded-interval-not-total-boot-wall-time'),
        arming=dict(epoch=epoch, jobs=jobs, fence=fence, ready=ready),
        native_root=dict(armed=True, close_clean=True),
        MTLDevice_qualified=False, desktop_qualified=False,
        FPS_qualified=False, high_refresh_qualified=False,
        daily_use_qualified=False)
