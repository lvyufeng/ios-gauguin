#!/usr/bin/env python3
"""Validate the positive lifetime and ordering contracts of a619-ownership.

Builds the actual full core with ASan/UBSan and its real FakeGpu. Requires the
ownership prepare receipt; baseline vulnerability scenarios are never run.
Fresh output only. No device access. Admission covers the entire build batch.
"""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys

UNITS = ['pm4','gpu','command','compute','texture','render','link','compiler',
         'metallib','fake_gpu','iokit_transport']
SCENARIOS = [f'callback-{mode}-{outcome}' for mode in ['deferred','synchronous']
             for outcome in ['success','refusal','allocation','submission']] + [
    'wrappers-first','external-free-success','external-free-error',
    'different-recorders','release-other-recorder','fifo-encoding','mode-frozen',
    'worker-exception','enqueue-allocation','error-to-caller','append-source',
    'queued-arguments','synchronous-exception','nested-completion','ordered-indexed-refusal',
]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepared', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--cxx', default='clang++')
    ap.add_argument('--planned-bytes', type=int, default=2147483648)
    a = ap.parse_args()
    repo = Path(__file__).resolve().parents[1]
    receipt = a.prepared.resolve()/'result.json'
    r = json.loads(receipt.read_text())
    assert r['profile'] == 'a619-ownership', 'ownership profile required'
    source = Path(r['source'])
    pins = {str(source/p): h for p,h in r['source_pins'].items()}
    assert len(pins) == 228 and all(sha(Path(p)) == h for p,h in pins.items())
    harness = repo/'tests/fixtures/metal_owned_recording.cpp'
    budget_tool = repo/'tools/storage-budget.py'
    for p in [harness, receipt, Path(__file__).resolve(), budget_tool]: pins[str(p)] = sha(p)
    out = a.out.resolve()
    assert not out.exists(), 'fresh output required'
    assert not out.is_relative_to(source) and not source.is_relative_to(out)
    budget = subprocess.run([sys.executable, str(budget_tool), '--planned-bytes', str(a.planned_bytes)],
                            capture_output=True, text=True, check=True)
    admission = json.loads(budget.stdout); assert admission['admitted'] is True
    out.mkdir(parents=True, exist_ok=False)
    (out/'storage-budget.json').write_text(budget.stdout)
    proof = dict(state='building', source=str(source), prepared=str(a.prepared.resolve()),
                 input_pins=pins, storage_budget=admission, builds=[], scenarios=[], device_commands=0,
                 physical_gpu_qualified=False)
    def save(): (out/'result.json').write_text(json.dumps(proof,indent=2)+'\n')
    save()
    common = ['-std=c++17','-O1','-g','-fno-omit-frame-pointer','-pthread',
              '-Wall','-Wextra','-Werror','-Wno-unused-function',
              '-fsanitize=address,undefined','-fno-sanitize-recover=all',
              '-DHAKIOS_METAL_TARGET_A619', '-I'+str(source/'include'), '-I'+str(source/'src')]
    def run(argv, name, timeout=120):
        try:
            p = subprocess.run(argv,capture_output=True,text=True,timeout=timeout,
                env={**os.environ,'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'})
            code, stdout, stderr = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            code, stdout, stderr = 'timeout', str(e.stdout or ''), str(e.stderr or '')
        log = out/(name+'.log')
        log.write_text('$ '+repr(argv)+'\n'+stdout+stderr)
        return dict(argv=argv,exit=code,log=str(log),sha256=sha(log),stdout=stdout,stderr=stderr)
    def compile(name):
        src = harness if name == 'ownership-contracts' else source/'src'/f'{name}.cpp'
        return run([a.cxx,*common,'-c',str(src),'-o',str(out/(name+'.o'))],'compile-'+name)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        proof['builds'] = list(pool.map(compile,[*UNITS,'ownership-contracts']))
    if any(step['exit'] != 0 for step in proof['builds']):
        proof['state'] = 'compile-failed'; save()
        print(json.dumps({k:v for k,v in proof.items() if k in ['state','builds']},indent=2)); return 1
    binary = out/'metal-owned-recording'
    proof['link'] = run([a.cxx,*common,*[str(out/(n+'.o')) for n in [*UNITS,'ownership-contracts']],
                         '-framework','IOKit','-framework','CoreFoundation','-o',str(binary)],'link')
    if proof['link']['exit'] != 0: proof['state']='link-failed'; save(); return 1
    proof['binary_sha256'] = sha(binary)
    for scenario in SCENARIOS:
        step = run([str(binary),scenario],scenario,timeout=15)
        step['scenario'] = scenario
        step['accepted'] = (step['exit'] == 0 and 'PASS '+scenario+':' in step['stdout']
                            and 'ERROR: AddressSanitizer' not in step['stderr']
                            and 'runtime error:' not in step['stderr'])
        proof['scenarios'].append(step); save()
        print(scenario, 'PASS' if step['accepted'] else 'FAIL', flush=True)
    proof['input_pins_unchanged'] = all(sha(Path(p)) == h for p,h in pins.items())
    accepted = proof['input_pins_unchanged'] and all(s['accepted'] for s in proof['scenarios'])
    proof['state'] = 'passed-host-ownership-contracts' if accepted else 'host-contracts-failed'
    save()
    print(json.dumps(dict(state=proof['state'],passed=sum(s['accepted'] for s in proof['scenarios']),
                         total=len(SCENARIOS),result=str(out/'result.json')),indent=2))
    return 0 if accepted else 1

if __name__ == '__main__': raise SystemExit(main())
