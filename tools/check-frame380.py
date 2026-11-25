#!/usr/bin/env python3
"""Exercise the actual predictor and scheduler on the restored 0379 DPU trace."""

import argparse
from importlib import import_module
import re
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import frame380_phase as phase
from frame344_log import TIMING, VBLANK, quantile, require

scope = import_module('prepare-frame380')
runner = import_module('run-frame379-trial')

NATIVE = r'''
#include "gauguin_frame380_phase.h"
#include <cassert>
#include <iostream>
#include <vector>

struct Bracket { uint32_t frame, step; uint64_t lo, hi; };

static void controls()
{
    const uint64_t origin = 10'000'000, period = 318'700;
    const uint32_t frame = UINT32_MAX - 7;
    f380_fit fit{};
    f380_prediction prediction{};
    for (unsigned i = 0; i < F380_HISTORY; ++i) {
        const auto tick = origin + i * period;
        assert(f380_fit_add(&fit, frame + i, tick - 500, tick + 500, &prediction) ==
               (i + 1 == F380_HISTORY));
    }
    assert(prediction.frame == frame + F380_HISTORY - 1);
    assert(prediction.period == period && prediction.edge == origin + F380_HISTORY * period);
    f380_sent sent{};
    f380_wake wake{};
    assert(!f380_pick(&prediction, &sent, prediction.observed - 1, &wake));
    assert(!f380_pick(&prediction, &sent, prediction.observed + F380_MAX_AGE + 1, &wake));
    assert(f380_pick(&prediction, &sent, prediction.observed, &wake));
    assert(wake.edge == prediction.edge && wake.edge - wake.wake == F380_LEAD);
    assert(!f380_due(&prediction, &sent, &wake, wake.wake - 1));
    assert(f380_due(&prediction, &sent, &wake, wake.wake));
    assert(!f380_due(&prediction, &sent, &wake, wake.edge));
    const f380_prediction advanced{prediction.edge + period, wake.edge, period, wake.scan};
    assert(!f380_due(&advanced, &sent, &wake, wake.edge + 1));
    sent = {wake.wake, wake.scan, true};
    assert(!f380_due(&prediction, &sent, &wake, wake.wake + 1));
    assert(!f380_can_send(&sent, sent.tick + F380_MIN_NOTIFY_GAP - 1));
    assert(f380_can_send(&sent, sent.tick + F380_MIN_NOTIFY_GAP));
    assert(f380_pick(&prediction, &sent, sent.tick, &wake));
    assert(f380_newer(wake.scan, sent.scan));
    assert(f380_newer(0, UINT32_MAX) && !f380_newer(UINT32_MAX, 0));
    auto hi = prediction.edge + 500;
    assert(!f380_fit_add(&fit, prediction.frame + 1, hi - F380_MAX_BRACKET - 1, hi, &prediction));
    assert(fit.count == 0);
    for (unsigned i = 0; i < F380_HISTORY - 1; ++i)
        assert(!f380_fit_add(&fit, frame + i, origin + i * period, origin + i * period + 1, &prediction));
    assert(!f380_fit_add(&fit, frame + F380_HISTORY, origin + F380_HISTORY * period,
                        origin + F380_HISTORY * period + 1, &prediction));
    assert(fit.count == 1);
}

int main()
{
    controls();
    uint64_t software, end, delay;
    if (!(std::cin >> software >> end >> delay)) return 0;
    std::vector<Bracket> edges;
    for (Bracket row{}; std::cin >> row.frame >> row.step >> row.lo >> row.hi;)
        edges.push_back(row);
    f380_fit fit{};
    f380_prediction prediction{};
    f380_sent sent{};
    f380_wake wake{};
    size_t i = 0;
    uint64_t retry = 0;
    unsigned misses = 0;
    for (;;) {
        const uint64_t timer = wake.wake ? wake.wake + delay : UINT64_MAX;
        const uint64_t now = software < timer ? software : timer;
        if (now >= end) break;
        while (i < edges.size() && edges[i].hi <= now) {
            const auto &row = edges[i++];
            prediction = {};
            if (row.step != 1) fit = {};
            else (void)f380_fit_add(&fit, row.frame, row.lo, row.hi, &prediction);
        }
        if (now == timer) {
            const auto pulse = wake;
            wake = {};
            if (f380_due(&prediction, &sent, &pulse, now)) {
                sent = {now, pulse.scan, true};
                misses = 0;
                std::cout << "P " << pulse.scan << ' ' << pulse.source << ' ' << pulse.wake
                          << ' ' << pulse.edge << ' ' << now << '\n';
            } else {
                std::cout << "M " << now << '\n';
                ++misses;
                retry = now + F380_FALLBACK;
            }
            if (now >= retry && misses < F380_MAX_CONSECUTIVE_MISSES)
                (void)f380_pick(&prediction, &sent, now, &wake);
        }
        if (now == software) {
            if (!wake.wake) {
                if ((now < retry || misses >= F380_MAX_CONSECUTIVE_MISSES ||
                     !f380_pick(&prediction, &sent, now, &wake)) && f380_can_send(&sent, now)) {
                    sent.tick = now;
                    std::cout << "S " << now << '\n';
                }
            }
            software += 320006; // 16,667 us on the recorded timebase
        }
    }
}
'''


def verify_source(candidate):
    relative = 'iokit/Kernel/arm/SweetFramebuffer.cpp'
    source = (candidate/relative).read_text()
    base375 = (scope.P375/'native-kernel/source'/relative).read_text()
    base379 = (scope.P379/'native-kernel/source'/relative).read_text()

    def function(text,name):
        begin = text.index('\nAppleCLCD::'+name+'(')
        end = text.index('\n}\n',begin)
        return text[begin:end]

    require(function(source,'takeBlankFrameLocked')==function(base375,'takeBlankFrameLocked') and
            'sweet_frame379_defer' not in source, '0380 did not restore 0375 take policy')
    for name in ('armVsync','readyEventFired','presentClockTickLocked','presentClockCopiedLocked',
                 'deliverFrameInfo375Locked','queueFrameInfo375','presentTimed'):
        require(function(source,name)==function(base379,name), '0380 moved original display work: '+name)
    for name in ('gauguin_copy356.h','gauguin_blank352.h','gauguin_copy379_probe.h','gauguin_frame377_slots.h'):
        require((candidate/'bsd/dev'/name).read_bytes()==
                (scope.P379/'native-kernel/source/bsd/dev'/name).read_bytes(), '0380 original copy or IPC differs')


def replay(program, delay):
    raw = (scope.REFERENCE/'kernel.log').read_text()
    start,end,n,d = runner.parent.envelope(raw)
    trace,strokes,_,_ = runner.trace.parse(raw,extra_kinds=(runner.score.PRESENT,runner.score.copy.WAKE,*runner.score.KINDS))
    require((n,d)==(625,12) and len(strokes)==13 and len(trace[TIMING])==1, '0380 reference clock differs')
    sw = int(re.search(r'^SWEET FB CLOCK: callbacks=2 .* next_beat=(\d+)',raw,re.M)[1])
    first = sw + ((start - sw + 320005)//320006)*320006
    edges = {e.id:e for e in trace[VBLANK]}
    source = f'{first} {end} {delay}\n' + ''.join(f'{e.id} {e.flags} {e.a} {e.b}\n' for e in edges.values())
    log = subprocess.check_output([str(program)],input=source,text=True,timeout=20)
    pulses = []
    notes = []
    software = misses = 0
    for line in log.splitlines():
        kind,*values = line.split()
        if kind=='P':
            scan,used,wake,predicted,tick = map(int,values)
            require(predicted-wake==phase.LEAD and tick-wake==delay and
                    edges[used].b<=wake and 1<=scan-used<=4 and (not pulses or pulses[-1][0]<scan),
                    'enqueued a duplicate or unsupported scan')
            pulses.append((scan,used,wake,predicted,tick))
            notes.append(tick)
        elif kind=='S':
            notes.append(int(values[0]))
            software+=1
        else:
            require(kind=='M','unknown host scheduler result')
            misses+=1
    require(notes and min(b-a for a,b in zip(notes,notes[1:]))>=phase.MIN_SPACING,
            'transition generated duplicate or non-monotonic notification')
    found = [(edges[scan],predicted,tick) for scan,_,_,predicted,tick in pulses
             if scan in edges and edges[scan].flags==1]
    lead = [(e.a-t)*n/d for e,_,t in found]
    errors = [max(abs(e.a-p),abs(e.b-p))*n/d for e,p,_ in found]
    if delay==0:
        samples = []
        for ordinal,(scan,used,wake,predicted,tick) in enumerate(pulses,1):
            if ordinal==1 or ordinal%phase.SAMPLE_STEP==0:
                samples.append(f'SWEET F380 P: seq={ordinal} scan={scan} source={used} '
                               f'o={edges[used].b-start} w={wake-start} p={predicted-start} a={tick-start}')
        checks = ['SWEET F380 READY: timer=1 lead=76800 history=20',*samples,
            f'SWEET F380 F: rows={len(samples)} aligned={len(pulses)} software={software} fallback=0 '
            f'missed={misses} first={pulses[0][-1]} last={pulses[-1][-1]}']
        frame = scope.load(scope.REFERENCE/'frame-scanout-analysis.json')
        motion = runner.score.parse_motion(raw,strokes,n,d,frame['crc_frame_calibration'])
        parsed = phase.phase(raw+'\n'+'\n'.join(checks)+'\n',trace,start,end,strokes,motion,n,d)
        require(parsed['qualified'] and parsed['matched_edges']==len(samples), '0380 phase receipts did not round trip')
    return dict(pulses=len(pulses),software=software,misses=misses,joined_edges=len(found),
                early_pulses=sum(x>0 for x in lead),minimum_lead_ns=min(lead,default=None),
                prediction_error_p95_upper_ns=quantile(errors,.95),max_prediction_error_upper_ns=max(errors,default=None))


def check(candidate):
    scope.check_reference()
    verify_source(candidate)
    with TemporaryDirectory(prefix='frame380-clock-') as temp:
        path = Path(temp)/'clock.cpp'
        path.write_text(NATIVE)
        program = path.with_suffix('')
        subprocess.run(['xcrun','clang++','-O2','-std=c++17','-Wall','-Wextra','-Werror',
                        '-fsanitize=address,undefined','-I',str(candidate/'bsd/dev'),
                        str(path),'-o',str(program)],check=True)
        subprocess.run([str(program)],input='',text=True,check=True)
        regular,delayed,missed = (replay(program,delay) for delay in (0,19200,76800))
    require(regular['early_pulses']>=2600 and regular['early_pulses']==regular['joined_edges'] and
            delayed['early_pulses']>=2600 and delayed['early_pulses']==delayed['joined_edges'] and
            missed['pulses']==0 and missed['misses']==3 and missed['software']>=2600,
            '0380 advance, late-callback or fallback replay differs')
    original = scope.load(scope.COMPARISON)
    for trial,scans,saved in (
        ('0375',scope.load(scope.P375/'partial-audit-0375.json')['native_alignment']['scans'],
         scope.P375/'execution/frame-scanout-analysis.json'),
        ('0379',original['native']['scans'],scope.REFERENCE/'frame-scanout-analysis.json'),
    ):
        onset = phase.onset(scans,scope.load(saved))['warm']
        require(onset['bounded_onset']==11 and (110e6 if trial=='0375' else 150e6) <
                onset['median_first_new_image_ns'][0] < (125e6 if trial=='0375' else 162e6),
                'onset audit differs from the restored controls')
    old = scope.load(scope.P379/'host-verification.json')
    projection = old['projected_ring_bound'] - 24*150 + 24*136 + 320 + 96
    require(projection<4_194_304, '0380 console reservation overflow')
    return dict(state='0380-offline-verified',patch_sha256=scope.sha(scope.PATCH),controls=21,
        original_0375_take_verified=True,original_copy_retry_FrameInfo_and_IPC_verified=True,
        replay=regular,replay_with_1ms_timer_delay=delayed,replay_with_expired_wakeup=missed,
        projected_ring_bound=projection,reference_raw_bytes=old['reference_raw_bytes'],
        device_writes=0,device_boots=0)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=scope.BASE/'native-kernel/source')
    parser.add_argument('--check-only',action='store_true')
    args = parser.parse_args()
    report = check(args.source)
    if not args.check_only:
        scope.save(scope.HOST,report)
    print(report)
