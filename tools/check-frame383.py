#!/usr/bin/env python3
"""Run the actual private descriptor helper against allocation and map failures."""

from importlib import import_module
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

scope = import_module('prepare-frame383')

STUBS = """#include <cassert>
#include <cstdint>
constexpr unsigned F382_SLOT_BYTES = 0x9e4000;
constexpr unsigned kIODirectionInOut = 3;
constexpr unsigned kIOMapWriteCombineCache = 8;
static unsigned allocations, live_desc, live_map, failed_step;
static bool fails() { return ++allocations == failed_step; }

struct IOMemoryMap {
    uintptr_t va;
    uintptr_t getVirtualAddress() const { return va; }
    void release() { assert(live_map); --live_map; delete this; }
};

struct IOMemoryDescriptor {
    uint64_t address;
    static IOMemoryDescriptor *withPhysicalAddress(uint64_t pa, unsigned n, unsigned d) {
        assert(n == F382_SLOT_BYTES && d == kIODirectionInOut);
        if (fails()) return nullptr;
        ++live_desc;
        return new IOMemoryDescriptor{pa};
    }
    IOMemoryMap *map(unsigned mode) {
        assert(mode == kIOMapWriteCombineCache);
        if (fails()) return nullptr;
        ++live_map;
        return new IOMemoryMap{0x100000000 + address};
    }
    void release() { assert(live_desc); --live_desc; delete this; }
};

#define OSSafeReleaseNULL(p) do { if (p) { (p)->release(); (p)=nullptr; } } while (0)
"""

FIXTURES = """int main()
{
    constexpr uint32_t first = 0xa8f30000;
    uintptr_t output[2] = {};
    for (unsigned step=1; step<=4; ++step) {
        allocations = 0;
        failed_step = step;
        output[0] = output[1] = 17;
        assert(!sweet_fb383_map(first,F382_SLOT_BYTES,output));
        assert(live_desc == 0 && live_map == 0 && output[0] == 17 && output[1] == 17);
    }
    failed_step = allocations = 0;
    assert(!sweet_fb383_map(first,F382_SLOT_BYTES-1,output));
    assert(allocations == 0);
    assert(sweet_fb383_map(first,F382_SLOT_BYTES,output));
    assert(output[0] == 0x100000000+first && output[1] == output[0]+F382_SLOT_BYTES);
    assert(live_desc == 2 && live_map == 2);
    assert(!sweet_fb383_map(first,F382_SLOT_BYTES,output));
    assert(live_desc == 2 && live_map == 2);
    sweet_fb383_discard();
    assert(live_desc == 0 && live_map == 0);
}
"""


def check():
    scope.baseline()
    native = scope.load(scope.BASE/'native-kernel/build-manifest.json')
    root = Path(native['source'])
    before = (root/'iokit/Kernel/arm/SweetFramebuffer.cpp').read_text()
    source = 'static struct {' + before.split('static struct {\n    IOMemoryDescriptor *memory[2];',1)[1]
    source = source.replace('static struct {','static struct {\n    IOMemoryDescriptor *memory[2];',1)
    source = source.split('extern "C" void\nsweet_fb382_poll(',1)[0]
    with TemporaryDirectory(prefix='gauguin-map383-host-') as tmp:
        cpp = Path(tmp)/'map.cpp'
        runner = Path(tmp)/'check'
        cpp.write_text(STUBS+source+FIXTURES)
        subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined',str(cpp),'-o',str(runner)],check=True,timeout=45)
        subprocess.run([str(runner)],check=True,timeout=10)
    donor = scope.load(scope.P382/'native-kernel/build-manifest.json')
    name = 'iokit/Kernel/arm/SweetFramebuffer.cpp'
    old = (Path(donor['source'])/name).read_text()
    assert before.replace(source,'') == old
    board = (root/'bsd/dev/gauguin_ui_trace_board.c').read_text()
    assert 'ml_io_map_wcomb' not in board and 'sweet_fb383_map' in board
    assert board.split('unsigned sweet_frame382_issue(',1)[1] == (
        Path(donor['source'])/'bsd/dev/gauguin_ui_trace_board.c'
    ).read_text().split('unsigned sweet_frame382_issue(',1)[1]
    assert import_module('check-frame382').check_fixtures()==7
    return dict(state='0383-private-mapping-allocation-and-release-verified',mapping_cases=6,
        patch_sha256=scope.sha(scope.PATCH),device_commands=0)


if __name__=='__main__':
    proof = check()
    scope.save(scope.HOST,proof)
    print('IOKit mapping cases',proof['mapping_cases'])
