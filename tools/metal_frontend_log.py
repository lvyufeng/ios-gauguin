#!/usr/bin/env python3
"""Qualify finite MTL-object receipts, not discovered Metal/CA/presentation.

Caller separately binds signed artifacts, complete old log prefixes, strict
kernel/image identity, physical recovery capture and the 600-second service.
"""
import re
from metal_probe_log import binary_color, fnv, need, records, single
from gpu_service_log import qualify_service_log

P = 'GAUGUIN METAL226 '
FORMATS = (70, 80, 71, 81)

def expected_hashes(seed):
    need(type(seed) is int and 0 <= seed < 2**32, 'invalid seed')
    out = {}
    for i, fmt in enumerate(FORMATS):
        red = 0xffff0000 if i & 1 else 0xff0000ff
        out[f'format-{fmt}-red'] = fnv([red] * 4096, 4)
        half = 0xffbcbcbc if i >= 2 else 0xff808080
        out[f'format-{fmt}-half-linear'] = fnv([half] * 4096, 4)
    for i in range(72):
        out[f'reuse-{i:02d}'] = fnv([binary_color((seed + i) & 7)] * 4096, 4)
    out['surface-GPU-to-CPU'] = fnv([0xffff0000] * 4096, 4)
    for i, suffix in enumerate(('A', 'B')):
        out['surface-CPU-to-GPU-' + suffix] = fnv([
            0xff000000 | ((seed ^ (x * 0x9e3779b1) ^ (i * 0xffffff)) & 0xffffff)
            for x in range(4096)], 4)
    return out

def qualify_frontend_log(stdout, stderr, native, *, build):
    need(re.fullmatch('[0-9a-f]{24}', build) is not None, 'invalid build')
    need(P+'FAIL' not in stdout+'\n'+stderr and P+'ABI rejected' not in stderr, 'probe/ABI failure')
    begin = single(records(stdout, P+'begin ', P+r'begin build=([0-9a-f]{24}) delay=90 scope=root-offscreen-objects-not-CA'), 'begin')
    need(begin[1] == (build,), 'begin identity differs')
    device = single(records(stdout, P+'device=', P+r'device=(.+) seed=(\d+) maxBO=67108864 queueSlots=4'), 'device')
    name, seed = device[1];seed = int(seed)
    need(name == 'Adreno (hakios-metal, chip 0x6010900)' and seed < 2**32, 'device identity differs')
    hashes = expected_hashes(seed)
    memory = records(stdout, P+'memory ', P+r'memory phase=(\S+) active=128 inactive=128 hard=1 footprint=(\d+)')
    need([x[1][0] for x in memory] == ['before-delay','opened','after-resource-release'], 'memory checkpoints differ')
    need(all(0 < int(x[1][1]) <= 128*1024*1024 for x in memory), 'memory budget differs')
    need(begin[0] < memory[0][0] < device[0] < memory[1][0], 'startup order differs')
    pixels = records(stdout, P+'pixels ', P+r'pixels phase=(\S+) words=4096 hash=([0-9a-f]{16}) PASS')
    need([x[1][0] for x in pixels] == list(hashes), '83 distinct pixel phases/order required')
    need(all(digest == hashes[phase] for _, (phase,digest) in pixels), 'independent expected pixel hash differs')
    abandoned = single(records(stdout, P+'abandoned-slots ', P+r'abandoned-slots count=80 PASS'), 'abandoned slots')
    surface = single(records(stdout, P+'surface ', P+r'surface id=(\d+) width=64 height=64 stride=256 format=BGRA cases=3 PASS'), 'surface')
    owner = single(records(stdout, P+'ownership ', P+r'ownership reacquired=1 closed=1 PASS'), 'owner release')
    need(0 < int(surface[1][0]) < 2**32, 'invalid surface ID')
    need(memory[1][0] < pixels[0][0] < pixels[7][0] < abandoned[0] < pixels[8][0] <= pixels[-1][0] <
         surface[0] < memory[2][0] < owner[0], 'resource/phase order differs')
    result = single(records(stdout, P+'RESULT ', P+r'RESULT PASS build=([0-9a-f]{24}) seed=(\d+) jobs=83 words=339968 abandoned=80 teardown-requested=1 discovery=0 shader-pipelines=0 UI=0'), 'result')
    need(result[1] == (build,str(seed)) and owner[0] < result[0], 'result identity/order differs')
    known = {row[0] for rows in ([begin],[device],memory,pixels,[abandoned],[surface],[owner],[result]) for row in rows}
    need({i for i,line in enumerate(stdout.splitlines()) if P in line} == known, 'unknown/interleaved/truncated receipt')
    admitted = single(records(stderr, P+'admitted ', P+r'admitted OS=20H392 methods=12 ivars=2 root-only no-discovery'), 'runtime ABI admission')
    need({i for i,line in enumerate(stderr.splitlines()) if P in line} == {admitted[0]}, 'unexpected runtime admission output')
    refusals = [line for line in stderr.splitlines() if 'refused:' in line]
    need(len(refusals) == 1 and refusals[0].endswith('refused: buffer length 67108865 outside 1..64MiB kernel cap'), 'unexpected GPU operation refusal')
    service = qualify_service_log(native, expected_seconds=600)
    need(service['native_submissions'] == 83, 'expected 83 native completed submissions')
    need('SWEET GPU AUTH: compositor opened ' not in native, 'compositor must not own the diagnostic GPU')
    need('SWEET GPU USER: client closed after fault;' not in native, 'faulted owner teardown')
    return dict(state='qualified226-bounded-MTL-objects-formats-and-IOSurface-only',build=build,seed=seed,
                jobs=83,output_words=339968,abandoned_command_buffers=80,owner_reacquired=True,
                runtime_ABI_gate_passed=True,device_discovery_qualified=False,
                shader_pipelines_qualified=False,desktop_qualified=False,high_refresh_qualified=False,
                hashes=hashes,finite_service=service)
