#!/usr/bin/env python3
"""Offline replay of the first included version retained by a Core Animation update."""

from importlib import import_module
from pathlib import Path
import argparse
import json

from frame373_coalescing import Version

scope = import_module('prepare-frame373')
require = scope.require


def membership(events):
    current, included = {}, {}
    for operation,version in events:
        identity = version.context,version.lifetime
        if operation=='apply':
            current[identity] = version
        elif operation=='close':
            require(current.pop(identity)==version, 'closing another context version')
        elif operation=='include':
            require(current.get(identity)==version, 'membership sample lacks an active context version')
            included.setdefault(identity,version)
        else:
            raise ValueError('unknown context observation')
    return tuple(included.values())


def replay(source, teardown):
    require(scope.sha(source)=='8421eac4d7bf1047e50776bb24aadcac1556a1ecaa3ea82a1e7d9b6c1989d193' and
            scope.sha(teardown)=='08c3facc783861ec297d0d628bda2c603c3ac77ab8c4344f9fa8b2ac1f8e60e3',
            'included-context source observations differ')
    implementation = scope.load(source)
    finish = scope.load(teardown)
    uuid = '9e40b2eb260c3af1ae45a1a551a8c1b9'
    require(implementation['cache_uuid']==finish['cache_uuid']==uuid, 'included-context cache differs')
    code = implementation['instructions']
    for address,instruction in {
        '0x1882e5680':'ldr\tx9, [x8, #0x8]',
        '0x1882e5684':'cmp\tx9, x21',
        '0x1882e5688':'b.eq\t#0x70',
        '0x1882e56a4':'str\tx21, [x0, #0x8]',
        '0x1882e56d8':'ldr\tw21, [x21, #0x38]',
        '0x1882e56e4':'str\tw21, [x22, #0x18]',
        '0x1882e56f4':'str\tx22, [x20, #0x128]',
    }.items():
        require(code[address]==instruction, 'included-context snapshot path differs')
    finish_code = dict(finish['teardown_window'])
    require(finish_code['0x1882c28cc']=='ldr\tw24, [x22, #0x18]' and
            finish_code['0x1882c28e8']=='str\tw24, [x21, #0x3c]', 'completion seed source differs')

    a,b,c = Version(12,1,25),Version(12,1,26),Version(20,1,7)
    reopened = Version(12,2,25)
    early_events = [('apply',a),('include',a),('apply',b),('include',b),('apply',c),('include',c)]
    later_events = [('apply',a),('apply',b),('include',b),('apply',c),('include',c)]
    early,later = membership(early_events),membership(later_events)
    require(early==(a,c) and later==(b,c), 'earlier inclusion hid a replaced seed')
    balanced = membership(early_events+[('close',b),('apply',reopened),('include',reopened)])
    require(balanced==(a,c,reopened),'context reuse changed the retained version')
    return dict(cache_uuid=uuid,source_sha256=scope.sha(source),teardown_sha256=scope.sha(teardown),
        early_and_original_memberships_equal=early==later,first_inclusion_retained=True,
        source_context_lifetime_remains_distinct=True,context_close_preserves_sealed_membership=True,
        completion_uses_saved_seed=True,exact_on_device_seed_handoff_verified=False,
        device_commands=0)


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('output',type=Path)
    args = cli.parse_args()
    result = replay(scope.BASE/'20H392-included-context-seed.json',scope.BASE/'20H392-publication-order.json')
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
