#!/usr/bin/env python3
"""Reject false stack evidence from malformed, partial or mistimed log records."""
import importlib.util
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'tools/analyze-sb-stack-log.py'
spec=importlib.util.spec_from_file_location('stack_log',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
prefix=m.PREFIX
active=prefix+'active '+' '.join(f'{key}={value}' for key,value in m.CONFIG.items())+'\n'
values=dict(sample=1,requested_us=230000000,us=230000010,held_us=230000020,resumed_us=230000100,
            watch=(226000000<<2)|2,stopped_watch=(226000000<<2)|2,suspend=0,state=0,read=0,resume=0,
            stop=5,frames=1,valid=1,pc=0x180001000,lr=0x180002000,sp=0x10000,fp=0x10020)
def sample(**changes):
    row={**values,**changes}
    return prefix+' '.join(f'{key}={row[key]:x}' if key in m.HEX else f'{key}={row[key]}' for key in m.SAMPLE_KEYS)+'\n'
def frames(ident=1):
    return ''.join(prefix+f'frame sample={ident} index={i} address={address:x} image=QuartzCore+0x{offset:x}\n'
                   for i,(address,offset) in enumerate([(values['pc'],0x1000),(values['lr'],0x2000),(0x180003000,0x3000)]))
good=active+sample()+frames()
checks=0
def check(ok):
    global checks
    checks+=1;assert ok
def summary(text):return m.summarize(m.parse(text))
check(summary(good)['usable_stack_samples']==1)
check(summary(good)['maximum_capture_elapsed_us']==90)
check(summary(sample()+frames())['usable_stack_samples']==0)
partial=summary(active+sample());check(partial['usable_stack_samples']==0 and partial['incomplete_frame_samples']==[1])
for change in [dict(requested_us=219999999),dict(requested_us=270000000),dict(watch=(226000000<<2)|0),
               dict(watch=(226000000<<2)|3),dict(watch=(229999999<<2)|2),dict(watch=(230000001<<2)|2),
               dict(stopped_watch=(226000001<<2)|2),dict(held_us=229999999),dict(resumed_us=230000001),
               dict(sp=0x10001),dict(fp=0xfff0),dict(fp=0x10021),dict(fp=0x20000)]:
    check(summary(active+sample(**change)+frames())['usable_stack_samples']==0)
over=summary(active+sample(resumed_us=230003000)+frames());check(over['over_budget_samples']==[1] and over['usable_stack_samples']==1)
missing=summary(active+sample(sample=2)+frames(2));check(missing['missing_sample_ids']==[1])
fast=summary(good+sample(sample=2,requested_us=230999999,us=231000010,held_us=231000020,resumed_us=231000100)+frames(2))
check(fast['policy_error_samples']==[2] and fast['usable_stack_samples']==1)
failure=summary(active+sample(suspend=5,state=m.NOT_CALLED,read=m.NOT_CALLED,resume=m.NOT_CALLED,stop=1,frames=0,valid=0))
check(failure['suspend_failures']==1 and failure['usable_stack_samples']==0)
stale=summary(active+sample(state=m.NOT_CALLED,read=m.NOT_CALLED,stop=2,frames=0,valid=0,stopped_watch=0))
check(stale['stale_watch_samples']==[1] and stale['usable_stack_samples']==0)
stopped=summary(active+prefix+'stopped=resume-failure\n');check(stopped['resume_failures']==1 and stopped['usable_stack_samples']==0)
unavailable=summary(prefix+'unavailable=mach-context\n');check(unavailable['unavailable']==['mach-context'] and not unavailable['active'])
bad=[good+active,active+sample()+sample(),active+sample(sample=65),active+sample(frames=17),
     active+sample(valid=2),active+sample(stop=11),active+sample(pc=1<<64),active+sample(resume=1<<31),
     good.replace('pc=180001000','pc=-1'),good.replace(' state=0',' state=0 state=0'),
     good.replace(' held_us=230000020',''),active+frames(),good+frames(),
     good.replace('index=0 address=180001000','index=0 address=180001001'),
     good.replace('index=1','index=2'),active+sample(valid=0)+frames(),
     active+sample(resume=5)+frames(),good.replace('depth=16','depth=17'),
     good.replace('version=315','version=314'),prefix+'stopped=unknown\n']
for text in bad:
    try:m.parse(text)
    except ValueError:checks+=1
    else:raise AssertionError('malformed stack log accepted')
print(f'PASS SpringBoard stack-log checks={checks}; partial/error/clock/policy records cannot become qualified stacks')
