#!/usr/bin/env python3
"""Build/run our image shaders on Mac Metal, independently check every pixel."""
from pathlib import Path
import argparse, hashlib, json, subprocess
from metal_image_oracle import qualify_image_oracle


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--shader-receipt', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); repo = Path(__file__).resolve().parents[1]
    receipt = json.loads(a.shader_receipt.read_text()); library = Path(receipt['library'])
    assert receipt['platform'] == 'macos' and receipt['inputs_unchanged']
    assert sha(library) == receipt['library_sha256']
    unit = repo / 'tests/fixtures/metal_image_oracle.mm'
    pins = dict(receipt['input_pins'])
    for p in [Path(__file__).resolve(), repo/'tools/metal_image_oracle.py', unit, a.shader_receipt.resolve(), library]:
        pins[str(p)] = sha(p)
    assert all(sha(p) == h for p, h in pins.items())
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    binary = out/'image-oracle'
    argv = ['xcrun','--sdk','macosx','clang++','-std=c++17','-O2','-fno-fast-math',
            '-Wall','-Wextra','-Werror','-fobjc-arc',str(unit),'-framework','Foundation',
            '-framework','Metal','-o',str(binary)]
    with (out/'compile.log').open('x') as f:
        subprocess.run(argv, check=True, stdout=f, stderr=subprocess.STDOUT)
    results = []; controls = 0
    for seed in [0, 0xffffffff, 0xdeadbeef, 0x12345678]:
        name = f'{seed:08x}'
        with (out/(name+'.stdout')).open('x') as stdout, (out/(name+'.stderr')).open('x') as stderr:
            subprocess.run([str(binary),str(library),str(seed)], stdout=stdout,stderr=stderr,check=True,timeout=45)
        text = (out/(name+'.stdout')).read_text()
        results.append(qualify_image_oracle(text,seed))
        lines = text.splitlines()
        bad = [text.replace('plane=image y=0', 'plane=image y=1', 1),
               text.replace('plane=sample y=0', 'plane=sample y=1', 1),
               text.replace('plane=coverage y=0', 'plane=coverage y=1', 1),
               '\n'.join(lines[:-1]), text+'\n'+lines[-1],
               text.replace('data=', 'data=0', 1), text.replace('data=', 'data=g', 1)]
        # Corrupt a real coverage pixel, retaining correct row sizes/labels.
        mutated = lines[:]; idx = next(i for i,r in enumerate(mutated) if 'plane=coverage y=0 ' in r)
        prefix, raw = mutated[idx].split('data='); mutated[idx]=prefix+'data='+f'{int(raw[:8],16)^1:08x}'+raw[8:]
        bad.append('\n'.join(mutated))
        for changed in bad:
            try:
                qualify_image_oracle(changed,seed)
            except ValueError:
                controls += 1
            else:
                raise AssertionError('corrupted actual oracle log accepted')
    assert controls == 32 and all(sha(p)==h for p,h in pins.items())
    proof = dict(state='actual-Mac-Metal-own-image-shaders-all-raw-pixels-passed',
                 seeds=results,total_raw_pixels=sum(r['raw_pixels'] for r in results),
                 corrupted_actual_logs_rejected=controls,device_commands=0,
                 phone_GPU_qualified=False,A619_qualified=False,desktop_qualified=False,
                 binary_sha256=sha(binary),input_pins=pins)
    with (out/'result.json').open('x') as f:
        json.dump(proof,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in proof.items() if k!='input_pins'},indent=2))


if __name__ == '__main__':
    main()
