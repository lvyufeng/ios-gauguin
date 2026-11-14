#!/usr/bin/env python3
"""Distinguish arrival, long dispatch, missing spans and unavailable evidence."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sb_log',ROOT/'tools/analyze-sb-rate-log.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
ACTIVE='SWEET SB INPUT: active send_event=1 target=SpringBoard watch=1; unchanged forwarding'


def watch(us,phase=0,start=0,inputs=0,turns=0,metadata=0,writes=0):
    return f'SWEET SB WATCH: us={us} phase={phase} turn_start_us={start} inputs={inputs} turns={turns} metadata_errors={metadata} write_errors={writes}'


def summary(lines,start=1000000,end=5000000):
    return M.summarize(M.parse('\n'.join(lines)),start,end)['input']


def rejected(lines):
    try:summary(lines)
    except ValueError:return
    raise AssertionError('invalid observer log accepted')


def main():
    empty=[ACTIVE,*[watch(t) for t in range(1000000,6000000,1000000)]]
    zero=summary(empty)
    assert zero['hook_active'] and zero['watch_covers_window']
    assert zero['no_new_touch_entries_with_window_coverage'] and not zero['touch_entry_observed']
    assert not zero['gesture_acceptance_qualified'] and not zero['physical_fps_qualified']
    assert not summary(empty[1:])['no_new_touch_entries_with_window_coverage']
    assert not summary([ACTIVE.replace('send_event=1','send_event=0'),*empty[1:]])['no_new_touch_entries_with_window_coverage']
    assert not summary([*empty,'SWEET SB RATE: lost=1'])['no_new_touch_entries_with_window_coverage']
    assert not summary([*empty[:-1],watch(5000000,metadata=1)])['no_new_touch_entries_with_window_coverage']
    assert not summary([*empty[:-1],watch(5000000,writes=1)])['no_new_touch_entries_with_window_coverage']
    assert not summary([ACTIVE,watch(1000000),watch(5000000)])['watch_covers_window']
    assert not summary([ACTIVE,*empty])['hook_active']
    assert not M.summarize(M.parse('ordinary startup warnings'))['input']['touch_entry_observed']

    # One callback spans five seconds and crosses both edges of the selection.
    begin='SWEET SB INPUT: begin id=1 us=900000 event_us=899900 touches=1 phases=1 flags=0 view=FixtureView window=FixtureWindow'
    end='SWEET SB INPUT: end id=1 us=5900000 entered_us=900000 returned=1'
    slow=summary([ACTIVE,begin,*[watch(t,1,900000,1,0) for t in range(1000000,6000000,1000000)],end])
    assert slow['entries_in_window']==0 and len(slow['callback_spans'])==1
    assert slow['callback_spans_overlap_window']
    assert slow['callback_durations']['max_us']==5000000
    assert slow['watch_turn_ages']['1']['max_us']==3100000
    assert slow['callback_spans'][0]['returned']

    inside_begin=begin.replace('us=900000','us=1500000')
    inside_end=end.replace('us=5900000','us=1600000').replace('entered_us=900000','entered_us=1500000')
    arrived=summary([ACTIVE,inside_begin,inside_end])
    assert arrived['touch_entry_observed'] and arrived['main_thread_entries_in_window']==1
    assert arrived['callback_durations']['max_us']==100000
    assert not arrived['no_new_touch_entries_with_window_coverage']
    off_main=summary([ACTIVE,inside_begin.replace('flags=0','flags=8'),inside_end])
    assert off_main['touch_entry_observed'] and off_main['main_thread_entries_in_window']==0
    assert summary([ACTIVE,inside_begin,inside_end.replace('returned=1','returned=0')])['callbacks_with_original_exception']==1
    assert summary([ACTIVE,inside_begin])['unpaired_entry_ids']==[1]
    assert summary([ACTIVE,inside_end])['unpaired_end_ids']==[1]
    assert summary([ACTIVE,watch(1000000,3,0)])['watch_turn_ages']['3']['samples']==0
    after_ca=summary([ACTIVE,watch(1000000,3,500000)])
    assert after_ca['watch_turn_ages']['3']['max_us']==500000

    # A malformed record, mixed boot counter reset or mismatched span is refused.
    for bad in [inside_begin.replace('id=1','id=0'),inside_begin.replace('flags=0','flags=10'),
                inside_begin.replace('phases=1','phases=100000000'),
                inside_begin.replace('event_us=899900','event_us=18446744073709551616'),
                watch(1000000,0,1),watch(1000000,1,0),watch(1000000,2,2000000)]:
        rejected([ACTIVE,bad])
    rejected([ACTIVE,inside_begin,inside_begin])
    rejected([ACTIVE,inside_end,inside_end])
    rejected([ACTIVE,inside_begin,inside_end.replace('entered_us=1500000','entered_us=1500001')])
    rejected([ACTIVE,watch(2000000),watch(1000000)])
    rejected([ACTIVE,watch(1000000,inputs=3),watch(2000000,inputs=2)])
    rejected([ACTIVE,watch(1000000,writes=1),watch(2000000,writes=0)])
    print('PASS SpringBoard input/dispatch/watch analysis: arrival, five-second span, loss and coverage controls')


if __name__=='__main__':main()
