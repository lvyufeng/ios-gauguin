#!/usr/bin/env python3
"""Independent fixed-image, source-difference, budget and approval-gate audit."""
from pathlib import Path
import ast,hashlib,json

WORK=Path(__file__).resolve().parents[1];BASE=WORK/'research/tmp/queue-loss-337'
PRIOR=WORK.parent/'gauguin-cache-adapt-worktree-20261116/research/tmp/bo-reuse-336'
def load(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    assert not (BASE/'approval.json').exists()and not (BASE/'execution').exists()
    ready=load(BASE/'ready.json');p=load(BASE/'trial-plan.json');old=load(PRIOR/'trial-plan.json')
    assert ready['state']=='ready-q337-one-shot'and ready['pin_count']==len(ready['input_pins'])>17452
    assert ready['trial_plan_sha256']==sha(BASE/'trial-plan.json')and ready['install_plan_sha256']==sha(BASE/'slot-delta/install-plan.json')
    for path,h in ready['input_pins'].items():assert sha(path)==h,path
    expected={'state','root_header_sha256','install_plan_sha256','image','image_sha256','kernel_banner','kernel_identity',
        'EDR_helper_sha256','C4_sha256','SB_sha256','unchanged_321_C4','diagnostic_only','performance_candidate',
        'collector_changes','queue_identity_trace','capture_log_limits','collection_before_backlog_interpretation',
        'storage_reserve_bytes','unchanged_336_GPU_and_cache'}
    changed={k for k in p.keys()|old.keys()if p.get(k)!=old.get(k)}
    assert changed==expected,changed
    assert p['diagnostic_only']and not p['performance_candidate']and not p['physical_FPS_qualified']
    assert p['collector_changes']['kernel_wire_version']==2 and p['collector_changes']['SB_slots']==1024
    assert p['queue_identity_trace']['trace_max_bytes']==32769*192==6291648
    assert p['queue_identity_trace']['unobserved_interior_tickets_refused']
    assert p['capture_log_limits']==dict(backboard=22*1048576,springboard=40*1048576)
    assert p['owned_core_sha256']==old['owned_core_sha256']and p['boot_command']==old['boot_command']
    manifest=load(BASE/'local-link/build-manifest.json');parent=load(PRIOR/'local-link/build-manifest.json')
    assert len(manifest['object_replacements'])==13 and len(parent['object_replacements'])==11
    assert set(manifest['object_replacements'])-set(parent['object_replacements'])=={
        next(k for k in manifest['object_replacements']if k.endswith('/gauguin_ui_trace.o')),
        next(k for k in manifest['object_replacements']if k.endswith('/gauguin_ui_trace_board.o'))}
    for key,value in parent['object_replacements'].items():assert manifest['object_replacements'][key]==value
    assert manifest['inputs_unchanged']and manifest['baseline_relink_identical_except_LC_UUID']and manifest['link_exit']==0
    image=load(BASE/'ui337-image.json');r=load(BASE/'ui337-review.json')
    assert sha(p['image'])==p['image_sha256']==ready['image_sha256']==image['image_sha256']==r['image_sha256']
    assert p['image_sha256']=='765e7c7cc2efb84d24ee1404f94b3f866dcf98e04e6a755d53a808b35a3841f3'
    assert sha(manifest['kernel']['path'])==r['kernel_sha256']=='adc3a0bbf71cbde1b374143d6e243a9ed6d630c62228758af3447811ac2d0846'
    assert image['image_bytes']==20054016 and r['undefined_symbol_count']==0 and r['raw_MachO_segment_bytes_verified']
    assert p['kernel_identity']==image['build_identity']=='xnu-local337-d846caeab5924ac49b8ac8802e070e95'
    install=load(BASE/'slot-delta/install-plan.json')
    assert install['changed_ranges']==11 and install['install_write_bytes']==p['install_userdata_bytes']==10301440
    assert install['restore_max_write_bytes']==p['maximum_restore_userdata_bytes']==10305536
    assert p['normal_userdata_write_bytes_max']==20606976 and p['maximum_userdata_write_bytes']==51523584
    for field,receipt in [('SB_sha256','sb-qualified-v1'),('C4_sha256','c4-native-v2'),('EDR_helper_sha256','edr-native-v1')]:
        product=load(BASE/receipt/'result.json')['products']['candidate'];assert sha(product['binary'])==product['sha256']==p[field]
    assert load(BASE/'abi-v1/result.json')['total_imports']==53
    assert all(v['signature_verified']and v['extents_unchanged']for v in load(BASE/'slot-signature-review.json')['checks'])
    for name in('install','restore'):
        model=load(BASE/(name+'-model-review.json'))
        assert model['base_plan_sha256']==sha(BASE/'slot-delta/install-plan.json')and model['partial_write_failure_tested']
        assert model['rollback_verified']and model['rollback_failure_reported']and model['device_writes']==0
    bound=load(BASE/'storage-bound.json')
    assert bound['full_captures']==3 and bound['per_capture_max_bytes']==137919024
    assert bound['extra_log_copies_max_bytes']==(40+22*2+2)*1048576
    total=bound['full_captures']*bound['per_capture_max_bytes']+sum(v for k,v in bound.items()if k.endswith('_max_bytes')and k!='per_capture_max_bytes')
    assert total==bound['worst_case_bytes']==628260496<bound['reserve_bytes']==p['storage_reserve_bytes']==640*1048576
    budget=load(BASE/'storage-trial-admission.json');batch=load(BASE/'storage-whole-batch-admission.json')
    assert budget['admitted']and budget['planned_batch_bytes']==p['storage_reserve_bytes']and batch['planned_batch_bytes']==950000000
    assert budget['current_accounted_bytes']+budget['planned_batch_bytes']<=500000000000
    assert load(BASE/'collection-tests.json')['successful']and load(BASE/'analysis-order-test.json')['restoration_precedes_analysis']
    source=(WORK/'tools/run-sb-cadence-trial.py').read_text();tree=ast.parse(source)
    auth=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='authorization')
    flags=ast.literal_eval(next(n.value for n in auth.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='expected'for t in n.targets)))
    assert len(flags)==37 and {'allow_concurrent_trace_collectors','allow_queue_identity_CPU_trace'}<=set(flags)
    assert 'Q 0337 gate refused before any device command; observation classification checked'in(BASE/'gate-test.log').read_text()
    assert "'Q337-lossless-queue-CPU-observed-root-restored'"in source
    assert "elif result['legacy_observation_state']!='BC336-cache-reuse-observed-root-restored'"in source
    before=source.index('restored=True;result[\'partition_write_phase\']')
    collection=source.index("save(EXEC/'collection-analysis.json'")
    backlog=source.index('backlog=backlog_log.analyze(collection,queue_analysis,identity)')
    assert before<collection<backlog
    paths=[Path(__file__),BASE/'ready.json',BASE/'trial-plan.json',BASE/'gate-test.log',
           WORK/'docs/gauguin-queue-loss-337-trial-20261116.md',BASE/'collection-tests.log']
    result=dict(state='reviewed-Q337-frozen-collection-first-queue-identity-trial',all_pins_unchanged=True,
        pin_count=ready['pin_count'],changed_plan_keys=sorted(changed),consent_flags=37,
        independently_recomputed_runtime_bound=total,approval_absent=True,execution_absent=True,
        source_GPU_and_cache_unchanged=True,restoration_precedes_collection_gate=True,
        collection_gate_precedes_backlog_interpretation=True,device_commands=0,
        input_pins={str(q):sha(q)for q in paths})
    with (BASE/'final-review.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
