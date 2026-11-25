#!/usr/bin/env python3
"""Verify and sign the exact 0389 packet recording Core offline."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from statistics import median
import subprocess

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-389'
PATCH = WORK/'graphics/gauguin-program-io/0389-render-packet-recording.patch'
FIXTURE = WORK/'tests/fixtures/frame389_render_recording.cpp'
BASE361 = MAIN/'research/tmp/gauguin-warm-recording-worktree-20261120/research/tmp/frame-361'
BASE346 = MAIN/'research/tmp/gauguin-dpu-hwcg-worktree-20261119/research/tmp/frame-346/core-native'
REFERENCE = BASE361/'core-signed-current-sdk/reference.dylib'
REFERENCE_SHA = '08400c4b1da6915a58102529f87defa12be95f99309ad1847be20b323ec70496'
DEVELOPER = Path('/Applications/Xcode.app/Contents/Developer')
IOS_CLANG = DEVELOPER/'Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++'
IOS_SDK = DEVELOPER/'Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.2.sdk'
CHANGED = ('include/hakios-metal/command.hpp', 'src/render.cpp')


def write_json(path, contents):
    path.write_text(json.dumps(contents, indent=2)+'\n')


def run(argv, log=None, allowed=(0,)):
    env = dict(os.environ, ASAN_OPTIONS='abort_on_error=1:detect_leaks=0',
               UBSAN_OPTIONS='halt_on_error=1')
    result = subprocess.run(argv, capture_output=True, env=env, timeout=180)
    if log:
        log.write_bytes(result.stdout+result.stderr)
    require(result.returncode in allowed, f'{Path(argv[0]).name} exited {result.returncode}: '
            +result.stderr.decode(errors='replace')[-2000:])
    return result


def stage():
    budget = load(BASE/'core-build-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes'] == 75_000_000 and
            budget['current_accounted_bytes']+budget['planned_batch_bytes'] <= budget['limit_bytes'],
            '0389 Core build and offline checks exceed the storage admission')
    recipe = load(BASE346/'result.json')
    source = Path(recipe['source'])
    for name, digest in recipe['source_pins'].items():
        require(sha(source/name) == digest, '0346 sources changed: '+name)
    patch_src = BASE/'host/candidate'
    for path in CHANGED:
        dest = patch_src/path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((source/path).read_bytes())
    subprocess.run(['patch','-p1','-F','0','-i',str(PATCH)], cwd=patch_src,
                   check=True, capture_output=True, timeout=30)
    return recipe, {'reference':source, 'candidate':patch_src}


def host():
    _, sources = stage()
    original = sources['reference']
    owner = MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
    out = BASE/'host'
    evidence = {str(FIXTURE):sha(FIXTURE), str(PATCH):sha(PATCH)}

    def build_variants(mode, flags):
        directory = out/mode
        directory.mkdir(exist_ok=True)
        unchanged = [p for p in sorted((BASE361/'draw-checks'/mode).glob('*.o'))
                     if p.stem not in ('reference', 'candidate', 'draw-fixture')]
        require(len(unchanged) == 11, '0361 host baseline object count differs')
        evidence.update({str(p):sha(p) for p in unchanged})
        common = ['xcrun','--sdk','macosx','clang++','-O2','-std=c++17','-pthread',
                  '-Wall','-Wextra','-Werror','-Wno-unused-function','-DHAKIOS_METAL_TARGET_A619',
                  *flags]
        frameworks = ['-framework','IOKit','-framework','CoreFoundation']

        def build(pair):
            tag, source = pair
            includes = ['-I'+str(p) for p in (source/'include',original/'include',original/'src',original/'tests')]
            obj = directory/(tag+'-render.o')
            binary = directory/tag
            run([*common,*includes,'-c',str(source/'src/render.cpp'),'-o',str(obj)],directory/(tag+'-compile.log'))
            run([*common,*includes,str(FIXTURE),str(obj),*map(str,unchanged),*frameworks,
                 '-o',str(binary)],directory/(tag+'-link.log'))
            return tag, binary

        with ThreadPoolExecutor(max_workers=2) as pool:
            variants = dict(pool.map(build,sources.items()))
        if mode == 'sanitized':
            fixture = owner/'tests/fixtures/metal_owned_recording.cpp'
            lifetime = directory/'ownership'
            includes = ['-I'+str(p) for p in (sources['candidate']/'include',original/'include',original/'src',
                                               original/'tests',fixture.parent)]
            run([*common,*includes,str(fixture),str(directory/'candidate-render.o'),
                 *[str(p) for p in unchanged if p.name!='c_api.o'],*frameworks,'-o',str(lifetime)])
            owner_script = owner/'tools/check-metal-owned-recording.py'
            import runpy
            scenarios = runpy.run_path(str(owner_script))['SCENARIOS']
            for case in scenarios:
                require(('PASS '+case).encode() in run([str(lifetime),case]).stdout, 'ownership check did not finish')
            evidence.update({str(path):sha(path) for path in (fixture,owner_script)})
            return variants, len(scenarios)
        return variants, 0

    sanitized, ownership = build_variants('sanitized',['-fsanitize=address,undefined','-fno-sanitize-recover=all'])
    snapshots = [run([str(path),'snapshot']).stdout for path in sanitized.values()]
    require(snapshots[0] == snapshots[1] and len(snapshots[0]) > 240_000, 'PM4 output differs')
    regressions = {}
    for name, path in sanitized.items():
        result = run([str(path),'regressions'],path.parent/(name+'-regressions.log'),allowed=(0,1))
        summaries = re.findall(rb'^(\d+) render tests, (\d+) failed checks$',result.stdout,re.M)
        failures = [line.decode() for line in result.stderr.splitlines() if line.startswith(b'  FAIL ')]
        require(len(summaries) == 1 and int(summaries[0][1]) == len(failures),'sanitized regressions did not finish')
        regressions[name] = dict(tests=int(summaries[0][0]),failures=failures)
    require(regressions['reference'] == regressions['candidate'],'candidate render regression results changed')

    variants, _ = build_variants('timing',['-DNDEBUG'])
    timing = {}
    for mode in ('repeat','mixed'):
        times = {name:[] for name in variants}
        same_lengths = set()
        for attempt in range(10):
            order = tuple(variants)[::1 if attempt%2==0 else -1]
            for name in order:
                ns, draws, words = map(int,run([str(variants[name]),mode]).stdout.split())
                require(ns > 0 and draws == 32_000 and words > 0,'host recording workload changed')
                same_lengths.add(words)
                if attempt:
                    times[name].append(ns/draws)
        require(len(same_lengths) == 1,'recording workload PM4 length differs')
        middle = {name:median(samples) for name,samples in times.items()}
        timing[mode] = dict(samples_ns_per_draw=times, median_ns_per_draw=middle,
            draws=32_000, words=same_lengths.pop(),
            relative_time_saved=1-middle['candidate']/middle['reference'])
    result = dict(state='0389-packet-recording-verified-offline', packet_bytes=len(snapshots[0]),
        packet_sha256=sha256(snapshots[0]).hexdigest(), render_regressions=regressions['candidate'],
        ownership_checks=ownership, host_recording=timing, device_commands=0,
        host_time_improvement=all(row['relative_time_saved'] >= .03 for row in timing.values()),
        source_sha256={path:sha(sources['candidate']/path) for path in CHANGED}, input_pins=evidence)
    write_json(out/'result.json',result)
    return {key:value for key,value in result.items() if key!='input_pins'}


def sign():
    recipe, sources = stage()
    original, source = sources.values()
    out = BASE/'core-native'
    out.mkdir(exist_ok=True)
    reference_objects = REFERENCE.parent
    require(sha(REFERENCE) == REFERENCE_SHA, '0388 exact Core differs')
    require(IOS_SDK.is_dir() and IOS_CLANG.is_file(),'the 0388 iOS 27.2 build toolchain is unavailable')
    obj = out/'render.o'
    binary = out/'libGauguinMetalCore.dylib'
    reference_binary = out/'reference-relinked.dylib'
    pins = {str(path):sha(path) for path in (BASE346/'result.json',REFERENCE,PATCH,*[source/p for p in CHANGED])}

    def args(name):
        argv = list(next(step['argv'][4:] for step in recipe['steps'] if step['name']==name and step['exit']==0))
        argv[argv.index('-isysroot')+1] = str(IOS_SDK)
        return argv

    compile_args = args('compile-render')
    compile_args[compile_args.index('-o')+1] = str(obj)
    compile_args[compile_args.index(str(original/'src/render.cpp'))] = str(source/'src/render.cpp')
    compile_args[:0] = ['-I'+str(source/'include'),'-I'+str(original/'src')]
    run([str(IOS_CLANG),*compile_args],out/'compile.log')
    for dest, render in ((reference_binary,reference_objects/'reference-render.o'),(binary,obj)):
        argv = args('link')
        argv[argv.index('-o')+1] = str(dest)
        for i, arg in enumerate(argv):
            if arg.endswith('.o'):
                path = render if Path(arg).stem=='render' else reference_objects/Path(arg).name
                argv[i] = str(path)
                if path != obj:
                    pins[str(path)] = sha(path)
            elif arg.endswith('.a'):
                pins[arg] = sha(arg)
            elif arg.startswith('-Wl,-exported_symbols_list,'):
                exports = reference_objects/'exports.txt'
                argv[i] = '-Wl,-exported_symbols_list,'+str(exports)
                pins[str(exports)] = sha(exports)
        run([str(IOS_CLANG),*argv],out/(dest.stem+'-link.log'))
        run(['xcrun','strip','-x',str(dest)])
        # Use the production reference's signing identifier for the control
        # so the reconstructed baseline can match its complete signed bytes.
        signing = ['codesign','--force','--sign','-']
        if dest == reference_binary:
            display = run(['codesign','-dv',str(REFERENCE)]).stderr
            identifier, = re.findall(rb'^Identifier=(.+)$',display,re.M)
            signing += ['--identifier',identifier.decode()]
        run([*signing,str(dest)])
        run(['codesign','--verify','--strict',str(dest)])
    require(sha(reference_binary)==REFERENCE_SHA,'the ARM64 link did not reproduce the installed reference')
    require(sha(binary)!=REFERENCE_SHA and 0<binary.stat().st_size<=2053*4096,
            'replacement Core is unchanged or exceeds its owned allocation')
    for argv in (['nm','-gUj'], ['nm','-uj'], ['otool','-L']):
        a,b = (run([*argv,str(path)]).stdout.splitlines() for path in (REFERENCE,binary))
        if argv[0] == 'otool':
            a,b = a[1:],b[1:]
        require(sorted(a)==sorted(b),'signed Core ABI differs: '+argv[0])
    metadata = run(['vtool','-show-build',str(binary)]).stdout
    require(all(re.search(pattern,metadata) for pattern in (rb'platform\s+IOS\b',rb'minos\s+16\.0',rb'sdk\s+27\.2')),
            'signed Core SDK or minimum version differs')
    receipt = dict(state='0389-exact-ARM64-Core-signed',binary=str(binary),binary_sha256=sha(binary),
        bytes=binary.stat().st_size,sdk='27.2',minos='16.0',signature_verified=True,compiled_tus=1,
        reconstructed_reference_sha256=sha(reference_binary),device_commands=0,
        source_sha256={path:sha(source/path) for path in CHANGED},input_pins=pins)
    write_json(out/'result.json',receipt)
    return {key:value for key,value in receipt.items() if key!='input_pins'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=('host','sign'))
    print(json.dumps({'host':host,'sign':sign}[parser.parse_args().step](),indent=2))
