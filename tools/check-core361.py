#!/usr/bin/env python3
"""Compare the exact 0346 and 0361 draw encoders on the host and ARM64."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import re
from statistics import median
import subprocess

from frame360_scope import MAIN, P358, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-361'
PATCH = WORK/'graphics/gauguin-program-io/0361-warm-draw-setup.patch'
REFERENCE = Path(load(P358/'core-native/result.json')['binary']).parent/'result.json'
OWNER = MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'


def stage():
    volume = load(BASE/'recording-budget.json')
    require(volume['admitted'] and volume['planned_batch_bytes']>=80_000_000,
            '0361 full Core and host validation batch did not fit storage')
    before = load(REFERENCE)
    original = Path(before['source'])
    changed = BASE/'draw-validation-source'
    (changed/'src').mkdir(parents=True,exist_ok=True)
    text = (original/'src/render.cpp').read_bytes()
    require(sha(original/'src/render.cpp')==before['source_pins']['src/render.cpp'],'0346 render reference differs')
    (changed/'src/render.cpp').write_bytes(text)
    subprocess.run(['patch','-p1','-F','0','-i',str(PATCH)],cwd=changed,check=True,capture_output=True,timeout=60)
    return before,{'reference':original,'candidate':changed}


def cross_compile():
    before,sources = stage()
    argv = next(s['argv'] for s in before['steps'] if s['name']=='compile-render' and s['exit']==0)
    require(argv[:4]==['xcrun','--sdk','iphoneos','clang++'],'original compiler invocation differs')
    developer = Path('/Applications/Xcode.app/Contents/Developer')
    compiler = developer/'Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++'
    sdk = (developer/'Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk').resolve(strict=True)
    original = sources['reference']
    out = BASE/'draw-cross-compile'
    out.mkdir(exist_ok=True)
    objects = {}
    for name,source in sources.items():
        obj = out/(name+'.o')
        args = argv[4:]
        args[args.index('-isysroot')+1] = str(sdk)
        args[args.index('-o')+1] = str(obj)
        args[args.index(str(original/'src/render.cpp'))] = str(source/'src/render.cpp')
        proc = subprocess.run([str(compiler),'-I'+str(original/'src'),*args],capture_output=True,timeout=90)
        (out/(name+'.log')).write_bytes(proc.stdout+proc.stderr)
        require(proc.returncode==0,'ARM64 render compile failed: '+name)
        objects[name] = obj

    def symbols(path,*mode):
        return set(subprocess.check_output(['nm',*mode,str(path)],text=True).splitlines())

    a,b = objects.values()
    metadata = subprocess.check_output(['vtool','-show-build',str(b)],text=True)
    require(re.search(r'platform\s+IOS\b',metadata) and re.search(r'minos\s+16\.0',metadata),
            'ARM64 candidate minimum iOS target differs')
    definitions_match = symbols(a,'-gUj')==symbols(b,'-gUj')
    imports_match = symbols(a,'-uj')==symbols(b,'-uj')
    require(definitions_match and imports_match,'render object symbols changed against the same SDK')
    receipt = dict(state='0361-arm64-render-unit-compiled',sdk=str(sdk),minimum_ios='16.0',
        reference_sha256=sha(a),candidate_sha256=sha(b),render_source_sha256=sha(sources['candidate']/'src/render.cpp'),
        same_global_definitions=definitions_match,same_undefined_symbols=imports_match,device_commands=0)
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


def run_checks():
    _,sources = stage()
    original = sources['reference']
    original = sources['reference']
    out = BASE/'draw-checks'
    out.mkdir(exist_ok=True)
    fixture = WORK/'tests/fixtures/core361_draw_setup.cpp'
    lifetime = OWNER/'tests/fixtures/metal_owned_recording.cpp'
    owner = importlib.util.spec_from_file_location('owned_recording',OWNER/'tools/check-metal-owned-recording.py')
    tests = importlib.util.module_from_spec(owner)
    owner.loader.exec_module(tests)
    frameworks = ['-framework','IOKit','-framework','CoreFoundation']
    env = {**os.environ,'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'}

    def run(argv):
        proc = subprocess.run(argv,env=env,capture_output=True,timeout=180)
        if proc.returncode:
            raise RuntimeError(str(argv[0])+' failed\n'+proc.stderr.decode(errors='replace'))
        return proc.stdout

    def build_variants(mode,extra):
        directory = out/mode
        directory.mkdir(exist_ok=True)
        compiler = ['xcrun','--sdk','macosx','clang++','-O2','-std=c++17','-pthread',
                    '-Wall','-Wextra','-Werror','-Wno-unused-function','-DHAKIOS_METAL_TARGET_A619',
                    *extra,'-I'+str(original/'include'),'-I'+str(original/'src'),
                    '-I'+str(original/'tests'),'-I'+str(OWNER/'tests/fixtures')]

        def build(item):
            name,path = item
            obj = directory/(name+'.o')
            run([*compiler,'-c',str(path),'-o',str(obj)])
            return str(obj)

        common = [(unit,original/'src'/(unit+'.cpp')) for unit in ('c_api',*tests.UNITS) if unit!='render']
        renders = [(name,source/'src/render.cpp') for name,source in sources.items()]
        with ThreadPoolExecutor(max_workers=5) as pool:
            units = list(pool.map(build,common+renders))
        unchanged = units[:len(common)]
        fixture_obj = build(('draw-fixture',fixture))
        executables = {}
        for name,obj in zip(sources,units[len(common):],strict=True):
            binary = directory/name
            run([*compiler,fixture_obj,*unchanged,obj,*frameworks,'-o',str(binary)])
            executables[name] = binary
        if mode=='sanitized':
            binary = directory/'ownership'
            library = [path for path in unchanged if Path(path).name!='c_api.o']
            run([*compiler,str(lifetime),*library,units[-1],*frameworks,'-o',str(binary)])
            for case in tests.SCENARIOS:
                require(('PASS '+case).encode() in run([str(binary),case]), 'ownership check did not complete')
        return executables

    correctness = build_variants('sanitized',['-fsanitize=address,undefined','-fno-sanitize-recover=all'])
    snapshot = {name:run([str(binary),'snapshot']) for name,binary in correctness.items()}
    require(snapshot['reference']==snapshot['candidate'] and len(snapshot['candidate'])>5*8192,
            'draw table or command words differ')
    regression = {}
    for name,binary in correctness.items():
        process = subprocess.run([str(binary),'regressions'],env=env,capture_output=True,text=True,timeout=90)
        summaries = re.findall(r'^(\d+) render tests, (\d+) failed checks$',process.stdout,re.M)
        failures = [line for line in process.stderr.splitlines() if line.startswith('  FAIL ')]
        require(process.returncode in (0,1) and len(summaries)==1 and int(summaries[0][1])==len(failures),
                'render tests did not finish under sanitizers')
        regression[name] = dict(tests=int(summaries[0][0]),failures=failures)
    require(regression['reference']==regression['candidate'],'candidate changed render regression results')
    bench = build_variants('timing',[])
    results = {}
    for shape in ('short','long','masked'):
        samples = {variant:[] for variant in bench}
        words = set()
        for cycle in range(9):
            order = list(bench) if cycle%2==0 else list(reversed(bench))
            for variant in order:
                ns,draws,encoded_words = map(int,run([str(bench[variant]),shape]).split())
                require(draws==30_000 and ns>0 and encoded_words>0, 'draw benchmark shape changed')
                words.add(encoded_words)
                samples[variant].append(ns/draws)
        require(len(words)==1,'benchmark command stream length changed')
        results[shape] = dict(ns_per_draw={tag:median(value) for tag,value in samples.items()},
                              samples_ns=samples,draws_per_trial=30_000,words_per_trial=words.pop())
    receipt = dict(state='0361-byte-equivalent-draw-encoding-and-ownership-passed',
        compared_packet_and_table_bytes=len(snapshot['candidate']),byte_exact_layouts=5,
        render_regressions=regression,ownership_cases=len(tests.SCENARIOS),host_timing=results,
        render_source_sha256=sha(sources['candidate']/'src/render.cpp'),device_commands=0)
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(state=receipt['state'],byte_exact_layouts=receipt['byte_exact_layouts'],
        render_tests=regression['candidate']['tests'],matching_baseline_failed_checks=len(regression['candidate']['failures']),
        ownership_cases=receipt['ownership_cases'],
        median_ns_per_draw={shape:data['ns_per_draw'] for shape,data in results.items()}),indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=('cross-compile','verify'))
    {'cross-compile':cross_compile,'verify':run_checks}[parser.parse_args().step]()
