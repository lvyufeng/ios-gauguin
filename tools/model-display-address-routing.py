"""Classify a future passive APPS SMMU capture of the known display streams."""

import json


DISPLAY_STREAMS = (0x800, 0x802)
ID0_STREAM_MATCH = 1 << 27
ID0_EXTENDED_IDS = 1 << 8
CR0_DISABLE = 1
CR0_EXTENDED_IDS = 1 << 3
CR0_UNMATCHED_FAULT = 1 << 10
S2CR_EXTENDED_VALID = 1 << 10


def classify(id0, control, words, *, stable, route_verified):
    """Report current stream routing. This never certifies a framebuffer address."""
    if not stable or not route_verified:
        return {'state':'unqualified-capture'}
    if not (id0 & ID0_STREAM_MATCH) or not 0 < (id0 & 255) <= 128 or len(words)!=(id0 & 255):
        return {'state':'unsupported-mapping-inventory'}
    if id0==0xffffffff or control==0xffffffff or control & CR0_DISABLE:
        return {'state':'unqualified-control'}
    extended = bool(control & CR0_EXTENDED_IDS)
    if extended and not id0 & ID0_EXTENDED_IDS:
        return {'state':'inconsistent-stream-width'}
    mask = 0xffff if extended else 0x7fff
    streams = []
    for sid in DISPLAY_STREAMS:
        candidates = []
        for index, (smr,s2cr) in enumerate(words):
            valid = s2cr & S2CR_EXTENDED_VALID if extended else smr >> 31
            ignore = (smr >> 16) & mask
            if valid and not ((smr ^ sid) & mask & ~ignore):
                candidates.append((index,s2cr))
        if not candidates:
            status = 'unmatched-fault' if control & CR0_UNMATCHED_FAULT else 'unmatched-default'
            streams.append(dict(sid=sid,state=status))
        elif len(candidates)!=1:
            streams.append(dict(sid=sid,state='ambiguous'))
        else:
            index,s2cr = candidates[0]
            mode = ('translated','physical-route','fault','reserved')[(s2cr >> 16) & 3]
            streams.append(dict(sid=sid,state=mode,index=index,
                context_bank=(s2cr & 255) if mode=='translated' else None))
    return dict(state='display-streams-classified',streams=streams,scanout_address_proven=False)


def exercise():
    ready = dict(stable=True,route_verified=True)
    id0 = ID0_STREAM_MATCH | 2
    other = ((1 << 31) | 0x801, 2 << 16)
    match = ((1 << 31) | (2 << 16) | 0x800, 1 << 16)
    physical = classify(id0,0,(match,other),**ready)
    assert [r['state'] for r in physical['streams']]==['physical-route']*2
    assert not physical['scanout_address_proven']
    mismatch = classify(id0,0,(match,match),**ready)
    assert [r['state'] for r in mismatch['streams']]==['ambiguous']*2
    translated = classify(id0,0,((match[0],17),other),**ready)
    assert [r['context_bank'] for r in translated['streams']]==[17,17]
    missed = classify(id0,CR0_UNMATCHED_FAULT,(other,other),**ready)
    assert [r['state'] for r in missed['streams']]==['unmatched-fault']*2
    ext = classify(id0 | ID0_EXTENDED_IDS,CR0_EXTENDED_IDS,
        ((2 << 16 | 0x800, S2CR_EXTENDED_VALID | (1 << 16)),(0,0)),**ready)
    assert [r['state'] for r in ext['streams']]==['physical-route']*2
    assert classify(id0,CR0_EXTENDED_IDS,(match,other),**ready)['state']=='inconsistent-stream-width'
    assert classify(id0,0,(match,other),stable=False,route_verified=True)['state']=='unqualified-capture'
    assert classify(id0,CR0_DISABLE,(match,other),**ready)['state']=='unqualified-control'
    assert classify(id0,0,(match,),**ready)['state']=='unsupported-mapping-inventory'
    return dict(model_cases=9,physical_devices_used=0,registers_written=0,
        scope='Only current routing for two non-secure display stream IDs. Buffer ownership, permissions and latch remain separate.')


if __name__=='__main__':
    print(json.dumps(exercise(),indent=2))
