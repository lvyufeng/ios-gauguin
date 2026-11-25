"""Retain the qualified337 collection contract, add strict339 core/notice join."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('unchanged_collection337_contract',Path(__file__).with_name('collection337.py'))
BASE=importlib.util.module_from_spec(spec);spec.loader.exec_module(BASE)


def analyze(kernel,backboard,springboard,prefix_ok,allocation,c4,identity,core):
    # Fixed337 kernel/helper/SB are intentional unchanged0339 inputs. In
    # particular the unique SpringBoard constructor remains337, not339.
    result=BASE.analyze(kernel,backboard,springboard,prefix_ok,allocation,c4,identity)
    if not core.get('coverage_qualified'):result['errors'].append('core339-wait-execution-coverage')
    expected=c4.get('complete_cb_count',0)
    if any(core.get(k)!=expected for k in ('core_records','notification_records','complete_count')):
        result['errors'].append('core339-independent-record-count')
    result['coverage_qualified']=not result['errors']
    result['state']='Q339-collection-qualified' if result['coverage_qualified'] else 'Q339-collection-unqualified'
    result['core_complete']=core.get('complete_count');result['notice_records']=core.get('notification_records')
    result['scope']=result.get('scope','The inherited337 parser rejected this collection.')+(
        ' Includes independent339 core and notification records; fixed337 kernel and SB identity remain required.')
    return result
