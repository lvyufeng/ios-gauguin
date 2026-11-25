#!/usr/bin/env python3
"""Exercise actual present/vsync code with the candidate present-stats patch.

The candidate source is used when the applied tree exists; otherwise the
candidate patch is applied to a temporary copy of the actual baseline source.
The baseline itself is only read. Marked instrumentation blocks are removed
from the candidate and must reproduce the baseline byte for byte, then the
actual extracted present/vsync bodies are compiled and run with host surfaces,
GPU read guards, pixel buffers, a virtual mach clock and locks under ASan/UBSan.
"""
from pathlib import Path
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/present_stats_integration_host.cpp'
PATCH = ROOT / 'xnu/patches/0221-gauguin-present-copy-stats.patch'
DEFAULT_BASELINE = (ROOT.parent / 'gauguin-fault297-worktree-20261111' /
                    '.deps-cache/p0-20261105/source297')
FRAMEBUFFER = 'iokit/Kernel/arm/SweetFramebuffer.cpp'
STATS_HEADER = 'iokit/Kernel/arm/SweetPresentStats.h'

# BEGIN/END labels emitted by the candidate. The label is matched exactly on
# the END line, so a block cannot absorb a later marker.
BLOCK = re.compile(
    rb'^[ \t]*/\* BEGIN SWEET PRESENT STATS (?P<label>[A-Z0-9 ]+?) \*/'
    rb'.*?'
    rb'^[ \t]*/\* END SWEET PRESENT STATS (?P=label) \*/[ \t]*\r?\n',
    re.MULTILINE | re.DOTALL,
)
EXPECTED_BLOCKS = [
    'INCLUDE', 'FIELDS', 'INIT', 'START', 'CLEAR', 'RECORD',
    'GUARD START', 'GUARD END', 'COPY START', 'COPY END',
]


def fail(message):
    raise SystemExit(message)


def read_bytes(path):
    try:
        return path.read_bytes()
    except OSError as error:
        fail(f'cannot read {path}: {error}')


def baseline_source_path():
    configured = os.environ.get('PRESENT_REFERENCE')
    tree = Path(configured) if configured else DEFAULT_BASELINE
    if not configured and not tree.is_dir():
        fail(f'actual baseline source tree missing: {tree}; set PRESENT_REFERENCE')
    path = tree / FRAMEBUFFER
    if not path.is_file():
        fail(f'actual baseline SweetFramebuffer.cpp missing: {path}')
    return path


def candidate_tree():
    configured = os.environ.get('XNU_SOURCE')
    return Path(configured) if configured else ROOT / '.deps-cache/p0-20261105/source-present-stats'


def apply_patch_to_baseline(baseline):
    if not PATCH.is_file():
        fail(f'candidate patch missing: {PATCH}')
    patch_tool = shutil.which('patch')
    if patch_tool is None:
        fail('candidate tree is unavailable and the patch utility is not on PATH')
    with tempfile.TemporaryDirectory(prefix='present-stats-patch-') as directory:
        root = Path(directory)
        target = root / FRAMEBUFFER
        target.parent.mkdir(parents=True)
        shutil.copyfile(baseline, target)
        result = subprocess.run(
            [patch_tool, '-p1', '--no-backup-if-mismatch', '-d', str(root)],
            input=PATCH.read_bytes(), capture_output=True,
        )
        if result.returncode != 0:
            fail('candidate patch did not apply to the actual baseline source:\n' +
                 result.stdout.decode(errors='replace') +
                 result.stderr.decode(errors='replace'))
        patched_source = root / FRAMEBUFFER
        patched_header = root / STATS_HEADER
        if not patched_source.is_file() or not patched_header.is_file():
            fail('candidate patch did not produce both SweetFramebuffer.cpp and SweetPresentStats.h')
        return patched_source.read_bytes(), patched_header.read_bytes()


def candidate_bytes(baseline):
    tree = candidate_tree()
    source_path = tree / FRAMEBUFFER
    header_path = tree / STATS_HEADER
    source = source_path.read_bytes() if source_path.is_file() else None
    header = header_path.read_bytes() if header_path.is_file() else None
    if source is not None and header is not None:
        return source, header, f'applied candidate {tree}', [source_path, header_path]
    if 'XNU_SOURCE' in os.environ or (source is None) != (header is None):
        fail(f'incomplete explicit or partially present candidate tree: {tree}')
    patched_source, patched_header = apply_patch_to_baseline(baseline)
    used = []
    if source is None:
        source = patched_source
        used.append('patched framebuffer')
    else:
        used.append(f'candidate framebuffer {source_path}')
    if header is None:
        header = patched_header
        used.append('patched header')
    else:
        used.append(f'candidate header {header_path}')
    if source is None or header is None:
        fail(f'candidate missing in {tree} and patching did not supply it')
    return source, header, 'temporary patch application: ' + ', '.join(used), used_paths(tree)


def used_paths(tree):
    return [tree / FRAMEBUFFER, tree / STATS_HEADER]


def strip_blocks(source):
    stripped, count = BLOCK.subn(b'', source)
    labels = [match.group('label').decode('ascii') for match in BLOCK.finditer(source)]
    if count != len(EXPECTED_BLOCKS) or sorted(labels) != sorted(EXPECTED_BLOCKS):
        fail(f'candidate stats markers changed: removed {count} blocks {labels}; '
             f'expected {EXPECTED_BLOCKS}')
    if b'BEGIN SWEET PRESENT STATS' in stripped or b'END SWEET PRESENT STATS' in stripped:
        fail('candidate has an unpaired SWEET PRESENT STATS marker')
    return stripped, labels


def extract_method(text, signature):
    start = text.find(signature)
    if start < 0:
        fail(f'candidate is missing method signature {signature!r}')
    end = text.find('\n}\n', start)
    if end < 0:
        fail(f'candidate method {signature!r} has no closing brace')
    return text[start:end + 3]


def require_order(text, pairs):
    for first, second in pairs:
        first_at = text.find(first)
        second_at = text.find(second)
        if first_at < 0 or second_at < 0 or first_at >= second_at:
            fail(f'candidate order is wrong: {first!r} must precede {second!r}')


def check_candidate_structure(source_text, baseline_bytes):
    stripped_bytes, _ = strip_blocks(source_text.encode('utf-8'))
    if stripped_bytes != baseline_bytes:
        fail('removing the marked stats blocks does not reproduce the actual baseline '
             'SweetFramebuffer.cpp byte for byte')

    text = source_text
    present_call = 'fb->present(rec, fb->fHoldPresent ? frame.surfaces : NULL);'
    finish = 'if (fb->fHoldPresent) fb->finishHeldFrame(&frame);'
    free = 'else IOFreeData(rec, SWEET_FB_SWAP_REC_SIZE);'
    record_begin = '/* BEGIN SWEET PRESENT STATS RECORD */'
    record_end = '/* END SWEET PRESENT STATS RECORD */'
    require_order(text, [
        (present_call, '/* BEGIN SWEET PRESENT STATS CLEAR */'),
        ('/* BEGIN SWEET PRESENT STATS CLEAR */', finish),
        (finish, free),
        (free, record_begin),
        (record_begin, record_end),
        ('/* BEGIN SWEET PRESENT STATS GUARD START */', 'SweetSurfaceGPURead gpuRead(s);'),
        ('SweetSurfaceGPURead gpuRead(s);', 'if(!gpuRead.valid()){s->release();continue;}'),
        ('/* BEGIN SWEET PRESENT STATS COPY START */', 'for (int32_t y = 0; y < h; y++) {'),
        ('for (int32_t y = 0; y < h; y++) {', '/* BEGIN SWEET PRESENT STATS COPY END */'),
    ])

    for marker in ('/* BEGIN SWEET PRESENT STATS START */',
                   '/* BEGIN SWEET PRESENT STATS CLEAR */',
                   record_begin, record_end):
        if marker not in text:
            fail(f'candidate is missing marker {marker!r}')
    start_at = text.index(record_begin)
    end_at = text.index(record_end)
    record_block = text[start_at:end_at]
    if 'sweet_present_stats_record(&fb->fPresentStats, &sample' not in record_block:
        fail('stats collection is not in the marked record block')
    for forbidden in ('frame', 'surfaces', 'release', 'retain', 'finishHeldFrame'):
        if forbidden in record_block:
            fail(f'record block touches frame ownership token {forbidden!r}')
    if 'IOLockLock(fb->fLock);' not in record_block:
        fail('stats collection is not protected by fLock')

    begin_at = text.index('/* BEGIN SWEET PRESENT STATS START */')
    clear_at = text.index('/* BEGIN SWEET PRESENT STATS CLEAR */')
    start_block = text[begin_at:clear_at]
    if 'fb->fPresentSample = &sample;' not in start_block:
        fail('present stats sample is not installed on the stack')
    clear_block = text[clear_at:text.index(record_begin)]
    if 'fb->fPresentSample = priorSample;' not in clear_block:
        fail('present stats sample is not restored after present')


def check_header(header):
    for token in (b'struct SweetPresentSample', b'struct SweetPresentStats',
                  b'sweet_present_stats_record', b'timingValid'):
        if token not in header:
            fail(f'candidate SweetPresentStats.h is missing {token!r}')
    if b'CPU-side present diagnostics only' not in header:
        fail('candidate SweetPresentStats.h does not state the CPU-only limit')


def run_checked(argv, env, timeout, cwd=None):
    result = subprocess.run(argv, env=env, cwd=cwd, capture_output=True, text=True,
                            timeout=timeout)
    if result.returncode != 0:
        print(f'FAILED ({result.returncode}): {" ".join(argv)}', file=sys.stderr)
        if result.stdout:
            print(result.stdout, end='', file=sys.stderr)
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
        raise SystemExit(result.returncode or 1)
    return result


def main():
    baseline = baseline_source_path()
    baseline_bytes = read_bytes(baseline)
    source_bytes, header_bytes, origin, candidate_paths = candidate_bytes(baseline)
    source_text = source_bytes.decode('utf-8')
    header_text = header_bytes.decode('utf-8')

    check_header(header_bytes)
    check_candidate_structure(source_text, baseline_bytes)

    if not FIXTURE.is_file():
        fail(f'present-stats integration fixture missing: {FIXTURE}')
    fixture = FIXTURE.read_text(encoding='utf-8')
    for marker in ('@STATS_HEADER@', '@GET32@', '@PRESENT_METHOD@', '@VSYNC_METHOD@'):
        if fixture.count(marker) != 1:
            fail(f'fixture must contain exactly one {marker} marker')

    compiler = shutil.which('clang++')
    if compiler is None:
        fail('clang++ not found on PATH')

    unit = fixture
    replacements = {
        '@STATS_HEADER@': header_text,
        '@GET32@': extract_method(source_text, 'static uint32_t\nget32('),
        '@PRESENT_METHOD@': extract_method(source_text, 'void\nAppleCLCD::present('),
        '@VSYNC_METHOD@': extract_method(source_text, 'void\nAppleCLCD::vsyncFired('),
    }
    for marker, replacement in replacements.items():
        unit = unit.replace(marker, replacement)

    watched = [Path(__file__).resolve(), FIXTURE, baseline, PATCH]
    watched.extend(path for path in candidate_paths if path.is_file())
    pins = {path: hashlib.sha256(read_bytes(path)).hexdigest() for path in watched}

    env = dict(os.environ)
    env['ASAN_OPTIONS'] = 'halt_on_error=1:detect_leaks=0'
    env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    with tempfile.TemporaryDirectory(prefix='present-stats-integration-') as directory:
        work = Path(directory)
        cpp = work / 'present_stats_integration_host.cpp'
        exe = work / 'present_stats_integration_host'
        cpp.write_text(unit, encoding='utf-8')
        run_checked([
            compiler, '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
            '-Wno-unused-function', '-Wno-unused-parameter', '-Wno-unused-variable',
            '-pedantic', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
            '-fno-omit-frame-pointer', str(cpp), '-pthread', '-o', str(exe),
        ], env, 180, cwd=work)
        result = run_checked([str(exe)], env, 90, cwd=work)

    if 'PASS present-stats integration' not in result.stdout:
        fail('integration harness did not report PASS')
    if 'not kernel timing' not in result.stdout or 'CPU-side' not in result.stdout:
        fail('integration harness did not state the CPU-only limits')
    for path, digest in pins.items():
        if hashlib.sha256(read_bytes(path)).hexdigest() != digest:
            fail(f'{path} changed during the test; baseline/candidate files must stay untouched')
    print(f'candidate: {origin}')
    print(result.stdout, end='')


if __name__ == '__main__':
    main()
