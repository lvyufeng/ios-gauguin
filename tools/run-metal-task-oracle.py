#!/usr/bin/env python3
"""Run five actual public Mac sampler formats; check all raw pixels and bad controls."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess
from metal_task_surface_log import CASES, expected

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def qualify(text, seed):
    lines = text.splitlines(); prefix = 'GAUGUIN TASK ORACLE '
    if len(lines) != 322 or lines[0] != prefix+f'begin seed={seed} cases=5 scope=public-macOS-Metal' or lines[-1] != prefix+'end cases=5 pixels=20480 jobs=5':
        raise ValueError('oracle framing')
    at = 1
    for index, (name, _, _) in enumerate(CASES):
        pixels = bytearray()
        for y in range(64):
            row = re.fullmatch(re.escape(prefix)+rf'row case={name} y={y} rgba=([0-9a-f]{{512}})', lines[at]); at += 1
            if not row: raise ValueError('oracle row identity/length/order')
            pixels.extend(bytes.fromhex(row[1]))
        if pixels != expected(seed, index)[0]: raise ValueError('actual sampler pixels')
    return dict(seed=seed, raw_pixels=20480, formats=5, jobs=5)

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--out', type=Path, required=True)
    out = ap.parse_args().out.resolve(); repo = Path(__file__).resolve().parents[1]
    paths = [Path(__file__).resolve(), repo/'tools/metal_task_surface_log.py',
             repo/'tests/fixtures/metal_task_surface_oracle.m', repo/'userland/metal/pipeline_fixture.metal']
    pins = {str(p): sha(p) for p in paths}; out.mkdir(parents=True, exist_ok=False)
    def run(argv, log):
        with (out/log).open('x') as f:
            subprocess.run(argv, check=True, stdout=f, stderr=subprocess.STDOUT, timeout=60)
    air = out/'task.air'; lib = out/'task.metallib'; binary = out/'oracle'
    run(['xcrun','--sdk','macosx','metal','-target','air64-apple-macos13.0','-std=macos-metal2.4',
         '-O1','-fno-fast-math','-Wall','-Wextra','-Werror','-c',str(paths[3]),'-o',str(air)], 'metal-compile.log')
    run(['xcrun','--sdk','macosx','metallib',str(air),'-o',str(lib)], 'metal-link.log')
    run(['xcrun','--sdk','macosx','clang','-O1','-Wall','-Wextra','-Werror','-fobjc-arc',str(paths[2]),
         '-framework','Foundation','-framework','Metal','-o',str(binary)], 'compile.log')
    results = []; controls = 0
    for seed in [0, 0xffffffff, 0xdeadbeef, 0x12345678]:
        path = out/f'{seed:08x}.stdout'
        with path.open('x') as stdout, (out/f'{seed:08x}.stderr').open('x') as stderr:
            subprocess.run([str(binary),str(lib),str(seed)], check=True, stdout=stdout, stderr=stderr, timeout=45)
        text = path.read_text(); results.append(qualify(text, seed)); lines = text.splitlines()
        bad = [text.replace('y=0 ', 'y=1 ', 1), '\n'.join(lines[:-1]), text+'\n'+lines[-1],
               text.replace('rgba=', 'rgba=0', 1), text.replace('case=R8 ', 'case=RG8 ', 1)]
        for name, _, _ in CASES:
            changed = lines[:]; i = next(i for i,r in enumerate(changed) if f'case={name} y=0 ' in r)
            prefix, raw = changed[i].split('rgba='); changed[i] = prefix+'rgba='+f'{int(raw[:2],16)^1:02x}'+raw[2:]
            bad.append('\n'.join(changed))
        for changed in bad:
            try: qualify(changed, seed)
            except ValueError: controls += 1
            else: raise AssertionError('corrupted actual oracle accepted')
    assert controls == 40 and all(sha(p) == h for p,h in pins.items())
    proof = dict(state='actual-public-Mac-five-format-sampling-passed', seeds=results,
                 raw_pixels=81920, corrupted_actual_logs_rejected=controls,
                 phone_commands=0, task_IOSurface_lifetime_qualified=False, A619_qualified=False,
                 desktop_qualified=False, input_pins=pins)
    (out/'result.json').write_text(json.dumps(proof,indent=2)+'\n'); print(json.dumps(proof,indent=2))
if __name__ == '__main__': main()
