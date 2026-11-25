#!/usr/bin/env python3
"""Stage the measured DPU work-duration variant without changing the boot profile."""

import argparse
from difflib import unified_diff
import json
from pathlib import Path

from frame366_scope import MAIN,WORK,load,require,sha

P407 = MAIN/'research/tmp/gauguin-frame406-completion-hint-worktree-20261124/research/tmp/frame-407'
P405 = MAIN/'research/tmp/gauguin-frame405-eop-deadline-worktree-20261124/research/tmp/frame-405'
CONTROL = P407/'native-kernel/build-manifest.json'
ADMISSION = P407/'dispatch-development-admission.json'
REPLAY = P407/'0404-dispatch-budget-replay.json'
BASE = WORK/'research/tmp/frame-408'
PATCH = BASE/'408-compositor-work-duration.patch'
STOCK_PATCH = BASE/'408-restore-measured-stock-1401600.patch'
FRAMEBUFFER = Path('iokit/Kernel/arm/SweetFramebuffer.cpp')
CPU = Path('bsd/dev/gauguin_cpufreq402.h')
SCOPE = '''        uint32_t workUs = 0;
        PE_parse_boot_argn("sweet_ca_work_us", &workUs, sizeof(workUs));'''


def host(work):
    admission = load(ADMISSION)
    require(admission['admitted'] and admission['planned_batch_bytes']==238_000_000,
            '0408 source batch exceeds the active trial reserve')
    checks = [row for row in load(REPLAY) if row['work_us']==work]
    require(len(checks)==3 and all(row['scheduled']==row['eligible']==2690 and not row['invalid'] and
            row['minimum_early_margin_ns']>0 for row in checks),'0408 work budget needs a DPU edge replay')
    tree = Path(load(CONTROL)['source'])
    before = tree/FRAMEBUFFER
    source = before.read_text()
    require(source.count(SCOPE)==1,'0407 work override site differs')
    chosen = '''        uint32_t workUs = 0;
        if (!PE_parse_boot_argn("sweet_ca_work_us", &workUs, sizeof(workUs))) {
            // The bounded scripted profile uses the independently replayed
            // work duration. Keep the inherited default for other profiles.
            uint32_t script = 0, mode = 0, rate = 0, physical = 0, gpu = 0;
            PE_parse_boot_argn("swp", &script, sizeof(script));
            PE_parse_boot_argn("sweetfb_stats", &mode, sizeof(mode));
            PE_parse_boot_argn("sweetfb_hz", &rate, sizeof(rate));
            PE_parse_boot_argn("sweetnvt", &physical, sizeof(physical));
            PE_parse_boot_argn("gpf", &gpu, sizeof(gpu));
            if (script == 4 && mode == 9 && rate == 60 && !physical && gpu == 5)
                workUs = %d;
        }'''%work
    candidate = source.replace(SCOPE,chosen)
    require(candidate.replace(chosen,SCOPE)==source,'phase staging changed another framebuffer path')
    PATCH.write_text(''.join(unified_diff(source.splitlines(keepends=True),candidate.splitlines(keepends=True),
        'a/'+str(FRAMEBUFFER),'b/'+str(FRAMEBUFFER))))
    donor = P405/'native-kernel/build-manifest.json'
    stock = Path(load(donor)['source'])/CPU
    high,normal = (p.read_text() for p in (tree/CPU,stock))
    require(high.replace('92, /* 1,766,400','73, /* 1,401,600')==normal and normal!=high,
            '0408 stock clock reversion changes another controller contract')
    STOCK_PATCH.write_text(''.join(unified_diff(high.splitlines(keepends=True),normal.splitlines(keepends=True),
        'a/'+str(CPU),'b/'+str(CPU))))
    return dict(state='0408-DPU-work-duration-offline-verified',device_commands=0,work_us=work,phase_replay=checks,
        stock_target_khz=1_401_600,patch_sha256=sha(PATCH),stock_patch_sha256=sha(STOCK_PATCH),
        input_pins={str(p):sha(p) for p in (CONTROL,ADMISSION,REPLAY,before,PATCH,STOCK_PATCH,donor,stock,tree/CPU)})


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work_us',type=int,choices=(4200,5200,6200,7200,9200))
    print(json.dumps(host(parser.parse_args().work_us),indent=2))
