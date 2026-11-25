"""Retain the qualified337 collection contract, add strict342 core/notice join."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('unchanged_collection337_contract',Path(__file__).with_name('collection337.py'))
BASE=importlib.util.module_from_spec(spec);spec.loader.exec_module(BASE)


def analyze(kernel,backboard,springboard,prefix_ok,allocation,c4,identity,core,kernel_stream=None,kernel_join=None,
            *, program_slabs=False):
    # The old337 SB and collection contract remain required. In
    # particular the unique SpringBoard constructor remains337, not340.
    result=BASE.analyze(kernel,backboard,springboard,prefix_ok,allocation,c4,identity)
    if not core.get('coverage_qualified'):result['errors'].append('core342-wait-execution-coverage')
    if not core.get('worker_reuse',{}).get('observed'):result['errors'].append('worker-CPU-scratch-reuse-not-observed')
    if not core.get('CPU_accounting',{}).get('observed'):result['errors'].append('IO-CPU-accounting-not-observed')
    if not core.get('program_detail',{}).get('observed'):result['errors'].append('program-table-detail-not-observed')
    program = core.get('newbo_detail', {})
    slab_reuses = program.get('slab_reuses', 0)
    # A qualified slab row already reconciles each resident miss to a native
    # allocation or a slab reuse. An all-reuse run still exercises that path.
    reuse_only = (program_slabs and core.get('coverage_qualified') and program.get('calls') == 0
                  and type(slab_reuses) is int and slab_reuses > 0)
    if not program.get('observed') and not reuse_only:
        result['errors'].append('program-new-BO-not-observed')
    if not (kernel_stream or {}).get('coverage_qualified'):result['errors'].append('kernel-IO-stream-incomplete')
    if not (kernel_join or {}).get('coverage_qualified'):result['errors'].append('kernel-IO-identity-join-incomplete')
    expected=c4.get('complete_cb_count',0)
    if any(core.get(k)!=expected for k in ('core_records','notification_records','complete_count')):
        result['errors'].append('core342-independent-record-count')
    result['coverage_qualified']=not result['errors']
    result['state']='Q342-collection-qualified' if result['coverage_qualified'] else 'Q342-collection-unqualified'
    result['core_complete']=core.get('complete_count');result['notice_records']=core.get('notification_records')
    result['scope']=result.get('scope','The inherited337 parser rejected this collection.')+(
        ' Includes independent342 core and notification records; a new342 kernel IO stream and exact call joins are also required; SB remains337.')
    return result
