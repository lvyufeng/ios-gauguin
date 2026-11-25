#!/usr/bin/env python3
"""Select and verify a DPU work budget from measured full-frame deadlines."""

import argparse
from contextlib import redirect_stdout
from difflib import unified_diff
from importlib import import_module
from io import StringIO
import json
import math
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha
from frame384_stage import parse, verified_latches
import frame344_log as trace

BASE = WORK/'research/tmp/frame-410'
P408 = MAIN/'research/tmp/gauguin-frame408-dpu-dispatch-budget-worktree-20261124/research/tmp/frame-408'
P409 = MAIN/'research/tmp/gauguin-frame409-stock-bus-worktree-20261124/research/tmp/frame-409'
P407 = MAIN/'research/tmp/gauguin-frame406-completion-hint-worktree-20261124/research/tmp/frame-407'
LAST = P409/'execution'
CHOICE = BASE/'phase-selection.json'
PATCH = BASE/'410-measured-compositor-work-duration.patch'
HOST = BASE/'offline.json'
KERNEL = BASE/'native-kernel/build-manifest.json'
SIMULATOR = P407/'replay-aosp-dispatch.cpp'
HEADER = Path('bsd/dev/gauguin_frame380_phase.h')
FRAMEBUFFER = Path('iokit/Kernel/arm/SweetFramebuffer.cpp')
COMPILER = Path('/Library/Developer/CommandLineTools/usr/bin')
WORK_BUDGETS_US = (8200,9200,10200,11200,11800,12200,13200,14200)
NATIVE_BATCH = 72_000_000
audit = import_module('audit-frame388-restored')


def archive(trial):
    base = {'0408':P408,'0409':P409}[trial]
    run = base/'execution'
    terminal,proof,plan = (load(path) for path in (
        run/'result.json',run/'independent-restore.json',base/'trial-plan.json'))
    require(terminal['trial']==trial and terminal['boot_attempts']==1 and terminal['restored'] and
            terminal['static_root_comparison_passed'] and terminal['independent_restore_verified'] and
            proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and
            proof['misc_original_4096_bytes_match'] and proof['install_plan_sha256']==plan['install_plan_sha256'],
            'phase selection requires independent original root and misc readback')
    return base,run,terminal,plan


def measured(trial):
    base,run,terminal,plan = archive(trial)
    comparison = run/terminal['comparison']
    report = load(comparison)
    measurement = report['measurements'][trial]
    phase = measurement['ca_phase']
    require(terminal['DPU_independent_physical_FPS_qualified'] and phase['qualified'] and not phase['missed'] and
            phase['work_duration_us']==plan['work_duration_us']==7200 and
            terminal['stable_60_fps_observed']==report['stable_60_fps_observed'] and
            report['stock_interaction_CPU'][trial]['selector_cleanup_qualified'] and
            report['native_GPU_profile']['native_request_accepted'],'phase reference differs from physical replay')
    return base,run,terminal,plan,comparison,report,measurement


def missed_stage_margins_ms(run, report):
    raw = (run/'kernel.log').read_text()
    events,_,n,d = parse(raw)
    receipts = audit.flip.latch_receipts(raw,events)['accepted_by_scan']
    latches = verified_latches(events,receipts)
    writers = {row['generation']:(scan,row) for scan,row in latches.items()}
    observed = []
    for miss in report['raw_GPU_completion']['repeats']:
        cutoff = miss['cutoff_ticks'][0]
        for candidate in miss['candidates']:
            if candidate['stage']!=miss['strongest_observed_candidate']:
                continue
            generation = candidate['generation']
            if generation not in writers:
                continue
            scan,latch = writers[generation]
            require(latch['fence']==candidate['fence'],'repeat and later latch differ')
            if scan!=((miss['scan']+1)&0xffffffff):
                continue
            observed.append(dict(stroke=miss['stroke'],workload=miss['workload'],scan=miss['scan'],
                stage=candidate['stage'],after_earliest_cutoff_ms=(latch['tick']-cutoff)*n/d/1e6))
    return observed


def motion_rank(reference):
    metrics = reference[-1]
    warm = metrics['onset']['warm']
    drag = metrics['metrics']['slow_drag']
    counts = (reference[-2]['motion_after_onset']['counts'],drag['scans'])
    repeats = sum(row.get('repeated',0) for row in counts)
    scans = sum(sum(row.values()) for row in counts)
    return repeats/scans,warm['p95_first_new_image_ns'][1]


def select():
    _,_,last,_ = archive('0409')
    references = [measured('0408')]
    if last.get('DPU_independent_physical_FPS_qualified'):
        references.append(measured('0409'))
    control = references[-1] if last.get('stable_60_fps_observed') else min(references,key=motion_rank)
    base,run,terminal,plan,comparison,report,_ = control
    observed = [] if terminal['stable_60_fps_observed'] else missed_stage_margins_ms(run,report)
    lateness_us = math.ceil(max((row['after_earliest_cutoff_ms'] for row in observed),default=0)*1000)
    work = plan['work_duration_us']
    if not terminal['stable_60_fps_observed']:
        # Select the smallest replay candidate covering the linked observed
        # lateness plus 0.25 ms for staging dispatch and prediction error.
        require(observed,'no exact later staged frame for the repeat model')
        needed = work+max(0,lateness_us)+250
        work = next((candidate for candidate in WORK_BUDGETS_US if candidate>=needed),None)
        require(work is not None,'observed lateness exceeds the prepared phase range')
    return dict(state='0409-independent-motion-selects-0410',control=terminal['trial'],
        work_us=work,source_work_us=plan['work_duration_us'],repeat=terminal['stable_60_fps_observed'],
        native_bandwidth_index=plan.get('native_bandwidth_index',10),
        cleanup_reference_sha256=sha(LAST/'result.json'),comparison_sha256=sha(comparison),
        plan_sha256=sha(base/'trial-plan.json'),deadline_samples=observed)


def replay(run,measurement,source,work):
    raw = (run/'kernel.log').read_text()
    rows,*_ = parse(raw)
    pulses = measurement['ca_phase']['pulses']
    max_delay = max(row['notification_tick']-row['wake_tick'] for row in pulses)
    require(max_delay>0,'recorded DPU dispatch delay unavailable')
    payload = ''.join(f'{edge.id} {edge.flags} {edge.a} {edge.b}\n' for edge in rows[trace.VBLANK])
    results = []
    with TemporaryDirectory(prefix='0410-phase-',dir=BASE) as tmp:
        executable = Path(tmp)/'replay'
        sdk = subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
        subprocess.run([str(COMPILER/'clang++'),'-isysroot',sdk,'-std=c++20','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all',
            '-I'+str(source/'bsd/dev'),str(SIMULATOR),'-o',str(executable)],check=True,timeout=50)
        for delay in (0,max_delay,max_delay+19200):
            result = subprocess.run([str(executable)],input=f'{work*96//5} {delay}\n'+payload,
                capture_output=True,text=True,check=True,timeout=20)
            eligible,scheduled,invalid,margin = map(int,result.stdout.split())
            require(eligible==scheduled and eligible>2600 and invalid==0 and margin>0,
                    'selected phase skips a DPU scan in edge replay')
            results.append(dict(work_us=work,delay_ticks=delay,eligible=eligible,scheduled=scheduled,
                                invalid=invalid,min_margin_ticks=margin))
    return results


def source_manifest(trial):
    if trial=='0408':
        return P408/'native-kernel-1401/build-manifest.json'
    plan = load(P409/'frame409-image.json')
    return Path(plan['kernel_manifest'])


def host():
    choice = load(CHOICE)
    require(choice==select() and not choice['repeat'],'phase choice does not require a linked variant')
    trial,work = choice['control'],choice['work_us']
    _,run,_,_,comparison,_,measurement = measured(trial)
    manifest = source_manifest(trial)
    kernel = load(manifest)
    source = Path(kernel['source'])
    tests = replay(run,measurement,source,work)
    unit = source/FRAMEBUFFER
    before = unit.read_text()
    original = f"                workUs = {choice['source_work_us']};"
    require(before.count(original)==1,'exact scoped compositor override differs')
    after = before.replace(original,f'                workUs = {work};')
    PATCH.write_text(''.join(unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),
        'a/'+str(FRAMEBUFFER),'b/'+str(FRAMEBUFFER))))
    paths = (CHOICE,manifest,SIMULATOR,source/HEADER,unit,PATCH,comparison,run/'kernel.log',
             run/'kernel.log.bin',run/'independent-restore.json')
    return dict(state='0410-work-duration-hardware-edge-replay-passed',work_us=work,control=trial,
                replay=tests,device_commands=0,input_pins={str(path):sha(path) for path in paths})


def native():
    admission = load(BASE/'complete-batch-admission.json')
    planned = admission['planned_batch_bytes']
    require(admission['admitted'] and planned==447_000_000 and
            admission['current_accounted_bytes']+planned<=admission['limit_bytes'],'0410 whole batch exceeds storage')
    choice = load(CHOICE)
    proof = load(HOST)
    require(not choice['repeat'] and proof['work_us']==choice['work_us'] and
            proof['control']==choice['control'] and not proof['device_commands'] and
            all(sha(path)==digest for path,digest in proof['input_pins'].items()),'0410 offline evidence differs')
    trial = choice['control']
    reference = source_manifest(trial)
    same_framebuffer = source_manifest('0408')
    with redirect_stdout(StringIO()):
        import_module('build-frame347').link_scanout(reference,KERNEL.parent,parent_trial=trial,trial='0410',
            patches=(PATCH,),extra_units=(('SweetFramebuffer',same_framebuffer,'compile-SweetFramebuffer'),),
            recompile_scanout=False,compiler_bin=COMPILER)
    result = load(KERNEL)
    old,new = next(iter(result['object_replacements'].items()))
    nm = lambda path:set(subprocess.check_output([str(COMPILER/'nm'),'-uj',path],text=True).splitlines())
    require(Path(old).stem==Path(new).stem=='SweetFramebuffer' and nm(old)==nm(new),'0410 framebuffer imports differ')
    return {key:result[key] for key in ('state','identity','kernel_sha256','kernel_bytes','object_replacements',
                                       'baseline_reproduced_except_uuid','inputs_unchanged')}


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('stage',choices=('select','host','native'))
    print(json.dumps(globals()[cli.parse_args().stage](),indent=2))
