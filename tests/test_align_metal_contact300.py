#!/usr/bin/env python3
"""Check exact clock origin, skipped-beat refusal and boundary uncertainty."""

import importlib.util
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1]/'tools/align-metal-contact300.py'
spec = importlib.util.spec_from_file_location('align_metal_contact300', SOURCE)
analyzer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyzer)


def clock_row(n, skipped, origin=123456):
    next_beat = origin+(n+skipped)*320006
    return (f'SWEET FB CLOCK: callbacks={n} skipped={skipped} copies=0 '
            f'next_beat={next_beat} next_copy=0; software only\n')


def synthetic(skipped=0, origin=123456):
    start=(origin+600*320006)/19200
    metal=(f'HakiosMetal[backboardd 57]: timeline: made {start+5000:.1f} '
           f'committed {start+5001:.1f} done {start+5010:.1f} gpu 7.50\n')
    kernel=('SWEET FB CLOCK: enabled software_us=16667 beat_ticks=320006 '
            'copy_ticks=320006 held=1 physical_rate=unqualified\n'
            'SWEET FB: vsync=600 dirty=0 presents=0 client=1 px sample 4102 '
            'nonblack=1 distinct=1 colours: ffffff hz=19200000\n'
            +clock_row(600,0,origin)+clock_row(1200,skipped,origin))
    cadence={'state':'sampled-held-retirement-cadence-not-optical-fps',
             'intervals':[{'from_vsync':600,'to_vsync':1200,
                           'contact_edges':3,'held_retired':1}]}
    return kernel,metal,cadence


def rejects(fn, why):
    try:fn()
    except ValueError as error:
        assert why in str(error), (why,str(error))
    else:raise AssertionError('invalid clock/timeline was accepted')


def main():
    kernel,metal,cadence=synthetic()
    result=analyzer.align(kernel,metal,cadence)
    row=result['intervals'][0]
    assert row['state']=='aligned' and row['c4_buffers_made']==1
    assert row['c4_buffers_done_within_window']==1 and row['held_retired']==1
    assert row['contact_mask_changes']==3 and row['c4_reported_gpu_ms']==[7.5]
    kernel,metal,cadence=synthetic(skipped=1)
    assert analyzer.align(kernel,metal,cadence)['intervals'][0]['state'].startswith('not-aligned')
    kernel,metal,cadence=synthetic()
    bad=kernel.replace(clock_row(1200,0),clock_row(1200,0,123457))
    rejects(lambda:analyzer.align(bad,metal,cadence),'one absolute clock')
    bad=kernel.replace('hz=19200000','hz=24000000')
    rejects(lambda:analyzer.align(bad,metal,cadence),'timebase')
    bad=metal+'HakiosMetal[backboardd 57]: timeline: made broken\n'
    rejects(lambda:analyzer.align(kernel,bad,cadence),'malformed C4 timeline')
    print('0300 C4/FB clock alignment, skip and malformed-input controls passed')


if __name__=='__main__':
    main()
