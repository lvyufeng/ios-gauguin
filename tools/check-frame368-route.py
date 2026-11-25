#!/usr/bin/env python3
"""Exercise the actual route sampler and its production log decoder."""

from importlib import import_module
import json
import subprocess

from frame367_route import PREFIX, decode, require

scope = import_module('prepare-frame368')

STUB = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { F344_PAGE = 0x4000 };
typedef uintptr_t vm_offset_t;
enum { VM_PROT_READ = 1 };
static uint32_t mdp[F344_PAGE/4], regs[3][F344_PAGE/4];
static const volatile uint32_t *scan_mdp = mdp;
static const vm_offset_t physical[] = {0x0ae04000,0x0ae24000,0x0ae28000};
static unsigned mapped, invalid_map = 3, position_calls;
static uint32_t scan_frame;
static bool open_window = true, cross, pause_inside_read;
static struct { bool configured; } scan = {true};
struct scan351_position { uint64_t tick; uint32_t frame, line, end; };
typedef struct { uint64_t v_baseAddr, v_width, v_height, v_rowBytes; } PE_Video;

static vm_offset_t ml_io_map_with_prot(vm_offset_t pa, size_t size, unsigned protection)
{
    assert(size==F344_PAGE && protection==VM_PROT_READ && mapped<3 && pa==physical[mapped]);
    unsigned i = mapped++;
    return i==invalid_map ? 0 : (uintptr_t)regs[i];
}

static vm_offset_t ml_vtophys(vm_offset_t va)
{
    for (unsigned i = 0; i < 3; ++i) {
        uintptr_t begin = (uintptr_t)regs[i];
        if (va>=begin && va<begin+F344_PAGE) return physical[i]+va-begin;
    }
    abort();
}

static int PE_current_console(PE_Video *video)
{
    *video=(PE_Video){0xa0000000,1080,2400,4320};
    return 0;
}

static bool sweet_frame351_window(void) { return open_window; }
static bool scan351_position(struct scan351_position *pos)
{
    const bool second = (++position_calls % 2)==0;
    *pos=(struct scan351_position){position_calls*UINT64_C(10000) +
        (second && pause_inside_read ? UINT64_C(2000000) : 0),
        scan_frame + (second && cross), 5 + second, 4878};
    return true;
}
static void absolutetime_to_nanoseconds(uint64_t tick, uint64_t *ns) { *ns=tick; }
'''

DRIVER = r'''
static void set_route(void)
{
    uint32_t *ctl = mdp+0x2400/4;
    uint32_t *pipe = regs[1]+0x1000/4;
    ctl[0]=1u<<18;
    ctl[0xf4/4]=2;
    pipe[0]=pipe[0xc/4]=(2400u<<16)|1080u;
    pipe[0x14/4]=0xa0000000;
    pipe[0x24/4]=4320;
    pipe[0x30/4]=3u<<9;
}

static void tick(uint32_t frame)
{
    scan_frame=frame;
    scan367_poll(frame);
}

int main(int argc, char **argv)
{
    assert(argc==2);
    set_route();
    uint32_t test = (uint32_t)atoi(argv[1]);
    open_window = false;
    tick(9);
    assert(mapped==0);
    open_window = true;
    if (test==1) invalid_map=1;
    if (test==2) cross=true;
    if (test==3) pause_inside_read=true;
    tick(UINT32_MAX-1);
    tick(UINT32_MAX-1);
    if (test==1) {
        assert(mapped==2 && scan367.done);
    } else {
        assert(scan367.attempts==1);
        if (test==4) {
            regs[1][(0x1000+0x30)/4] |= 1u<<19;
            tick(UINT32_MAX);
            assert(scan367.samples==1 && scan367.first_frame==UINT32_MAX);
            regs[1][(0x1000+0x30)/4] &= ~(1u<<19);
        }
        tick(0);
        tick(1);
        tick(2);
        for (uint32_t i=3;i<11;++i) tick(i);
        assert(scan367.done && mapped==3);
        assert(scan367.attempts<=8);
        if (test==2 || test==3) assert(scan367.attempts==8 && scan367.samples==0);
        else assert(scan367.samples==3 && scan367.attempts==(test==4 ? 5 : 3));
    }
    return 0;
}
'''


def main():
    source = (scope.BASE/'native-kernel/source'/scope.SOURCE).read_text()
    require("ml_io_unmap" not in source,"a permanent MMIO map must survive the temporary boot")
    begin = source.index('enum { F367_CONTROLS')
    end = source.index('static void scan_report',begin)
    out = scope.BASE/'frame-host'
    out.mkdir()
    model, exe = out/'route-model.c', out/'route-model'
    model.write_text(STUB+source[begin:end]+DRIVER)
    subprocess.run(['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror',
        '-fsanitize=address,undefined',str(model),'-o',str(exe)],check=True,timeout=60)
    lines = [subprocess.check_output([str(exe),str(i)],text=True,timeout=15) for i in range(5)]
    results = [decode(s) for s in lines]
    require(results[0]['route']['pipe']==results[4]['route']['pipe']=='DMA0' and
        results[0]['route']['control_index']==results[4]['route']['control_index']==2 and
        [r['snapshot_status'] for r in results]==['stable','map-failed','unstable','unstable','stable'],
        'route model results differ')

    sample = lines[0]
    records = sample.splitlines()
    fb = next(line for line in records if line.startswith(PREFIX+'FB: '))
    for bad in (sample+fb+'\n',sample.replace(fb+'\n',''),sample.replace('samples=3','samples=2'),
                sample.replace('width=1080','width=1081'),sample.replace('attempts=3','attempts=9'),
                '\n'.join(record for record in records if not record.startswith(PREFIX+'SSPP: index=2'))):
        try:
            decode(bad)
        except ValueError:
            continue
        raise ValueError('decoder accepted a malformed route capture')
    stages = next(line for line in records if line.startswith(PREFIX+'CTL: index=2 '))
    altered = sample.replace(stages,stages.replace('00040000','00040001'))
    require(decode(altered)['mismatch']=='source-not-uniquely-staged','mixed pipe route qualified')
    report = dict(state='0368-permanent-route-mapping-native-model-passed',boot_lifetime_readonly_mapping=True,native_sample_cases=5,decoder_cases=7,
        patch_sha256=scope.sha(scope.PATCH),source_sha256=scope.sha(scope.BASE/'native-kernel/source'/scope.SOURCE),
        input_pins={str(model):scope.sha(model),str(exe):scope.sha(exe)},device_mutations=0)
    scope.save(out/'result.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
