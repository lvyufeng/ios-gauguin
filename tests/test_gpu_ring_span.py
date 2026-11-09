#!/usr/bin/env python3
"""Exercise the actual runtime plus the actual board CPU-only span callback."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source204-codex'))
DEV = SOURCE / 'bsd/dev'
BASE = ROOT / 'tests/fixtures/gpu-user/runtime_host.c'
EXTRA = ROOT / 'tests/fixtures/gpu-user/ring_span_host.c'

BOARD = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "gauguin_gpu_runtime.h"
typedef uintptr_t vm_offset_t;
enum { GGP_RING,GMB_PAGE=16384,GMB_READY=2 };
static uint32_t ring[8192],wanted[GGR_RING_PACKET_WORDS];
static vm_offset_t gmb_ram;
static struct {struct {uint32_t offset;} region[1];} ggb_plan;
static struct ggr_context ggrb_context;
static uint64_t ggrb_end,now;
static unsigned state,loads,stores,poison_after;
static struct {uint32_t op,off,value;bool ok;} note;
static unsigned sweet_gmu_board_state(void){return state;}
static uint64_t ggrb_ns(void *cookie){assert(!cookie);return now+=100;}
static uint64_t mach_absolute_time(void){return now;}
static bool ggrb_note(uint32_t op,uint32_t space,uint32_t off,uint32_t value,bool ok){
    assert(!space);note.op=op;note.off=off;note.value=value;note.ok=ok;return ok;
}
static uint32_t gfw_load32(vm_offset_t address){
    assert(address>=(uintptr_t)ring&&address<=(uintptr_t)(ring+8191)&&!(address&3));
    ++loads;return *(uint32_t *)address;
}
static void gfw_store32(vm_offset_t address,uint32_t value){
    assert(address>=(uintptr_t)ring&&address<=(uintptr_t)(ring+8191)&&!(address&3));
    ++stores;*(uint32_t *)address=value;if(stores==poison_after)state=0;
}
@CALLBACK@
static void setup(void){
    for(unsigned i=0;i<8192;i++)ring[i]=0xa5a5a5a5;
    for(unsigned i=0;i<GGR_RING_PACKET_WORDS;i++)wanted[i]=0x13570000+i;
    ggb_plan.region[0].offset=GMB_PAGE;gmb_ram=(uintptr_t)ring;
    ggrb_context.state=GGR_BUSY;ggrb_context.operation_end_ns=2000000000;
    ggrb_end=UINT64_MAX;now=loads=stores=poison_after=0;state=GMB_READY;
    memset(&note,0,sizeof(note));
}
int main(void){
    setup();assert(ggrb_ring_span(NULL,32764,wanted,GGR_RING_PACKET_WORDS,false));
    assert(stores==GGR_RING_PACKET_WORDS&&!loads&&note.op==7&&note.ok);
    for(unsigned i=0;i<GGR_RING_PACKET_WORDS;i++)assert(ring[(8191+i)%8192]==wanted[i]);
    assert(ring[GGR_RING_PACKET_WORDS-1]==0xa5a5a5a5);
    assert(ggrb_ring_span(NULL,32764,wanted,GGR_RING_PACKET_WORDS,true));
    assert(loads==GGR_RING_PACKET_WORDS&&note.op==8&&note.ok);
    ring[0]^=1;loads=0;
    assert(!ggrb_ring_span(NULL,32764,wanted,GGR_RING_PACKET_WORDS,true));
    assert(loads==2&&note.off==0&&note.value==ring[0]&&!note.ok);
    for(unsigned which=0;which<7;which++){
        setup();const uint32_t *p=wanted;uint32_t off=0,count=1;
        switch(which){case 0:p=NULL;break;case 1:count=0;break;
        case 2:count=GGR_RING_PACKET_WORDS+1;break;case 3:off=1;break;
        case 4:off=32768;break;case 5:gmb_ram=0;break;case 6:ggrb_context.state=GGR_READY;break;}
        assert(!ggrb_ring_span(NULL,off,p,count,false));assert(!stores&&!loads);
    }
    setup();ggrb_context.operation_end_ns=250;
    assert(!ggrb_ring_span(NULL,0,wanted,10,false));assert(stores==2&&note.off==8);
    setup();ggrb_end=250;
    assert(!ggrb_ring_span(NULL,0,wanted,10,false));assert(stores==2&&note.off==8);
    setup();poison_after=2;
    assert(!ggrb_ring_span(NULL,0,wanted,10,false));assert(stores==2&&note.off==8);
    puts("Board span: actual callback bounds/wrap/readback/deadline/authority retention checks passed; CPU RAM only");
}
'''


def main():
    inputs = [Path(__file__), BASE, EXTRA, DEV / 'gauguin_gpu_runtime.c',
              DEV / 'gauguin_gpu_runtime.h', DEV / 'gauguin_gmu_board.c']
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    runtime = BASE.read_text().replace('int main(void)', 'static int baseline_main(void)', 1) + EXTRA.read_text()
    source = (DEV / 'gauguin_gmu_board.c').read_text()
    start = source.index('static bool ggrb_ring_span(')
    callback = source[start:source.index('\n}\n', start) + 3]
    board = BOARD.replace('@CALLBACK@', callback)
    with tempfile.TemporaryDirectory(prefix='gpu-ring-span-') as directory:
        directory = Path(directory)
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for name, body, core in [('runtime', runtime, True), ('board', board, False)]:
            unit = directory / (name + '.c')
            unit.write_text(body)
            binary = directory / name
            command = ['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                       '-O1', '-g', '-fsanitize=address,undefined',
                       '-fno-omit-frame-pointer', '-I' + str(DEV)]
            if core:
                command += [str(DEV / 'gauguin_gpu_runtime.c')]
            subprocess.run(command + [str(unit), '-o', str(binary)], env=env, check=True)
            subprocess.run([str(binary)], env=env, check=True, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
