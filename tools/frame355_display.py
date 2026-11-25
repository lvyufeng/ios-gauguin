"""Check the startup empty-layer update and locate missed present attempts."""

from collections import Counter, defaultdict
import re

import frame344_log as trace
import frame351_display as present
import frame352_display as copy
import frame354_display as retained

EMPTY_PREFIX = 'SWEET FB EMPTY355:'
MAX_EMPTY_RECEIPTS = 8
EMPTY = re.compile(
    r'SWEET FB EMPTY355: gen=(\d+) swap=(\d+) attempt=(\d+) tick=(\d+) '
    r'mask=1 surface=0 timed=([01]) versioned=([01]) guards=(\d+) bytes=(\d+) ready=([01])')
EMPTY_FIELDS = ('generation','swap','attempt','tick','timed','versioned','guards','bytes','ready')


def verify_startup(text):
    trace.require(not re.search(r'^SWEET PANIC ENTRY:|^Kernel data abort\.',text,re.M),
                  'kernel panic in 0355 observation')
    first = int(trace.one(r'^SWEET UI SCRIPT: begin stroke=0 tick=(\d+) origin=synthetic$',text,'first scripted stroke'))
    receipts = []
    for line in text.splitlines():
        if line.startswith(EMPTY_PREFIX):
            match = EMPTY.fullmatch(line)
            trace.require(match is not None,'malformed completed empty swap receipt')
            receipts.append(dict(zip(EMPTY_FIELDS,map(int,match.groups()))))
    trace.require(0 < len(receipts) <= MAX_EMPTY_RECEIPTS and
                  all(row['generation']>0 and row['attempt']>0 and row['tick']>0 and row['ready']==1 and
                      not (row['timed'] or row['versioned'] or row['guards'] or row['bytes']) for row in receipts) and
                  all(l['generation']<r['generation'] and l['attempt']<r['attempt'] and l['tick']<=r['tick']
                      for l,r in zip(receipts,receipts[1:])), 'empty swaps lack bounded, ordered legacy completions')
    startup = [row for row in receipts if row['tick']<first]
    trace.require(startup,'no completed empty-layer legacy update before the first stroke')
    return dict(state='empty-layer-legacy-update-completed-before-stroke',qualified=True,
                first_stroke_tick=first,startup_completions=startup,receipt_count=len(receipts),
                all_receipts=receipts)


def missed_stages(rows, missed):
    swaps = trace.indexed((r for r in rows[trace.SWAP] if not r.flags),lambda r:r.id,'accepted swap')
    edges = trace.indexed(rows[trace.VBLANK],lambda r:r.id,'hardware frame edge')
    completions = trace.indexed(rows[trace.READY],lambda r:r.id,'GPU completion')
    promotions = trace.indexed(rows[retained.PROMOTE],lambda r:r.id,'ready promotion')
    writers, takes, next_swap = defaultdict(list), defaultdict(list), {}
    for row in rows[trace.WRITER]:
        if row.b:
            writers[row.b].append(row)
    for row in rows[retained.TAKE]:
        takes[row.a].append(row)
    for older,newer in zip(swaps.values(),list(swaps.values())[1:]):
        next_swap[older.id] = newer

    windows = []
    for entry in missed:
        edge = edges[entry['hardware_frame']]
        detail = []
        for generation in entry['new_generations']:
            swap = swaps[generation]
            surface,version = swap.c & retained.MASK32,swap.c >> 32
            ticket = (generation<<32)|surface
            observed = [row for row in writers[ticket] if row.tick<=edge.b] if surface else []
            matching = [row for row in observed if row.a==surface and row.c==version]
            writer = matching[-1] if matching else None
            completion = completions.get(writer.id) if writer else None
            promotion = promotions.get(generation)
            following = next_swap.get(generation)
            trace.require(swap.tick<=edge.b,'swap was accepted after its reported hardware interval')
            if not surface:
                stage = 'empty_or_multi_layer'
            elif not writer:
                stage = 'different_write_version' if observed else 'awaiting_matching_GPU_writer'
            elif not completion or completion.tick>edge.b:
                stage = 'awaiting_GPU_fence'
            elif not promotion or promotion.tick>edge.b:
                stage = 'GPU_fence_complete_awaiting_promotion'
            else:
                stage = 'ready_without_present_attempt'
            detail.append(dict(generation=generation,surface=surface,version=version,stage_at_edge=stage,
                accepted_tick=swap.tick,writer_tick=writer.tick if writer else None,fence=writer.id if writer else None,
                fence_complete_tick=completion.tick if completion else None,
                ready_tick=promotion.tick if promotion else None,
                later_swap_by_edge=bool(following and following.tick<=edge.b),
                first_timed_take_tick=takes[generation][0].tick if takes[generation] else None))
        windows.append(dict(entry,edge_upper_tick=edge.b,swaps=detail))
    summaries = {}
    for phase in ('active','release','all'):
        selected = [row for row in windows if phase=='all' or row['phase']==phase]
        stages = Counter(swap['stage_at_edge'] for row in selected for swap in row['swaps'])
        summaries[phase] = dict(interval_count=len(selected),swaps_by_stage=dict(stages),
            windows_with_ready_candidate=sum(bool(row['new_generations_ready_by_edge']) for row in selected),
            superseded_by_edge=sum(swap['later_swap_by_edge'] and swap['stage_at_edge']!='ready_without_present_attempt'
                                   for row in selected for swap in row['swaps']))
    return dict(phases=summaries,windows=windows)


def inventory(text, selection, *, extra_kinds=()):
    rows,_,_,_ = trace.parse(text,extra_kinds=(present.PRESENT,copy.WAKE,*retained.KINDS,*extra_kinds))
    return missed_stages(rows,selection['unpresented_new_swaps'])
