#!/usr/bin/env python3
"""Exercise HakiOS-style SpringBoard request and run-loop log analysis."""

import importlib.util
from pathlib import Path


TARGET = Path(__file__).resolve().parents[1]/'tools/analyze-sb-rate-log.py'
SPEC = importlib.util.spec_from_file_location('analyze_sb_rate_log',TARGET)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def check():
    log = '\n'.join([
        'prefix SWEET SB RATE: active animation=1 link_fps=1 link_range=1 loop=1 flush=1; read-only',
        'SWEET SB RATE: us=1000001 kind=animation class=CAAnimation key=move min=0.0 max=0.0 preferred=0.0 caller=SpringBoard+0x10',
        'SWEET SB RATE: us=1000002 kind=link-fps asked=60 caller=QuartzCore+0x20',
        'SWEET SB RATE: us=1000003 kind=link-range min=30.0 max=60.0 preferred=60.0 caller=QuartzCore+0x30',
        'SWEET SB TURN: woke_us=1000010 before_ca_us=1000020 after_ca_us=1000025',
        'SWEET SB TURN: woke_us=1020010 before_ca_us=1020020 after_ca_us=1020100',
        'SWEET SB TURN: woke_us=1030000 before_ca_us=0 after_ca_us=1030010',
        'SWEET SB RATE: us=1060000 kind=animation class=CAAnimation key=late min=0.0 max=30.0 preferred=30.0 caller=SpringBoard+0x10',
        'SWEET SB RATE: lost=2',
    ])
    kernel = '\n'.join([
        'SWEET UI254 H: version=1 count=0 reason=1 lost=0 start=1000000000 end=1050000000 numer=1 denom=1 which=2 gestures=2',
        'SWEET UI254 F: count=0 lost=0; CPU-clock capture only',
    ])
    bounds = MOD.window_from_kernel(kernel)
    assert bounds == (1000000,1050000)
    result = MOD.summarize(MOD.parse(log),*bounds)
    assert result['observer_seen'] is True
    assert result['active_markers'] == [{'animation':True,'link_fps':True,'link_range':True,'loop':True}]
    assert result['lost_rows_in_log_tail'] == 2
    assert result['records_total'] == 7 and result['records_in_window'] == 6
    assert result['animation']['count'] == result['animation']['zero_maximum'] == 1
    assert result['display_link']['fps_request_counts'] == {'60':1}
    assert len(result['display_link']['range_rows']) == 1
    turns = result['turns']
    assert turns['count'] == 3 and turns['valid_observer_order'] == 2
    assert turns['invalid_observer_order'] == 1
    assert turns['wakeup_gaps']['max_us'] == 20000
    assert turns['wakeup_gaps']['over_16667_us'] == 1
    assert turns['observer_bracket']['max_us'] == 80
    assert turns['rows'][-1]['observer_bracket_us'] is None
    assert MOD.summarize(MOD.parse('ordinary SpringBoard log'))['observer_seen'] is False
    for bad in ('SWEET SB RATE: us=1 kind=animation class=A key=B min=nan max=60 preferred=60 caller=X',
                'SWEET SB RATE: us=1 kind=link-range min=30 max=60 preferred=bad caller=X',
                'SWEET SB TURN: woke_us=1 before_ca_us=2 after_ca_us=bad'):
        try: MOD.parse(bad)
        except ValueError: pass
        else: raise AssertionError('malformed row accepted: '+bad)
    try:MOD.summarize(MOD.parse(log),100,100)
    except ValueError:pass
    else:raise AssertionError('empty clock window accepted')
    print('SpringBoard rate/turn log analysis checks passed')


if __name__ == '__main__':
    check()
