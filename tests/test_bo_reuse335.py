#!/usr/bin/env python3
"""Exercise the actual full IOUserClient cache with typed board/allocator seams."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess

WORK = Path(__file__).resolve().parents[1]
BASE = WORK / 'research/tmp/bo-reuse-335'
PARENT = Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    assert out.is_relative_to(BASE) and not out.exists()
    source = BASE / 'kernel-source'
    paths = [Path(__file__).resolve(), WORK / 'tests/fixtures/gpu-user/iokit_host.cpp',
             WORK / 'tests/fixtures/bo_reuse335_main.inc', BASE / 'source-preparation.json']
    paths += [p for p in source.rglob('*') if p.is_file()]
    manifest = json.loads((PARENT / 'local-link/build-manifest.json').read_text())
    surface = source / 'iokit/Kernel/arm/SweetSurface.cpp'
    if not surface.is_file():
        surface = Path(manifest['source_union']['base']) / 'iokit/Kernel/arm/SweetSurface.cpp'
    paths.append(surface)
    pins = {str(p): sha(p) for p in paths}
    fixture = (WORK / 'tests/fixtures/gpu-user/iokit_host.cpp').read_text()
    fixture = fixture[:fixture.index('int main(int argc,char **argv)')]
    fixture = '#include <atomic>\n#include <thread>\n' + fixture
    fixture = fixture.replace('static unsigned checks;', 'static std::atomic<unsigned> checks;')
    fixture = fixture.replace('static uint64_t ticks;return ++ticks;', 'static std::atomic<uint64_t> ticks;return ++ticks;')
    fixture = fixture.replace('    void retain(){++refs;}', '    unsigned getRetainCount() const{return refs;}\n    void retain(){++refs;}')
    fixture = fixture.replace('static unsigned allocations,frees,cache_calls,sync_calls,submit_calls;',
        'static unsigned allocations,frees,cache_calls,sync_calls,submit_calls;\nstatic unsigned fail_allocations;')
    marker = '        auto m=new IOBufferMemoryDescriptor;m->size=size;'
    assert fixture.count(marker) == 1
    fixture = fixture.replace(marker, '        if(fail_allocations){--fail_allocations;return nullptr;}\n' + marker)
    marker = 'extern "C" void sweet_ui_trace_record(uint32_t,uint64_t,uint32_t,uint32_t,uint64_t,uint64_t,uint64_t){}'
    assert fixture.count(marker) == 1
    fixture = fixture.replace(marker, '''static uint64_t current_thread(){return 1234;}
static uint64_t thread_tid(uint64_t value){return value;}
extern "C" bool sweet_gpu_runtime_pending_metadata(uint32_t){return false;}
extern "C" void sweet_ui_trace_record(uint32_t,uint64_t,uint32_t,uint32_t,uint64_t,uint64_t,uint64_t){}
''')
    fixture = fixture.replace('extern "C" enum ggr_error sweet_gpu_runtime_issue',
        'static enum ggr_error host_poll_result=GGR_OK;\nstatic uint32_t host_issued;\nextern "C" enum ggr_error sweet_gpu_runtime_issue', 1)
    fixture = fixture.replace('const uint32_t *,uint32_t,uint32_t *)\n{return GGR_UNAVAILABLE;}',
        'const uint32_t *,uint32_t,uint32_t *fence)\n{++submit_calls;*fence=++host_issued;return GGR_OK;}')
    fixture = fixture.replace('extern "C" enum ggr_error sweet_gpu_runtime_poll(uint32_t){return GGR_UNAVAILABLE;}',
        'extern "C" enum ggr_error sweet_gpu_runtime_poll(uint32_t fence){assert(fence==host_issued);return host_poll_result;}')
    strip = lambda p: re.sub(r'^#include .*\n', '', p.read_text(), flags=re.M)
    fixture = fixture.replace('@SURFACE_HEADER@', strip(source / 'iokit/Kernel/arm/SweetSurface.h'))
    methods = re.findall(r'uintptr_t\nSweetSurface::kernelAddress\(\)\n\{[\s\S]*?\n\}', surface.read_text())
    assert len(methods) == 1
    fixture = fixture.replace('@SURFACE_KERNEL_ADDRESS@', methods[0])
    extra = strip(source / 'iokit/Kernel/arm/SweetMetalBootstrap.h') + '''
static bool cache335_host_async;
static bool PE_parse_boot_argn(const char *name,void *out,int bytes){
    if(cache335_host_async&&!strcmp(name,"sweetgpuasync")&&bytes==4){*(uint32_t *)out=1;return true;}
    return false;
}
static bool sweet_metal_desktop_enabled(){return false;}
'''
    actual = strip(source / 'iokit/Kernel/arm/GauguinGPU.cpp')
    actual = actual.replace('class GauguinGPUUserClient : public IOUserClient {',
        'class GauguinGPUUserClient : public IOUserClient {\n    friend struct BC335Host;')
    fixture = fixture.replace('@SOURCE@', extra + actual)
    fixture += (WORK / 'tests/fixtures/bo_reuse335_main.inc').read_text()
    fixture = fixture.replace('__asm__ volatile("dsb sy" ::: "memory")', '__atomic_thread_fence(__ATOMIC_SEQ_CST)')
    assert '@SOURCE@' not in fixture
    out.mkdir()
    unit = out / 'actual-cache.cpp'
    unit.write_text(fixture)
    flags = ['-O1', '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
             '-fno-omit-frame-pointer', '-I' + str(source / 'bsd/dev')]
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1')
    steps = []
    result = dict(state='BC335-host-running', input_pins=pins, steps=steps, device_commands=0)
    def run(argv, label, timeout=120):
        with (out / (label + '.log')).open('x') as log:
            proc = subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        steps.append(dict(label=label, exit=proc.returncode, argv=argv))
        assert proc.returncode == 0, (label, proc.returncode)
    try:
        run(['clang', '-std=c11', *flags, '-c', str(source / 'bsd/dev/gauguin_gpu_runtime.c'), '-o', str(out / 'runtime.o')], 'compile-runtime')
        run(['clang++', '-std=c++17', *flags, '-DGAUGUIN_GPU_REQUEST_LOCKS=2', '-DGAUGUIN_GPU_PILOT_HOST=1',
             str(unit), str(out / 'runtime.o'), '-o', str(out / 'cache')], 'compile-cache')
        names = ['basic', 'flags', 'aliases', 'pending', 'fault', 'caps', 'quota', 'pressure', 'oom', 'wrap', 'evict-fault', 'surface', 'concurrent']
        for name in names:
            run([str(out / 'cache'), name], name)
            assert 'PASS ' + name + ':' in (out / (name + '.log')).read_text()
        result.update(state='BC335-actual-completed-owned-cache-host-passed', scenarios=names,
                      exported_alias_exclusion=True, pending_and_fault_escrow_retained=True,
                      fresh_handle_and_zeroing_verified=True, exact_size_and_flags_verified=True,
                      byte_slot_and_residency_caps_verified=True, zero_hit_PTE_sync_allocations_verified=True,
                      allocator_retry_bound_verified=True, sanitizer='ASan+UBSan')
    except BaseException as error:
        result.update(state='BC335-host-failed', error=repr(error))
        raise
    finally:
        result['inputs_unchanged'] = all(sha(p) == digest for p, digest in pins.items())
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    assert result['inputs_unchanged']
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
