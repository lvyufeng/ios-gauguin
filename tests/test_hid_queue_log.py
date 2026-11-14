#!/usr/bin/env python3
"""Queue identities, wrap, reset and invalid indices must not fake consumption."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('ui_trace',Path(__file__).resolve().parents[1]/'tools/ui_trace_log.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def parse(rows):
    n=len(rows)
    lines=[f'SWEET UI254 H: version=1 count={n} reason=1 lost=0 start=100 end=1000 numer=1 denom=1 which=1 gestures=1']
    for i,(ident,pid,flags,head,tail,capacity,notifications) in enumerate(rows,1):
        lines.append(f'SWEET UI254 E: seq={i} tick={100+i} kind=31 id={ident} pid={pid} flags={flags} a={(head<<32)|tail} b={capacity} c={notifications}')
    lines.append(f'SWEET UI254 F: count={n} lost=0; CPU-clock capture only')
    return M.parse('\n'.join(lines))


def main():
    sample=parse([(1,57,3,0,36,256,1),(2,57,3,100,136,256,8),
                  (1,57,3,36,72,256,2),(2,57,1,100,172,256,8),(1,57,3,0,36,256,3)])
    a,b=sample['queue_state_summary']
    assert a['queue_registry_id']==1 and a['head_changes_observed']==2 and a['consumer_index_progress_observed']
    assert a['notification_attempt_delta']==2 and a['nonnull_port_samples']==3
    assert b['queue_registry_id']==2 and b['head_changes_observed']==0 and not b['consumer_index_progress_observed']
    assert b['nonnull_port_samples']==1 and b['notification_attempt_delta']==0
    assert not sample['physical_touch_qualified']
    for rows in [[(1,57,3,0,36,256,1),(1,26,3,36,72,256,2)],
                 [(1,57,3,0,36,256,1),(1,57,3,36,72,512,2)],
                 [(1,57,3,0,36,256,2),(1,57,3,36,72,256,1)],
                 [(1,57,3,0,36,256,1),(1,57,3,257,72,256,2)]]:
        result=parse(rows)['queue_state_summary'][0]
        assert not result['state_consistent'] and not result['consumer_index_progress_observed']
    for bad in [(0,57,3,0,36,256,1),(1,57,4,0,36,256,1),(1,57,3,0,36,0,1)]:
        try:parse([bad])
        except ValueError:pass
        else:raise AssertionError('invalid queue observation accepted')
    assert parse([])['queue_state_summary']==[]
    print('PASS HID queue identity/progress parser: no cross-queue, reset or wrap inference')


if __name__=='__main__':main()
