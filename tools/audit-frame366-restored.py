#!/usr/bin/env python3
"""Audit 0366's scoped motion and distinguish a wide edge bracket from an uncertified copy."""

from dataclasses import replace
from importlib import import_module
import json

from frame364_analysis import motion_deadlines, motion_io_join, producer_intervals, score, trace
from frame366_retry import analyze as analyze_retries
from frame366_scope import BASE, load, require, sha

MASK = 0xffffffff
RESULT = '543969bd06e2134c9b4d76eec1bc53df459b25047e1ad6082505735ff4f4fd39'
PROOF = '1188de6ac1913786c010e60dca47c34dbf28df470858bcd2b5a2510c563323f2'


def check_restored(execution):
    result_path = execution/'result.json'
    proof_path = execution/'independent-restore.json'
    require(sha(result_path)==RESULT and sha(proof_path)==PROOF,'0366 terminal receipts differ')
    result,proof = load(result_path),load(proof_path)
    require(result['trial']=='0366' and result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'] and all(result['other_log_prefix_preserved'].values()) and
        result['frame_trace_complete'] and
        proof['state']=='independently-verified-six-original-files-misc-and-empty-journal' and
        len(proof['files'])==6 and proof['all_original_slot_bits_allocated'] and proof['journal_empty'] and
        proof['misc_original_4096_bytes_match'] and not (proof['device_writes'] or proof['device_boots']),
        'independent restoration must precede this audit')
    return result


def refine_post_copy_edges(rows, display, timing):
    """The same-frame read after DSB and F344_COPY constrains the next edge."""
    edges = trace.indexed(rows[trace.VBLANK],lambda r:r.id,'original hardware brackets')
    refined = dict(edges)
    copies = trace.indexed(rows[trace.COPY],lambda r:(r.id,r.a,r.b),'copy timestamps')
    proofs = rows[score.PRESENT]
    additions = []
    for attempt in display['attempts']:
        for layer in attempt['layers']:
            begin,end,surface = (layer[name] for name in ('copy_start_tick','copy_end_tick','surface'))
            for proof in attempt['blanking_proofs']:
                if proof['disposition']!='verified-blank' or not proof['paired_copy'] or proof['surface']!=surface:
                    continue
                left,right = edges.get(proof['frame']),edges.get((proof['frame']+1)&MASK)
                if not (left and right and left.flags==right.flags==1 and left.b<=begin<right.a<end<right.b and
                        timing.c<proof['begin_line']<=proof['finish_line']<proof['end_guard_line']<=timing.a):
                    continue
                copied = copies[surface,begin,end]
                after = [row for row in proofs if row.id==left.id and row.a==surface and row.flags==5 and
                         row.b==proof['begin_line'] and row.c==((proof['end_guard_line']<<32)|proof['finish_line']) and
                         end<=copied.tick<row.tick<=min(right.b,attempt['result_tick']) and copied.seq<row.seq]
                if len(after)!=1:
                    continue
                new_edge = refined[right.id]
                refined[right.id] = replace(new_edge,a=max(new_edge.a,end))
                additions.append(dict(attempt=attempt['attempt'],frame=right.id,copy_end_tick=end,
                    original_edge_lo=right.a,edge_hi=right.b,paired_post_copy_seq=after[0].seq,
                    post_copy_same_frame_line=proof['finish_line']))
    return refined,additions


def copy_boundary_audit(rows, display, num, den):
    edges = trace.indexed(rows[trace.VBLANK],lambda row:row.id,'hardware frame')
    outside = []
    for attempt in display['attempts']:
        for proof in attempt['blanking_proofs']:
            if proof['disposition']!='end-unverified':
                continue
            right = edges.get((proof['frame']+1)&MASK)
            for layer in attempt['layers']:
                if layer['surface']!=proof['surface']:
                    continue
                end = layer['copy_end_tick']
                outside.append(dict(attempt=attempt['attempt'],frame=proof['frame'],
                    begin_line=proof['begin_line'],post_copy_line=proof['finish_line'],duration_ns=layer['copy_ns'],
                    copy_end_after_latest_next_edge_ns=(end-right.b)*num/den if right else None,
                    probe_receipts_for_scan=[row.kind for kind in (60,61) for row in rows[kind] if row.id==proof['frame']]))
    return outside


def analyze(execution):
    result = check_restored(execution)
    frame = load(execution/'frame-scanout-analysis.json')
    cal = frame['crc_frame_calibration']
    require(frame['frame_trace_complete'] and frame['misr']['qualified'] and
        cal['qualified'] and cal['lag_frames']==0 and cal['marker_pixel_restored'] and
        len(cal['dedicated_witnesses'])==3,'frame or CRC latch evidence missing')
    kernel = BASE/'native-kernel/source'
    presenter = kernel/'iokit/Kernel/arm/SweetFramebuffer.cpp'
    position = kernel/'bsd/dev/gauguin_ui_trace_board.c'
    text = presenter.read_text()
    after_barrier = text.index('if (checked) __asm__ volatile("dsb sy"')
    order = [after_barrier,text.index('F344_COPY,id,layer',after_barrier),
        text.index('sweet_frame351_position(&copyEnd) && copyEnd.frame == blankFrame',after_barrier),
        text.index('F351_PRESENT,blankFrame,flags',after_barrier)]
    observed = position.read_text()
    require(order==sorted(order) and 'copyEnd.line < copyStart.end' in text and
        'if (frame != last || count != 0 || line >= geometry.vtotal' in observed,
        'production readback ordering differs')

    raw = (execution/'kernel.log').read_text()
    rows,strokes,num,den = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    display = score.copy.analyze(raw,frame,extra_kinds=score.KINDS)
    timing, = rows[trace.TIMING]
    refined,additions = refine_post_copy_edges(rows,display,timing)
    certs = score.copy.copy_certificates(display['attempts'],refined,timing)
    resolved = []
    for window,lane in zip(frame['hardware']['windows'],display['windows'],strict=True):
        for out,row in zip(window['outputs'],lane['intervals'],strict=True):
            if row['after_copy_boundary_check']!='unknown':
                continue
            alternative = score.copy.resolve_overlap(out,certs)
            new = row['crc_relation']
            if alternative and new in ('changed','repeated'):
                row.update(after_copy_boundary_check=new,certified_blanking_overlaps=alternative)
                counts = display['phases'][lane['phase']]['verified_full_frame_counts']
                counts['unknown'] -= out['step']
                counts[new] += out['step']
                resolved.append(dict(phase=lane['phase'],stroke=lane['stroke'],frame=row['frame'],classification=new))
    corrected = rows | {trace.VBLANK:list(refined.values())}
    ordinary = score.window_metrics(frame,display,corrected)

    core = load(execution/'core-wait-execution-analysis.json')
    original = load(execution/'kernel-IO-identity-analysis.json')
    decoded = load(execution/'kernel-IO-analysis.json')
    require(original['coverage_qualified'] and core['coverage_qualified'],'original Core/IO capture is incomplete')
    ns = lambda tick:tick*num//den
    producer = producer_intervals(execution,corrected,display,core['rows'],strokes,num,den)
    producer_budget = import_module('audit-frame364-deadlines').producer_budget
    ordinary_producer = producer_budget(dict(frontend=producer),corrected,core['rows'],original['submits'],ns)
    stimulus = score.parse_motion(raw,strokes,num,den,cal)
    join = motion_io_join(decoded,core,stimulus,ns)
    require(not ({r['kernel_token'] for r in original['submits']} & {r['kernel_token'] for r in join['submits']}),
            'slow drag overlaps original Core/IO score')
    moving,alignment = score.motion_display(raw,frame,rows,stimulus,core['rows'],join['submits'],num,den)
    slow = score.window_metrics(moving,alignment,rows,motion=stimulus)['active']
    slow['identity'] = motion_deadlines(rows,alignment,core,join,ns,num/den)
    slow['hardware_refresh_hz_bounds'] = moving['hardware']['hardware_refresh_hz_bounds']
    hz = slow['hardware_refresh_hz_bounds']
    require(hz and 59<=hz[0]<=hz[1]<=61 and slow['known_scans']>=60 and
        slow['scored_span_ns_bounds'][0]>=1000*score.MS and
        len(slow['identity']['repeats'])==slow['scans']['repeated'],'incomplete 60 Hz slow-drag capture')
    phases = {row['previous_frame']:w['phase'] for w in display['windows'] for row in w['intervals']}
    phases.update({(row['frame']-1)&MASK:'slow_drag' for row in slow['identity']['frames']})
    copies = {((row['frame']-1)&MASK,row['certified_copy']['native_fence']):row['kind']
              for row in slow['identity']['frames'] if row['certified_copy']}
    for row in load(execution/'fence-probe-analysis.json')['probes']:
        if row.get('same_scan') and row.get('accepted_full_frame'):
            copies[row['hardware_frame'],row['fence']]='changed'
    retries = analyze_retries(rows,phases,copies)
    bad = copy_boundary_audit(rows,display,num,den)
    names = ('result.json','independent-restore.json','kernel.log','frame-scanout-analysis.json',
        'core-wait-execution-analysis.json','kernel-IO-identity-analysis.json','kernel-IO-analysis.json',
        'fence-probe-analysis.json','springboard-new.log')
    return dict(state='0366-scoped-scan-audit-root-restored',original_verdict=result['state'],
        ordinary_13_strokes=ordinary,ordinary_edge_refinements=additions,resolved_scans=resolved,
        ordinary_producer=ordinary_producer,
        slow_drag=slow,probe_retries=retries,uncertified_completions=bad,
        whole_run_copy_boundary_qualified=not bad,stable_60_fps_qualified=False,
        input_pins={str(path):sha(path) for path in
            (*(execution/name for name in names),presenter,position)})


if __name__=='__main__':
    print(json.dumps(analyze(BASE/'execution'),indent=2))
