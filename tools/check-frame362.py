#!/usr/bin/env python3
"""Exercise the candidate drag, 0361 reference and restore-before-analysis flow."""

from collections import deque
from importlib import import_module
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

import frame344_log as trace
import frame362_analysis as analysis
from frame362_scope import (BASE, CONSOLE_RESERVE, MOTION, REF361, WORK, check_budget,
    expected_plan, load, require, sha)

FIXTURE = WORK/'tests/fixtures/motion362.c'
WRITER = import_module('prepare-frame349').stage.save


def motion_program(out):
    source = BASE/'native-kernel/source/bsd/dev/sweet_touch.c'
    body = source.read_text()
    begin,end = body.index('/* The 13-stroke test'),body.index('static void\nsweet_script_abort')
    require(begin<end and body.count('if (sweet_motion_mode) sweet_motion_arm();')==1 and
            'if (sweet_script_wake_mode) sweet_frame357_calibrate_after_script();' in body,
            'motion is not scoped behind original input and calibration')
    target = out/'motion-fixture.c'
    target.write_text(FIXTURE.read_text().replace('/* MOTION_IMPLEMENTATION */',body[begin:end]))
    binary = out/'motion'
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-g','-O1','-fsanitize=undefined,address',
                    str(target),'-o',str(binary)],check=True,capture_output=True,timeout=120)
    session = subprocess.run([str(binary)],check=True,capture_output=True,text=True,timeout=20)
    require(session.stdout.count('SWEET M362: complete reports=162')==1 and
            session.stdout.count('SWEET M362: aborted')==4,'motion control coverage differs')
    (out/'motion-model.log').write_text(session.stdout)
    return dict(cases=5,source_sha256=sha(source),device_commands=0)


def extra_capacity(raw, frame):
    # Periodic vblank and CRC events are already present across the full
    # window. Use the densest four seconds of nonperiodic observed activity
    # to reserve extra space for the motion and its follow-on animation.
    records = []
    for row in raw.splitlines():
        if row.startswith('SWEET F344 E '):
            fields = row.split()[3:]
            _,tick,kind = (int(value,16) for value in fields[:3])
            if kind not in (trace.CRC,trace.VBLANK):
                records.append((tick,len(row)+1))
    num,den = frame['tick_numer'],frame['tick_denom']
    cutoff = 4_000_000_000*den//num
    pending = deque()
    peak_count = peak_bytes = total = 0
    for tick,length in sorted(records):
        pending.append((tick,length))
        total += length
        while tick-pending[0][0]>cutoff:
            total -= pending.popleft()[1]
        peak_count = max(peak_count,len(pending))
        peak_bytes = max(peak_bytes,total)
    matched = re.search(r'^SWEET F344 H: count=(\d+) reason=1 lost=0 ',raw,re.M)
    require(matched is not None and 0<peak_count+int(matched[1])<20480 and
            peak_bytes+20_000<CONSOLE_RESERVE,'motion estimate exceeds archived trace headroom')
    return dict(original_f344_rows=int(matched[1]),modeled_extra_f344_rows=peak_count,
        modeled_extra_f344_bytes=peak_bytes,motion_event_reserve_bytes=20_000,
        modeled_window_ms=4000)


def modeled_motion(raw, frame):
    num,den = frame['tick_numer'],frame['tick_denom']
    due = frame['strokes'][-1][1]+2500*analysis.MS*den//num+1000
    step_ticks = 10*analysis.MS*den//num
    limit = due+2400*analysis.MS*den//num
    samples = []
    for i in range(MOTION['normal_reports']):
        entered = due+i*(step_ticks+1500)
        returned = entered+1000
        x = 900-720*min(i,160)//160
        samples.append(f'SWEET M362: sample={i} tick={entered} returned={returned} x={x} down={int(i<=160)}')
    return raw+'\n'+f'SWEET M362: armed due={due} limit={limit} reports=162\n'+'\n'.join(samples)+(
        '\nSWEET M362: complete reports=162\n')


def replay(out, plan, *, base=BASE):
    model = analysis.measure(REF361)
    reference = load(REF361/'driver-copy-rate-comparison.json')
    require(model['driver_copy_motion_cadence']['copies_per_second']==
            reference['hakios_style']['weighted_copy_cadence_per_second'] and
            model['same_13_strokes']['active']['completed_copies']==123 and
            model['same_13_strokes']['active']['scans']==dict(changed=121,repeated=146,unknown=0) and
            model['original_stroke_core']['joined_submissions']==741 and
            model['active_repeats_without_new_swap']['scans']==64 and
            model['active_repeats_without_new_swap']['open_touch_callback']==40,
            'the new scorer does not reproduce independent 0361 evidence')
    runner = import_module('run-frame362-trial')
    try:
        runner.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,
                             static_root_comparison_passed=True),None,0)
    except ValueError as error:
        require('independent restore' in str(error),'invalid early motion gate')
    else:
        raise ValueError('0362 analysis ran before independent restore')

    fixture = import_module('check-core342-pipeline')
    scenarios = []
    with TemporaryDirectory(prefix='0362-flow-',dir=base) as temporary:
        for case in ('success','post-capture-failure','independent-failure','restore-rollback',
                     'install-rollback','final-capture-failure','observer-owner-alive','suffix-success',
                     'suffix-prefix-mismatch'):
            fixture.control_fixture(Path(temporary),plan,case,scenarios)
    raw = (REF361/'kernel.log').read_text()
    frame = load(REF361/'frame-scanout-analysis.json')
    with TemporaryDirectory(prefix='0362-motion-replay-',dir=base) as temporary:
        path = Path(temporary)
        for name in ('frame-scanout-analysis.json','core-wait-execution-analysis.json',
                     'kernel-IO-identity-analysis.json','springboard-new.log'):
            (path/name).symlink_to(REF361/name)
        fake = modeled_motion(raw,frame)
        (path/'kernel.log').write_text(fake)
        replayed = analysis.measure(path,with_motion=True)
        require('sustained_motion' in replayed, replayed.get('sustained_motion_error','missing motion score'))
        sustained = replayed['sustained_motion']
        require(sustained['scans']['changed']==sustained['completed_copies']==0 and
                not sustained['steady_60_qualified'] and sustained['known_scans']>=60,
                'static replay incorrectly qualified sustained motion')
        wrong = fake.replace('x=900 down=1','x=899 down=1',1)
        try:
            analysis.parse_motion(wrong,frame['strokes'],frame['tick_numer'],frame['tick_denom'],
                                  frame['crc_frame_calibration'])
        except ValueError:
            pass
        else:
            raise ValueError('altered fixed-motion coordinate was accepted')
    return dict(scored_original_strokes=13,reference_copy_cadence=50.291612304367135,
        reference_no_swap_scans=64,reference_open_callback=40,control_models=len(scenarios),
        archived_stationary_motion_fixture_not_qualified=True,actuation_fixture_is_synthetic=True,
        capture_headroom=extra_capacity(raw,frame),device_commands=0)


def check():
    check_budget()
    out = BASE/'frame-host'
    out.mkdir()
    report = dict(state='0362-host-candidate-and-restored-replay-qualified',
                  kernel_motion=motion_program(out),replay=replay(out,expected_plan()))
    WRITER(out/'result.json',report)
    return report


if __name__=='__main__':
    print(json.dumps(check(),indent=2))
