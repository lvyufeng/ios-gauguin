#!/usr/bin/env python3
"""Check admission through the physical report path and the unchanged scanout guards."""

from importlib import import_module
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

scope = import_module('prepare-frame387')

STUB = r"""
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "gauguin_frame387_preview.h"
#ifndef __unused
#define __unused __attribute__((unused))
#endif
typedef void *thread_call_t;
typedef void *thread_call_param_t;
enum { GUT_ARMED = 1, GUT_CAPTURE = 2 };
static struct { unsigned state; } frames = {GUT_ARMED};
static int trace;
static unsigned display = 1, queued, opens, reports;
static bool pending;
static thread_call_t manual_preview_call;

static uint32_t sweet_fb_display_state(void) { return display; }
static void sweet_frame344_prepare(void) { ++opens; frames.state = GUT_CAPTURE; }
static void thread_call_enter(thread_call_t call)
{
    assert(call == manual_preview_call);
    if (!pending) ++queued;
    pending = true;
}
static uint64_t gut_report(__unused void *core, __unused uint64_t begin, __unused uint64_t end,
                           __unused uint32_t status, __unused uint32_t mask)
{
    ++reports;
    return 0;
}
"""

EXERCISE = r"""
int main(void)
{
    assert(f387_physical_profile(9,0,1,60));
    assert(!f387_physical_profile(8,0,1,60) && !f387_physical_profile(9,4,1,60));
    assert(!f387_physical_profile(9,0,0,60) && !f387_physical_profile(9,0,1,120));
    assert(sweet_ui_trace_report(0,0,0,1) == 0 && queued == 0);
    manual_preview_call = &trace;
    assert(sweet_ui_trace_report(0,0,0,0) == 0 && queued == 0);
    assert(sweet_ui_trace_report(0,0,1,1) == 0 && queued == 0);
    assert(sweet_ui_trace_report(0,0,0,1024) == 0 && queued == 0);
    display = 0;
    assert(sweet_ui_trace_report(0,0,0,1) == 0 && queued == 0);
    display = 1;
    assert(sweet_ui_trace_report(0,0,0,1) == 0 && queued == 1);
    assert(sweet_ui_trace_report(0,0,0,1) == 0 && queued == 1);
    pending = false;
    display = 0;
    start_manual_preview(NULL,NULL);
    assert(opens == 0);
    display = 1;
    assert(sweet_ui_trace_report(0,0,0,1) == 0 && queued == 2);
    pending = false;
    start_manual_preview(NULL,NULL);
    assert(opens == 1 && sweet_ui_trace_report(0,0,0,1) == 0 && queued == 2 && reports == 9);
    return 0;
}
"""


def check():
    scope.baseline()
    previous = scope.P384/'native-kernel'
    candidate = scope.BASE/'native-kernel'
    old,new = (dict((str(path.relative_to(root)),scope.sha(path)) for path in root.rglob('*') if path.is_file())
               for root in (previous/'source',candidate/'source'))
    changed = {path for path,value in new.items() if old.get(path) != value}
    scope.require(old.keys() <= new.keys() and changed ==
        {'bsd/dev/gauguin_ui_trace_board.c','bsd/dev/gauguin_frame387_preview.h',
         'iokit/Kernel/arm/SweetFramebuffer.cpp'}, '0384 sources differ beyond preview admission')
    nvt, = [line for line in (candidate/'candidate.filelist').read_text().splitlines() if line.endswith('/nvt_runtime.o')]
    scope.require(nvt in (previous/'candidate.filelist').read_text().splitlines(), 'physical driver object changed')
    disassembly = subprocess.check_output(['xcrun','llvm-objdump','-d','-r','--disassemble-symbols=_nrt_poll',nvt],
                                          text=True,timeout=30)
    scope.require(disassembly.rindex('_sweet_ui_trace_report') < disassembly.index('_sweet_hid_touch_frame_traced'),
                  'physical polling does not report before HID dispatch')
    dev = candidate/'source/bsd/dev'
    board = (dev/'gauguin_ui_trace_board.c').read_text()
    worker = board[board.index('static void start_manual_preview('):board.index('static void frame_init(void)')]
    report = board[board.index('uint64_t sweet_ui_trace_report('):board.index('void sweet_ui_trace_record(')]
    with TemporaryDirectory(prefix='frame387-') as directory:
        root = Path(directory)
        (root/'test.c').write_text(STUB+worker+report+EXERCISE)
        subprocess.run(['xcrun','clang','-std=c17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
            '-I',str(dev),str(root/'test.c'),'-o',str(root/'test')],check=True,timeout=60)
        subprocess.run([str(root/'test')],check=True,timeout=15)
    return dict(test_passed=True, physical_driver_reference=nvt, input_pins={nvt:scope.sha(nvt)},
        physical_reports_replayed=9, on_screen_preview_starts=1, device_commands=0)


if __name__ == '__main__':
    result = check()
    scope.save(scope.BASE/'manual-host-proof.json',result)
    print(result)
