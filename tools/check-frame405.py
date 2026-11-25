#!/usr/bin/env python3
"""Observe the exact in-flight completion word without changing driver readiness."""

from difflib import unified_diff
from importlib import import_module
import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

prior = import_module('check-frame404')
P401 = MAIN/'research/tmp/gauguin-frame401-render-ownership-worktree-20261123/research/tmp'
CONTROL = P401/'frame-404/native-kernel/build-manifest.json'
BASE = WORK/'research/tmp/frame-405'
PATCH = BASE/'405-read-completion-deadline.patch'
SOURCE = WORK/'graphics/gauguin-program-io/CompletionSample405.h'
FIXTURE = WORK/'tests/fixtures/frame405_completion_sample.c'
GPU = prior.producer.GPU
GMU = Path('bsd/dev/gauguin_gmu_board.c')
SCAN = Path('bsd/dev/gauguin_ui_trace_board.c')
replace = prior.producer.replace


def gmu_unit(unit):
    site = 'static struct ggr_context ggrb_context;'
    unit = replace(unit,site,site+'''
static vm_offset_t ggrb_completion405;

bool sweet_gpu_runtime_observe_completion405(uint32_t *out);
bool sweet_gpu_runtime_observe_completion405(uint32_t *out)
{
    const vm_offset_t word = __atomic_load_n(&ggrb_completion405, __ATOMIC_ACQUIRE);
    if (!out || !word || sweet_gmu_board_state() != GMB_READY) return false;
    const uint32_t value = gfw_load32(word);
    if (__atomic_load_n(&ggrb_completion405, __ATOMIC_ACQUIRE) != word ||
        sweet_gmu_board_state() != GMB_READY) return false;
    *out = value;
    return true;
}''')
    site = '    /* Every legacy continuation is excluded by mode12. Invalidate the boot'
    unit = replace(unit,site,'''    __atomic_store_n(&ggrb_completion405, 0, __ATOMIC_RELEASE);
'''+site)
    site = '    if(ggrb_service)gmb_record("SWEET GPU USER: runtime READY initial_shadow=20 service=1; health-gated watchdog owner, no Metal");'
    return replace(unit,site,'''    // This NC board reservation survives quarantine. Reuse exactly the
    // same completion word that ggrb_memory reads under the GPU lock.
    if (ggrb_service && ggq_nc_valid()) {
        const vm_offset_t word = gmb_ram + ggb_data_plan.data.offset - GMB_PAGE;
        __atomic_store_n(&ggrb_completion405, word, __ATOMIC_RELEASE);
    }
'''+site)


def gpu_unit(unit):
    site = 'static uint64_t gIssuedDisplayProbeTicket;'
    unit = replace(unit,site,site+'''
static uint32_t gIssuedDisplayFence405;
extern "C" bool sweet_gpu_runtime_observe_completion405(uint32_t *);

extern "C" bool GauguinGPUObserveDisplayWord405(uint64_t *ticket, uint32_t *fence, uint32_t *observed)
{
    const uint64_t issued = __atomic_load_n(&gIssuedDisplayProbeTicket, __ATOMIC_ACQUIRE);
    if (!issued) return false;
    const uint32_t expected = __atomic_load_n(&gIssuedDisplayFence405, __ATOMIC_RELAXED);
    if (!expected || !sweet_gpu_runtime_observe_completion405(observed) ||
        __atomic_load_n(&gIssuedDisplayProbeTicket, __ATOMIC_ACQUIRE) != issued ||
        __atomic_load_n(&gIssuedDisplayFence405, __ATOMIC_RELAXED) != expected) return false;
    *ticket = issued;
    *fence = expected;
    return true;
}''')
    site = '''        if (ok && fAsync && fPendingDisplayTicket)
            __atomic_store_n(&gIssuedDisplayProbeTicket, fPendingDisplayTicket, __ATOMIC_RELEASE);'''
    return replace(unit,site,'''        if (ok && fAsync && fPendingDisplayTicket) {
            __atomic_store_n(&gIssuedDisplayFence405, fence, __ATOMIC_RELAXED);
            __atomic_store_n(&gIssuedDisplayProbeTicket, fPendingDisplayTicket, __ATOMIC_RELEASE);
        }''')


def scan_unit(unit):
    site = '#include "gauguin_cpufreq402.h"'
    unit = replace(unit,site,site+'\n#include "gauguin_completion_sample405.h"')
    site = 'static bool frame_active(void)'
    unit = replace(unit,site,'''extern bool GauguinGPUObserveDisplayWord405(uint64_t *, uint32_t *, uint32_t *);

enum { EOP405_LIMIT = 256 };
static struct eop405_state eop405_probe;
static struct {
    struct eop405_bracket bounds;
    uint64_t ticket;
    uint32_t fence, frame, line, stroke;
} eop405_records[EOP405_LIMIT];
static unsigned eop405_used, eop405_lost;
static uint64_t eop405_recorded_ticket;

static void scan405_observe(uint32_t frame, uint32_t line)
{
    if (!cpu402.configured) return;
    const uint64_t contact = __atomic_load_n(&cpu402_touch_lease, __ATOMIC_ACQUIRE);
    if (!contact) return;
    const uint64_t begin = mach_absolute_time();
    const unsigned stroke = cpu402_contact(contact, begin, cpu402.lease);
    if (stroke < 3 || stroke > 13) return;
    uint64_t ticket;
    uint32_t fence, value;
    if (!GauguinGPUObserveDisplayWord405(&ticket, &fence, &value)) return;
    const uint64_t end = mach_absolute_time();
    struct eop405_bracket got;
    if (!eop405_observe(&eop405_probe, ticket, fence, value, begin, end, &got)) return;
    if (ticket != eop405_recorded_ticket) {
        eop405_recorded_ticket = ticket;
        if (eop405_used == EOP405_LIMIT) {
            ++eop405_lost;
        } else {
            ++eop405_used;
        }
    }
    if (!eop405_lost)
        eop405_records[eop405_used-1] = (typeof(eop405_records[0])){got,ticket,fence,frame,line,stroke};
}

static void scan405_dump(void)
{
    printf("SWEET EOP405: samples=%u lost=%u\\n", eop405_used, eop405_lost);
    for (unsigned i = 0; i < eop405_used; ++i) {
        const typeof(eop405_records[0]) *s = &eop405_records[i];
        char line[96];
        const int size = snprintf(line, sizeof(line), "\\nEOP405 %llx %x %x %x %x %llx %llx\\n",
            (unsigned long long)s->ticket, s->fence, s->frame, s->line, s->stroke,
            (unsigned long long)s->bounds.earliest_tick, (unsigned long long)s->bounds.latest_tick);
        if (size > 0 && (size_t)size < sizeof(line)) sweet_log_append(line, size);
    }
}

'''+site)
    site = '    scan402_dump();'
    unit = replace(unit,site,site+'\n    scan405_dump();')
    site = '''            if (scan357_enabled && !manual_preview && scan358_probe_line(line) && sweet_frame351_window())
                sweet_fb358_request_probe(frame);'''
    return replace(unit,site,site+'\n            scan405_observe(frame, line);')


def host():
    admission = P401/'frame-404/eop-development-admission.json'
    scope = load(admission)
    require(scope['admitted'] and scope['planned_batch_bytes']==347_000_000,
        '0405 source-only batch was not admitted with the 0404 runtime')
    control = load(CONTROL)
    source = Path(control['source'])
    data = []
    for path, fn in ((GMU,gmu_unit),(GPU,gpu_unit),(SCAN,scan_unit)):
        original = (source/path).read_text()
        data.extend(unified_diff(original.splitlines(keepends=True),fn(original).splitlines(keepends=True),
                    'a/'+str(path),'b/'+str(path)))
    gmu = (source/GMU).read_text()
    require(gmu.count('gmb_ram=ml_io_map_wcomb(')==1 and
            'else if(m==GGR_COMPLETION&&!off)va=gmb_ram+ggb_data_plan.data.offset-GMB_PAGE;' in gmu and
            'authorities before cached diagnostics; mappings and DMA pages remain.' in gmu and
            'ml_io_unmap(gmb_ram' not in gmu and 'mappings retained, no retry/rollback' in gmu,
            'the exact permanent NC completion word differs')
    data.extend(unified_diff([], SOURCE.read_text().splitlines(keepends=True),
        '/dev/null','b/bsd/dev/gauguin_completion_sample405.h'))
    PATCH.write_text(''.join(data))
    with TemporaryDirectory(prefix='405-eop-',dir=BASE) as name:
        test = str(Path(name)/'test')
        subprocess.run(['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
            '-fno-sanitize-recover=all','-I'+str(SOURCE.parent),str(FIXTURE),'-o',test],check=True,timeout=45)
        subprocess.run([test],check=True,timeout=15)
    return dict(state='0405-exact-EOP-sample-host-verified',ASan_UBSan=True,device_commands=0,patch_sha256=sha(PATCH),
        input_pins={str(p):sha(p) for p in (admission,CONTROL,PATCH,SOURCE,FIXTURE,*(source/p for p in (GMU,GPU,SCAN)))})


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(host(),indent=2))
