#!/usr/bin/env python3
"""Run the real SpringBoard probe over real ObjC dispatch and typed UIKit seams."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'graphics/gauguin-sb-rate-trace/SBRateTrace.m'
FIXTURE = ROOT / 'tests/fixtures/sb_input_probe_host.m'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    analyzer = ROOT/'tools/analyze-sb-stack-log.py'
    files = [Path(__file__).resolve(), SOURCE, FIXTURE, analyzer, *sorted(SOURCE.parent.glob("SBStack*.h"))]
    pins = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    source = SOURCE.read_text()
    assert source.count('#import <UIKit/UIKit.h>') == 1
    source = source.replace('#import <UIKit/UIKit.h>', '/* typed host UIKit declarations precede this source */')
    fixture = FIXTURE.read_text()
    assert fixture.count('@SOURCE@') == 1
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    logs = {}
    with tempfile.TemporaryDirectory(prefix='sb-input-probe-') as directory:
        unit = Path(directory) / 'probe.m'
        unit.write_text(fixture.replace('@SOURCE@', source))
        binary = Path(directory) / 'probe'
        subprocess.run(['clang', '-std=gnu11', '-O1', '-g', '-fno-objc-arc',
                        '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-framework', 'Foundation', '-framework', 'QuartzCore', '-lobjc', '-I', str(SOURCE.parent),
                        str(unit), '-o', str(binary)], env=env, check=True)
        for case in ['abi', 'inherited', 'own', 'stack-format']:
            result = subprocess.run([str(binary), case], env=env, capture_output=True,
                                    text=True, timeout=30)
            assert result.returncode == 0, (case, result.returncode, result.stdout, result.stderr)
            assert result.stdout.startswith('PASS SpringBoard probe ')
            print(result.stdout, end='')
            logs[case] = {'stdout': result.stdout, 'stderr': result.stderr}
            if case == 'stack-format':
                spec = importlib.util.spec_from_file_location('stack_log', analyzer)
                module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                summary = module.summarize(module.parse(result.stderr))
                assert summary['active'] and summary['sample_count']==summary['usable_stack_samples']==1
                assert len(summary['samples'][0]['frame_rows'])==3 and not summary['resume_failures']
                logs[case]['actual_format_parsed'] = True
    assert pins == {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    if args.receipt:
        assert not args.receipt.exists()
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps({'state': 'passed-actual-SpringBoard-observer-host',
            'input_pins': pins, 'inputs_unchanged': True, 'sanitizers': 'address,undefined',
            'scope': 'actual wrappers and ObjC method installation with UIKit event seams',
            'cases': logs, 'hardware_qualified': False, 'device_writes': 0}, indent=2)+'\n')


if __name__ == '__main__':
    main()
