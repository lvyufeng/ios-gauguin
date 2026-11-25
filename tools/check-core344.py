#!/usr/bin/env python3
"""Run the same production encoding paths and ownership fixtures on the host."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess

from core343_scope import MAIN, WORK, load, require, sha


BASE = WORK/'research/tmp/frame-344'
P342 = MAIN/'research/tmp/gauguin-io-path-worktree-20261117/research/tmp/io-path-342'
OWNER = MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112'
RENDER_CASES = (
    'a_draw_like_the_last', 'draws_into_the_same_attachments', 'append_runs_another',
    'a_pass_in_gmem_loads', 'a_draw_writes_two_colour', 'a_draw_loads_the_ubo',
    'an_indexed_draw_is_the', 'a_draw_that_reads_its_target',
)


def check(base, reference, *, trial='0344', baseline_workmeter_split=True, program_fixture=None,
          packet_benchmark=False):
    native = load(base/'core-native/result.json')
    require(native['state']==trial+'-native-core-signed' and native['inputs_unchanged'], 'unchecked native Core')
    spec = importlib.util.spec_from_file_location('owned_fixtures', OWNER/'tools/check-metal-owned-recording.py')
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    out = base/'core-host-reviewed'
    out.mkdir()
    fixture = WORK/'tests/fixtures/core344_encoding.cpp'
    flags = ['clang++','-std=c++17','-O2','-pthread','-Wall','-Wextra','-Werror',
             '-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all',
             '-DHAKIOS_METAL_TARGET_A619']
    frameworks = ['-framework','IOKit','-framework','CoreFoundation']
    env = {**os.environ, 'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0', 'UBSAN_OPTIONS':'halt_on_error=1'}

    def run(label, argv):
        process = subprocess.run(argv, capture_output=True, env=env, timeout=180)
        log = out/(label+'.stderr')
        log.write_bytes(process.stderr)
        if process.returncode:
            raise RuntimeError(f'{label} failed, see {log}')
        return process.stdout

    packets, encoders = {}, {}
    for variant, source in (('reference', reference), ('candidate', Path(native['source']))):
        here = out/variant
        here.mkdir()
        cflags = [*flags, *['-I'+str(source/folder) for folder in ('include','src','tests')],
                  '-I'+str(OWNER/'tests/fixtures')]

        def compile_unit(unit):
            path = here/(unit+'.o')
            run(variant+'-'+unit, [*cflags,'-c',str(source/'src'/(unit+'.cpp')),'-o',str(path)])
            return str(path)

        with ThreadPoolExecutor(max_workers=5) as pool:
            objects = list(pool.map(compile_unit, owner.UNITS))
        capi = compile_unit('c_api')
        command = here/'encoding'
        reference_flag = ['-DREFERENCE_0343'] if variant=='reference' and baseline_workmeter_split else []
        run(variant+'-link-encoding', [*cflags,*reference_flag,str(fixture),*objects,capi,
                                     *frameworks,'-o',str(command)])
        packets[variant] = run(variant+'-encoding',[str(command)])
        encoders[variant] = command
        if variant=='candidate':
            ownership = here/'ownership'
            run('link-ownership', [*cflags,str(OWNER/'tests/fixtures/metal_owned_recording.cpp'),
                                   *objects,*frameworks,'-o',str(ownership)])
            for scenario in owner.SCENARIOS:
                require(('PASS '+scenario).encode() in run('owner-'+scenario,[str(ownership),scenario]),
                        'ownership scenario did not finish: '+scenario)
            tests = here/'tests'
            inputs = sorted(str(path) for path in (source/'tests').glob('*.cpp'))
            run('link-tests', [*cflags,*inputs,*objects,capi,*frameworks,'-o',str(tests)])
            suite = b''.join(run('render-'+case,[str(tests),case]) for case in RENDER_CASES)
            require(suite.count(b'1 tests, 0 failed checks') == len(RENDER_CASES),
                    'a selected render regression was not run')
            (out/'core-tests.log').write_bytes(suite)
            if program_fixture:
                program=here/'program-slabs'
                run('link-program-slabs',[*cflags,str(program_fixture),*objects,capi,*frameworks,'-o',str(program)])
                log=run('program-slabs',[str(program)])
                require(b'PASS: immutable program slabs' in log,'program BO lifetime fixture did not pass')
                (out/'program-slabs.log').write_bytes(log)
    require(packets['reference']==packets['candidate'], 'submission words differ')
    result = dict(state=trial+'-encoding-byte-equivalence-and-lifetimes-passed', replay_iterations=512,
                  wire_words=len(packets['candidate'])//4,
                  wire_sha256=hashlib.sha256(packets['candidate']).hexdigest(),
                  ownership_cases=len(owner.SCENARIOS), native_sha256=native['binary_sha256'],
                  fixture_sha256=sha(fixture), reference_split_race_reproduced=baseline_workmeter_split,
                  candidate_single_snapshot=True, render_cases=len(RENDER_CASES),
                  sanitizers=['address','undefined'])
    if program_fixture:
        result.update(program_slabs_passed=True,program_fixture_sha256=sha(program_fixture))
    if packet_benchmark:
        samples = {name: [] for name in encoders}
        shapes = set()
        for repeat in range(5):
            for name, binary in encoders.items():
                ns, draws, words = map(int,run(f'bench-{repeat}-{name}', [str(binary),'--packet-benchmark']).split())
                require(ns>0 and draws==30_000 and words>0, 'packet benchmark shape differs')
                samples[name].append(ns/draws)
                shapes.add((draws,words))
        require(len(shapes)==1, 'packet benchmark emitted different streams')
        result['warm_packet_benchmark'] = dict(ns_per_draw=samples, draws=draws, emitted_words=words,
                                                address_and_undefined_sanitizers=True)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    check(BASE,Path(load(P342/'prepared-v3/result.json')['sources']['candidate']))
