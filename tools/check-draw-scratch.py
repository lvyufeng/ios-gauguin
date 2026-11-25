#!/usr/bin/env python3
"""Full-core ASan/UBSan encoder equivalence, allocation and ownership checks."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import re
import statistics
import subprocess

WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/draw-scratch-329'
MAIN=Path('/Users/baai/Project/ios-gauguin')
OWNER=MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
UNITS=['pm4','gpu','command','compute','texture','render','link','compiler','metallib','fake_gpu','iokit_transport']


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert not out.exists() and out.is_relative_to(STATE)
    prepared=STATE/'prepared-v1/result.json';r=json.loads(prepared.read_text())
    assert r['state']=='prepared-DR329-bounded-draw-scratch'
    pins=dict(r['input_pins'])
    for v,items in r['source_pins'].items():
        for p,h in items.items():pins[str(Path(r['sources'][v])/p)]=h
    for p in [prepared,Path(__file__),WORK/'tests/fixtures/draw_scratch329.cpp',OWNER/'tests/fixtures/metal_owned_recording.cpp',OWNER/'tools/check-metal-owned-recording.py']:
        pins[str(p)]=sha(p)
    assert all(sha(p)==h for p,h in pins.items())
    spec=importlib.util.spec_from_file_location('ownership',OWNER/'tools/check-metal-owned-recording.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    out.mkdir(parents=True);result=dict(state='DR329-host-running',input_pins=pins,steps=[],device_commands=0)
    def save(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    regressions={}
    def run(argv,name,binary=False,timeout=180):
        p=subprocess.run(argv,capture_output=True,timeout=timeout,
            env={**os.environ,'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'})
        log=out/(name+'.log');log.write_bytes(p.stderr if binary else p.stdout+p.stderr)
        step=dict(name=name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log))
        if binary:step.update(stdout_bytes=len(p.stdout),stdout_sha256=hashlib.sha256(p.stdout).hexdigest())
        result['steps'].append(step);save()
        if name.endswith('-render-regression'):
            # The imported upstream suite has seven A635-specific expectations
            # (12 checks) on this A619 target. Keep all results, require the
            # exact observed baseline failures, and reject any new difference.
            v=name.split('-')[0]
            normalized=p.stderr.decode().replace(r['sources'][v],'<SOURCE>')
            expected_lines=[663,967,977,1854,2150,2151,2159,2160,4651,5348,5465,5465]
            assert p.returncode==1 and b'render tests=98 failures=12\n' in p.stdout
            assert [int(n) for n in re.findall(r'render_test.cpp:(\d+):',normalized)]==expected_lines
            regressions[v]=dict(stdout=p.stdout.decode(),stderr=normalized)
        else:
            assert p.returncode==0, f'{name} failed: {p.stderr[:1200]!r}'
        assert b'ERROR: AddressSanitizer' not in p.stderr and b'runtime error:' not in p.stderr
        return p.stdout
    common=['clang++','-std=c++17','-O2','-gline-tables-only','-fno-omit-frame-pointer','-pthread',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-DHAKIOS_METAL_TARGET_A619']
    try:
        binaries={}
        for v in ('baseline','candidate'):
            source=Path(r['sources'][v]);dest=out/v;dest.mkdir()
            flags=[*common,'-I'+str(source/'include'),'-I'+str(source/'src'),'-I'+str(source/'tests')]
            if v=='candidate':flags+=['-DDR329_CANDIDATE']
            jobs={u:source/'src'/f'{u}.cpp' for u in UNITS}
            jobs['draw-scratch']=WORK/'tests/fixtures/draw_scratch329.cpp'
            if v=='candidate':jobs['ownership']=OWNER/'tests/fixtures/metal_owned_recording.cpp'
            def compile(item):
                name,path=item
                argv=[*flags,'-c',str(path),'-o',str(dest/(name+'.o'))]
                p=subprocess.run(argv,capture_output=True,timeout=180)
                log=out/(v+'-compile-'+name+'.log');log.write_bytes(p.stdout+p.stderr)
                return dict(name=v+'-compile-'+name,argv=argv,exit=p.returncode,log=str(log),sha256=sha(log))
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:steps=list(pool.map(compile,jobs.items()))
            result['steps']+=steps;save();assert all(s['exit']==0 for s in steps),'compile failed; inspect logs'
            for harness in (['draw-scratch','ownership'] if v=='candidate' else ['draw-scratch']):
                binary=dest/harness
                run([*flags,*[str(dest/(u+'.o')) for u in [*UNITS,harness]],'-framework','IOKit','-framework','CoreFoundation','-o',str(binary)],v+'-link-'+harness)
            binaries[v]=dest/'draw-scratch'
            run([str(binaries[v]),'regression'],v+'-render-regression')
            run([str(binaries[v]),'failures'],v+'-failure-injection')
        streams={v:run([str(p),'equivalence'],v+'-equivalence',binary=True) for v,p in binaries.items()}
        assert regressions['baseline']==regressions['candidate'],'upstream A619 regression results differ'
        result['upstream_regression_results']=dict(tests_per_variant=98,passed_cases_per_variant=91,
            unchanged_preexisting_failed_cases=7,unchanged_preexisting_failed_checks=12,baseline_equals_candidate=True,
            evidence=regressions['baseline'])
        assert streams['baseline']==streams['candidate'],'GPU command or backing-table bytes changed'
        result['equivalence']=dict(cases=48,bytes=len(streams['baseline']),sha256=hashlib.sha256(streams['baseline']).hexdigest(),raw_byte_comparison=True,backing_slabs_included=True)
        del streams
        for scenario in module.SCENARIOS:
            output=run([str(out/'candidate/ownership'),scenario],'ownership-'+scenario,timeout=20)
            assert ('PASS '+scenario+':').encode() in output
        result['ownership_scenarios']=len(module.SCENARIOS)
        measurements={v:{str(m):[] for m in range(4)} for v in binaries}
        # Interleave variants and reverse order on alternating rounds.
        for n in range(7):
            for m in range(4):
                for v in (list(binaries) if n%2==0 else list(reversed(binaries))):
                    raw=run([str(binaries[v]),'bench',str(m)],f'{v}-bench-{m}-{n}')
                    row=json.loads(raw);assert row['failures']==0
                    measurements[v][str(m)].append(row)
        comparisons=[]
        for m in range(4):
            old=measurements['baseline'][str(m)];new=measurements['candidate'][str(m)]
            assert max(x['allocations'] for x in new)<min(x['allocations'] for x in old)
            comparisons.append(dict(mode=m,baseline_allocations=old[0]['allocations'],candidate_allocations=new[0]['allocations'],
                baseline_median_us=statistics.median(x['recording_us'] for x in old),candidate_median_us=statistics.median(x['recording_us'] for x in new)))
        result.update(state='DR329-full-core-host-equivalence-and-ownership-passed',measurements=measurements,comparisons=comparisons,
            render_regressions_per_variant=98,sanitizers=['address','undefined'],benchmark_sanitized=True,
            binaries={v:dict(path=str(p),sha256=sha(p)) for v,p in binaries.items()},physical_FPS_qualified=False)
    except BaseException as e:result.update(state='DR329-host-failed',error=repr(e));raise
    finally:
        result['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    assert result['inputs_unchanged']
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps','measurements')},indent=2))


if __name__=='__main__':main()
