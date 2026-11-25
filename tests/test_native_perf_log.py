#!/usr/bin/env python3
"""Reject old profiles and incomplete, malformed, duplicate or failed acknowledgments."""
import hashlib
import importlib.util
import json
from pathlib import Path

WORK=Path(__file__).resolve().parents[1]
SOURCE=WORK/'tools/analyze-native-perf-log.py'
spec=importlib.util.spec_from_file_location('native_perf',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def main():
    old=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-map-query-worktree-20261115/research/tmp/map-query-324/execution/kernel.log')
    baseline=old.read_text(errors='replace')
    # Real observed ACKs with only the planned fixed request substituted.
    fixture=baseline.replace('perf_index=1 hz=253000000 bw_index=5 Bps=2188000000 option=00000000 perf=30000001 bw=00005005',
                             'perf_index=4 hz=565000000 bw_index=9 Bps=5412000000 option=00000000 perf=30000004 bw=00009009')
    good=module.analyze(fixture);assert good['active'] and not good['frequency_measured'] and not good['physical_fps_qualified']
    lines=good['lines'];cases=['',baseline,fixture+lines[-1]+'\n',fixture+'SWEET GMU DCVS: partial refused\n',
         fixture.replace(lines[0]+'\n',''),fixture.replace(lines[1]+'\n',''),fixture.replace(lines[2]+'\n',''),
         fixture.replace(lines[3]+'\n',''),fixture.replace(lines[4]+'\n',''),
         '\n'.join(reversed(lines)),fixture.replace('hz=565000000','hz=565000001'),
         fixture.replace('bw_index=9 Bps=5412000000','bw_index=5 Bps=2188000000'),
         fixture.replace('perf=30000004','perf=30000001'),fixture.replace('bw=00009009','bw=00005005'),
         fixture.replace('before=00000000 ack=80000000','before=80000000 ack=80000000'),
         fixture.replace('ack=80000000 cleared=00000000','ack=80008000 cleared=00000000'),
         fixture.replace('cleared=00000000 return=00000000','cleared=00000000 return=00000007'),
         fixture.replace('cleared=00000000 return=00000000','cleared=80000000 return=00000000')]
    for row in lines[:3]:
        cases += [fixture+row+'\n',fixture.replace(row,row.replace('/00000000','/00000001'))]
    for old_value,new in [('0022047e','0022047f'),('0022047e','0021047e'),('0022047e','0022027e'),
                          ('0022047e','0022147e'),('00300004','00200004')]:
        cases.append(fixture.replace(old_value,new))
    prior330=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-direct-load-worktree-20261116/research/tmp/direct-load-330/execution/kernel.log')
    cases.append(prior330.read_text(errors='replace'))
    for broken in cases:assert not module.analyze(broken)['active']
    accepted=fixture.replace('0022047e','fff2137e').replace('00300004','003fffff')
    assert module.analyze(accepted)['active']  # Native contract compares echoed sequence only.
    result=dict(state='passed-PERF331-native-request-parser',positive_cases=2,negative_cases=len(cases),
                synthetic_fixed_request_over_real324_ACKs=True,device_commands=0,
                input_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE,Path(__file__).resolve(),old,prior330)})
    with (WORK/'research/tmp/key-perf565-331/perf-log-test.json').open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
