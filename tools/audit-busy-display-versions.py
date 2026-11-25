#!/usr/bin/env python3
"""Join the busy version seen by each unbound swap to its native recorder."""

import argparse
from collections import Counter, defaultdict
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace

from frame366_scope import MAIN, load, sha
import frame369_swap_timing
import frame374_native_ca as ca
import frame399_writer
from frame357_replay import TOTAL_LINES
import kernel342_log

trial_runner = import_module('run-frame398-trial')
trace = trial_runner.trace
stage, flip = trial_runner.stage, trial_runner.flip
feasible = import_module('audit-frame-supply').feasible
ARCHIVES = {
    '0394': ('gauguin-frame394-compositor-qos-worktree-20261123', '0398-0394'),
    '0397': ('gauguin-frame397-resident-buffer-overlap-worktree-20261123', '0393-0397'),
    '0398': ('gauguin-frame398-renderer-performance-core-worktree-20261123', '0397-0398'),
    '0399': ('gauguin-frame399-cpu-frequency-observation-worktree-20261123', '0394-0399'),
}


def conditional_supply(raw, rows, windows, latches, bound, ready, candidates):
    line = int(trace.one(r'^SWEET F351 WINDOW: available=1 frame=\d+ end=(\d+)$',
                         raw,'display flip window'))-192
    edges = trace.indexed(rows[trace.VBLANK],lambda row:row.id,'physical vblank')
    bound_ready = {generation:ready[writer.id].tick for generation,writer in bound.items()
                   if writer.id in ready}
    extra = {row['generation']:row['producer_available_tick'] for row in candidates
             if row.get('command_buffer_and_swap_in_render_span')}
    verified_extra = {row['generation']:row['producer_available_tick'] for row in candidates
                      if row.get('exact_recording_thread_and_surface')}
    outcomes = dict(scans=0,recorded=[0,0],conditional_same_render=[0,0],conditional_recording_thread_and_surface=[0,0])
    trace.require(0 < line < TOTAL_LINES,'invalid final flip line')
    for window in windows:
        first,last = window['first_scan'],window['last_scan']
        earlier = max((scan for scan in latches if scan < first),default=0)
        initial = latches[earlier]['generation'] if earlier else 0
        final = latches[last]['generation']
        cutoffs = []
        for scan in range(first,last+1):
            before,after = edges[scan-1],edges[scan]
            trace.require(before.flags==after.flags==1 and before.b<after.a,'unbracketed warm window')
            cutoffs.append(tuple(((TOTAL_LINES-line)*a+line*b)//TOTAL_LINES
                            for a,b in zip((before.a,before.b),(after.a,after.b),strict=True)))
        outcomes['scans'] += len(cutoffs)
        for index in (0,1):
            slots = [SimpleNamespace(end=reading[index]) for reading in cutoffs]
            for name, optional in (('recorded', {}), ('conditional_same_render',extra),
                                   ('conditional_recording_thread_and_surface',verified_extra)):
                events = [(g,tick) for g,tick in (bound_ready|{g:t for g,t in optional.items() if g<=final}).items()
                          if g > initial and tick <= slots[-1].end]
                outcomes[name][index] += feasible(slots,events,initial)
    return outcomes | dict(scope='Potential distinct images with perfect retention and zero downstream work. '
                                 'The extra producer is conditional on intent and version lifetime.')


def analyze(trial):
    name, pair = ARCHIVES[trial]
    folder = MAIN/'research/tmp'/name/'research/tmp'/f'frame-{int(trial)}'
    execution = folder/'execution'
    report = execution/f'scanout-comparison-{pair}.json'
    inputs = [folder/'trial-plan.json', report, *(execution/name for name in (
        'result.json', 'independent-restore.json', 'kernel.log', 'kernel.log.bin',
        'kernel-IO-analysis.json', 'kernel-IO-identity-analysis.json',
        'core-wait-execution-analysis.json', 'c4-queue-analysis.json'))]
    plan, _, result, proof = map(load,inputs[:4])
    trace.require(result['restored'] and result['independent_restore_verified'] and
                  result['DPU_independent_physical_FPS_qualified'] and proof['journal_empty'] and
                  proof['misc_original_4096_bytes_match'] and
                  plan['install_plan_sha256'] == proof['install_plan_sha256'], 'latest independent proof differs')
    _, measured = trial_runner.common.audit.score_archive(execution, plan['kernel_banner'],
                                                          expected_pairs=None, require_first=False)
    trace.require(measured == load(report)['measurements'][trial], 'physical warm windows differ on replay')
    raw = inputs[4].read_text()
    rows,_,n,d = stage.staging.parse(raw)
    start,end,native_n,native_d = ca.envelope(raw)
    trace.require((n,d) == (native_n,native_d), 'render and scanout clocks differ')
    links = ca.link_swaps(ca.decode(raw,start,end),frame369_swap_timing.decode(rows,n,d,begin_threads=True),start,end,n,d)
    latches = stage.staging.verified_latches(rows,flip.latch_receipts(raw,rows)['accepted_by_scan'])
    io, joined, core, frontend = map(load, inputs[6:])
    trace.require(io['coverage_qualified'] and frontend['coverage_qualified'] and
                  kernel342_log.join(io,core,joined['full_script_bounds_us']) == joined,
                  'native issue or frontend command buffers did not replay')
    attachments, capped = {},False
    if trial=='0399':
        attachment_path = execution/'backboardd.log.current'
        attachments,capped = frame399_writer.decode(attachment_path.read_text(errors='replace'))
        inputs.append(attachment_path)
    gpu_calls = trace.indexed((r for r in io['rows'] if r['selector'] == 70 and not r['result']),
                              lambda r:r['token'],'native submit')
    submissions = trace.indexed(joined['submits'],lambda r:r['kernel_token'],'Core/kernel join')
    jobs = trace.indexed(core['rows'],lambda r:(r['queue'],r['ticket'],r['job']),'Core recorder job')
    buffers = trace.indexed(frontend['buffers'],lambda r:(r['object'],r['made_us']),'front command buffer')
    issued, eop, ready = (trace.indexed(rows[kind],lambda r:r.id,'native fence stage')
                          for kind in (trace.ISSUE,trace.EOP,trace.READY))
    swaps = trace.indexed((r for r in rows[trace.SWAP] if not r.flags and r.c),lambda r:r.id,'accepted generation')
    timings = trace.indexed(rows[trace.SWAP_TIMING],lambda r:r.id,'same-client timing')
    bound = trace.indexed((r for r in rows[trace.WRITER] if r.b),lambda r:r.b>>32,'bound writer')
    versions = defaultdict(list)
    for row in rows[trace.WRITER]:
        versions[row.a,row.c].append(row)

    def ns(tick):
        return tick*n//d

    candidates = []
    windows = measured['moving_GPU']['ordinary']['windows']
    for window in windows:
        first,last = window['first_scan'],window['last_scan']
        earlier = max((scan for scan in latches if scan < first),default=0)
        initial = latches[earlier]['generation'] if earlier else 0
        final = latches[last]['generation']
        for generation, swap in swaps.items():
            if not initial < generation <= final or generation in bound:
                continue
            version,surface = divmod(swap.c,1<<32)
            timing = timings.get(generation)
            row = dict(stroke=window['stroke'],generation=generation,surface=surface,expected_version=version)
            candidates.append(row)
            if not timing or timing.c != swap.c:
                continue
            current_state = timing.b & 0xffffffff
            previous = versions[surface,current_state & ~3]
            later = versions[surface,version]
            row.update(observed_surface_state=current_state,skipped_pending_version=bool(timing.flags),
                       exact_expected_writers=len(later),observed_version_writers=len(previous))
            if len(later)==1:
                row['expected_writer_issue_after_swap_ns'] = ns(issued[later[0].id].tick)-ns(swap.tick)
            if current_state & 3 != 1 or len(previous)!=1 or previous[0].b:
                continue
            writer, = previous
            issue, done, visible = issued[writer.id],eop.get(writer.id),ready.get(writer.id)
            row.update(busy_version=writer.c,unclaimed_fence=writer.id,
                       busy_writer_issue_after_swap_ns=ns(issue.tick)-ns(swap.tick))
            if not done or not visible or not issue.tick<=writer.tick<=done.tick<=visible.tick or swap.tick>=done.tick:
                continue
            row['busy_writer_ready_after_swap_ns'] = ns(visible.tick)-ns(swap.tick)
            row['producer_available_tick'] = max(visible.tick,swap.tick)
            render = links.get(generation,{}).get('render')
            link, call = submissions.get(issue.a), gpu_calls.get(issue.a)
            if not render or not link or not call:
                continue
            job = jobs[link['queue'],link['ticket'],link['job']]
            cb = buffers[job['object'],job['made_us']]
            trace.require((issue.b,issue.c)==(link['driver_queue'],link['driver_fence'])==(call['queue'],call['fence']) and
                          call['first_ns']<=ns(issue.tick)<=call['last_ns'],'busy writer lost its command buffer')
            made, committed = cb['made_us']*1000, int(cb['times_us']['0'])*1000
            begin, end = ns(render['begin_tick']), ns(render['end_tick'])
            row['command_buffer_and_swap_in_render_span'] = begin<=made<=committed<=ns(swap.tick)<=end
            row['render_scope_ns'] = [begin,end]
            row['frontend_times_ns'] = [made,committed]
            receipt = attachments.get((job['object'],job['made_us'],surface))
            if receipt:
                row['attachment_receipt'] = receipt
                row['exact_recording_thread_and_surface'] = (
                    not capped and receipt['tid']==timing.b>>32 and
                    render['begin_tick']<=receipt['tick']<=render['end_tick'] and
                    made-1000<=ns(receipt['tick'])<=committed+1000 and
                    row['command_buffer_and_swap_in_render_span'])
    status = Counter('busy_writer_in_render_span' if row.get('command_buffer_and_swap_in_render_span')
                     else 'busy_writer_without_render_join' if 'busy_version' in row else 'other_unbound'
                     for row in candidates)
    return dict(trial=trial, unbound_accepted=len(candidates), counts=dict(status), rows=candidates,
                exact_recording_threads_and_surfaces=sum(bool(row.get('exact_recording_thread_and_surface'))
                                                        for row in candidates),
                conditional_warm_supply=conditional_supply(raw,rows,windows,latches,bound,ready,candidates),
                device_commands=0,input_pins={str(p):sha(p) for p in inputs},
                scope='Exact buffer-to-fence and same-thread swap-to-render joins. An attachment receipt adds '
                      'the recording thread and target IOSurface. Render-span containment alone is timing evidence.')


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('trials',nargs='+',choices=tuple(ARCHIVES))
    print(json.dumps([analyze(trial) for trial in cli.parse_args().trials],separators=(',', ':')))
