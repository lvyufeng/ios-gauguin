#!/usr/bin/env python3
"""Score the restored 0388 DPU capture using hardware and exact writer receipts."""

from importlib import import_module
import json

import frame344_log as trace

trial = import_module('run-frame388-trial')
scope, stage = trial.scope, trial.stage
flip = stage.parent
crc, score = flip.crc, flip.score
PINS = {
    'result.json': 'acd0c27b139a079c6297bcffa4edab5baf2f43e00df7daac38dbc6b20fe43ce2',
    'independent-restore.json': 'a42aa547e31dfcb37d620b3a5164d2328dcd3a0488c4a2762afc23b7affcac7b',
    'restored-capture/result.json': 'bc92015a259a06d199707176a4a1e3d6e7f757367cae12f6d5f10bd4df369605',
    'kernel.log': '826001434b7ce9b68c55d488c4d07810b125aef8ef8688471c1ff8314c0e4e42',
    'kernel.log.bin': '2ba209587cb9abc478b72ffa891a08aeadd1e5d3f54e061673f63149a2a8a4a2',
    'springboard-new.log': 'df1738d16330c83baf4ac982aacb2ba8cba8b1062382b53d78d941023b7eb37f',
    'page-flip-latches.json': '3438c3762ff01f31cc7818a240f466b5486eaa499d3cab9c4277d92f05e51dbf',
    'collection-analysis.json': '918cebb62cf74c21598d59c7d3d76010d77e73da33345c8a16541cd99f341777',
    'core-wait-execution-analysis.json': '8bd26a9701ca5aaba6a3a7460143e1f6ec81f48a81a37e705982b6011b7831a8',
}


def score_archive(execution, banner, *, expected_pairs=2704, require_first=True):
    raw = (execution/'kernel.log').read_text()
    console = flip.ring_status((execution/'kernel.log.bin').read_bytes(),raw)
    recorded = scope.load(execution/'page-flip-latches.json')
    map_witness = flip.IOKIT_WC_MAP
    if recorded.get('managed_linear_slot_bytes'):
        map_witness = flip.MANAGED_LINEAR_MAP
    elif recorded.get('reserved_linear_slot_bytes'):
        map_witness = flip.RESERVED_LINEAR_MAP
    trace.require(raw.splitlines().count(banner) == 1 and console['qualified'] and
                  flip.preflight.dma_route(raw)['address_translation_bypassed_for_both'] and
                  map_witness in raw,
                  'kernel, console or scanout route witness differs')
    rows, strokes, n, d = stage.staging.parse(raw)
    edges = rows[trace.VBLANK]
    route = score.scanout.probe(raw,read_only_counts_with_crc=True)
    timing, = rows[trace.TIMING]
    trace.require((timing.a,timing.b,timing.c) == (4910,32,2431) and
                  all(check['hsync'] >> 16 == 462 and check['counter_enable'] == 0
                      for check in route['checkpoints'] if check['gate'] == 'ok'),
                  'DPU and CRC geometry differ')
    misr = crc.misr_receipts(raw,route,edges,n/d,preserve_data_preimage=True)
    pairs = crc.paired_reads(rows[trace.CRC],trace.indexed(edges,lambda row:row.id,'DPU edge'),misr,n/d)
    trace.require(misr['qualified'] and pairs and (expected_pairs is None or len(pairs) == expected_pairs)
                  and all(pair['agrees'] for pair in pairs.values()),
                  'CRC reset or pair agreement incomplete')
    evidence = flip.latch_receipts(raw,rows)
    trace.require(json.loads(json.dumps(evidence)) == recorded,
                  'recomputed latch receipts differ from the executor')
    latches = stage.staging.verified_latches(rows,evidence['accepted_by_scan'])
    offscreen = {row[2] for row in evidence['staged']}
    trace.require(all(0 < row.a < row.b <= row.tick and 0 < row.c <= trace.FRAME_BYTES for row in rows[trace.COPY]),
                  'malformed copy interval')
    front_writes = [entry for entry in score.layers_for_copies(rows,[]) if entry['end_tick'] not in offscreen]
    calibration = flip.calibration(rows,strokes,pairs,front_writes,n/d)
    trace.require(calibration['qualified'] and calibration['lag_frames'] == 0 and
                  len(calibration['dedicated_witnesses']) == 3 and calibration['marker_pixel_restored'],
                  'CRC scan-slot calibration is incomplete')
    motion = score.parse_motion(raw,strokes,n,d,calibration)
    ordinary = score.scanout.hardware(route,rows|{trace.CRC:[]},strokes,[],n,d)
    moving = score.scanout.hardware(route,rows|{trace.CRC:[]},
        [(motion['start_tick'],motion['end_tick'])],[],n,d)
    moving['windows'] = [window for window in moving['windows'] if window['window'] == 'active']
    for workload in (ordinary,moving):
        workload['windows'] = crc.summarize_windows(workload,edges,pairs,front_writes,calibration,True,n/d)
    trace.require(len(ordinary['windows']) == 26 and len(moving['windows']) == 1, 'gesture or drag window missing')
    scans = flip.scan_rows(ordinary['windows'],moving['windows'],latches)
    trace.require(all(row['crc'] != 'unknown' and (row['crc'] != 'changed' or row['frame'] in latches)
                      for row in scans), 'scored scan is unknown or changed without an exact latch')
    active = [window for window in ordinary['windows'] if window['window'] == 'active']
    metrics = dict(ordinary_active=flip.rates(active,n,d),
        warm_active=flip.rates([window for window in active if window['stroke'] >= 2],n,d),
        ordinary_release=flip.rates([window for window in ordinary['windows'] if window['window'] == 'release'],n,d),
        slow_drag=flip.rates(moving['windows'],n,d))
    start,end,*_ = trial.native.envelope(raw)
    pacing = trial.phase.phase(raw,rows,start,end,strokes,motion,n,d)
    try:
        first = stage.staging.first_frames(execution,raw,rows,strokes,n,d,scans,latches)
    except (KeyError, OSError, ValueError) as error:
        if require_first:
            raise
        first = dict(trace_error=str(error))
    gpu = trial.executor.module('restored_moving_gpu',scope.MOTION_ANALYZER).measure(rows,scans,n,d)
    return scans, dict(metrics=metrics,ca_phase=pacing,first_ordinary_frames=first,moving_GPU=gpu,
        onset=trial.phase.onset(scans,dict(hardware=ordinary,tick_numer=n,tick_denom=d)),
        early_staging=stage.staging.early_timing(raw,rows,latches,n,d),
        hardware_refresh_hz_bounds=ordinary['hardware_refresh_hz_bounds'],crc_pairs=len(pairs),crc_control=misr,
        calibration_witnesses=calibration['dedicated_witnesses'],console=console,
        drag_repeats=flip.drag_wait(scans,rows,latches))


def analyze():
    execution = scope.BASE/'execution'
    trace.require(all(scope.sha(execution/name) == digest for name,digest in PINS.items()),
                  '0388 terminal evidence differs')
    terminal, proof, restored = (scope.load(execution/name) for name in (
        'result.json','independent-restore.json','restored-capture/result.json'))
    trace.require(terminal['boot_attempts'] == 1 and terminal['observer_exit'] == 0 and terminal['restored'] and
                  terminal['independent_restore_verified'] and terminal['static_root_comparison_passed'] and
                  all(terminal['other_log_prefix_preserved'].values()) and proof['journal_empty'] and
                  proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'] and
                  proof['root_header_sha256'] == restored['root_header_sha256'] and not proof['device_writes'],
                  'independent restoration is incomplete')
    old = scope.load(scope.COMPARISON)
    old_plan = scope.load(scope.P384/'trial-plan.json')
    old_scans, reference = score_archive(scope.REFERENCE,old_plan['kernel_banner'])
    archived = stage.staging.trial_rows(old,'0384')
    reproduced = dict(scans=flip.parent.parent.paired_ordinals({'0384':old_scans}))
    trace.require(stage.staging.trial_rows(reproduced,'0384') == archived and reference['metrics'] == old['metrics'],
                  'DPU-only path did not reproduce the already qualified 0384 data')
    plan = scope.load(scope.BASE/'trial-plan.json')
    scans, candidate = score_archive(execution,plan['kernel_banner'])
    deadline = trial.deadline_receipts((execution/'kernel.log').read_text(),candidate['ca_phase'])
    trace.require(deadline['qualified'], '0388 independent deadline receipts did not qualify')
    compare = flip.parent.parent.paired_ordinals({'0384':old_scans,'0388':scans})
    stable = all(candidate['metrics'][name]['scans']['repeated'] == 0 for name in ('warm_active','slow_drag'))
    return dict(state='0388-restored-independent-DPU-and-deadline-score',device_commands=0,
        stable_60_fps_observed=stable,input_sha256=PINS,original_executor_state=terminal['state'],
        core_collection_errors=scope.load(execution/'collection-analysis.json')['errors'],
        core_record_errors=scope.load(execution/'core-wait-execution-analysis.json')['errors'],
        measurements={'0384':reference,'0388':candidate},deadline_dispatch=deadline,per_scan=compare)


if __name__ == '__main__':
    print(json.dumps(analyze(),indent=2))
