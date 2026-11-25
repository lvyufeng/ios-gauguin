#!/usr/bin/env python3
"""Run the frozen 0372 60 Hz compact transport comparison once."""

from collections import Counter
import hashlib
from importlib import import_module
from types import SimpleNamespace

from frame364_analysis import score, trace
from frame367_route import decode as decode_route
from frame369_analysis import analyze
from frame371_transport import analyze_transport
from frame372_transport import decode, snapshot_handoff, workload_scope

scope = import_module('prepare-frame372')
previous = import_module('run-frame371-trial')
scorer = previous.scorer
EXEC = scope.BASE/'execution'


def check_consent(approval, ready, plan, *, trial, flags):
    wording = previous.prior.STANDING_INSTRUCTION
    scope.require(trial==scope.TRIAL and all(approval.get(flag) is True for flag in flags) and
        not approval.get('fixture_only') and approval.get('source')=='actual-user-60Hz-standing-grant' and
        approval.get('provenance')=='direct-standing-user-instruction' and approval.get('user_answer')==wording and
        approval.get('user_answer_sha256')==hashlib.sha256(wording.encode()).hexdigest() and
        approval.get('plan_sha256')==ready['install_plan_sha256'] and
        approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
        approval.get('image_sha256')==plan['image_sha256'],'standing grant differs from 0372')


def summarize_deadline_candidates(transport):
    for row in transport['cutoff_details']:
        candidates = row.pop('candidate_transports')
        row.update(candidate_serials=[p['serial'] for p in candidates],
            by_position=dict(Counter(p['stage'] for p in candidates)),
            by_receiver_thread=dict(Counter(p['receiver_thread'] for p in candidates)))
    transport['capture'].pop('pairs')


def after_restore(execution, plan, result, before, code):
    original = scope.REFERENCE
    history = scope.load(original/'frame-pacing-0370-0371.json')['0371']
    scorer.after_restore(execution,plan,result,before,code,trial=scope.TRIAL,refs={'0371':original},
        history={'0371':history},success='0372-original-strokes-measured-root-restored')
    if not result.get('frame_trace_complete'):
        return
    try:
        proof = scope.load(execution/'independent-restore.json')
        c4 = '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'
        scope.require(proof['files'][c4]['fork']['extents']==scope.C4_EXTENTS,'0372 C4 extent proof differs')
        raw = (execution/'kernel.log').read_text()
        route = decode_route(raw)['route']
        scope.require(route and route['pipe']=='VIG0','0372 inherited scanout route differs')
        rows,strokes,numer,denom = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
        scoped = analyze(execution,begin_threads=True)
        scoped['route'] = route
        scoped['comparison_0371_0372'] = {
            '0371':previous.motion_summary(scope.load(original/'scoped-swap-timing-0371.json')),
            '0372':previous.motion_summary(scoped),
        }
        scorer.prior.timeline.write(execution/'scoped-swap-timing-0372.json',scoped,3_500_000)
    except (KeyError,ValueError) as error:
        result.update(state='0372-frame-motion-unqualified-root-restored',motion_error=str(error))
        return
    result.update(frame_score_state=result['state'],verified_warm_motion=scoped['warm_active'],
        verified_slow_motion={key:value for key,value in scoped['slow_drag'].items() if key!='identity'},
        stable_60_fps_observed=scoped['stable_60_fps_qualified'])
    try:
        frame = scope.load(execution/'frame-scanout-analysis.json')
        motion = score.parse_motion(raw,strokes,numer,denom,frame['crc_frame_calibration'])
        capture = decode(raw,numer,denom)
        workload = workload_scope(capture,strokes,motion)
        code_map = scope.load(scope.HOST.parent/'20H392-ca-code-ranges.json')
        scope.require(code_map['cache_build']=='20H392','BackBoard stage code map differs')
        snapshots = snapshot_handoff(raw,capture,scoped['swap_timing']['swap_timing'],code_map['ranges'])
        transport = analyze_transport(execution,scoped,raw,rows,numer,denom,scope.load,capture=capture)
        summarize_deadline_candidates(transport)
        transport.update(workload=workload,observed_handoff=snapshots,
            kernel_log_sha256=scope.sha(execution/'kernel.log'))
        scorer.prior.timeline.write(execution/'producer-transport-0372.json',transport,4_000_000)
    except (KeyError,ValueError) as error:
        result.update(state='0372-hardware-measured-transport-unqualified-root-restored',transport_error=str(error))
        return
    qualified = workload['complete_13_and_fixed_drag']
    result.update(state=scope.SUCCESS if qualified else '0372-transport-incomplete-root-restored',
        producer_transport_counters=capture['counters'],
        producer_transport_complete_workload=qualified,
        warm_no_swap_deadlines=transport['warm_strokes_3_to_13'],
        recv_to_swap_transaction_link_proven=snapshots['continuous_transaction_identity_verified'])


def main():
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            SimpleNamespace(check_consent=check_consent),base=scope.BASE,trial=scope.TRIAL,
            expected=scope.expected_plan,flags=scope.FLAGS,reserve=scope.RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0372 refused before device IO: '+repr(error),flush=True)
        return 2
    return import_module('run-core342-trial').execute(plan,approval,budget,scope.BASE,EXEC,
        trial=scope.TRIAL,after_restore=after_restore,success_state=scope.SUCCESS)


if __name__=='__main__':
    raise SystemExit(main())
