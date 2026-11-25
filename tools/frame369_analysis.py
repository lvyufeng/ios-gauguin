"""Scope exact CRC and producer timing to an independently restored 0369 capture."""

from importlib import import_module

from frame364_analysis import motion_deadlines, motion_io_join, producer_intervals, score, trace
from frame369_swap_timing import observe

boundaries = import_module('audit-frame366-restored')
pacing = import_module('audit-frame-pacing')


def analyze(path, *, swap_timing=True, begin_threads=False):
    load = score.load
    proof = load(path/'independent-restore.json')
    trace.require(len(proof['files'])==6 and proof['all_original_slot_bits_allocated'] and
        proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and
        not (proof['device_writes'] or proof['device_boots']), 'independent restore proof is incomplete')
    f = load(path/'frame-scanout-analysis.json')
    cal = f['crc_frame_calibration']
    trace.require(f['frame_trace_complete'] and f['misr']['qualified'] and cal['qualified'] and
        cal['lag_frames']==0 and cal['marker_pixel_restored'] and len(cal['dedicated_witnesses'])==3,
        'CRC calibration or coverage differs')
    raw = (path/'kernel.log').read_text()
    rows,strokes,n,d = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    display = score.copy.analyze(raw,f,extra_kinds=score.KINDS)
    timing, = rows[trace.TIMING]
    edges,proofs = boundaries.refine_post_copy_edges(rows,display,timing)
    certs = score.copy.copy_certificates(display['attempts'],edges,timing)
    resolved = []
    paired = list(zip(f['hardware']['windows'],display['windows'],strict=True))
    for window,lane in paired:
        for output,row in zip(window['outputs'],lane['intervals'],strict=True):
            if row['after_copy_boundary_check']!='unknown':
                continue
            cl = row['crc_relation']
            matches = score.copy.resolve_overlap(output,certs)
            if cl in ('changed','repeated') and matches:
                row.update(after_copy_boundary_check=cl,certified_blanking_overlaps=matches)
                totals = display['phases'][lane['phase']]['verified_full_frame_counts']
                totals['unknown'] -= output['step']
                totals[cl] += output['step']
                resolved.append(dict(frame=row['frame'],stroke=lane['stroke'],phase=lane['phase'],classification=cl))
    refined = rows | {trace.VBLANK:list(edges.values())}
    ordinary = score.window_metrics(f,display,refined)
    ns = lambda tick:tick*n//d
    warm = pacing.cadence([pair for pair in paired if pair[1]['phase']=='active' and pair[1]['stroke']>=3],
        [r.tick for r in rows[trace.SWAP] if not r.flags and r.b],ns)
    core = load(path/'core-wait-execution-analysis.json')
    io = load(path/'kernel-IO-analysis.json')
    original = load(path/'kernel-IO-identity-analysis.json')
    trace.require(core['coverage_qualified'] and original['coverage_qualified'],'incomplete Core or IO capture')
    stimulus = score.parse_motion(raw,strokes,n,d,cal)
    join = motion_io_join(io,core,stimulus,ns)
    trace.require(not ({r['kernel_token'] for r in original['submits']} & {r['kernel_token'] for r in join['submits']}),
        'fixed drag overlaps ordinary IO scope')
    moving,alignment = score.motion_display(raw,f,rows,stimulus,core['rows'],join['submits'],n,d)
    slow = score.window_metrics(moving,alignment,rows,motion=stimulus)['active']
    slow['identity'] = motion_deadlines(rows,alignment,core,join,ns,n/d)
    slow['hardware_refresh_hz_bounds'] = moving['hardware']['hardware_refresh_hz_bounds']
    trace.require(59<=slow['hardware_refresh_hz_bounds'][0]<=slow['hardware_refresh_hz_bounds'][1]<=61 and
        slow['known_scans']>=60 and len(slow['identity']['repeats'])==slow['scans']['repeated'],
        'incomplete sustained-motion score')
    bad = boundaries.copy_boundary_audit(rows,display,n,d)
    stable = not bad and all(lane['scans']['repeated']==lane['scans']['unknown']==0 and
        lane['new_images_per_second_bounds'][0]>=59 for lane in (ordinary['active'],warm,slow))
    frontend = producer_intervals(path,refined,display,core['rows'],strokes,n,d)
    report = dict(ordinary=ordinary,warm_active=warm,slow_drag=slow,refined_edges=proofs,resolved_scans=resolved,
        unverified_copy_completions=bad,stable_60_fps_qualified=stable,frontend_cutoffs=frontend)
    if swap_timing:
        report['swap_timing'] = observe(rows,n,d,frontend,begin_threads=begin_threads)
    return report
