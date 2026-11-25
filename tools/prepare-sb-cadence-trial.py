#!/usr/bin/env python3
"""Freeze one BO333 CPU allocation diagnostic against independently restored0332."""
from pathlib import Path
import copy,hashlib,json
MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/bo-allocation-333'
PRIOR=MAIN/'research/tmp/gauguin-present-retry-worktree-20261116/research/tmp/present-retry-332'
CORE_BASE=MAIN/'research/tmp/gauguin-key-perf565-worktree-20261116/research/tmp/key-perf565-331'
HEADER='059102aec366fd57b104f571bd1074cc5938eb9882f9df266447f75621300cc3'
CORE='1e48b6f1b375519af151db4d09ccf368a56c969cd8ae8305a48c540a2e0eb681'
RESERVE=536870912
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,d):
    with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
def main():
    assert not any((STATE/n).exists() for n in ('ready.json','trial-plan.json','approval.json','execution'))
    assert sha(PRIOR/'ready.json')=='e28d920ead32342b01e186d4efde1b96be96a2742fb3d690104fee234550d89b'
    old=load(PRIOR/'ready.json');assert old['state']=='ready-present332-one-shot' and old['pin_count']==15569
    pins=dict(old['input_pins'])
    def pin(p,h=None):
        p=str(Path(p).resolve());h=h or sha(p);assert p not in pins or pins[p]==h,p;pins[p]=h
    def receipt(p):
        d=load(p);pin(p)
        for path,h in d.get('input_pins',{}).items():
            if isinstance(h,dict):
                assert Path(path).stat().st_mtime_ns==h['mtime_ns'];h=h['sha256']
            pin(path,h)
        return d
    terminal=receipt(PRIOR/'execution/result.json');independent=receipt(PRIOR/'execution/independent-restore.json')
    assert sha(PRIOR/'execution/result.json')=='46f2fa9137cb084ecdd2a302b85e961fe04c843c5b9e4781b6a3211c85945215'
    assert terminal['state']=='PRESENT332-display-retry-observed-root-restored' and terminal['restored'] and terminal['boot_attempts']==1
    assert independent['state']=='independently-verified-six-original-files-and-misc' and independent['misc_original_4096_bytes_match'] and independent['root_header_sha256']==HEADER
    expected=receipt(STATE/'expected-baseline.json');assert expected==load(PRIOR/'execution/restored-capture/result.json') and expected['root_header_sha256']==HEADER
    profile=receipt(STATE/'capture-profile.json');assert profile['expected_header_sha256']==HEADER and profile['files']==load(PRIOR/'capture-profile.json')['files'] and profile['trial_instance']=='bo-allocation-333'
    capture=receipt(STATE/'slot-capture/result.json');install=receipt(STATE/'slot-delta/install-plan.json')
    assert capture['state']=='readonly-six-file-BO333-capture' and capture['root_header_sha256']==HEADER and capture['baseline_sha256']==sha(STATE/'expected-baseline.json')
    assert install['state']=='prepared-six-file-BO333-cadence-delta' and install['root_header_sha256']==HEADER and install['capture_sha256']==sha(STATE/'slot-capture/result.json')
    assert len(capture['files'])==len(install['rows'])==6 and install['changed_ranges']==11 and install['install_write_bytes']==10301440 and install['restore_max_write_bytes']==10305536
    assert install['written_catalog_groups']==install['read_catalog_groups']==5 and install['core_sha256']==CORE
    for name,row in install['rows'].items():
        prior=load(PRIOR/'slot-delta/install-plan.json')['rows'][name]
        assert row['old_file_sha256']==prior['old_file_sha256'] and row['data_blocks']==prior['data_blocks']
        if name!='admission':assert row['new_file_sha256']==prior['new_file_sha256']
    core=receipt(CORE_BASE/'core-native-v1/result.json')
    assert core['products']['candidate']['sha256']==CORE and core['inputs_unchanged'] and core['all_core_TUs_recompiled']
    assert install['core_receipt_sha256']==sha(CORE_BASE/'core-native-v1/result.json');pin(core['products']['candidate']['binary'],CORE)
    source=receipt(STATE/'source-preparation.json');policy=receipt(STATE/'allocation-policy.json')
    assert source['state']=='prepared-BO333-CPU-allocation-phases' and source['changed_files']==['iokit/Kernel/arm/GauguinGPU.cpp','bsd/dev/gauguin_ui_trace.h']
    assert source['source_change_reversible'] and source['original_validators_waits_ownership_preserved']
    assert source['maximum_trace_records_per_new_BO']==6 and source['trace_capacity_unchanged']==4096 and source['trace_window_seconds_unchanged']==4
    assert source['new_GPU_commands']==source['new_MMIO_reads']==source['new_threads']==source['new_allocations_in_producer']==0
    assert receipt(STATE/'patch-replay-v1/result.json')['state']=='BO333-patch-forward-reverse-exact'
    native=receipt(STATE/'kernel-native-v1/result.json');host=receipt(STATE/'host-v1/result.json');trace=receipt(STATE/'trace-host-v1/result.json')
    assert native['state']=='passed-native-ARM64-selected-TUs' and native['inputs_unchanged'] and native['reference_files_unchanged']
    assert len(native['results'])==1 and native['results'][0]['file']=='iokit/Kernel/arm/GauguinGPU.cpp'
    assert host['state']=='BO333-actual-IOUserClient-equivalence-and-phase-contract-passed' and host['paired_request_observations']==6900 and host['parent_candidate_observations_identical'] and host['inputs_unchanged']
    assert trace['state']=='passed-actual-core-and-board-host' and trace['inputs_unchanged']
    parser=receipt(STATE/'allocation-log-test.json');assert parser['positive_cases']==3 and parser['negative_cases']==30 and parser['actual332_log_rejected']
    image=receipt(STATE/'ui333-image.json');review=receipt(STATE/'ui333-review.json');pin(image['image'],image['image_sha256'])
    assert image['image_sha256']==review['image_sha256']=='373f3bbef16104e5dd08617c6fcfde2d4dc07217a170abde0063a2052af39939'
    assert image['inputs_unchanged'] and not image['booted'] and image['command_changes_from_0332']==[] and review['undefined_symbols_unchanged'] and review['raw_MachO_segment_bytes_verified']
    manifest=receipt(STATE/'local-link/build-manifest.json');parent=load(PRIOR/'local-link/build-manifest.json')
    assert manifest['inputs_unchanged'] and manifest['baseline_relink_identical_except_LC_UUID'] and manifest['kernel']['sha256']==image['kernel_sha256']=='78cafe8198bd38f4ecf75b015afa5acfc8d73301438e907db7a11732a0955807'
    assert len(manifest['object_replacements'])==11 and manifest['build_identity']['id']==image['build_identity']=='xnu-local333-d4c7c2f6b8d9455ba5120f81dd7f535a'
    changed=[k for k,v in manifest['object_replacements'].items() if v!=parent['object_replacements'][k]];assert len(changed)==1 and changed[0].endswith('/GauguinGPU.cpo')
    previous={name:digest for name,kind,digest in parent['source_union']['entries']}
    assert {name for name,kind,digest in manifest['source_union']['entries'] if previous[name]!=digest}==set(source['changed_files'])
    helper=receipt(STATE/'edr-native-v1/result.json');helper_host=receipt(STATE/'edr-host-v2/result.json');abi=receipt(STATE/'abi-v2/result.json')
    assert helper['state']=='native-EDR333-kernel-scope-baseline-reproduced-candidate-signed' and helper['inputs_unchanged']
    assert helper['products']['baseline']['sha256']=='5cce66b7fae4e2cdf374b088b7a9bbc16ce7bbf72fb59ddbd3df73aca55977fd'
    assert helper['products']['candidate']['sha256']=='c9c7932dd37ae25375f1f54ec91e4dc9a008aedc89f6ae660535359cf939ad2d'
    assert helper['image_sha256']==image['image_sha256'] and helper['pointer_write_and_once_contract_unchanged'] and helper['imports_unchanged'] and helper['loads_unchanged'] and helper['exports_unchanged']
    assert helper_host['checks']==2143 and not helper_host['sanitizer_stderr'] and abi['binary_sha256']==helper['products']['candidate']['sha256'] and abi['total_imports']==53 and not abi['missing_imports']
    for name in ('install','restore'):
        model=receipt(STATE/(name+'-model.log'));assert model['base_plan_sha256']==sha(STATE/'slot-delta/install-plan.json')
        assert model['device_writes']==model['device_boots']==0 and model['partial_write_failure_tested'] and model['rollback_verified'] and model['rollback_failure_reported']
    order=receipt(STATE/'analysis-order-test.json');assert order['state']=='BO333-diagnostics-and-samples-saved-before-observed-negative-timeline-failure' and order['strict_negative_M_refusal_preserved'] and order['original326_result_unchanged']
    wake=receipt(STATE/'wake-validation-test.json');logs=receipt(STATE/'log-storage-test.json')
    assert wake['positive_cases']==2 and wake['negative_cases']==12 and wake['executor_sha256']==logs['executor_sha256']==sha(WORK/'tools/run-sb-cadence-trial.py') and logs['no_log_truncation']
    oldplan=load(PRIOR/'trial-plan.json');assert old['trial_plan_sha256']==sha(PRIOR/'trial-plan.json') and image['command']==oldplan['boot_command']
    assert install['admission_sha256']==helper['products']['candidate']['sha256'] and install['c4_sha256']==oldplan['C4_sha256']
    bound=copy.deepcopy(load(PRIOR/'storage-bound.json'));assert bound['worst_case_bytes']==522747536 and bound['reserve_bytes']==RESERVE
    bound.update(BO_allocation_analysis_max_bytes=4194304,BO_allocation_result_copy_max_bytes=65536,worst_case_bytes=527007376);assert bound['worst_case_bytes']<RESERVE
    admission=receipt(STATE/'storage-trial-admission.json');assert admission['admitted'] and admission['planned_batch_bytes']==RESERVE and admission['current_accounted_bytes']+RESERVE<=500000000000
    receipt(PRIOR/'cleanup333-plan.json');receipt(PRIOR/'cleanup333-result.json')
    paths=[Path(__file__),WORK/'tools/review-bo-allocation-trial.py',PRIOR/'ready.json',PRIOR/'storage-next333-admission.json',STATE/'storage-whole-batch-admission.json',WORK/'docs/gauguin-bo-allocation-333-trial-20261116.md']
    paths+=list((PRIOR/'execution/restored-capture').glob('*'))
    paths+=[PRIOR/'execution'/n for n in ('supplemental-analysis332.json','kernel-interval-analysis332.json','display-delivery332.json','process-round-alignment332.json','owned-core-symbol-inference332.json','compiler-workload332.json')]
    for pattern in ('tools/*sb-cadence*.py','tests/test_sb_cadence*.py','tools/*bo*allocation*.py','tests/test_bo_allocation*.py','tools/*present*retry*.py','tests/test_present_retry*.py','tests/fixtures/present_retry*.cpp'):
        paths+=list(WORK.glob(pattern))
    for name in ('sb_cadence_launch.py','analyze-process-samples328.py','analyze-process-samples.py','analyze-submit-reject-log.py','analyze-stage-cache-log.py','analyze-c4-queue-log.py','analyze-sb-rate-log.py','analyze-sb-stack-log.py','analyze-ui-timeline.py','ui_trace_log.py','analyze-map-query-log.py','analyze-native-perf-log.py'):
        file=WORK/'tools'/name
        if name!='ui_trace_log.py':assert sha(file)==sha(PRIOR.parents[2]/'tools'/name),name
        paths.append(file)
    for folder in ('slot-capture','slot-delta','kernel-native-v1','host-v1','trace-source-v1','trace-host-v1','edr-native-v1','edr-host-v2','abi-v2','patch-replay-v1','local-link'):
        paths += [p for p in (STATE/folder).rglob('*') if p.is_file()]
    paths += list(STATE.glob('*.py'))+[STATE/'kernel-identity.json']
    for p in paths:pin(p)
    for p,h in pins.items():assert sha(p)==h,p
    plan=copy.deepcopy(oldplan)
    plan.update(state='prepared-bo333-one-shot',root_header_sha256=HEADER,install_plan_sha256=sha(STATE/'slot-delta/install-plan.json'),image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_banner=image['kernel_banner'],kernel_identity=image['build_identity'],boot_command=image['command'],EDR_helper_sha256=helper['products']['candidate']['sha256'],diagnostic_only=True,performance_candidate=False,BO_allocation_diagnostics=policy)
    assert plan['device_writes']==plan['boot_attempts']==0 and not plan['physical_FPS_qualified']
    assert plan['normal_userdata_write_bytes_max']==plan['install_userdata_bytes']+plan['maximum_restore_userdata_bytes']==20606976
    assert plan['maximum_userdata_write_bytes']==plan['install_userdata_bytes']+4*plan['maximum_restore_userdata_bytes']==51523584
    save(STATE/'trial-plan.json',plan);save(STATE/'storage-bound.json',bound)
    for p in (STATE/'trial-plan.json',STATE/'storage-bound.json'):pin(p)
    ready=dict(state='ready-bo333-one-shot',trial_plan_sha256=sha(STATE/'trial-plan.json'),install_plan_sha256=sha(STATE/'slot-delta/install-plan.json'),image_sha256=plan['image_sha256'],root_header_sha256=HEADER,input_pins=dict(sorted(pins.items())),pin_count=len(pins),approval_pending=True,device_writes=0,boot_attempts=0)
    save(STATE/'ready.json',ready);print(json.dumps({k:v for k,v in ready.items() if k!='input_pins'},indent=2))
if __name__=='__main__':main()
