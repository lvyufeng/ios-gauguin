#!/usr/bin/env python3
"""Characterize a pinned historical runtime, not a performance acceptance test.

Changed guard counts may be intentional in an optimized candidate; compare its
behavior and fault handling separately instead of treating these counts as a
requirement for future implementations.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / '.deps-cache/p0-20261105/source204-codex'
SOURCE = Path(os.environ.get('XNU_SOURCE', DEFAULT_SOURCE)).expanduser().resolve()
DEV = SOURCE / 'bsd/dev'
RUNTIME_C = DEV / 'gauguin_gpu_runtime.c'
RUNTIME_H = DEV / 'gauguin_gpu_runtime.h'
FIXTURE = ROOT / 'tests/fixtures/gpu-user/submit_guard_counts_host.c'
BASELINE_C_SHA256 = 'cd9c4a91c4d400f821c659470a2ca9054fc510535f87db4a84e8a430a5ab6adb'
BASELINE_H_SHA256 = '9c8499b6f2a16d542a70299eac9d0fb7a2d6e66f261621f2857cb48e92a4e597'

BASE_NS = 1700000000000000000
WINDOW_NS = 2000000000
FENCE_SENTINEL = 0xdeadbeef

PHASES = [
    'initial_idle_validation',
    'ring_writes_readback',
    'fence_off',
    'completion_polling',
    'complete',
]
SCENARIOS = [
    'valid_ib_immediate',
    'pending_completion_1',
    'pending_completion_3',
    'delayed_fence',
]
CONFIGS = ['production_ring_span', 'legacy_fallback']
CONFIG_PREFIX = {'production_ring_span': 'production', 'legacy_fallback': 'legacy'}
SCOPE = ('host-only callback counts against a register/RAM model; no GPU or IB '
         'execution, no device operation, no hardware timing, and no frame rate '
         'or FPS measurement')
DISCLAIMERS = [
    'fake ring_span',
    'models only GGR_BUSY state, operation_end_ns, and',
    'not the production ggrb_ring_span board callback',
    'does not perform the full ggrb_live checks',
    'board-state (GMB_READY) and global ggrb_end deadline predicates',
]
EVENTS = {
    'healthy', 'read_reg', 'write_reg', 'read_memory', 'write_ring',
    'ring_span', 'barrier', 'delay_us', 'quarantine', 'success', 'clock_jump',
}

# total, phase counts, completion polls, fence-off guard writes, ring words,
# ring-span calls, legacy write/read calls, and final clock offset per scenario.
EXPECTED = {
    ('production_ring_span', 'valid_ib_immediate'):
        (40, [12, 10, 5, 0, 13], 1, 3, 24, 2, 0, 0, 0),
    ('production_ring_span', 'pending_completion_1'):
        (54, [12, 10, 5, 14, 13], 2, 3, 24, 2, 0, 0, 10000),
    ('production_ring_span', 'pending_completion_3'):
        (82, [12, 10, 5, 42, 13], 4, 3, 24, 2, 0, 0, 30000),
    ('production_ring_span', 'delayed_fence'):
        (56, [12, 10, 21, 0, 13], 1, 5, 24, 2, 0, 0, 20000),
    ('legacy_fallback', 'valid_ib_immediate'):
        (84, [12, 54, 5, 0, 13], 1, 15, 0, 0, 12, 12, 0),
    ('legacy_fallback', 'pending_completion_1'):
        (98, [12, 54, 5, 14, 13], 2, 15, 0, 0, 12, 12, 10000),
    ('legacy_fallback', 'pending_completion_3'):
        (126, [12, 54, 5, 42, 13], 4, 15, 0, 0, 12, 12, 30000),
    ('legacy_fallback', 'delayed_fence'):
        (100, [12, 54, 21, 0, 13], 1, 17, 0, 0, 12, 12, 20000),
}
PENDING = [0, 1, 3, 0]
BUSY = [0, 0, 0, 2]
EDGE_IDS = [
    'nonzero_clock_open_idle',
    'deadline_exact_production_initial_idle_validation',
    'deadline_exact_production_ring_writes_readback',
    'deadline_exact_production_fence_off',
    'deadline_exact_production_complete',
    'deadline_exact_legacy_initial_idle_validation',
    'deadline_exact_legacy_ring_writes_readback',
    'deadline_exact_legacy_fence_off',
    'deadline_exact_legacy_complete',
    'deadline_minus_one_production_initial_idle_validation',
    'deadline_minus_one_production_ring_writes_readback',
    'deadline_minus_one_production_fence_off',
    'deadline_minus_one_production_complete',
    'deadline_minus_one_legacy_initial_idle_validation',
    'deadline_minus_one_legacy_ring_writes_readback',
    'deadline_minus_one_legacy_fence_off',
    'deadline_minus_one_legacy_complete',
    'deadline_overflow_open',
    'deadline_overflow_submit',
    'deadline_max_boundary_open_idle',
    'deadline_max_boundary_plus_one',
]
EDGE_RESULT = re.compile(
    r'^EDGE (\S+) expected=(\S+) rc=(\S+) phase=(\S+) fence=(\d+) '
    r'quarantines=(\d+) clock=(\d+) deadline=(\d+) detail=(.+)$',
    re.MULTILINE)
U64_MAX = (1 << 64) - 1


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_edges(stderr):
    edges = EDGE_RESULT.findall(stderr)
    check(len(edges) == 21,
          f'expected 21 deadline EDGE lines, found {len(edges)}\n{stderr}')
    ids = [edge[0] for edge in edges]
    check(ids == EDGE_IDS, f'unexpected deadline edge order: {ids}')
    for edge in edges:
        name, expected, rc, _phase, fence, quarantines, clock, deadline, detail = edge
        fence, quarantines, clock, deadline = map(
            int, (fence, quarantines, clock, deadline))
        check(detail.strip(), f'{name}: empty deadline detail')
        if name == 'nonzero_clock_open_idle':
            check((expected, rc) == ('success', 'GGR_OK'),
                  f'{name}: unexpected result {expected}/{rc}')
            check((fence, quarantines) == (0, 0),
                  f'{name}: unexpected fence/quarantine state')
            check((clock, deadline) == (BASE_NS, BASE_NS + WINDOW_NS),
                  f'{name}: nonzero-clock window changed: {clock}/{deadline}')
        elif name == 'deadline_overflow_open':
            check((expected, rc) != ('success', 'GGR_OK'),
                  f'{name}: overflow was accepted')
            check((fence, quarantines) == (FENCE_SENTINEL, 1),
                  f'{name}: overflow did not quarantine once')
            check((clock, deadline) == (U64_MAX - 1000000000, 0),
                  f'{name}: unexpected overflow clocks: {clock}/{deadline}')
        elif name == 'deadline_overflow_submit':
            check((expected, rc) != ('success', 'GGR_OK'),
                  f'{name}: overflow was accepted')
            check((fence, quarantines) == (FENCE_SENTINEL, 1),
                  f'{name}: overflow did not quarantine once')
            check((clock, deadline) == (U64_MAX - 1000000000,
                                        BASE_NS + WINDOW_NS),
                  f'{name}: unexpected overflow clocks: {clock}/{deadline}')
        elif name == 'deadline_max_boundary_open_idle':
            check((expected, rc) == ('success', 'GGR_OK'),
                  f'{name}: safe arithmetic boundary was rejected')
            check((fence, quarantines) == (0, 0),
                  f'{name}: boundary success changed fence/quarantine state')
            check((clock, deadline) == (U64_MAX - WINDOW_NS, U64_MAX),
                  f'{name}: boundary clocks changed: {clock}/{deadline}')
        elif name == 'deadline_max_boundary_plus_one':
            check((expected, rc) != ('success', 'GGR_OK'),
                  f'{name}: past-boundary clock was accepted')
            check((fence, quarantines) == (FENCE_SENTINEL, 1),
                  f'{name}: past-boundary clock did not quarantine once')
            check((clock, deadline) == (U64_MAX - WINDOW_NS + 1, 0),
                  f'{name}: unexpected past-boundary clocks: {clock}/{deadline}')
        elif name.startswith('deadline_exact_'):
            check((expected, rc) != ('success', 'GGR_OK'),
                  f'{name}: exact deadline was accepted')
            check((fence, quarantines) == (FENCE_SENTINEL, 1),
                  f'{name}: exact deadline did not quarantine once')
            check(clock == deadline,
                  f'{name}: clock {clock} did not reach deadline {deadline}')
        elif name.startswith('deadline_minus_one_'):
            check((expected, rc) == ('success', 'GGR_OK'),
                  f'{name}: deadline - 1 was rejected')
            check((fence, quarantines) == (1, 0),
                  f'{name}: deadline - 1 success state changed')
            check(clock + 1 == deadline,
                  f'{name}: clock {clock} is not deadline - 1 of {deadline}')
        else:
            raise AssertionError(f'unexpected deadline edge {name}')


def validate_trace(temp, scenario, expected):
    total, phases = expected[0], expected[1]
    name = scenario['trace']
    check(name == f"traces/{scenario['id']}.jsonl",
          f"{scenario['id']}: unexpected trace path {name!r}")
    check(not Path(name).is_absolute(),
          f"{scenario['id']}: trace path is absolute")
    path = temp / name
    check(path.is_file(), f"{scenario['id']}: missing trace {path}")
    try:
        events = [json.loads(line) for line in path.read_text().splitlines() if line]
    except json.JSONDecodeError as error:
        raise AssertionError(f"{scenario['id']}: invalid trace JSON: {error}") from error
    check(len(events) == scenario['events_total'],
          f"{scenario['id']}: trace length {len(events)} != "
          f"{scenario['events_total']}")
    check([event.get('seq') for event in events] == list(range(1, len(events) + 1)),
          f"{scenario['id']}: trace sequence is not contiguous")
    phase_counts = {phase: 0 for phase in PHASES}
    successes = 0
    for event in events:
        kind = event.get('event')
        check(kind in EVENTS, f"{scenario['id']}: unknown trace event {kind!r}")
        check(not any(word in str(kind).lower() for word in ('gpu', 'device', 'fps')),
              f"{scenario['id']}: trace claims {kind!r}")
        check(event.get('phase') in PHASES,
              f"{scenario['id']}: unknown trace phase {event.get('phase')!r}")
        if kind == 'healthy':
            phase_counts[event['phase']] += 1
        elif kind == 'quarantine':
            raise AssertionError(f"{scenario['id']}: success trace contains quarantine")
        elif kind == 'success':
            successes += 1
            check(event.get('fence') == 1,
                  f"{scenario['id']}: success event fence is not 1")
    check([phase_counts[phase] for phase in PHASES] == phases,
          f"{scenario['id']}: trace phase counts {phase_counts} != {phases}")
    check(sum(phase_counts.values()) == total,
          f"{scenario['id']}: trace healthy total != {total}")
    check(successes == 1, f"{scenario['id']}: trace has {successes} success events")
    check(events[-1]['event'] == 'success',
          f"{scenario['id']}: trace does not end at success")


def validate(raw, temp, stderr):
    check(isinstance(raw, dict), 'probe report is not a JSON object')
    check(raw.get('schema') == 'ggr-submit-healthy-counts/v1',
          f"unexpected report schema {raw.get('schema')!r}")
    check(raw.get('scope') == SCOPE, f'unexpected report scope {raw.get("scope")!r}')
    check(raw.get('base_clock_ns') == BASE_NS,
          f"unexpected base clock {raw.get('base_clock_ns')}")
    check(raw.get('phases') == PHASES, 'report phase list changed')
    check(raw.get('configs') == [
        {'id': 'production_ring_span', 'ring_span': True},
        {'id': 'legacy_fallback', 'ring_span': False},
    ], 'report config list changed')
    check(raw.get('startup') == {
        'ggr_open_healthy_per_run': 12,
        'ggr_check_idle_healthy_per_run': 12,
    }, f"unexpected startup counts {raw.get('startup')}")

    scenarios = raw.get('scenarios')
    check(isinstance(scenarios, list) and len(scenarios) == 8,
          f"expected 8 scenario runs, found {scenarios!r}")
    expected_ids = [f'{CONFIG_PREFIX[config]}_{scenario}' for config in CONFIGS
                    for scenario in SCENARIOS]
    check([scenario.get('id') for scenario in scenarios] == expected_ids,
          f"scenario matrix order changed: {[s.get('id') for s in scenarios]}")
    totals = {config: [] for config in CONFIGS}
    for scenario in scenarios:
        config, name = scenario['config'], scenario['scenario']
        key = (config, name)
        check(key in EXPECTED, f'unexpected scenario {key}')
        total, phases, polls, writes, ring_words, span_calls, legacy_writes, \
            legacy_reads, final_delta = EXPECTED[key]
        totals[config].append(scenario['healthy_total'])
        check(scenario['id'] == f'{CONFIG_PREFIX[config]}_{name}',
              f'{key}: inconsistent scenario id')
        check(scenario['ring_span'] is (config == 'production_ring_span'),
              f'{key}: wrong ring_span flag')
        check(scenario['pending_completion_polls'] == PENDING[SCENARIOS.index(name)],
              f'{key}: wrong pending completion count')
        check(scenario['fence_status_busy_polls'] == BUSY[SCENARIOS.index(name)],
              f'{key}: wrong fence-busy count')
        check('frame rate' not in scenario['description'].lower()
              and 'fps' not in scenario['description'].lower(),
              f'{key}: description claims frame performance')
        check(scenario['healthy_total'] == total,
              f'{key}: total {scenario["healthy_total"]} != {total}')
        check([scenario['healthy_by_phase'][phase] for phase in PHASES] == phases,
              f'{key}: phase counts changed')
        result = scenario['result']
        check(result['rc'] == 'GGR_OK', f'{key}: rc is {result["rc"]}')
        check(result['fence'] == 1, f'{key}: success fence is not 1')
        check(result['state'] == 'GGR_READY', f'{key}: state is not GGR_READY')
        check(result['quarantines'] == 0, f'{key}: success run quarantined')
        check(result['polls'] == polls, f'{key}: polls {result["polls"]} != {polls}')
        check(result['writes'] == writes, f'{key}: writes {result["writes"]} != {writes}')
        check(result['ring_words'] == ring_words,
              f'{key}: ring words {result["ring_words"]} != {ring_words}')
        check(result['ring_span_calls'] == span_calls,
              f'{key}: ring span calls changed')
        check(result['legacy_write_ring_calls'] == legacy_writes,
              f'{key}: legacy write calls changed')
        check(result['legacy_read_ring_calls'] == legacy_reads,
              f'{key}: legacy read calls changed')
        check(result['start_clock_ns'] == BASE_NS,
              f'{key}: start clock changed')
        check(result['final_clock_ns'] == BASE_NS + final_delta,
              f'{key}: final clock {result["final_clock_ns"]} != '
              f'{BASE_NS + final_delta}')
        check(result['final_clock_ns'] < result['operation_end_ns'],
              f'{key}: success clock reached the deadline')
        check(result['operation_end_ns'] == BASE_NS + WINDOW_NS,
              f'{key}: operation deadline changed')
        validate_trace(temp, scenario, EXPECTED[key])
    check(totals['production_ring_span'] == [40, 54, 82, 56],
          f'production totals changed: {totals["production_ring_span"]}')
    check(totals['legacy_fallback'] == [84, 98, 126, 100],
          f'legacy totals changed: {totals["legacy_fallback"]}')

    injection = raw.get('injection')
    check(isinstance(injection, dict), 'report has no injection block')
    check(injection.get('cases') == 832,
          f"expected 832 injected cases, found {injection.get('cases')}")
    check(injection.get('all_passed') is True, 'injection block did not pass')
    by_site = {
        'ggr_open/initial_idle_validation': 96,
        'ggr_check_idle/initial_idle_validation': 96,
        'ggr_submit/initial_idle_validation': 96,
        'ggr_submit/ring_writes_readback': 256,
        'ggr_submit/fence_off': 72,
        'ggr_submit/completion_polling': 112,
        'ggr_submit/complete': 104,
    }
    check(injection.get('by_site_phase') == by_site,
          f'unexpected injection site counts {injection.get("by_site_phase")}')
    check(sum(by_site.values()) == 832, 'injection site counts do not sum to 832')
    check(len(injection.get('assertions_per_case', [])) == 8,
          'injection assertion contract changed')
    per_run = injection.get('per_run')
    check(isinstance(per_run, list) and len(per_run) == 8,
          'injection per_run matrix is incomplete')
    rows = {row['scenario']: row for row in per_run}
    check(len(rows) == 8, 'injection per_run has duplicate scenarios')
    for config in CONFIGS:
        for name in SCENARIOS:
            key = (config, name)
            row = rows.get(f'{CONFIG_PREFIX[config]}_{name}')
            check(row is not None, f'injection row missing for {key}')
            boundaries = EXPECTED[key][0] + 24
            check(row['config'] == config, f'{key}: injection config changed')
            check(row['boundaries'] == boundaries,
                  f'{key}: injection boundaries {row["boundaries"]} != {boundaries}')
            check(row['submit_boundaries'] == EXPECTED[key][0],
                  f'{key}: submit boundary count changed')
            check(row['passed'] == row['boundaries'],
                  f'{key}: injection cases failed')

    deadline = raw.get('deadline_checks')
    check(isinstance(deadline, dict), 'report has no deadline block')
    check(deadline.get('passed') == 21,
          f"expected 21 deadline checks, found {deadline.get('passed')}")
    for flag in ('base_clock_nonzero', 'exact_deadline_fails_closed',
                 'deadline_minus_one_passes',
                 'overflow_rejected_before_ring_write',
                 'max_arithmetic_boundary_accepted'):
        check(deadline.get(flag) is True, f'deadline check {flag} did not pass')
    check(raw.get('assertions', 0) >= 150000,
          f"unexpectedly low assertion count {raw.get('assertions')}")
    check('/Users/' not in json.dumps(raw)
          and '/private/' not in json.dumps(raw)
          and '/tmp/' not in json.dumps(raw),
          'report contains an absolute machine-specific path')
    validate_edges(stderr)


def main():
    missing = [path for path in (RUNTIME_C, RUNTIME_H, FIXTURE) if not path.is_file()]
    check(not missing,
          'missing required inputs: ' + ', '.join(str(path) for path in missing)
          + '; set XNU_SOURCE to a complete XNU root')
    fixture_text = FIXTURE.read_text()
    for phrase in DISCLAIMERS:
        check(phrase in fixture_text,
              f'fixture does not state host-model limit: {phrase!r}')
    check('fps' not in fixture_text.lower().replace('or fps measurement', ''),
          'fixture claims FPS measurement')

    pins = {path: sha256(path) for path in (RUNTIME_C, RUNTIME_H, FIXTURE)}
    check(pins[RUNTIME_C] == BASELINE_C_SHA256 and pins[RUNTIME_H] == BASELINE_H_SHA256,
          'this characterization requires the pinned 0297 runtime; '
          'a changed candidate needs its own behavioral comparison')
    env = dict(os.environ,
               ASAN_OPTIONS='halt_on_error=1:detect_leaks=0:abort_on_error=1',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    with tempfile.TemporaryDirectory(prefix='gpu-submit-guard-counts-') as directory:
        directory = Path(directory)
        traces = directory / 'traces'
        traces.mkdir()
        executable = directory / 'submit_guard_counts'
        command = [
            'clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1', '-g',
            '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
            '-fno-omit-frame-pointer', '-I' + str(DEV), str(FIXTURE),
            str(RUNTIME_C), '-o', str(executable),
        ]
        try:
            compiled = subprocess.run(command, cwd=directory, env=env,
                                      capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise AssertionError(f'could not compile fixture: {error}') from error
        check(compiled.returncode == 0,
              'clang compile failed\n' + compiled.stdout + compiled.stderr)
        try:
            run = subprocess.run([str(executable), str(traces)], cwd=directory,
                                 env=env, capture_output=True, text=True,
                                 timeout=120)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise AssertionError(f'could not run fixture: {error}') from error
        check(run.returncode == 0,
              'fixture failed\nstdout:\n' + run.stdout + '\nstderr:\n' + run.stderr)
        try:
            raw = json.loads(run.stdout)
        except json.JSONDecodeError as error:
            raise AssertionError(
                f'fixture emitted invalid JSON: {error}\n{run.stdout}') from error
        validate(raw, directory, run.stderr)

    check({path: sha256(path) for path in pins} == pins,
          'source, header, or fixture changed during the run')
    print('PASS: host-only ggr_submit counts [40,54,82,56] and '
          '[84,98,126,100], 832 injections, 21 deadline edges; '
          'no device execution or timing claim')


if __name__ == '__main__':
    main()
