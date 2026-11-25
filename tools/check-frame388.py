#!/usr/bin/env python3
"""Check the Gauguin DPU deadline port against restored iOS traces and Android modes."""

from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

import frame344_log as trace
from frame366_scope import MAIN, WORK, load, require, sha


BASE = WORK/'research/tmp/frame-388'
P387 = MAIN/'research/tmp/gauguin-frame387-manual-touch-worktree-20261123/research/tmp/frame-387'
ANDROID = MAIN/'research/tmp/dsh-display-modes-0272/capture/modes.log'
DTB = (MAIN/'research/tmp/gauguin-boot250-worktree-20261111/research/tmp/'
       'dsh-preflight-0251-device/memory-capture-v1/live.dtb')
PROFILE_TOOL = (MAIN/'research/tmp/gauguin-mode295-worktree-20261111/'
                'tools/gauguin-display-profile.py')
PACING_AUDIT = (MAIN/'research/tmp/gauguin-ca-receipt-analysis-worktree-20261123/research/tmp/'
                'frame387-pacing-audit/0384-0387-pacing.json')
FIXTURES = (
    ('0384', 'gauguin-early-stage', 'bcc537391ce079b7ffe2deb987e0f4caa5ecdcd2b1fe392b35e953e0df16a708'),
    ('0385', 'gauguin-frame385-ca-transaction', '26b04f6280f8dd99610fa18e9357353d2bfc306a688fd15b089841d44bb2410e'),
    ('0386', 'gauguin-frame386-ca-swipe-arm', '29238ea006a525b6dcc28be1d6e41f1cf6740d5c53f459525f26c38bb63ac655'),
    ('0387', 'gauguin-frame387-manual-touch', '0b64eed1b249e39010fcd356dddfdf94b578a177c6fe9f0993e5a50a4f81d085'),
)
RATE_TOTALS = {60: 4910, 90: 3286, 120: 2445}
REF_HS, REF_VSTART, REF_VEND = 0x01ce000c, 0x39c0, 0x1124ff


def command(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=60).stdout


def guard_constants(source):
    blank, page = (source/'bsd/dev'/name for name in ('gauguin_blank351.h', 'gauguin_page_flip.h'))
    return tuple(int(trace.one(r'\b'+key+r' = (\d+)', path.read_text(), key))
                 for path, key in ((blank, 'SCAN351_OPEN'), (blank, 'SCAN351_END_GUARD'),
                                   (page, 'F382_CUTOFF_GUARD_LINES')))


def android_modes(profile, guards):
    require(profile['selected_panel_node'] == 'qcom,mdss_dsi_j17_36_02_0a_dsc_video' and
            profile['dynamic_refresh_method'] == 'dfps_immediate_porch_mode_vfp' and
            (profile['dsi_controller'], profile['dsi_phy'], profile['sde_interface']) == (0, 0, 1),
            'J17/DSI0/PHY0/INTF1 route differs')
    contract, catalog = (profile[key] for key in ('drm_timing_contract', 'refresh_timing_catalog'))
    require(contract['matched_modes'] == 12 and contract['active_mode_key'] == [60, 136659],
            'Android source timing contract differs')
    base = profile['base_timing']
    require(tuple(base[key] for key in ('width', 'height', 'h-pulse-width', 'h-back-porch',
                                       'v-pulse-width', 'v-back-porch')) == (1080, 2400, 12, 40, 2, 30)
            and (catalog['dsc_transport_width'], catalog['lanes'], catalog['source_bits_per_pixel'],
                 catalog['compressed_bits_per_pixel']) == (360, 4, 24, 8),
            'J17 DSC payload or fixed porches differ')
    opening, fetch_guard, flip_guard = guards
    active_start = base['v-pulse-width'] + base['v-back-porch']
    active_end = active_start + base['height']
    # The pinned Lagoon catalog uses 24 prefill lines, below the 32 lines
    # between the scan edge and the active start. No advance fetch is needed.
    horizontal = 462
    line_ns = horizontal * 1e9 * 6 / 819957600
    result = {}
    for rate, total in RATE_TOTALS.items():
        by_rate = [mode for mode in catalog['modeled_modes'] if mode['reported_hz'] == rate and
                   mode['reported_clock_khz'] == 136659]
        require(len(by_rate) == 1, f'expected one same-clock {rate} Hz Android mode')
        mode, = by_rate
        require((mode['vertical_total'], mode['horizontal_total'], mode['horizontal_front_porch'],
                 mode['transport_horizontal_total'], mode['lane_bit_clock_hz']) ==
                (total, 1182, 50, horizontal, 819957600) and total - active_end == mode['vertical_front_porch'],
                f'{rate} Hz timing tuple differs')
        last = total - fetch_guard - flip_guard
        lines = max(0, last - opening + 1)
        result[rate] = dict(vfp_lines=total-active_end, vtotal=total,
            modeled_hz=mode['modeled_transport_hz'], vfp_duration_ns=round((total-active_end)*line_ns),
            legacy_flip_open=opening, legacy_flip_last=last, legacy_flip_lines=lines,
            legacy_flip_window_ns=round(lines*line_ns),
            sde_intf1_values=dict(HSYNC_CTL=horizontal << 16 | base['h-pulse-width'],
                VSYNC_PERIOD_F0=total*horizontal, DISPLAY_V_START_F0=active_start*horizontal,
                DISPLAY_V_END_F0=active_end*horizontal-1),
            dsi0_values=dict(VIDEO_MODE_TOTAL=(total-1) << 16 | (horizontal-1),
                VIDEO_MODE_ACTIVE_V=active_end << 16 | active_start))
    return result


def archive(trial, name, digest, guards):
    folder = MAIN/'research/tmp'/f'{name}-worktree-20261123'/f'research/tmp/frame-{int(trial)}/execution'
    path = folder/'kernel.log'
    require(sha(path) == digest, f'{trial} retained kernel log differs')
    terminal, restoration = (load(folder/name) for name in ('result.json', 'independent-restore.json'))
    require(terminal['trial'] == trial and terminal['boot_attempts'] == 1 and
            terminal['independent_restore_verified'] and terminal['static_root_comparison_passed'] and
            restoration['journal_empty'] and restoration['misc_original_4096_bytes_match'],
            f'{trial} lacks independent restore evidence')
    raw = path.read_text()
    count, start, end = map(int, trace.one(
        r'^SWEET F344 H: count=(\d+) reason=1 lost=0 start=(\d+) end=(\d+) numer=625 denom=12$',
        raw, 'restored frame header'))
    encoded = re.findall(r'^SWEET F344 E (.*)$', raw, re.M)
    require(0 < count < 20480 and count == len(encoded) and end-start == 864000000 and
            int(trace.one(r'^SWEET F344 F: count=(\d+) lost=0$', raw, 'restored frame footer')) == count,
            f'{trial} frame capture is incomplete')
    events = [trace.Event(*[int(value, 16) for value in record.split()]) for record in encoded]
    require(all(event.seq == i and start <= event.tick < end for i,event in enumerate(events, 1)),
            f'{trial} frame envelope differs')
    geometry, = (row for row in events if row.kind == trace.TIMING)
    window = int(trace.one(r'^SWEET F351 WINDOW: available=1 frame=\d+ end=(\d+)$', raw, 'blanking window'))
    require((geometry.a, window) == (RATE_TOTALS[60], RATE_TOTALS[60]-guards[1]),
            f'{trial} current fetch/vertical geometry changed')
    sde = trace.one(r'^SWEET F345 G: poll=1 gate=0 .*hsync=([0-9a-f]+) period=([0-9a-f]+) '
                    r'start=([0-9a-f]+) end=([0-9a-f]+)$', raw, 'programmed INTF1 timing')
    edges = sorted((row for row in events if row.kind == trace.VBLANK), key=lambda row: (row.tick,row.seq))
    require(len(edges) >= 2500 and all(row.a < row.b <= row.tick for row in edges),
            f'{trial} lacks DPU edge brackets')
    tail = RATE_TOTALS[60] - window + guards[2]
    replay = ''.join(f'{row.id} {row.flags} {row.a} {row.b} {tail}\n' for row in edges)
    return replay, tuple(int(value, 16) for value in sde), len(edges), phase_receipts(raw, trial, start, edges)


def phase_receipts(raw, trial, start, edges):
    if trial == '0387':
        require('SWEET F374: unavailable active=0' in raw and 'SWEET F380 F:' not in raw,
                '0387 phase receipt scope differs')
        return None
    rows, aligned, software, fallback, missed = map(int, trace.one(
        r'^SWEET F380 F: rows=(\d+) aligned=(\d+) software=(\d+) fallback=(\d+) missed=(\d+) '
        r'first=\d+ last=\d+$', raw, 'archived phase footer'))
    samples = re.findall(r'^SWEET F380 P: seq=(\d+) scan=(\d+) source=(\d+) o=(\d+) w=(\d+) '
                         r'p=(\d+) a=(\d+)$', raw, re.M)
    require(len(samples) == rows and [int(sample[0]) for sample in samples] == [1, *range(128, aligned+1, 128)],
            f'{trial} phase sample sequence differs')
    by_scan = trace.indexed(edges, lambda edge: edge.id, 'phase target scan')
    lead_lower = []
    for _, scan, source, observed, wake, predicted, actual in (map(int, row) for row in samples):
        require(start+observed == by_scan[source].b and observed <= wake <= actual < predicted and
                predicted-wake == 76800 and start+actual < by_scan[scan].a,
                f'{trial} CA phase sample lacks a bracketed notification')
        lead_lower.append((by_scan[scan].a-start-actual)*625//12)
    return dict(aligned=aligned, software=software, fallback=fallback, missed=missed, sampled=rows,
                minimum_certified_lead_ns=min(lead_lower))


def previous_pacing():
    require(sha(PACING_AUDIT) == 'e499f7405952f758b9838d679578384e87162f43a18d94c0a465b35e937cae1f',
            'retained pacing audit differs')
    data = load(PACING_AUDIT)
    motion = data['manual']['dense_motion_by_max_gap_in_scans']['3']
    return dict(warm_callback_to_linked_first_render_ns={
        trial: row['warm_callback_to_exact_render'] for trial,row in data['scripted'].items()},
        manual_dense_motion=motion,
        inference=('Default phase alignment had zero misses in the three scripted windows. '
                   'Observed CA render latency spans several scans, and fixed arrivals leave '
                   'gaps even with ideal presentation. Per-frame first CA update membership is pending.'))


def main():
    native = BASE/'native-kernel-final'
    source = native/'source'
    donor = P387/'native-kernel/source'
    test = WORK/'tests/gauguin-display-deadline.cpp'
    require(sha(ANDROID) == '722b541417410fe436ad6e86623df69436446d3ffadcd3ac794f0b84df245f34' and
            sha(DTB) == '0b73e7afcc926c6b691ce6612de3f2d68f04fbb6e24e54edeb4b029d3fcc08d2',
            'retained Android sources differ')
    profile = json.loads(command([sys.executable, PROFILE_TOOL, DTB, '--drm-mode-log', ANDROID]))
    properties = command(['fdtget', '-p', DTB, '/soc/qcom,mdss_mdp']).splitlines()
    require('qcom,sde-intf-max-prefetch-lines' not in properties, 'INTF1 has a prefill override')
    guards = guard_constants(source)
    modes = android_modes(profile, guards)
    expected_sde = (REF_HS, 4910*462, REF_VSTART, REF_VEND)
    require(tuple(modes[60]['sde_intf1_values'].values()) == expected_sde, 'Android SDE model differs')
    require(modes[90]['legacy_flip_lines'] > 0 and modes[120]['legacy_flip_lines'] == 0,
            'legacy flip-window outcome differs')
    phase_header = (source/'bsd/dev/gauguin_frame380_phase.h').read_text()
    require(all(int(trace.one(r'\bF380_VTOTAL_'+str(hz)+r' = (\d+)', phase_header, 'mode total')) == lines
                for hz,lines in RATE_TOTALS.items()), 'scheduler and Android mode totals differ')
    for section, key, value in (('', 'dsi_phy', 1), ('drm_timing_contract', 'matched_modes', 11),
                                ('base_timing', 'v-back-porch', 31)):
        broken = deepcopy(profile)
        (broken[section] if section else broken)[key] = value
        try:
            android_modes(broken, guards)
        except ValueError:
            continue
        raise ValueError(f'corrupt Android {key} was accepted')

    results = {}
    with TemporaryDirectory(prefix='frame388-deadline-') as tmp:
        candidate, baseline = (Path(tmp)/name for name in ('candidate', 'baseline'))
        for unit, tree, flags in ((candidate, source, []), (baseline, donor, ['-DBASELINE'])):
            command(['xcrun', 'clang++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                     '-fsanitize=address,undefined', '-I'+str(tree/'bsd/dev'), *flags, test, '-o', unit])
        for trial,name,digest in FIXTURES:
            replay, registers, count, phase = archive(trial, name, digest, guards)
            require(registers == expected_sde, f'{trial} programmed SDE differs from Android')
            old, new = (subprocess.run([unit], input=replay, capture_output=True, check=True,
                                       text=True, timeout=30).stdout for unit in (baseline,candidate))
            require(old == new and new, f'{trial} default 4 ms deadline dispatch changed')
            decisions = new.splitlines()
            results[trial] = dict(DPU_brackets=count, decisions=len(decisions),
                selected=sum(row.split()[3] == '1' for row in decisions), archived_CA_phase=phase)
    manifest = load(native/'build-manifest.json')
    require(manifest['baseline_reproduced_except_uuid'] and manifest['inputs_unchanged'] and
            manifest['kernel_sha256'] == sha(native/'candidate.kernel'), 'candidate ARM64 link differs')
    print(json.dumps(dict(state='0388-Android-display-port-offline-verified',
        native_kernel_sha256=manifest['kernel_sha256'], device_commands=0,
        calibrated_default_lead_ticks=76800, DPU_deadline_replay=results, same_clock_modes=modes,
        prior_frame_pacing=previous_pacing(),
        scope='Paired timing values and synthetic high-rate scheduler tests. Runtime DSI/SDE modesetting unqualified.'),
        indent=2))


if __name__ == '__main__':
    main()
