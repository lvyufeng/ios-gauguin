#!/usr/bin/env python3
"""Synthetic receipt rejection tests, not GPU/rendering qualification."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from metal_probe_log import PREFIX,PHASES,qualify_probe_log,expected_hashes

BUILD='123456789abcdef012345678';CORE='a'*64
checks=0
def check(ok):
    global checks
    checks+=1;assert ok
def make_stdout(seed,hashes):
    rows=[f'{PREFIX}begin build={BUILD} core={CORE} scope=offscreen-core-not-MTLDevice',
          f'{PREFIX}memory phase=before-delay active_mb=128 inactive_mb=128 active_attr=1 inactive_attr=1 footprint=16777216',
          f'{PREFIX}identity gpu=619 chip=06010900 gmem=524288 base=100000 seed={seed}',
          f'{PREFIX}memory phase=compiled active_mb=128 inactive_mb=128 active_attr=1 inactive_attr=1 footprint=33554432']
    for i,phase in enumerate(PHASES):
        rows.extend([f'{PREFIX}submit phase={phase}',f'{PREFIX}completed phase={phase} gpu_ns=1000000 fences={i+1}',
                     f'{PREFIX}pixels phase={phase} compared={256 if phase=="compute" else 4096} hash={hashes[phase]} PASS'])
    rows.extend(f'{PREFIX}fence queue=1 value={i} complete=1' for i in range(1,9))
    rows.extend([f'{PREFIX}memory phase=completed active_mb=128 inactive_mb=128 active_attr=1 inactive_attr=1 footprint=33554432',
                 f'{PREFIX}RESULT PASS build={BUILD} seed={seed} connection-teardown-requested=1 stages=8'])
    return '\n'.join(rows)+'\n'
def make_native():
    rows=['SWEET GPU AUTH: recorded launchd compositor proxy pid=57']
    rows.extend(f'SWEET GPU USER: submit rc=0 ibs=1 submitted={i} completed={i} shadow={20+12*i} polls=1'for i in range(1,9))
    rows.extend(['SWEET GPU AUTH: compositor opened pid=57 root_fence=8']*3)
    return '\n'.join(rows)+'\n'
def reject(stdout,stderr='',native=None,**kwargs):
    try:qualify_probe_log(stdout,stderr,make_native()if native is None else native,build=kwargs.get('build',BUILD),core=kwargs.get('core',CORE))
    except ValueError:check(True);return
    raise AssertionError('invalid or stale receipt accepted')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--hashes',type=Path,required=True);a=ap.parse_args();groups={}
    for line in a.hashes.read_text().splitlines():
        seed,phase,digest=line.split();group=groups.setdefault(int(seed),{});assert phase not in group;group[phase]=digest
    check(set(groups)=={0,1,0xffffffff,0x6a09e667})
    for seed,hashes in groups.items():
        check(hashes==expected_hashes(seed));stdout=make_stdout(seed,hashes)
        result=qualify_probe_log(stdout,'compiler diagnostic\n',make_native(),build=BUILD,core=CORE)
        check(result['output_words']==28928 and result['completed_root_fences']==8 and result['compositor_opens']==3)
        check(not result['MTLDevice_qualified'] and not result['desktop_qualified'] and not result['high_refresh_qualified'])
    stdout=make_stdout(1,groups[1]);native=make_native()
    reject(stdout,build='f'*24);reject(stdout,core='b'*64)
    reject(stdout+'GAUGUIN METAL223 FAIL stage=late why=fault\n')
    reject(stdout,'GAUGUIN METAL223 FAIL stage=late why=fault\n')
    reject(stdout,stdout)
    reject(stdout+stdout);reject(stdout[:-1]+' truncated\n')
    reject(stdout.replace('seed=1','seed=4294967296'))
    reject(stdout.replace('gpu=619','gpu=635'))
    reject(stdout.replace('gmem=524288','gmem=1048576'))
    for old,new in [('active_mb=128','active_mb=6'),('inactive_mb=128','inactive_mb=6'),('active_attr=1','active_attr=0'),('footprint=33554432','footprint=134217729')]:
        reject(stdout.replace(old,new))
    for phase in PHASES:
        reject('\n'.join(l for l in stdout.splitlines()if not l.startswith(PREFIX+'pixels phase='+phase+' '))+'\n')
    reject(stdout.replace('compared=256','compared=255'))
    reject(stdout.replace('compared=4096','compared=4095',1))
    reject(stdout.replace(groups[1]['triangle'],'0'*16))
    reject(stdout.replace('fences=8','fences=7'))
    reject(stdout.replace('gpu_ns=1000000','gpu_ns=120000000000',1))
    reject(stdout.replace('value=8','value=7'))
    reject(stdout.replace('queue=1 value=8','queue=2 value=8'))
    reject(stdout.replace('complete=1\n','complete=1 interleaved\n',1))
    reject(stdout+PREFIX+'unknown event\n')
    reject(stdout.replace(PREFIX+'identity ','noise '+PREFIX+'identity '))
    lines=stdout.splitlines();i=lines.index(PREFIX+'submit phase=triangle');lines[i],lines[i+1]=lines[i+1],lines[i]
    reject('\n'.join(lines)+'\n')
    reject(stdout,native='')
    reject(stdout,native=native.replace('root_fence=8','root_fence=6'))
    reject(stdout,native=native.replace('completed=8','completed=7'))
    reject(stdout,native=native.replace('rc=0','rc=5',1))
    reject(stdout,native=native.replace('shadow=32','shadow=33'))
    reject(stdout,native=native.replace('polls=1','polls=0'))
    reject(stdout,native=native.replace('proxy pid=57','proxy pid=58'))
    reject(stdout,native=native.replace('compositor opened pid=57','compositor opened pid=0'))
    reject(stdout,native='SWEET GPU AUTH: compositor opened pid=57 root_fence=8\n'+native)
    reject(stdout,native=native+'SWEET GPU USER: submit rc=0 truncated\n')
    reject(stdout,native=native+'SWEET GPU USER: client closed after fault; DMA-visible memory/tables retained until reset\n')
    stopped=native+'SWEET GPU SERVICE: test deadline reached; no more refresh, owners retained until hardware reset\nSWEET GPU USER: client closed after fault; DMA-visible memory/tables retained until reset\n'
    check(qualify_probe_log(stdout,'',stopped,build=BUILD,core=CORE)['completed_root_fences']==8)
    print(f'PASS {checks} CPU hash/receipt/handoff rejection checks; synthetic logs only, no GPU execution')
if __name__=='__main__':main()
