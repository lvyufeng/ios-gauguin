#!/usr/bin/env python3
"""Gate the actual C4 frontend methods against fake ordered core completion."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess


QUEUE = ['- (void)hakiosAdmit:(dispatch_block_t)commit',
         '- (void)setCompletionQueue:(dispatch_queue_t)queue',
         '- (dispatch_queue_t)hakiosCompletionQueue']
BUFFER = ['- (void)commit\n', '- (void)waitUntilScheduled',
          '- (void)waitUntilCompleted',
          '- (void)hakiosDeliver:(MTLCommandBufferHandler)handler',
          '- (void)hakiosMarkScheduled', '- (void)hakiosCompletedNow',
          '- (void)addScheduledHandler:(MTLCommandBufferHandler)handler',
          '- (void)addCompletedHandler:(MTLCommandBufferHandler)handler']


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(source: str, signature: str) -> str:
    matches = list(re.finditer(re.escape(signature) + r'\s*\{', source))
    assert len(matches) == 1, (signature, len(matches))
    start = matches[0].start()
    opening = matches[0].end() - 1
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('unclosed method: ' + signature)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    receipt = json.loads(args.prepared.read_text())
    assert receipt['state'] == 'prepared-owned-C4-desktop-frontend'
    source_dir = Path(receipt['source'])
    source_path = source_dir / 'userland/src/HakiosMetalCA.m'
    for name, digest in receipt['source_pins'].items():
        assert sha(source_dir / name) == digest, name
    source = source_path.read_text()
    template_path = repo / 'tests/fixtures/metal_ca_c4_host.m'
    template = template_path.read_text()
    assert template.count('/* QUEUE_METHODS */') == template.count('/* CB_METHODS */') == 1
    generated = template.replace('/* QUEUE_METHODS */', '\n\n'.join(extract(source, item) for item in QUEUE))
    generated = generated.replace('/* CB_METHODS */', '\n\n'.join(extract(source, item) for item in BUFFER))
    assert not args.out.exists(), 'test output must be fresh'
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    unit = out / 'actual-frontend-methods.m'
    unit.write_text(generated)
    binary = out / 'host-gate'
    command = ['xcrun', 'clang', '-std=gnu11', '-x', 'objective-c', '-fblocks',
               '-fno-objc-arc', '-O1', '-g', '-fsanitize=address,undefined',
               '-framework', 'Foundation', str(unit), '-o', str(binary)]
    with (out / 'compile.log').open('x') as log:
        compiled = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    assert compiled.returncode == 0, (out / 'compile.log').read_text()[-3000:]
    try:
        with (out / 'run.log').open('x') as log:
            ran = subprocess.run([str(binary)], stdout=log, stderr=subprocess.STDOUT, timeout=15)
    except subprocess.TimeoutExpired as error:
        raise AssertionError('actual method gate hung') from error
    assert ran.returncode == 0, (out / 'run.log').read_text()[-3000:]
    assert 'PASS: actual frontend methods preserve FIFO, broadcast waits and handler order' in (out / 'run.log').read_text()
    result = dict(state='actual-C4-methods-host-gate-passed', prepared_sha256=sha(args.prepared),
                  source_sha256=sha(source_path), template_sha256=sha(template_path),
                  generated_sha256=sha(unit), binary_sha256=sha(binary),
                  compile_exit=compiled.returncode, run_exit=ran.returncode,
                  sanitizer='address,undefined', device_commands=0, hardware_qualified=False)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
