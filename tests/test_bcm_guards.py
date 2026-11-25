#!/usr/bin/env python3
"""Host-only tests of the actual RSC helper and actual legacy entry guard.

No device, MMIO, shell, network, assembly generation or object patching. Only
the helper's DMB is replaced with an ordered host seam. The legacy body is
explicitly omitted and replaced by a fallback sentinel; its byte preservation
against source114 is verified separately before compilation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_SOURCE = Path(os.environ.get('XNU_SOURCE', str(ROOT / '.deps-cache/p0-20261105/source115-codex')))
BASELINE_LEGACY_SHA256 = 'df880803f76a3a65596ecefd5729991c2fa905bcc91fb5c751dccbeae1095da1'
FLAGS = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
         '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-g', '-O1']


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, old, new):
    check(text.count(old) == 1, f'expected one source seam: {old!r}')
    return text.replace(old, new, 1)


def function_span(text, result, name):
    pattern = r'^' + re.escape(result) + r'[ \t\r\n]+' + re.escape(name) + r'\([^;]*?\)\n\{'
    match = re.search(pattern, text, re.MULTILINE)
    check(match is not None, f'actual function definition not found: {name}')
    opening = match.end() - 1
    depth, position = 0, opening
    while position < len(text):
        if text.startswith('//', position):
            end = text.find('\n', position + 2)
            check(end != -1, f'unterminated line comment in {name}')
            position = end
            continue
        if text.startswith('/*', position):
            end = text.find('*/', position + 2)
            check(end != -1, f'unterminated comment in {name}')
            position = end + 2
            continue
        char = text[position]
        if char in ('"', "'"):
            quote = char
            position += 1
            while position < len(text) and text[position] != quote:
                position += 2 if text[position] == '\\' else 1
            check(position < len(text), f'unterminated literal in {name}')
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return match.start(), opening, position + 1
        position += 1
    raise ValueError(f'unterminated function: {name}')


def actual_function(text, result, name):
    start, _opening, end = function_span(text, result, name)
    return text[start:end] + '\n'


def legacy_gate(text):
    start, opening, end = function_span(text, 'int', 'sweet_rpmh_vreg_enable')
    guard_start = opening + 2
    check(text[opening:guard_start] == '{\n', 'unexpected legacy opening')
    check(text.startswith('#if defined(GAUGUIN)\n', guard_start),
          'guard must be the first legacy-function statement/directive')
    depth = 0
    position = guard_start
    for line in text[guard_start:end].splitlines(keepends=True):
        directive = re.match(r'^\s*#\s*(if|ifdef|ifndef|endif)\b', line)
        if directive:
            depth += -1 if directive[1] == 'endif' else 1
            if depth == 0:
                guard_end = position + len(line)
                return text[start:guard_end], guard_start, guard_end
        position += len(line)
    raise ValueError('legacy entry guard has no matching #endif')


def prepare(inputs):
    pe = inputs['pe'].decode('utf-8')
    legacy = inputs['legacy'].decode('utf-8')
    transport = inputs['transport'].decode('utf-8')
    helper = actual_function(pe, 'bool', 'sweet_rsc_irq_quiet')
    helper = replace_once(helper, '__asm__ volatile("dmb oshld" ::: "memory");',
                          'fake_dmb();')
    selector = actual_function(transport, 'bool', 'sweet_bcm_vote_requested')
    entry, guard_start, guard_end = legacy_gate(legacy)
    restored = legacy[:guard_start] + legacy[guard_end:]
    restored = replace_once(restored, '#include <pexpert/arm64/board_config.h>\n', '')
    restored = replace_once(restored,
        '#if defined(GAUGUIN)\nextern bool sweet_bcm_vote_requested(void);\n#endif\n', '')
    restored_bytes = restored.encode('utf-8')
    check(digest(restored_bytes) == BASELINE_LEGACY_SHA256,
          'legacy file differs from baseline114 beyond the entry guard/include/prototype')
    # The remainder of the actual legacy function is never compiled/executed.
    entry += '    return legacy_fallback(res, mv);\n}\n'
    helper_unit = replace_once(inputs['helper_fixture'].decode('utf-8'),
                               '@RSC_HELPER@', helper)
    gate_unit = replace_once(inputs['gate_fixture'].decode('utf-8'),
                             '@ACTUAL_FLAG_SELECTOR@', selector)
    gate_unit = replace_once(gate_unit, '@ACTUAL_LEGACY_ENTRY@', entry)
    for unit in (helper_unit, gate_unit):
        check('__asm__' not in unit and re.search(r'\bvolatile\b', unit) is None,
              'unseamed assembly/direct volatile access remains')
    preservation = {
        'scope': 'whole legacy file byte-identical after removing only the three additions',
        'baseline_sha256': BASELINE_LEGACY_SHA256,
        'normalized_legacy_sha256': digest(restored_bytes),
        'entry_guard_sha256': digest(legacy[guard_start:guard_end].encode('utf-8')),
        'legacy_body_executed': False,
    }
    return helper_unit, gate_unit, preservation


def invoke(command, log, env):
    log.write('$ ' + shlex.join(map(str, command)) + '\n')
    log.flush()
    result = subprocess.run(list(map(str, command)), capture_output=True,
                            text=True, env=env, timeout=60)
    log.write(result.stdout)
    log.write(result.stderr)
    log.write(f'exit={result.returncode}\n')
    log.flush()
    if result.returncode != 0:
        raise RuntimeError(f'{command[0]} failed with exit {result.returncode}')
    return result.stdout


def main(temporary):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    source = args.source_root.resolve()
    paths = {
        'pe': source / 'pexpert/arm/pe_fiq.c',
        'legacy': source / 'bsd/dev/sweet_rpmh.c',
        'transport': source / 'bsd/dev/gauguin_bcm_transport.c',
        'helper_fixture': HERE / 'fixtures/gauguin_rsc_irq_host.c',
        'gate_fixture': HERE / 'fixtures/gauguin_rpmh_exclusion_host.c',
        'runner': Path(__file__).resolve(),
    }
    for path in paths.values():
        if not path.is_file():
            parser.exit(2, f'missing input: {path}\n')
    run = Path(temporary)
    log_path, report_path = run / 'run.log', run / 'result.json'
    inputs = {key: path.read_bytes() for key, path in paths.items()}
    before = {key: digest(data) for key, data in inputs.items()}
    report = {
        'state': 'running', 'source_root': str(source), 'baseline_sha256': BASELINE_LEGACY_SHA256,
        'run': str(run), 'inputs': {key: {'path': str(paths[key]), 'sha256': value}
                                   for key, value in before.items()},
        'scope': 'host seams: actual GIC helper and actual entry gate only; no hardware/reset qualification',
        'cases': {},
    }
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    env = os.environ.copy()
    env['ASAN_OPTIONS'] = 'halt_on_error=1'
    env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    try:
        with log_path.open('x') as log:
            helper, gate, preservation = prepare(inputs)
            report['legacy_preservation'] = preservation
            log.write('PASS source preservation: normalized legacy == baseline114 bytes\n')
            helper_path, gate_path = run / 'helper.c', run / 'gate.c'
            helper_path.write_text(helper)
            gate_path.write_text(gate)
            jobs = [('rsc-helper', helper_path, ['-DGAUGUIN=1']),
                    ('legacy-gate-gauguin', gate_path, ['-DGAUGUIN=1']),
                    ('legacy-gate-other', gate_path, [])]
            for name, unit, defines in jobs:
                binary = run / name
                invoke(['clang', *FLAGS, *defines, unit, '-o', binary], log, env)
                output = invoke([binary], log, env)
                matches = re.findall(r'^PASS ' + re.escape(name) + r' cases=(\d+)$',
                                     output, re.MULTILINE)
                check(len(matches) == 1 and int(matches[0]) > 0,
                      f'{name}: missing or ambiguous completion count')
                report['cases'][name] = int(matches[0])
            after = {key: digest(path.read_bytes()) for key, path in paths.items()}
            check(after == before, 'source/fixture/runner changed during the run')
            report['state'] = 'passed'
    except Exception as error:
        report.update(state='failed', error=str(error))
        with log_path.open('a') as log:
            log.write(f'FAIL: {error}\n')
        print(f'FAIL: {error}; {log_path}', file=sys.stderr)
        return 1
    finally:
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS controller guards: {report["cases"]}; {report_path}')
    return 0


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix="gauguin-bcm-guards-") as temporary:
        raise SystemExit(main(temporary))
