#!/usr/bin/env python3
"""Replay update coalescing, bound the new wire and recheck the archived retry counters."""

from importlib import import_module, util
import re

from frame373_coalescing import NextUpdate, Replay, Version, merge_update
from frame373_receipts import decode_with_unmatched

scope = import_module('prepare-frame373')
require = scope.require


def refuses(action):
    try:
        action()
    except ValueError:
        return
    raise ValueError('invalid CA, held-frame or receive observation accepted')


def coalescing():
    normal = NextUpdate(20,1,2)
    cases = [
        (NextUpdate(None),normal,normal),
        (normal,NextUpdate(30,4,8),NextUpdate(20,1,10)),
        (normal,NextUpdate(20,4,8),NextUpdate(20,5,10)),
        (normal,NextUpdate(15,4,8),NextUpdate(15,4,10)),
        (normal,NextUpdate(0,4,8),NextUpdate(0,5,10)),
        (NextUpdate(0,4,8),normal,NextUpdate(0,4,10)),
    ]
    require(all(merge_update(old,new)==expected for old,new,expected in cases), 'deadline/flag merge differs')
    refuses(lambda:merge_update(normal,NextUpdate(None)))
    replay = Replay()
    a0,a1,a2,b0,b1 = (Version(1,1,0xffffffff),Version(1,1,0),Version(1,1,1),
                      Version(2,1,7),Version(2,1,8))
    replay.open_context(a0)
    replay.open_context(b0)
    refuses(lambda:replay.schedule(a1,normal))
    replay.apply(a1,11)
    replay.schedule(a1,normal)
    replay.apply(b1,12)
    replay.schedule(b1,NextUpdate(20,4,8))
    replay.apply(a2,13)
    replay.schedule(a2,NextUpdate(15,16,32))
    require(replay.pending==NextUpdate(15,16,42) and replay.applied[a2]==13,'batched apply lost its identity')
    refuses(lambda:replay.consume(1,(a1,b1)))
    refuses(lambda:replay.consume(1,(a2,a2)))
    require(replay.consume(1,(a2,b1))==(a2,b1) and replay.pending==NextUpdate(None),'render chose wrong seed')
    replay.close_context(a2)
    a3,a4 = Version(1,2,1),Version(1,2,2)
    replay.open_context(a3)
    refuses(lambda:replay.open_context(a2))
    replay.apply(a4,14)
    replay.schedule(a4,NextUpdate(0,1,2))
    refuses(lambda:replay.consume(2,(a2,)))
    require(replay.consume(2,(a4,))==(a4,), 'new lifetime did not keep its own seed')
    refuses(lambda:replay.swap(2,1))
    require(replay.swap(1,1)==(a2,b1) and replay.swap(2,2)==(a4,), 'sealed render membership changed')
    refuses(lambda:replay.complete(2))
    refuses(lambda:replay.swap(2,2))
    require(replay.complete(1)==(a2,b1) and replay.complete(2)==(a4,), 'completion lost the held version')
    refuses(lambda:replay.consume(2,(a4,)))
    return dict(finite_deadline_cases=len(cases),seed_wrap=True,multi_context_apply=True,
                retiring_and_reusing_context=True,ordered_swaps_and_completions=True,
                stale_seed_duplicate_and_lifetime_refused=True)


def static_code():
    resource = scope.MAIN/'research/tmp/gauguin-sb-stack-worktree-20261114/research/tmp/sb-stack-315'
    resolver_path = resource/'symbolize_stack315_v2.py'
    spec = util.spec_from_file_location('local20H392CA',resolver_path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    resolver = module.Resolver()
    try:
        quartz = '/System/Library/Frameworks/QuartzCore.framework/QuartzCore'
        image = resolver.image(quartz)
        require(image['uuid']=='9e40b2eb260c3af1ae45a1a551a8c1b9', '0373 QuartzCore UUID differs')
        dis = resolver.ns['disasm']
        windows = {
            'advance_commit_seed': (0x1882ce21c,0x1882ce26c),
            'merge_deadline': (0x188500fac,0x188501038),
            'command_begin': (0x18846f418,0x18846f440),
            'command_end': (0x188470328,0x1884703a8),
            'render_add_context': (0x1882fc5a4,0x1882fc5cc),
        }
        code = {key:{address:instruction.split(';')[0].strip() for address,_,instruction in dis(*span)}
                for key,span in windows.items()}
        conditions = {
            'advance_commit_seed': {0x1882ce238:'ldr\tw8, [x19, #0x38]',0x1882ce23c:'add\tw8, w8, #0x1',
                                    0x1882ce240:'str\tw8, [x19, #0x38]'},
            'merge_deadline': {0x18850100c:'orr\tx9, x10, x9',0x188501018:'b.lt\t#0x4c',
                               0x18850101c:'fcmp\td0, #0.0',0x188501024:'b.gt\t#0xc',
                               0x18850102c:'orr\tx8, x9, x8',0x188501034:'str\td0, [x20, #0x2b0]'},
            'command_begin': {0x18846f420:'ldr\tw1, [x8, #0x10]!',0x18846f430:'mov\tx2, #0x0'},
            'command_end': {0x188470328:'ldr\tw19, [x24, #0xf0]',0x188470338:'ldr\tw22, [x24, #0x10]',
                            0x188470384:'bl\t#-0x1a2168',
                            0x18847039c:'mov\tx2, x22',0x1884703a0:'mov\tx3, x19'},
            'render_add_context': {0x1882fc5b4:'ldr\tw1, [x21, #0x10]',0x1882fc5bc:'mov\tx2, #0x0',
                                   0x1882fc5c0:'mov\tx3, #0x0',0x1882fc5c4:'mov\tx4, #0x0'},
        }
        require(all(code[name][address]==value for name,rows in conditions.items() for address,value in rows.items()),
                'exact CA argument or deadline code differs')
        return dict(image_uuid=image['uuid'],resolver_sha256=scope.sha(resolver_path),
            sites={k:[hex(a) for a in values] for k,values in conditions.items()},
            built_in_markers={
                'command_begin':dict(debugid='0x31ca0009',context_id='arg1',commit_seed=None),
                'command_end':dict(debugid='0x31ca000a',context_id='arg2',arg3_is_f0_not_seed_38=True),
                'render_add_context':dict(debugid='0x31ca027d',context_id='arg1',commit_seed=None),
            },
            set_next_update='The inspected ordinary path merges one deadline and two masks. It carries no context version.',
            exact_seed_provider_verified=False)
    finally:
        resolver.close()


def main():
    scope.check_budget()
    scope.check_reference()
    raw = (scope.REFERENCE/'kernel.log').read_text()
    numer,denom = map(int,re.search(r'^SWEET F344 H: .* numer=(\d+) denom=(\d+)$',raw,re.M).groups())
    tick, = map(int,re.findall(r'^SWEET F372 M: tick=(\d+)$',raw,re.M))
    synthetic = f'SWEET F373 U: ordinal=0 tick={tick} tid=1226 id=40002 reason=1 copyout={tick+1} result=0'
    for line,outcome in ((synthetic,'completed'), (synthetic[:-1]+'5','failed'),
                         (synthetic.replace(f'copyout={tick+1}','copyout=0'),'outside_capture')):
        row, = decode_with_unmatched(raw+line+'\n',numer,denom)['unmatched_receipts']
        require(row['outcome']==outcome and row['take_tick']==tick, 'unmatched completion lost its outcome')
    for tail in ('',synthetic+'\n'+synthetic,synthetic.replace('reason=1','reason=5'),
                 synthetic.replace(f'tick={tick}',f'tick={tick-1}')):
        refuses(lambda:decode_with_unmatched(raw+tail+'\n',numer,denom))
    held = import_module('analyze-present-retry-log')
    old,new = held.analyze(raw),held.analyze(raw,pending_limit=4)
    require(not old['active'] and new['active'] and new['snapshots']==71 and
            max(row['pending'] for row in new['rows'])==3, 'archived fourth-slot counter replay differs')
    invalid = raw.replace('pending=3 active=0','pending=5 active=0',1)
    require(not held.analyze(invalid,pending_limit=4)['active'], 'fifth slot was admitted')
    good = next(line for line in raw.splitlines() if 'pending=3 active=0' in line)
    invalid = raw.replace(good,good.replace('submitted=259','submitted=260'),1)
    require(not held.analyze(invalid,pending_limit=4)['active'], 'bad slot accounting was admitted')
    design = coalescing()
    static = static_code()
    raw_bytes = scope.load(scope.REFERENCE/'kernel-IO-analysis.json')['ring']['total_bytes']
    replaced = sum(len(line.encode())+2 for line in raw.splitlines() if line.startswith('SWEET F372 '))
    full = scope.load(scope.P372.parent/'frame-372-host/result.json')['full_scope_export_bound']+64*176+2048
    projected = raw_bytes-replaced+full
    require(projected<4_194_304, '0373 compact transport would exceed the measured persistent ring')
    scope.save(scope.HOST,dict(state='0373-offline-verified',patch_sha256=scope.sha(scope.PATCH),
        reference_raw_bytes=raw_bytes,projected_ring_bound=projected,full_scope_export_bound=full,
        held_snapshots=new['snapshots'],coalescing_verified=True,replay=design,static=static,
        exact_seed_provider_verified=False,device_writes=0,device_boots=0,
        synthetic_unmatched_copyout_outcomes=3,invalid_unmatched_wires_rejected=4))


if __name__=='__main__':
    main()
