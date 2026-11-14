#!/usr/bin/env python3
"""Exercise real C4 wait methods while a client handler is explicitly held."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

QUEUE = ['- (void)hakiosAdmit:(dispatch_block_t)commit',
         '- (void)setCompletionQueue:(dispatch_queue_t)queue',
         '- (dispatch_queue_t)hakiosCompletionQueue']
BUFFER = ['- (void)commit\n', '- (void)waitUntilScheduled',
          '- (void)waitUntilCompleted', '- (void)hakiosDeliver:(MTLCommandBufferHandler)handler',
          '- (void)hakiosMarkScheduled', '- (void)hakiosCompletedNow',
          '- (void)addScheduledHandler:(MTLCommandBufferHandler)handler',
          '- (void)addCompletedHandler:(MTLCommandBufferHandler)handler']


def extract(source, signature):
    matches = list(re.finditer(re.escape(signature)+r'\s*\{', source))
    assert len(matches) == 1, (signature, len(matches))
    start, opening = matches[0].start(), matches[0].end()-1
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == '{': depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0: return source[start:index+1]
    raise AssertionError('unclosed method: '+signature)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--source-sha256', required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--expect', choices=('early', 'respected'), required=True)
    args = ap.parse_args()
    assert sha(args.source) == args.source_sha256
    root = Path(__file__).resolve().parents[1]
    shell = root/'tests/fixtures/metal_ca_wait_contract_host.m'
    template = shell.read_text()
    source = args.source.read_text()
    methods = list(BUFFER)
    support = ''
    if '/* HM_CALLBACK_SCOPE_BEGIN:' in source:
        start = source.index('\n', source.index('/* HM_CALLBACK_SCOPE_BEGIN:'))+1
        end = source.index('/* HM_CALLBACK_SCOPE_END */', start)
        support = source[start:end]
        methods.append('- (void)hakiosQueueHandler:(MTLCommandBufferHandler)handler scheduled:(BOOL)scheduled')
    template = template.replace('/* CALLBACK_SUPPORT */', support)
    unit = template.replace('/* QUEUE_METHODS */', '\n\n'.join(extract(source, name) for name in QUEUE))
    unit = unit.replace('/* CB_METHODS */', '\n\n'.join(extract(source, name) for name in methods))
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    source_out = out/'actual-wait-contract.m'; source_out.write_text(unit)
    binary = out/'wait-contract'
    command = ['xcrun', 'clang', '-std=gnu11', '-x', 'objective-c', '-fblocks',
               '-fno-objc-arc', '-O1', '-g', '-fsanitize=address,undefined',
               '-framework', 'Foundation', str(source_out), '-o', str(binary)]
    with (out/'compile.log').open('x') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    results = []
    phases = ['scheduled', 'completed', 'scheduled-error', 'completed-error']
    if args.expect == 'respected':
        phases += ['scope-scheduled-self-complete', 'scope-completed-self',
                   'scope-cross-buffer', 'scope-late-completed', 'regression']
    for phase in phases:
        result = subprocess.run([str(binary), phase, args.expect], capture_output=True, text=True, timeout=15)
        (out/(phase+'.stdout')).write_text(result.stdout)
        (out/(phase+'.stderr')).write_text(result.stderr)
        assert result.returncode == 0 and not result.stderr, (phase, result.returncode, result.stderr)
        results.append({'phase':phase, 'exit':result.returncode, 'output':result.stdout.strip()})
    assert sha(args.source) == args.source_sha256
    receipt = dict(state=('reproduced-C4-wait-returns-before-handlers' if args.expect=='early'
                          else 'passed-C4-wait-handler-contract'),
                   input_pins={str(p.resolve()):sha(p) for p in (args.source, shell, Path(__file__))},
                   generated_sha256=sha(source_out), binary_sha256=sha(binary),
                   cases=results, sanitizer='ASAN+UBSAN', device_commands=0,
                   five_second_root_cause_proven=False, hardware_qualified=False)
    (out/'result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='input_pins'}, indent=2))


if __name__ == '__main__':
    main()
