#!/usr/bin/env python3
"""Qualify actual surface cache and Bo lifetime under controlled and natural races."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/surface-retire-334'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();out=args.out.resolve();assert out.is_relative_to(B) and not out.exists()
    prepared=B/'prepared-v1/result.json';prep=json.loads(prepared.read_text());fixture=W/'tests/fixtures/surface_retire334.cpp'
    pins={str(p):sha(p) for p in [Path(__file__),prepared,fixture]};pins.update(prep['input_pins'])
    for variant,items in prep['source_pins'].items():
        for name,digest in items.items():pins[str(Path(prep['sources'][variant])/name)]=digest
    assert all(sha(p)==d for p,d in pins.items())
    out.mkdir();steps=[];env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    def run(command,label,expected=0,timeout=30):
        with (out/(label+'.log')).open('x') as f:rc=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=timeout).returncode
        steps.append(dict(label=label,exit=rc));assert rc==expected,(label,rc,expected)
        text=(out/(label+'.log')).read_text();assert 'ERROR: AddressSanitizer' not in text and 'runtime error:' not in text
    scenarios=['race','many','recycled','reimport-error','basic','foreign','stress']
    for variant in ('baseline','candidate'):
        source=Path(prep['sources'][variant]);raw=(source/'src/command.cpp').read_text()
        a=raw.index('namespace {\n// '+('the live surface buffers' if variant=='baseline' else 'A dying Buffer'));z=raw.index('// --- CommandBuffer',a);body=raw[a:z]
        lam=body.index('[key](Buffer* x)');at=body.index('std::lock_guard<std::mutex> g(gSurfaceLock);',lam)
        body=body[:at]+'beforeRetireLock();\n            '+body[at:]
        marker='auto live = gSurfaceBuffers.find(key);';assert body.count(marker)==1
        body=body.replace(marker,marker+'\n        observeLookup(live != gSurfaceBuffers.end() && live->second.expired());')
        marker='const uint64_t length = bo->size();';assert body.count(marker)==1
        body=body.replace(marker,marker+'\n        beforePublicationAlloc();')
        unit=out/(variant+'.cpp');unit.write_text(fixture.read_text().replace('/* ACTUAL_SURFACE_BUFFER_SOURCE */',body))
        flags=['clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread','-I'+str(source/'include')]
        if variant=='candidate':flags+=['-DSURF334_CANDIDATE=1']
        run([*flags,str(unit),str(source/'src/gpu.cpp'),'-o',str(out/variant)],variant+'-compile',timeout=120)
        if variant=='baseline':
            run([str(out/variant),'race'],'baseline-functional-red',42)
            run([str(out/variant),'basic'],'baseline-basic')
            continue
        for name in scenarios:run([str(out/variant),name],'candidate-'+name)
        for n in range(1,5):run([str(out/variant),'allocation',str(n)],'candidate-allocation-'+str(n))
    assert all(sha(p)==d for p,d in pins.items())
    result=dict(state='SURF334-actual-cache-lifetime-and-publication-checks-passed',baseline_functional_failure_reproduced=True,candidate_scenarios=scenarios,simultaneous_importers_tested=16,handle_generation_reuse_tested=True,failed_reimport_tested=True,publication_allocation_failure_positions=[1,2,3],no_failure_after_three_allocations_tested=True,stress_threads=8,stress_imports=3200,actual_standard_mutex_and_condition_variable=True,actual_Gpu_and_Bo_compiled=True,scheduling_seams='pause before old deleter lock and observe expired lookup; no ownership or lock decisions replaced',no_duplicate_close_or_leaked_maps=True,sanitizers='ASan+UBSan',input_pins=pins,inputs_unchanged=True,steps=steps,device_commands=0)
    with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))
if __name__=='__main__':main()
