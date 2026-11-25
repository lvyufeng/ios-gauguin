#!/usr/bin/env python3
"""Exercise truncated, mixed and over-limit kernel process-sampler observations."""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('process_samples',ROOT/'tools/analyze-process-samples.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def fixture():
    lines=['SMP armed: SpringBoard,backboardd delay=220 interval=6 count=8',
           'SMP316 armed: targets=SpringBoard,backboardd delay=220 interval=6 count=8 max_targets=2 max_threads=64 frames=16 coherent_frames=0']
    for cycle in range(8):
        tick=220000000+cycle*6000000
        lines.extend([f'SMP316 begin cycle={cycle} tick={tick}',f'SMP --- sample {cycle}'])
        for name,pid,tid in [('SpringBoard',26,126),('backboardd',57,157)]:
            lines.extend([f'SMP {name}[{pid}] slide 0x40000000 mh 0x100000000',
                f'SMP {name} t0 tid {tid} st 1 ev 0xfffffe0008001000 wr -1 pc 0x1c2611030 lr 0x1c2622b18 sp 0x16f000000',
                f'SMP {name} t0 bt 0x1882fea04 0x1882d29fc'])
        lines.append(f'SMP316 end cycle={cycle} tick={tick+100} targets=2 duplicates=0')
    return '\n'.join(lines)+'\n'

def main():
    count=0;raw=fixture()
    def check(condition):
        nonlocal count;count+=1;assert condition
    def rejected(text):
        try:module.parse(text)
        except ValueError:return True
        return False
    good=module.summarize(module.parse(raw),1000,1)
    check(good['complete']and good['usable_register_samples']==16 and good['cycle_count']==8)
    check(good['cycles'][0]['begin_us']==220000000 and good['cycles'][0]['end_us']==220000100)
    check(not good['frame_walks_coherent']and not good['physical_fps_qualified'])
    check(not module.summarize(module.parse(''))['complete'])
    check(not module.summarize(module.parse(raw.replace(module.CONFIG+'\n','')))['complete'])
    check(not module.summarize(module.parse(raw.replace(module.LEGACY_CONFIG+'\n','')))['complete'])
    check(not module.summarize(module.parse(raw.rsplit('SMP316 end',1)[0]))['complete'])
    check(not module.summarize(module.parse(raw.replace('duplicates=0','duplicates=1',1)))['complete'])
    check(not module.summarize(module.parse(raw.replace('SpringBoard[26]','SpringBoard[27]',1)))['complete'])
    missing_frames=raw.replace('SMP SpringBoard t0 bt 0x1882fea04 0x1882d29fc\n','',1)
    check(not module.summarize(module.parse(missing_frames))['complete'])
    unavail=raw.replace('SMP SpringBoard t0 tid 126 st 1 ev 0xfffffe0008001000 wr -1 pc 0x1c2611030 lr 0x1c2622b18 sp 0x16f000000','SMP SpringBoard t0 tid 126 state unavailable 5',1)
    check(rejected(unavail))
    unavail=unavail.replace('SMP SpringBoard t0 bt 0x1882fea04 0x1882d29fc\n','',1)
    result=module.summarize(module.parse(unavail));check(result['unavailable_register_samples']==1 and not result['complete'])
    check(rejected(unavail.replace('state unavailable 5','state unavailable 0',1)))
    check(rejected(raw+module.CONFIG+'\n'))
    check(rejected(raw.replace(module.CONFIG+'\n','')+module.CONFIG+'\n'))
    check(rejected(raw.replace('SMP --- sample 0\n','',1)))
    check(rejected(raw.replace('begin cycle=1','begin cycle=0',1)))
    check(rejected(raw.replace('end cycle=1','end cycle=2',1)))
    check(rejected(raw.replace('tick=220000100','tick=1',1)))
    check(rejected(raw.replace('targets=2 duplicates=0','targets=1 duplicates=0',1)))
    check(rejected(raw.replace('t0 tid 126','t64 tid 126',1)))
    check(rejected(raw.replace('tid 157','tid 126',1)))
    check(rejected(raw.replace('tid 126','tid 0',1)))
    check(rejected(raw.replace('0x1882fea04 0x1882d29fc',' '.join(['0x1882fea04']*17),1)))
    check(rejected(raw.replace('wr -1','wr -2147483649',1)))
    check(rejected(raw.replace('slide 0x40000000','slide 0x10000000000000000',1)))
    check(rejected(raw.replace('pc 0x1c2611030','pc invalid',1)))
    check(rejected(raw.replace('SMP SpringBoard[26] slide 0x40000000 mh 0x100000000\n','',1)))
    split=raw.replace('SMP SpringBoard t0 bt 0x1882fea04 0x1882d29fc','SMP SpringBoard t0 bt 0x1882fea04\nSMP SpringBoard t0 bt 0x1882d29fc',1)
    check(module.summarize(module.parse(split))['complete'])
    check(rejected(split.replace('SMP SpringBoard t0 bt 0x1882d29fc','SMP SpringBoard t0 bt 0x1882d29fc\nSMP SpringBoard t0 bt',1)))
    refused=module.summarize(module.parse('SMP316 refused: reason=mixed-options\n'))
    check(not refused['complete']and refused['refused']==['mixed-options'])
    print(json.dumps(dict(state='process-sampler-parser-checks-passed',checks=count,device_commands=0)))

if __name__=='__main__':main()
