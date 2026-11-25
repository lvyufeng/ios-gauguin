#!/usr/bin/env python3
"""Compare raw 335/336 observations with qualified, separately recovered 337."""
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics

WORK=Path(__file__).resolve().parents[1]
MAIN=Path('/Users/baai/Project/ios-gauguin')
BASE=WORK/'research/tmp/queue-loss-337'
OUT=BASE/'recovered-analysis'


def load(path):return json.loads(path.read_text())


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def module(name,leaf):
    s=importlib.util.spec_from_file_location(name,WORK/'tools'/leaf)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def stats(values):
    v=sorted(values)
    return dict(count=len(v),median_us=statistics.median(v) if v else None,
        p95_us=v[math.ceil(.95*len(v))-1] if v else None,max_us=max(v) if v else None,
        over_16667_us=sum(n>16667 for n in v))


def main():
    collection=load(OUT/'collection-analysis.json');backlog=load(OUT/'queue-backlog-analysis.json')
    assert collection['coverage_qualified'] and backlog['state']=='Q337-identified-queue-backlog-observed'
    assert load(OUT/'result.json')['state']=='Q337-lossless-queue-CPU-observed-root-restored'
    UI=module('comparison_ui337','ui_trace_log.py');C4=module('comparison_c4','analyze-c4-queue-log.py')
    SB=module('comparison_sb','analyze-sb-rate-log.py');R=module('comparison_workload','run-sb-cadence-trial.py')
    SC=module('comparison_stage','analyze-stage-cache-log.py')
    before335=MAIN/'research/tmp/gauguin-bo-reuse-worktree-20261116/research/tmp/bo-reuse-335'
    before336=MAIN/'research/tmp/gauguin-cache-adapt-worktree-20261116/research/tmp/bo-reuse-336'
    trials={};pins={str(Path(__file__)):sha(Path(__file__))}
    for number,base,e in ((335,before335,before335/'execution'),(336,before336,before336/'execution'),(337,BASE,OUT)):
        terminal=load(e/'result.json')
        if number!=337:
            assert terminal['restored']
            assert load(e/'independent-restore.json')['state']=='independently-verified-six-original-files-and-misc'
        kernel=(e/'kernel.log').read_text(errors='replace')
        bb=(e/'backboardd.log.current').read_text(errors='replace')
        sb=(e/'springboard-new.log').read_text(errors='replace')
        assert load(base/'trial-plan.json')['kernel_banner'] in kernel
        trace=UI.parse(kernel);h=trace['header'];assert trace['clock_valid']
        wake=R.validate_wake_log(kernel);us=lambda tick:tick*h['numer']//h['denom']//1000
        begin,end=us(wake['first_stroke_tick']),us(wake['last_release_tick'])+1
        c4=C4.analyze(bb);assert c4['coverage_qualified']
        selected=[r for r in c4['buffers'] if begin<=r['made_us']<end]
        assert selected
        timing=SB.summarize(SB.parse(sb),begin,end)
        stages={k:stats([r['durations_us'][k] for r in selected]) for k in selected[0]['durations_us']}
        def detail(r):
            t={int(k):v for k,v in r['times_us'].items()}
            return dict(made_us=r['made_us'],commit_done_us=r['existing_timeline']['done_us']-t[0],
                frontend_queue_us=t[1]-t[0],turn_and_event_us=t[2]-t[1],core_commit_call_us=t[3]-t[2],
                core_call_to_callback_us=t[5]-t[2],callback_to_timeline_us=r['existing_timeline']['done_us']-t[5],
                core_status_drain_us=t[4]-t[3],status_snapshot=r['status'])
        details=[detail(r) for r in selected]
        assert all(r['existing_timeline']['gpu_us']>=0 for r in c4['buffers'])
        assert all(r['commit_done_us']==sum(r[k] for k in ('frontend_queue_us','turn_and_event_us',
                     'core_call_to_callback_us','callback_to_timeline_us')) for r in details)
        rank=sorted(details,key=lambda r:r['commit_done_us'])[math.ceil(.95*len(details))-1]
        stage_cache=SC.analyze(bb,True)
        shader_keys=sorted({r['key'] for r in stage_cache['rows'] if r['times_us']['start']<end and
                            r['times_us']['end']>begin and r['outcome']==3})
        inp=timing['input']
        item=dict(trial=number,script_window_us=[begin,end],script_buffers=len(selected),
            kernel_lost=h['lost'],SB_lost=timing['lost_rows_in_log_tail'],
            all_script_stages=stages,commit_done_us=stats([r['commit_done_us'] for r in details]),
            p95_ranked_CB=rank,status_snapshot_counts=dict(Counter(str(r['status']) for r in selected)),
            touch_entries=inp['entries_in_window'],callbacks=stats([r['duration_us'] for r in inp['callback_spans']]),
            compiled_shader_keys_in_script=shader_keys,original_verdict_preserved=True,
            whole_boot_loss_free_claim=False,physical_FPS_qualified=False)
        if number!=337:
            stored=load(e/('supplemental-analysis'+str(number)+'.json'))['after']
            assert stages==stored['queue']['all_script_stages']
            assert item['commit_done_us']==stored['timeline']['script_commit_to_done']
            assert item['touch_entries']==stored['springboard']['entries']
            assert item['callbacks']==stored['springboard']['callback_us']
            item['baseline_raw_metrics_exactly_reproduced']=True
        else:
            assert [begin,end]==collection['script_window_us'] and len(selected)==backlog['script_buffers']
            assert item['commit_done_us']['p95_us']==backlog['overall_metrics']['commit_done_us']['p95']
            assert item['all_script_stages']['frontend_queue']['p95_us']==backlog['overall_metrics']['queue_us']['p95']
            item['collection_qualified']=True
        trials[str(number)]=item
        for p in (e/'result.json',e/'kernel.log',e/'backboardd.log.current',e/'springboard-new.log',base/'trial-plan.json'):
            pins[str(p)]=sha(p)
    totals=backlog['tail_totals_us'];components=backlog['tail_predecessor_components_us']
    derived=dict(tail_count=backlog['tail_count'],tail_queue_us=totals['queue_us'],
        same_queue_body_fraction=totals['observed_same_queue_body_us']/totals['queue_us'],
        predecessor_status_drain_fraction=components['status_drain']/totals['queue_us'],
        uncovered_fraction=totals['uncovered_wait_us']/totals['queue_us'])
    old=trials['335']['p95_ranked_CB'];new=trials['336']['p95_ranked_CB']
    regression={k:new[k]-old[k] for k in ('commit_done_us','frontend_queue_us','turn_and_event_us',
                                         'core_call_to_callback_us','callback_to_timeline_us')}
    assert regression['commit_done_us']==sum(v for k,v in regression.items() if k!='commit_done_us')
    for p in (OUT/'provenance.json',OUT/'collection-analysis.json',OUT/'queue-backlog-analysis.json',
              OUT/'queue-identity-analysis.json',BASE/'execution/result.json',
              BASE/'trim-rescue/independent-six-file-restore.json',BASE/'trim-rescue/independent-metadata-restore.json'):
        pins[str(p)]=sha(p)
    result=dict(state='0337-qualified-queue-observations-with-original-failure-preserved',trials=trials,
        percentile_rank_component_change_335_to_336_us=regression,
        identified_337_tail=derived,same_workload_or_shader_causality_qualified=False,
        historical_regression_cause_proven=False,physical_FPS_qualified=False,device_commands=0,
        scope='Nearest-rank whole-script CPU elapsed including logging/scheduling. Historical p95-ranked buffers differ. '
              'Queue residence mechanism is identified in qualified337; historical caches/shader workloads are unmatched. '
              'Status3 is an intermediate snapshot. No GPU-only cost, whole-boot loss-free or panel60fps claim.',input_pins=pins)
    with (OUT/'comparison-summary.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','trials')},indent=2))
    print(json.dumps({n:{k:v for k,v in t.items() if k in ('script_buffers','kernel_lost','SB_lost','commit_done_us','p95_ranked_CB','touch_entries','compiled_shader_keys_in_script')} for n,t in trials.items()},indent=2))


if __name__=='__main__':main()
