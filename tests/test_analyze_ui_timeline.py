#!/usr/bin/env python3
"""Check shared-clock alignment, explicit HID queue links, and missing data."""

import importlib.util
from pathlib import Path


TARGET = Path(__file__).resolve().parents[1] / 'tools' / 'analyze-ui-timeline.py'
SPEC = importlib.util.spec_from_file_location('analyze_ui_timeline', TARGET)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def kernel(lost=0):
    entries = [
        (1, 1000600000, 1, 1, 0, 0, 1000500000, 1000550000, 1),
        (2, 1000700000, 2, 1, 0, 1, 1000600000, 0, 0),
        (3, 1000800000, 5, 1000600000, 0, 1, 1, 0, 0),
        (4, 1000850000, 3, 1, 0, 1, 1000600000, 0, 0),
        (5, 1002500000, 20, 9, 0, 0, 0, 0, 0),
        (6, 1003000000, 21, 9, 0, 0, 0, 0, 0),
        (7, 1003200000, 22, 9, 0, 0, 0, 0, 0),
    ]
    lines = [f'SWEET UI254 H: version=1 count=7 reason=1 lost={lost} '
             'start=1000000000 end=1100000000 numer=1 denom=1 which=2 gestures=2']
    for seq, tick, kind, ident, pid, flags, a, b, c in entries:
        lines.append(f'SWEET UI254 E: seq={seq} tick={tick} kind={kind} id={ident} '
                     f'pid={pid} flags={flags} a={a} b={b} c={c}')
    lines.append(f'SWEET UI254 F: count=7 lost={lost}; CPU-clock capture only')
    return '\n'.join(lines)


def check():
    text = 'prefix tl: M made 1001000 committed 1001200 done 1002000 gpu 300\n'
    result = MOD.analyze(kernel(), text)
    assert result['capture']['duration_us'] == 100000
    assert result['capture']['lost'] == 0
    assert result['metal']['made_in_window'] == 1
    assert result['metal']['missing_in_window'] is False
    assert result['display']['swap_end_count'] == 1
    contact = result['hid']['contacts'][0]
    assert contact['queue_status'] == 'accepted'
    assert contact['hid_begin_to_queue_us'] == 100
    assert (contact['next_metal_made_us'], contact['next_metal_commit_us'],
            contact['next_swap_end_us'], contact['next_present_end_us']) == (500, 700, 2000, 2700)
    assert result['timeline'][0]['offset_us'] == 600
    assert result['timeline'][-1]['offset_us'] == 3200
    missing = MOD.analyze(kernel(lost=1), '')
    assert missing['capture']['lost'] == 1 and missing['metal']['missing_in_window']
    assert missing['hid']['contacts'][0]['next_metal_made_us'] is None
    rejected = MOD.analyze(kernel().replace('id=1000600000 pid=0 flags=1 a=1',
                                             'id=1000600000 pid=0 flags=0 a=1'), text)
    assert rejected['hid']['queue_enqueued'] == 0 and rejected['hid']['queue_refused'] == 1
    invalid_clock = MOD.analyze(kernel().replace('id=1 pid=0 flags=0 a=1000500000',
                                                  'id=1 pid=0 flags=1 a=0'), text)
    assert invalid_clock['hid']['contacts'][0]['next_metal_made_us'] is None
    assert MOD.summarize_gaps([0, 1000000, 2000000, 30000000]) == {
        'samples': 3, 'median_us': 1000, 'max_us': 28000, 'over_16667_us': 1}
    for bad in ('tl: M made -1 committed 2 done 3 gpu 0',
                'tl: M made 5 committed 4 done 6 gpu 1',
                'tl: M made 1 committed 2 done 3 gpu nan'):
        try:
            MOD.parse_metal(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('malformed Metal line accepted: '+bad)
    try:
        MOD.analyze(kernel().replace('denom=1', 'denom=0'), text)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid kernel timebase accepted')
    print('shared-clock UI timeline checks passed')


if __name__ == '__main__':
    check()
