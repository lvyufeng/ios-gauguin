#!/usr/bin/env python3
"""Freeze one diagnostic 0337 image after component and rollback qualification."""
from pathlib import Path
import copy,hashlib,json

WORK=Path(__file__).resolve().parents[1]
MAIN=Path('/Users/baai/Project/ios-gauguin')
BASE=WORK/'research/tmp/queue-loss-337'
PRIOR=MAIN/'research/tmp/gauguin-cache-adapt-worktree-20261116/research/tmp/bo-reuse-336'
IMAGE='765e7c7cc2efb84d24ee1404f94b3f866dcf98e04e6a755d53a808b35a3841f3'
KERNEL='adc3a0bbf71cbde1b374143d6e243a9ed6d630c62228758af3447811ac2d0846'
IDENTITY='xnu-local337-d846caeab5924ac49b8ac8802e070e95'
HELPER='6bc54af153975708b05107c51333aff545b0a4e595e048473c395551a11f735f'
C4='d4e46b8e8541d3a674a6e814170b27d4d930b5d301f25dc016b5f7c9da34b6f3'
SB='3f6dba175451498e190f17bd4043cba5a79c377127b0422c1111fe3ba38b0925'
HEADER='9c10e4ea80fcf558561a5c2c9d0593c57f07b09248c8cd460e4b617191eb0226'
COLLECTOR=dict(kernel_wire_version=2,kernel_capacity=4096,kernel_writers='atomic-reservation',
    freeze_waits_for_admitted_writers=True,late_close_errors_retained=True,SB_slots=1024,SB_producer_mutex=False,new_threads=0)
QUEUE=dict(stages=3,record_limit=32768,line_max_bytes=192,trace_max_bytes=6291648,
    per_lifetime_queue_id=True,admission_ticket=True,retire_after_explicit_release=True,
    retire_excludes_final_logging_and_block_destruction=True,unobserved_interior_tickets_refused=True)
def load(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,d):
    with Path(p).open('x')as f:json.dump(d,f,indent=2);f.write('\n')

def main():
    assert not any((BASE/n).exists()for n in('ready.json','trial-plan.json','approval.json','execution'))
    old=load(PRIOR/'ready.json');assert old['pin_count']==17452
    pins=dict(old['input_pins'])
    def pin(p,h=None):
        p=str(Path(p).resolve());h=h or sha(p)
        assert p not in pins or pins[p]==h,p
        pins[p]=h
    def receipt(p):
        data=load(p);pin(p)
        if isinstance(data,dict):
            for name,h in data.get('input_pins',{}).items():pin(name,h['sha256']if isinstance(h,dict)else h)
        return data
    restored=receipt(PRIOR/'execution/independent-restore.json')
    assert restored['state']=='independently-verified-six-original-files-and-misc'and restored['root_header_sha256']==HEADER
    assert receipt(PRIOR/'execution/result.json')['restored']
    assert receipt(PRIOR/'execution/results-review.json')['all_pins_unchanged']
    local=receipt(BASE/'local-review-v2.json')
    assert local['selected_tests_passed']and not local['boot_image_built']
    for p in local['input_pins']:receipt(p)
    assert receipt(BASE/'host-v4/result.json')['state']=='0337-actual-queues-ASan-UBSan-TSan-passed'
    native=receipt(BASE/'kernel-native-v2/result.json')
    assert native['header_config_inputs']==2133 and native['inputs_unchanged']and native['reference_files_unchanged']
    prepared=receipt(BASE/'kernel-preparation-v2/result.json')
    assert prepared['changed_files']==['bsd/dev/gauguin_ui_trace.c','bsd/dev/gauguin_ui_trace.h','bsd/dev/gauguin_ui_trace_board.c']
    manifest=receipt(BASE/'local-link/build-manifest.json');image=receipt(BASE/'ui337-image.json');review=receipt(BASE/'ui337-review.json')
    assert manifest['link_exit']==0 and manifest['inputs_unchanged']and manifest['baseline_relink_identical_except_LC_UUID']
    previous=load(PRIOR/'local-link/build-manifest.json')
    assert len(manifest['object_replacements'])==13
    assert all(manifest['object_replacements'][key]==value for key,value in previous['object_replacements'].items())
    assert set(manifest['changed_source_files'])-set(previous['changed_source_files'])=={'bsd/dev/gauguin_ui_trace.c','bsd/dev/gauguin_ui_trace_board.c'}
    assert image['build_identity']==IDENTITY and image['image_sha256']==IMAGE and image['kernel_sha256']==KERNEL
    assert sha(image['image'])==IMAGE and sha(manifest['kernel']['path'])==KERNEL
    assert image['command_changes_from_0336']==[] and image['command']==load(PRIOR/'trial-plan.json')['boot_command']
    assert review['raw_MachO_segment_bytes_verified']and review['undefined_symbol_count']==0 and not image['booted']
    pin(image['image'],IMAGE);pin(manifest['kernel']['path'],KERNEL)
    helper=receipt(BASE/'edr-native-v1/result.json');abi=receipt(BASE/'abi-v1/result.json')
    assert helper['products']['candidate']['sha256']==abi['binary_sha256']==HELPER
    assert helper['products']['baseline']['sha256']==load(PRIOR/'trial-plan.json')['EDR_helper_sha256']
    assert helper['imports_unchanged']and helper['exports_unchanged']and helper['loads_unchanged']and helper['pointer_write_and_once_contract_unchanged']
    assert abi['total_imports']==53 and not abi['missing_imports']and receipt(BASE/'edr-host-v1/result.json')['checks']==2143
    sb=receipt(BASE/'sb-qualified-v1/result.json');c4=receipt(BASE/'c4-native-v2/result.json')
    assert sb['products']['candidate']['sha256']==SB and sb['imports_20H392_qualified']and sb['checked_imports']==65
    assert c4['products']['candidate']['sha256']==C4 and c4['imports_unchanged']and c4['original_loader_order_unchanged']
    assert c4['queue_metadata_max_bytes']==QUEUE['trace_max_bytes']and c4['queue_metadata_stages']==3
    capture=receipt(BASE/'slot-capture/result.json');install=receipt(BASE/'slot-delta/install-plan.json')
    assert capture['state']=='readonly-six-file-Q337-capture'and capture['root_header_sha256']==HEADER
    assert install['state']=='prepared-six-file-Q337-cadence-delta'and install['capture_sha256']==sha(BASE/'slot-capture/result.json')
    assert install['admission_sha256']==HELPER and install['c4_sha256']==C4 and install['rows']['eagl']['new_file_sha256']==SB
    assert install['core_sha256']==load(PRIOR/'trial-plan.json')['owned_core_sha256']
    assert install['changed_ranges']==11 and install['install_write_bytes']==10301440 and install['restore_max_write_bytes']==10305536
    for name in('install','restore'):
        model=receipt(BASE/(name+'-model-review.json'))
        assert model['base_plan_sha256']==sha(BASE/'slot-delta/install-plan.json')
        assert model['rollback_verified']and model['rollback_failure_reported']and model['partial_write_failure_tested']
    signatures=receipt(BASE/'slot-signature-review.json')
    assert signatures['device_writes']==0 and len(signatures['checks'])==4 and all(r['signature_verified']for r in signatures['checks'])
    assert receipt(BASE/'analysis-order-test.json')['restoration_precedes_analysis']
    assert receipt(BASE/'collection-tests.json')['successful']
    wake=receipt(BASE/'wake-validation-test.json');logs=receipt(BASE/'log-storage-test.json')
    assert wake['negative_cases']==12 and logs['no_log_truncation']
    assert wake['executor_sha256']==logs['executor_sha256']==sha(WORK/'tools/run-sb-cadence-trial.py')
    cleanup=receipt(BASE/'cleanup337-result.json');cleanup_plan=receipt(BASE/'cleanup337-plan.json')
    assert cleanup['retired_bytes']==670556160 and cleanup['protected_pins_verified_after']
    assert cleanup['plan_sha256']==sha(BASE/'cleanup337-plan.json')
    # Cleanup's pre-change337 source pins describe the completed previous
    # milestone. They must not be merged as if they were current runtime inputs.
    # The active336 pins were separately preserved and remain in this manifest.
    for name in cleanup_plan['protected_input_pins']:
        if name.startswith(str(PRIOR)):assert Path(name).exists()
    plan=copy.deepcopy(load(PRIOR/'trial-plan.json'))
    plan.update(state='prepared-q337-one-shot',root_header_sha256=HEADER,
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),image=image['image'],image_sha256=IMAGE,
        image_bytes=image['image_bytes'],kernel_banner=image['kernel_banner'],kernel_identity=IDENTITY,
        EDR_helper_sha256=HELPER,C4_sha256=C4,SB_sha256=SB,unchanged_321_C4=False,
        diagnostic_only=True,performance_candidate=False,collector_changes=COLLECTOR,queue_identity_trace=QUEUE,
        capture_log_limits=dict(backboard=23068672,springboard=41943040),collection_before_backlog_interpretation=True,
        storage_reserve_bytes=671088640,unchanged_336_GPU_and_cache=True)
    bound=copy.deepcopy(load(PRIOR/'storage-bound.json'))
    bound.update(per_capture_max_bytes=137919024,extra_log_copies_max_bytes=90177536,reserve_bytes=671088640,
        queue_identity_analysis_max_bytes=8388608,queue_identity_result_copy_max_bytes=65536,
        queue_backlog_analysis_max_bytes=8388608,queue_backlog_result_copy_max_bytes=65536,
        collection_analysis_max_bytes=131072,collection_result_copy_max_bytes=65536,
        queue_identity_trace_max_bytes_in_existing_log_limit=6291648)
    total=bound['full_captures']*bound['per_capture_max_bytes']+sum(v for k,v in bound.items()if k.endswith('_max_bytes')and k!='per_capture_max_bytes')
    bound['worst_case_bytes']=total
    assert total==628260496<bound['reserve_bytes']
    budget=receipt(BASE/'storage-trial-admission.json');batch=receipt(BASE/'storage-whole-batch-admission.json')
    assert budget['admitted']and budget['planned_batch_bytes']==671088640
    assert batch['admitted']and batch['planned_batch_bytes']==950000000
    assert budget['current_accounted_bytes']+671088640<=500000000000
    for filename in('expected-baseline.json','capture-profile.json','kernel-identity.json','relink337.py','package337.py',
                     'review337.py','qualify337_imports.py','storage-whole-batch-components.json'):
        pin(BASE/filename)
    for p in [PRIOR/'ready.json',Path(__file__),WORK/'tools/review-queue337-trial.py',WORK/'docs/gauguin-queue-loss-337-trial-20261116.md']:
        pin(p)
    for folder in('slot-capture','slot-delta','local-link','kernel-native-v2','kernel-preparation-v2',
                   'edr-native-v1','edr-host-v1','abi-v1','sb-qualified-v1','c4-native-v2'):
        for p in (BASE/folder).rglob('*'):
            if p.is_file():pin(p)
    for folder in('tools','tests','graphics/gauguin-edr-default'):
        for p in (WORK/folder).rglob('*'):
            if p.is_file()and p.suffix in('.py','.c','.h','.m','.cpp','.inc','.hpp'):pin(p)
    pin(WORK/'xnu/patches/series');pin(WORK/'xnu/patches/0249-gauguin-concurrent-ui-trace.patch')
    for p,h in pins.items():assert sha(p)==h,p
    save(BASE/'trial-plan.json',plan);save(BASE/'storage-bound.json',bound)
    pin(BASE/'trial-plan.json');pin(BASE/'storage-bound.json')
    ready=dict(state='ready-q337-one-shot',trial_plan_sha256=sha(BASE/'trial-plan.json'),
        install_plan_sha256=sha(BASE/'slot-delta/install-plan.json'),image_sha256=IMAGE,root_header_sha256=HEADER,
        input_pins=dict(sorted(pins.items())),pin_count=len(pins),approval_pending=True,device_writes=0,boot_attempts=0)
    save(BASE/'ready.json',ready);print(json.dumps({k:v for k,v in ready.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
