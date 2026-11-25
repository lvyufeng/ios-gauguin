#!/usr/bin/env python3
"""Read back the restored device before interpreting the 0381 DMA snapshot."""

from importlib import import_module
import re

scope = import_module('prepare-frame381')
parent = import_module('run-frame380-trial')
load, require = scope.load, scope.require


def dma_route(raw):
    footer, = re.findall(r'^SWEET F381 DMA: status=([a-z-]+) attempts=(\d+) samples=(\d+)'
                         r' first=(\d+) last=(\d+) extra_mmio_writes=0$', raw, re.M)
    status, *values = footer
    tries, samples, first, last = map(int, values)
    result = dict(status=status, attempts=tries, samples=samples, first=first, last=last,
                  candidate_ownership_verified=False, page_flip_enabled=False)
    require(0 <= samples <= tries <= 8, 'out-of-bounds 0381 snapshot')
    if status != 'stable':
        require(status in ('unstable','route-differs','map-failed') and samples < 3,
                'unrecognized snapshot outcome')
        return result | dict(route_snapshot_qualified=False, streams=[])
    require(samples == 3 and 2 <= (last-first) & 0xffffffff < 1 << 31, 'unstable scan sequence')
    header, = re.findall(r'^SWEET F381 APPS: id0=([0-9a-f]{8}) id1=([0-9a-f]{8})'
                         r' id2=([0-9a-f]{8}) control=([0-9a-f]{8}) secure=00000000 groups=71$', raw, re.M)
    id0,id1,id2,control = (int(x,16) for x in header)
    require((id0 & 255) == 71 and id0 & (1 << 27) and control != 0xffffffff and
            id1 != 0xffffffff and id2 != 0xffffffff, 'wrong APPS SMMU inventory')
    rows = re.findall(r'^SWEET F381 STREAM: sid=([0-9a-f]{3}) matches=(\d+) index=(\d+)'
                      r' smr=([0-9a-f]{8}) s2cr=([0-9a-f]{8}) cbar=([0-9a-f]{8})'
                      r' sctlr=([0-9a-f]{8})$', raw, re.M)
    require([int(row[0],16) for row in rows] == [0x800,0x802], 'missing non-secure display streams')
    extended = bool(control & (1 << 3))
    require(not extended or id0 & (1 << 8), 'inconsistent stream ID width')
    mask = 0xffff if extended else 0x7fff
    streams = []
    for sid,matches,index,smr,s2cr,cbar,sctlr in rows:
        sid,smr,s2cr,cbar,sctlr = (int(x,16) for x in (sid,smr,s2cr,cbar,sctlr))
        matches,index = int(matches),int(index)
        require(0 <= matches <= 71 and 0 <= index < 71, 'invalid stream match inventory')
        if matches:
            require((s2cr & (1 << 10) if extended else smr >> 31) and
                    not ((smr ^ sid) & mask & ~((smr >> 16) & mask)),
                    'stream match receipt contradicts SMR or S2CR')
        if control & 1:
            mode = 'global-client-disable'
        elif not matches:
            mode = 'unmatched-fault' if control & (1 << 10) else 'unmatched-default'
        elif matches != 1:
            mode = 'ambiguous'
        else:
            mode = ('context','explicit-bypass','fault','reserved')[(s2cr >> 16) & 3]
            if mode == 'context' and cbar != 0xffffffff and sctlr != 0xffffffff:
                if ((cbar >> 16) & 3) == 1 and not sctlr & 1:
                    mode = 'stage1-disabled-stage2-bypass'
                else:
                    mode = 'context-translation-unresolved'
        streams.append(dict(sid=hex(sid),matches=matches,index=index if matches==1 else None,
            smr=hex(smr),s2cr=hex(s2cr),cbar=hex(cbar),sctlr=hex(sctlr),mode=mode))
    return result | dict(route_snapshot_qualified=True,id0=hex(id0),id1=hex(id1),id2=hex(id2),
        control=hex(control),streams=streams,
        address_translation_bypassed_for_both=all(s['mode'] in
            ('explicit-bypass','stage1-disabled-stage2-bypass') for s in streams))


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'],
            'DMA analysis requires independent readback')
    proof = load(execution/'independent-restore.json')
    require(len(proof['files'])==6, 'independent restore omitted a file')
    try:
        route = dma_route((execution/'kernel.log').read_text())
    except (ValueError,OSError) as error:
        route = dict(route_snapshot_qualified=False,error=str(error),page_flip_enabled=False)
    parent.parent.previous.timeline.write(execution/'display-dma-preflight.json',route,20_000)
    result.update(display_DMA_qualification=route, page_flip_performed=False)
    collected = parent.runner.prior.collect_after_restore(execution,plan,result,before,code,
        trial=scope.TRIAL,extra_kinds=(parent.runner.PROBE,parent.runner.LOCK_RETRY),join_tail_copy=True,
        display_options=dict(copy_budget_ns=plan['copy_diagnostics']['required_early_lead_ns']))
    if collected is None:
        return
    frame,display,_,rows,_,_,inputs = collected
    try:
        report = parent.analyze(execution,plan,frame,display,rows,inputs)
        old = load(scope.REFERENCE/'scanout-comparison-0375-0379-0380.json')
        report['per_scan'] = parent.parent.paired_ordinals(
            {'0380':old['native']['scans'],'0381-control':report['native']['scans']})
        for key in ('metrics','onset','copy','guard'):
            current = report[key]['0380']
            report[key] = {'0380':old[key]['0380'],'0381-control':current}
        report.update(control_only=True,page_flip_performed=False,display_DMA=route)
        parent.parent.previous.timeline.write(execution/'scanout-comparison-0380-0381-control.json',report,5_000_000)
    except (KeyError,ValueError) as error:
        result.update(state='0381-DMA-observed-control-capture-incomplete-root-restored',
                      control_analysis_error=str(error))
        return
    result.update(state=scope.SUCCESS if route['route_snapshot_qualified'] else
                       '0381-display-DMA-unqualified-root-restored',
        frame_trace_complete=True, dpu_new_content_FPS_qualified=report['physical_score_qualified'],
        stable_60_fps_observed=report['stable_60_fps_observed'],
        system_present_alignment_qualified=report['system_present_alignment_qualified'],
        hardware_refresh_hz_bounds=report['hardware_refresh_hz_bounds'],
        control_comparison=report['metrics'],
        control_onset={k:{name:v[name] for name in ('ordinary','warm')} for k,v in report['onset'].items()},
        crc_calibration=report['crc_calibration'], crc_register=report['crc_register'],
        control_stroke_4_release=report['segments'].get('retest',{}).get('stroke_4_release'),
        control_fixed_drag_repeat_stages=[d['accepted_candidates'][0]['stage']
            for d in report['slow_drag']['repeats'] if d['accepted_candidates']])


if __name__=='__main__':
    raise SystemExit(parent.runner.main(scope,after_restore_fn=after_restore))
