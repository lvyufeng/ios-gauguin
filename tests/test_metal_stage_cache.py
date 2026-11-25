#!/usr/bin/env python3
"""Exercise extracted actual cache I/O and both original/patched lock scopes."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys

WORK = Path(__file__).resolve().parents[1]
MAIN = Path('/Users/baai/Project/ios-gauguin')
sys.path.insert(0, str(WORK/'tools'))
from stage_cache_patch import instrument


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    out = ap.parse_args().out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    old = MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112/research/tmp/metal-ownership-v1/implementation-20261112'
    receipt = json.loads((old/'native-03/result.json').read_text())
    source = Path(receipt['source'])
    compiler = source/'src/compiler.cpp'
    assert sha(compiler) == 'd17dcb7ad4d064b3a5bc99d367e47ac88f69e2b005b97a12c471f6ef9b3d8333'
    captured = MAIN/'research/tmp/gauguin-fault-cache-worktree-20261115/research/tmp/fault-cache-322/cache-readback'
    cache = json.loads((captured/'result.json').read_text())
    for name, row in cache['files'].items():
        assert sha(captured/name) == row['sha256']
    assert cache['count'] == 245 and cache['device_writes'] == cache['device_boots'] == 0
    original = compiler.read_text()
    patched = instrument(original)
    fixture = WORK/'tests/fixtures/metal_stage_cache_host.cpp'
    out.mkdir(parents=True)
    results = {}
    for variant, raw in [('baseline', original), ('candidate', patched)]:
        first = raw.index('struct CacheWriter {')
        last = raw.index('}  // namespace\n\nstd::unique_ptr<CompiledStage> compileStage(const void* bitcode', first)
        cache_source = raw[first:last]
        first = raw.index('std::unique_ptr<CompiledStage> compileStage(const void* bitcode, size_t size, std::string* why, const FunctionConstants& constants, uint32_t iboBase,')
        last = raw.index('\n\n\n\nnamespace {', first)
        function = raw[first:last]
        cpp = out/(variant+'.cpp')
        cpp.write_text(fixture.read_text().replace('// EXTRACT_CACHE', cache_source).replace('// EXTRACT_COMPILE', function))
        binary = out/variant
        argv = ['xcrun', '--sdk', 'macosx', 'clang++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-pthread',
                '-DHAKIOS_METAL_TARGET_A619', '-DHAKIOS_METAL_CACHE_BUILD="8a71fe61aded108fa9ba5a22"',
                '-DSC323_PATCHED='+str(int(variant == 'candidate')),
                '-I'+str(source/'include'), '-I'+str(WORK/'graphics/gauguin-stage-cache'), str(cpp), '-o', str(binary)]
        with (out/(variant+'-build.log')).open('x') as log:
            p = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT)
        assert p.returncode == 0, variant+'-build.log'
        # Apple ASan does not implement LeakSanitizer; address and UB checks stay enabled.
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1')
        with (out/(variant+'.stdout')).open('x') as log, (out/(variant+'.stderr')).open('x') as err:
            p = subprocess.run([str(binary), str(captured), str(out/(variant+'-files'))], stdout=log, stderr=err, env=env, timeout=90)
        assert p.returncode == 0, variant+'.stderr'
        results[variant] = json.loads((out/(variant+'.stdout')).read_text())
        rows = (out/(variant+'.stderr')).read_text().splitlines()
        if variant == 'candidate':
            assert len(rows) == 1025 and rows.count('GAUGUIN SC323: limit=1 max=1024') == 1
            assert max(map(len, rows)) < 640
        else:
            assert not rows
    result = dict(state='SC323-actual-cache-and-concurrency-host-passed', results=results,
        source_sha256=sha(compiler), patch_sha256=sha(WORK/'tools/stage_cache_patch.py'),
        fixture_sha256=sha(fixture), header_sha256=sha(WORK/'graphics/gauguin-stage-cache/GauguinStageCacheTrace.hpp'),
        captured_manifest_sha256=sha(captured/'result.json'), sanitizer='ASan+UBSan',
        baseline_blocked_and_candidate_completed_with_compiler_lock_held=True,
        real_GPU_or_shader_compilation=False, device_commands=0)
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
