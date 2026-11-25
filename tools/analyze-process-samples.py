#!/usr/bin/env python3
"""Parse bounded SMP316 process samples without claiming coherent frame walks."""
import argparse
import collections
import json
from pathlib import Path
import re

TARGETS=('SpringBoard','backboardd')
CONFIG='SMP316 armed: targets=SpringBoard,backboardd delay=220 interval=6 count=8 max_targets=2 max_threads=64 frames=16 coherent_frames=0'
LEGACY_CONFIG='SMP armed: SpringBoard,backboardd delay=220 interval=6 count=8'
BEGIN=re.compile(r'SMP316 begin cycle=(\d+) tick=(\d+)$')
END=re.compile(r'SMP316 end cycle=(\d+) tick=(\d+) targets=(\d+) duplicates=(\d+)$')
HEADER=re.compile(r'SMP (SpringBoard|backboardd)\[(\d+)\] slide (0x[0-9a-f]+) mh (0x[0-9a-f]+)$')
REGISTERS=re.compile(r'SMP (SpringBoard|backboardd) t(\d+) tid (\d+) st (-?\d+) ev (0x[0-9a-f]+) wr (-?\d+) pc (0x[0-9a-f]+) lr (0x[0-9a-f]+) sp (0x[0-9a-f]+)$')
UNAVAILABLE=re.compile(r'SMP (SpringBoard|backboardd) t(\d+) tid (\d+) state unavailable (-?\d+)$')
FRAMES=re.compile(r'SMP (SpringBoard|backboardd) t(\d+) bt((?: 0x[0-9a-f]+)*)$')

def integer(value,signed=False):
    result=int(value,16 if value.startswith('0x') else 10)
    if signed:
        if not -(1<<31)<=result<(1<<31):raise ValueError('signed sampler field overflow')
    elif not 0<=result<(1<<64):raise ValueError('sampler field overflow')
    return result

def parse(text):
    active=legacy=0;refused=[];cycles=[];cycle=task=thread=None
    tids=set()
    for original in text.splitlines():
        at=original.find('SMP316 ')
        if at<0:at=original.find('SMP ')
        if at<0:continue
        line=original[at:]
        if line==CONFIG:
            if cycles:raise ValueError('sampler activation follows observations')
            active+=1
            if active>1:raise ValueError('multiple sampler activations')
            continue
        if line==LEGACY_CONFIG:
            if active or cycles:raise ValueError('legacy configuration out of order')
            legacy+=1
            if legacy>1:raise ValueError('multiple legacy sampler activations')
            continue
        if line in ('SMP316 refused: reason=profile','SMP316 refused: reason=mixed-options'):
            refused.append(line.rsplit('=',1)[1]);continue
        m=BEGIN.fullmatch(line)
        if m:
            index,tick=map(integer,m.groups())
            if cycle is not None or index!=len(cycles) or index>=8:
                raise ValueError('missing, duplicate or reordered sampler cycle')
            if cycles and tick<cycles[-1]['end_tick']:raise ValueError('sampler clock regression')
            cycle=dict(index=index,begin_tick=tick,end_tick=None,legacy_marker=False,tasks={},closed=False)
            cycles.append(cycle);task=thread=None;tids=set();continue
        m=END.fullmatch(line)
        if m:
            index,tick,targets,duplicates=map(integer,m.groups())
            if cycle is None or index!=cycle['index'] or tick<cycle['begin_tick']:
                raise ValueError('orphan sampler end or reversed clock')
            if targets>2 or targets!=len(cycle['tasks']):raise ValueError('sampler target count mismatch')
            cycle.update(end_tick=tick,target_count=targets,duplicate_targets=duplicates,closed=True)
            cycle=task=thread=None;continue
        m=re.fullmatch(r'SMP --- sample (\d+)',line)
        if m:
            if cycle is None or integer(m[1])!=cycle['index'] or cycle['legacy_marker']:
                raise ValueError('legacy cycle marker mismatch')
            cycle['legacy_marker']=True;continue
        m=HEADER.fullmatch(line)
        if m:
            name=m[1];pid,slide,mh=map(integer,m.group(2,3,4))
            if cycle is None or not cycle['legacy_marker']or name in cycle['tasks'] or not 0<pid<(1<<31):
                raise ValueError('orphan or duplicate target header')
            task=dict(name=name,pid=pid,slide=slide,mach_header=mh,threads=[])
            cycle['tasks'][name]=task;thread=None;continue
        m=REGISTERS.fullmatch(line)or UNAVAILABLE.fullmatch(line)
        if m:
            name=m[1];index,tid=map(integer,m.group(2,3))
            if task is None or name!=task['name'] or index!=len(task['threads'])or index>=64 or not tid or tid in tids:
                raise ValueError('orphan, duplicate or out-of-bounds thread')
            tids.add(tid)
            if len(m.groups())==4:
                error=integer(m[4],True)
                if not error:raise ValueError('success code in unavailable state')
                thread=dict(index=index,tid=tid,available=False,error=error,frames=[],frame_chunks=0)
            else:
                thread=dict(index=index,tid=tid,available=True,state=integer(m[4],True),wait_event=integer(m[5]),
                            wait_result=integer(m[6],True),pc=integer(m[7]),lr=integer(m[8]),sp=integer(m[9]),
                            frames=[],frame_chunks=0)
            task['threads'].append(thread);continue
        m=FRAMES.fullmatch(line)
        if m:
            name=m[1];index=integer(m[2])
            if task is None or thread is None or name!=task['name']or index!=thread['index']or not thread['available']:
                raise ValueError('orphan frames or frames after unavailable state')
            values=[integer(v)for v in m[3].split()]
            if thread['frame_chunks']and(not values or not thread['frames']):
                raise ValueError('empty continuation frame chunk')
            if len(thread['frames'])+len(values)>16 or thread['frame_chunks']>=2:
                raise ValueError('sampler frame/chunk bound exceeded')
            thread['frames'].extend(values);thread['frame_chunks']+=1;continue
        raise ValueError('malformed or unexpected sampler row')
    return dict(active_markers=active,legacy_markers=legacy,refused=refused,cycles=cycles)

def summarize(parsed,numer=None,denom=None):
    if (numer is None)!=(denom is None)or(numer is not None and not 0<numer<(1<<64))or(denom is not None and not 0<denom<(1<<64)):
        raise ValueError('invalid sampler timebase')
    missing=[];partial=[];duplicates=[];limits=[];unavailable=0;available=0;usable=0;pids=collections.defaultdict(set)
    cycles=parsed['cycles']
    for cycle in cycles:
        if not cycle['closed']or not cycle['legacy_marker']:partial.append(cycle['index'])
        if cycle.get('duplicate_targets',0):duplicates.append(cycle['index'])
        for name in TARGETS:
            task=cycle['tasks'].get(name)
            if task is None:missing.append(dict(cycle=cycle['index'],target=name,reason='no-header'));continue
            pids[name].add(task['pid']);good=0
            if len(task['threads'])==64:limits.append(dict(cycle=cycle['index'],target=name))
            for thread in task['threads']:
                if not thread['available']:unavailable+=1;continue
                available+=1
                if not thread['frame_chunks']:partial.append(cycle['index'])
                if thread['frame_chunks']and thread['pc']and thread['sp']and not thread['sp']&15:
                    usable+=1;good+=1
            if not good:missing.append(dict(cycle=cycle['index'],target=name,reason='no-usable-registers'))
        if numer is not None:
            cycle['begin_us']=cycle['begin_tick']*numer//denom//1000
            cycle['end_us']=None if cycle['end_tick']is None else cycle['end_tick']*numer//denom//1000
    consistent=all(len(pids[name])==1 for name in TARGETS)
    complete=(parsed['active_markers']==parsed['legacy_markers']==1 and not parsed['refused']and len(cycles)==8
              and not missing and not partial and not duplicates and consistent)
    return dict(state='bounded-process-samples-observed'if complete else 'process-samples-incomplete-or-unqualified',
                active=parsed['active_markers']==1,cycle_count=len(cycles),complete=complete,
                target_pids={name:sorted(values)for name,values in pids.items()},target_pid_consistent=consistent,
                unavailable_register_samples=unavailable,available_register_samples=available,usable_register_samples=usable,
                missing_targets=missing,partial_cycles=sorted(set(partial)),duplicate_target_cycles=duplicates,
                thread_limit_reached=limits,refused=parsed['refused'],cycles=cycles,
                frame_walks_coherent=False,hard_realtime_pause_limit=False,physical_fps_qualified=False,
                scope='Registers, wait state and resumed-thread frame walks are separate observations. Cycle ticks only bound each round. A 64-thread count does not establish that all task threads were sampled.')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('kernel_log',type=Path);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--numer',type=int);ap.add_argument('--denom',type=int);args=ap.parse_args()
    result=summarize(parse(args.kernel_log.read_text(errors='replace')),args.numer,args.denom)
    with args.out.open('x')as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items()if k!='cycles'},indent=2))

if __name__=='__main__':main()
