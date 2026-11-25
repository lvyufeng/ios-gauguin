"""Join 20H392 frame requests, driver delivery and qualified physical scans."""

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict

import frame344_log as frame
import frame374_native_ca as native


def align_requests(events, scans, matches, swaps, edges, n, d, *, tolerance_ns=0):
    """Verify the exact target, accepted surface version and FrameInfo round trip."""
    target = frame.indexed((event for event in events if event.kind==native.DRIVER_TARGET),
                           lambda event:event.args[0], 'accepted frame target')
    delivered = frame.indexed((event for event in events if event.kind==native.DRIVER_DELIVERY),
                              lambda event:event.args[0], 'driver delivery')
    swap_rows = frame.indexed((event for event in swaps if not event.flags and event.c),
                              lambda event:event.a, 'accepted display swap')
    for swap, event in target.items():
        accepted = swap_rows.get(swap)
        require = (accepted and event.args[1]==accepted.id and event.args[3]==accepted.c and
                   accepted.tick<=event.tick and swap)
        frame.require(require, 'native target differs from the accepted swap or surface version')

    by_generation = {row['generation']:row for row in matches}
    for scan in scans:
        generation = scan.get('generation')
        link = by_generation.get(generation)
        if not link:
            continue
        swap = link['client_swap_id']
        request = target.get(swap)
        if request is None:
            continue
        desired = request.args[2]
        if (desired in native.NO_TIMESTAMP or
            abs(desired-request.tick)*n > 2_000_000_000*d):
            continue
        scan['CA_swap_target_tick'] = desired
        feedback = delivered.get(swap)
        if feedback is None:
            continue
        number_and_code, lower, upper = feedback.args[1:]
        scan_number, code = number_and_code & 0xffffffff, number_and_code >> 32
        edge = edges.get(scan_number)
        frame.require(scan_number==scan['frame'] and edge and edge.flags==1 and
                      (lower,upper)==(edge.a,edge.b) and scan['copy_end_tick'] < upper <= feedback.tick and
                      0 < upper-lower and (upper-lower)*n <= 4_000_000*d,
                      'driver delivery differs from the certified scan and copy')
        trusted_lower = max(lower,scan['vblank_ticks'][0],scan['copy_end_tick'])
        scan.update(driver_actual_tick_bounds=[trusted_lower,upper], frame_info_send_status=code,
                    physical_minus_target_ns_bounds=[(tick-desired)*n/d for tick in (trusted_lower,upper)])
        info = link['system_frame_info'] or {}
        if code==0 and info.get('requested_tick') is not None and info.get('actual_tick') is not None:
            requested_delta = info['requested_tick']-desired
            actual_delta = info['actual_tick']-upper
            scan['native_clock_residual_ticks'] = dict(requested=requested_delta, actual=actual_delta)
            scan['native_frame_info_roundtrip'] = (abs(requested_delta)*n<=tolerance_ns*d and
                                                   abs(actual_delta)*n<=tolerance_ns*d)

    active = {kind:[s for s in scans if s['workload']==kind and s['phase']=='active']
              for kind in ('ordinary','slow_drag')}
    status = Counter(event.args[1]>>32 for event in delivered.values())
    return dict(clock_match_tolerance_ns=tolerance_ns,accepted_target_rows=len(target), nonzero_target_rows=sum(bool(event.args[2]) for event in target.values()),
        driver_scan_rows=len(delivered), driver_send_status=dict(status),
        active={kind:dict(target=sum('CA_swap_target_tick' in s for s in lane),
                          DPU_actual=sum('driver_actual_tick_bounds' in s for s in lane),
                          FrameInfo_roundtrip=sum(s.get('native_frame_info_roundtrip',False) for s in lane))
                for kind,lane in active.items()})


def encode_spans(events):
    active = defaultdict(list)
    starts = []
    for event in events:
        if event.kind==native.ENCODE_BEGIN:
            slot = [event.tick,None]
            starts.append(slot)
            active[event.thread].append(slot)
        elif event.kind==native.ENCODE_END and active[event.thread]:
            active[event.thread].pop()[1] = event.tick
    return starts


def since_callback(events, matches, frontend, onset, n, d):
    """Attribute deadlines relative to the next exact render and report upstream observations."""
    ticks_ns = lambda tick: tick*n//d
    matches = {row['generation']:row for row in matches if row['render']}
    encode = [(ticks_ns(a),ticks_ns(b) if b is not None else None) for a,b in encode_spans(events)]
    starts = [start for start,_ in encode]
    server = [ticks_ns(event.tick) for event in events if event.kind==native.SERVER_THREAD]
    did_commit = [ticks_ns(event.tick) for event in events if event.kind==native.DID_COMMIT]
    rows = []
    for row in frontend['details']:
        stroke = row['stroke']
        limit = row['deadline_ns']
        first = onset['strokes'][stroke-1]['first_new_image_frame']
        swap = row['next_swap']
        native_render = matches.get(swap['generation']) if swap and row['next_swap_within_stroke_tail'] else None
        render_tick = ticks_ns(native_render['render']['begin_tick']) if native_render else None
        begin_tick = ticks_ns(native_render['begin_tick']) if native_render else None
        stage = ('unresolved' if render_tick is None else 'before_render' if limit < render_tick else
                 'render_before_SwapBegin' if limit < begin_tick else 'after_SwapBegin')
        selected = row['returned_main_callback']
        returned = selected['end_ns'] if selected and 'end_ns' in selected else None
        # The observer carries a measured return in microseconds. Use the
        # original callback boundary when the normalized timestamp is absent.
        if selected and returned is None:
            returned = selected['returned_us'] * 1000
        observed = 'no_callback_return'
        relative = dict()
        if returned is not None and returned <= limit:
            candidates = encode[bisect_left(starts,returned):bisect_right(starts,limit)]
            ended = [end for _,end in candidates if end is not None and end <= limit]
            if ended:
                observed = 'source_encode_ended'
                end = max(ended)
                relative['BackBoard_server_marker_after_encode'] = bisect_right(server,limit)>bisect_left(server,end)
                relative['BackBoard_did_commit_after_encode'] = bisect_right(did_commit,limit)>bisect_left(did_commit,end)
                relative['encode_end_minus_return_ns'] = end-returned
            elif candidates:
                observed = 'source_encode_incomplete_at_cutoff'
            else:
                observed = 'no_source_encode_begin_observed_after_return'
        rows.append(dict(stroke=stroke, scan=row['scan'], cutoff_ns=limit, before_first_image=bool(first and row['scan']<first),
                         following_swap=swap['generation'] if swap else None, exact_stage=stage,
                         callback_return_ns=returned, following_render_ns=render_tick,
                         callback_to_following_render_ns=render_tick-returned if returned is not None and render_tick is not None else None,
                         upstream=observed, **relative))
    first_warm = [row for row in rows if row['stroke']>=3 and row['before_first_image']]
    return dict(rows=rows, first_warm_stages=dict(Counter(row['exact_stage'] for row in first_warm)),
                first_warm_before_render_upstream=dict(Counter(row['upstream'] for row in first_warm
                                                             if row['exact_stage']=='before_render')),
                encode_spans=len(encode), server_thread_markers=len(server), did_commit_markers=len(did_commit),
                upstream_scope='Source and server trace markers show timing. They carry no common transaction or render membership identity.')
