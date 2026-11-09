#!/usr/bin/env python3
"""Validate finite 0223 offscreen probe receipts and native GPU handoff.

The caller must separately verify installed binaries, current-boot identity,
complete old log prefixes, the finite service and strict kernel banner. These
checks do not establish a discovered MTLDevice, a correct desktop or frame rate.
"""
import re

PREFIX = 'GAUGUIN METAL223 '
PHASES = ('clear-A', 'clear-B', 'compute', 'triangle', 'texture-A',
          'texture-B', 'additive', 'premultiplied-half')
GPU_SUBMIT = 'SWEET GPU USER: submit '
GPU_OPEN = 'SWEET GPU AUTH: compositor opened '
GPU_PROXY = 'SWEET GPU AUTH: recorded launchd compositor proxy '


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def records(text, prefix, pattern):
    result = []
    for at, line in enumerate(text.splitlines()):
        if prefix in line:
            match = re.fullmatch(pattern, line) if line.startswith(prefix) else None
            need(match is not None, 'malformed/interleaved ' + prefix)
            result.append((at, match.groups()))
    return result


def single(rows, label):
    need(len(rows) == 1, 'missing/duplicate ' + label)
    return rows[0]


def fnv(words, size):
    value = 14695981039346656037
    for word in words:
        for byte in word.to_bytes(size, 'little'):
            value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return '%016x' % value


def binary_color(bits):
    return (255 if bits & 1 else 0) | (65280 if bits & 2 else 0) | (
        16711680 if bits & 4 else 0) | 0xff000000


def expected_hashes(seed):
    need(type(seed) is int and 0 <= seed < 2**32, 'invalid probe seed')
    triangle = []
    # Independent doubled-screen-coordinate edge functions. All three edges
    # must have the same positive orientation; no sample lies on the diagonal.
    vertices = ((0, 0), (128, 0), (0, 126))
    for y in range(64):
        for x in range(64):
            px, py = 2*x+1, 2*y+1
            inside = all((bx-ax)*(py-ay) - (by-ay)*(px-ax) > 0
                         for (ax, ay), (bx, by) in zip(vertices, vertices[1:]+vertices[:1]))
            triangle.append(0xff0000ff if inside else 0xffff0000)
    out = {
        'clear-A': fnv([binary_color(seed & 7)] * 4096, 4),
        'clear-B': fnv([binary_color((seed & 7) ^ 7)] * 4096, 4),
        'compute': fnv([((i*0x9e3779b1)+seed) & 0xffffffff for i in range(256)], 4),
        'triangle': fnv(triangle, 4),
        'additive': fnv([0xff00ffff] * 4096, 4),
        'premultiplied-half': fnv([0x3c00000038003800] * 4096, 8),
    }
    for label, current in [('texture-A', seed), ('texture-B', seed ^ 8)]:
        out[label] = fnv([binary_color((current & 7) ^ (
            7 if ((x//8+y//8+(current >> 3)) & 1) else 0))
            for y in range(64) for x in range(64)], 4)
    return out


def qualify_probe_log(stdout, stderr, native, *, build, core):
    need(re.fullmatch(r'[0-9a-f]{24}', build) is not None and
         re.fullmatch(r'[0-9a-f]{64}', core) is not None, 'invalid expected build/core')
    need('GAUGUIN METAL223 FAIL' not in stdout + '\n' + stderr,
         'probe reports failure')
    need(PREFIX not in stderr, 'probe receipts on unexpected stderr stream')
    begin = single(records(stdout, PREFIX+'begin ',
        PREFIX+r'begin build=([0-9a-f]{24}) core=([0-9a-f]{64}) scope=offscreen-core-not-MTLDevice'), 'begin')
    need(begin[1] == (build, core), 'probe build/core mismatch')
    ident = single(records(stdout, PREFIX+'identity ',
        PREFIX+r'identity gpu=619 chip=06010900 gmem=524288 base=100000 seed=(\d+)'), 'identity')
    seed = int(ident[1][0]);need(seed < 2**32, 'seed overflow')
    hashes = expected_hashes(seed)
    memory = records(stdout, PREFIX+'memory ', PREFIX+r'memory phase=(\S+) active_mb=(\d+) inactive_mb=(\d+) active_attr=(\d+) inactive_attr=(\d+) footprint=(\d+)')
    need([r[1][0] for r in memory] == ['before-delay', 'compiled', 'completed'], 'memory checkpoint set/order differs')
    for _, (_, active, inactive, aa, ia, footprint) in memory:
        need((active, inactive, aa, ia) == ('128', '128', '1', '1') and
             0 < int(footprint) <= 128*1024*1024, 'effective hard memory policy differs')
    submits = records(stdout, PREFIX+'submit ', PREFIX+r'submit phase=(\S+)')
    completed = records(stdout, PREFIX+'completed ', PREFIX+r'completed phase=(\S+) gpu_ns=(-?\d+) fences=(\d+)')
    pixels = records(stdout, PREFIX+'pixels ', PREFIX+r'pixels phase=(\S+) compared=(\d+) hash=([0-9a-f]{16}) PASS')
    for rows in (submits, completed, pixels):
        need(tuple(r[1][0] for r in rows) == PHASES, 'job/phase set or order differs')
    last = memory[1][0]
    need(begin[0] < memory[0][0] < ident[0] < memory[1][0], 'startup checkpoint order differs')
    output_words = 0
    for i, phase in enumerate(PHASES):
        sa, _ = submits[i];ca, (_, ns, count) = completed[i];pa, (_, count_pixels, digest) = pixels[i]
        need(last < sa < ca < pa, 'submission/completion/readback order differs')
        need(int(count) == i+1 and -1 <= int(ns) < 120*10**9, 'completion count/time differs')
        count_pixels = int(count_pixels)
        need(count_pixels == (256 if phase == 'compute' else 4096) and
             digest == hashes[phase], 'output word count or CPU-expected hash differs: '+phase)
        last = pa;output_words += count_pixels
    fences = records(stdout, PREFIX+'fence ', PREFIX+r'fence queue=(\d+) value=(\d+) complete=1')
    receipts = [(int(q), int(f)) for _, (q, f) in fences]
    need(len(receipts) == 8 and len(set(receipts)) == 8 and
         len({q for q, _ in receipts}) == 1 and
         [f for _, f in receipts] == list(range(1, 9)) and
         all(q < 2**32 for q, _ in receipts), 'eight queue/fence receipts differ')
    need(last < fences[0][0] <= fences[-1][0] < memory[2][0], 'fence/memory checkpoint order differs')
    result = single(records(stdout, PREFIX+'RESULT ', PREFIX+r'RESULT PASS build=([0-9a-f]{24}) seed=(\d+) connection-teardown-requested=1 stages=8'), 'result')
    need(result[1] == (build, str(seed)) and memory[2][0] < result[0], 'result identity/order differs')
    # Every probe-prefixed line must be accounted for, including truncated or
    # unknown lines that an individual regex could otherwise silently ignore.
    known = {r[0] for rows in ([begin], [ident], memory, submits, completed, pixels, fences, [result]) for r in rows}
    need({i for i, line in enumerate(stdout.splitlines()) if PREFIX in line} == known,
         'unknown/truncated/interleaved probe record')

    native_submits = records(native, GPU_SUBMIT,
        GPU_SUBMIT+r'rc=(\d+) ibs=(\d+) submitted=(\d+) completed=(\d+) shadow=(\d+) polls=(\d+)')
    need(len(native_submits) >= 8, 'eight native completions missing')
    for i, (_, fields) in enumerate(native_submits[:8]):
        rc, ibs, submitted, done, shadow, polls = map(int, fields)
        need(rc == 0 and 1 <= ibs <= 128 and submitted == done == i+1 and
             0 <= shadow < 8192 and shadow % 4 == 0 and polls > 0,
             'native initial submission did not complete')
    opened = records(native, GPU_OPEN, GPU_OPEN+r'pid=(\d+) root_fence=(\d+)')
    proxies = records(native, GPU_PROXY, GPU_PROXY+r'pid=(\d+)')
    need(opened, 'no compositor owner handoff')
    for at, (pid, fence) in opened:
        need(int(pid) > 0 and int(fence) == 8 and at > native_submits[7][0] and
             any(pat < at and ppid == (pid,) for pat, ppid in proxies),
             'compositor opened without the expected clean eight-fence root release')
    fault = native.find('SWEET GPU USER: client closed after fault;')
    if fault >= 0:
        stop = native.find('SWEET GPU SERVICE: test deadline reached;')
        need(stop >= 0 and fault > stop, 'faulted client before planned stop')
    return dict(state='qualified223-offscreen-readback-and-native-owner-handoff',
                build=build, core=core, seed=seed, phases=list(PHASES),
                output_words=output_words, completed_root_fences=8,
                compositor_opens=len(opened), hashes=hashes,
                MTLDevice_qualified=False, desktop_qualified=False,
                high_refresh_qualified=False)
