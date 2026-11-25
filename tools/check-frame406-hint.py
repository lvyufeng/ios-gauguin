#!/usr/bin/env python3
"""Exercise a raw completion hint that queues the existing guarded probe."""

from difflib import unified_diff
from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

previous = import_module('check-frame405')
P405 = MAIN/'research/tmp/gauguin-frame405-eop-deadline-worktree-20261124/research/tmp/frame-405'
CONTROL = P405/'native-kernel/build-manifest.json'
ADMISSION = P405/'hint-development-admission.json'
BASE = WORK/'research/tmp/frame-406'
PATCH = BASE/'406-raw-completion-guard-wake.patch'
HINT = WORK/'graphics/gauguin-program-io/CompletionHint406.h'
TEST = WORK/'tests/fixtures/frame406_completion_hint.c'
PROBE = Path('bsd/dev/gauguin_probe358.h')
FB = Path('iokit/Kernel/arm/SweetFramebuffer.cpp')
FRAME = Path('bsd/dev/gauguin_frame344.h')
SCAN = previous.SCAN
replace = previous.replace


def probe_unit(unit):
    unit = replace(unit,'    bool retried;','    bool retried, raw_eop;')
    unit = replace(unit,'    uint32_t sent;','    uint32_t sent, last_raw_fence;')
    site = '    slot->request.retried = same;'
    unit = replace(unit,site,site+'\n    slot->request.raw_eop = false;')
    site = '    if (!request->ticket || request->retried || slot->request.retried ||'
    return replace(unit,site,'    if (!request->ticket || request->raw_eop || request->retried || slot->request.retried ||')


def framebuffer_unit(unit):
    site = '#include "../../../bsd/dev/gauguin_probe358.h"'
    unit = replace(unit,site,site+'\n#include "../../../bsd/dev/gauguin_completion_hint406.h"')
    start = unit.index('extern "C" void\nsweet_fb358_request_probe(uint32_t frame)')
    end = unit.index('\nstatic struct {',start)
    unit = unit[:start]+'''static bool
request358Probe(uint32_t frame, uint64_t ticket, uint32_t rawFence)
{
    if (!__atomic_load_n(&gReadyRetainsIssued, __ATOMIC_ACQUIRE) || !ticket) return false;
    IOLock *lock = __atomic_load_n(&gReadyLock, __ATOMIC_ACQUIRE);
    if (!IOLockTryLock(lock)) return false;
    bool queued = false;
    if (gReadySource && scan357_terminal(gReadyWriters) == SCAN357_NONE &&
        (!rawFence || GauguinGPUDisplayProbeTicket() == ticket)) {
        for (const auto &writer : gReadyWriters) {
            if (!writer.ticket || writer.terminal) continue;
            if (writer.ticket == ticket) {
                queued = rawFence ? scan406_offer(&gReadyProbe, frame, ticket, rawFence) :
                    scan358_offer(&gReadyProbe, frame, ticket);
                if (queued) gReadySource->interruptOccurred(nullptr, nullptr, 0);
            }
            break;
        }
    }
    IOLockUnlock(lock);
    return queued;
}

extern "C" void
sweet_fb358_request_probe(uint32_t frame)
{
    (void)request358Probe(frame, GauguinGPUDisplayProbeTicket(), 0);
}

extern "C" bool
sweet_fb406_request_raw_probe(uint32_t frame, uint64_t ticket, uint32_t fence)
{
    return fence && request358Probe(frame, ticket, fence);
}
'''+unit[end:]
    unit = replace(unit,'!scan358_still_timely(probe, &pos, &fBlankSlot)',
        '!scan406_still_timely(probe, &pos, &fBlankSlot)')
    site = '            sweet_frame344_record(rearm ? F366_PROBE_LOCK_RETRY : F358_PROBE,'
    return replace(unit,site,'''            sweet_frame344_record(probe->raw_eop ? F406_RAW_PROBE :
                (rearm ? F366_PROBE_LOCK_RETRY : F358_PROBE),''')


def scan_unit(unit):
    site = '#include "gauguin_completion_sample405.h"'
    unit = replace(unit,site,site+'\n#include "gauguin_completion_hint406.h"')
    site = 'static uint64_t eop405_recorded_ticket;'
    unit = replace(unit,site,site+'\nstatic uint32_t eop406_hinted_fence;')
    site = '''    const uint64_t end = mach_absolute_time();
    struct eop405_bracket got;'''
    return replace(unit,site,'''    const uint64_t end = mach_absolute_time();
    if (value == fence && fence > eop406_hinted_fence &&
        scan406_probe_line(line, SCAN351_TOTAL-SCAN351_END_GUARD) &&
        sweet_fb406_request_raw_probe(frame, ticket, fence))
        eop406_hinted_fence = fence;
    struct eop405_bracket got;''')


def frame_unit(unit):
    site = '    F357_BOUND, F357_CALIBRATION, F358_PROBE, F366_PROBE_LOCK_RETRY'
    return replace(unit,site,site+',\n    F406_RAW_PROBE = 64')


def host():
    budget = load(ADMISSION)
    require(budget['admitted'] and budget['planned_batch_bytes']==238_000_000,
            '0406 source batch exceeds the admitted remaining 0405 scope')
    source = Path(load(CONTROL)['source'])
    changed = {path:fn((source/path).read_text()) for path,fn in (
        (PROBE,probe_unit),(FB,framebuffer_unit),(FRAME,frame_unit),(SCAN,scan_unit))}
    with TemporaryDirectory(prefix='406-hint-',dir=BASE) as directory:
        directory = Path(directory)
        (directory/PROBE.name).write_text(changed[PROBE])
        (directory/'gauguin_completion_hint406.h').write_bytes(HINT.read_bytes())
        binary = str(directory/'test')
        subprocess.run(['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
            '-fno-sanitize-recover=all','-I'+str(directory),'-I'+str(source/'bsd/dev'),str(TEST),'-o',binary],
            check=True,timeout=45)
        subprocess.run([binary],check=True,timeout=15)
    lines = []
    for path,unit in changed.items():
        original = (source/path).read_text()
        lines.extend(unified_diff(original.splitlines(keepends=True),unit.splitlines(keepends=True),
                                  'a/'+str(path),'b/'+str(path)))
    lines.extend(unified_diff([],HINT.read_text().splitlines(keepends=True),
                             '/dev/null','b/bsd/dev/gauguin_completion_hint406.h'))
    PATCH.write_text(''.join(lines))
    return dict(state='0406-raw-hint-shared-probe-host-qualified',device_commands=0,ASan_UBSan=True,
        patch_sha256=sha(PATCH),input_pins={str(p):sha(p) for p in (
            CONTROL,ADMISSION,PATCH,HINT,TEST,*(source/path for path in changed))})


if __name__=='__main__':
    print(json.dumps(host(),indent=2))
