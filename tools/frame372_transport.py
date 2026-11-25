"""Decode compact receipts and qualify the measured BackBoard evidence."""

import base64
import binascii
from collections import Counter
import re
import struct

from frame344_log import one, require
from frame371_transport import HEADER, MAX_SENDS, phases


CAP = 10240
BLOCK = 64
THREADS = 256
MISSES = 64
ROW = struct.Struct('<HIIIIBB')
PACKET_FAMILY = frozenset((40002,40003,40004,40005))
COMPACT_HEADER = HEADER.replace('F371','F372').removesuffix('$') + r' start=(\d+)$'


def fixed_rows(packed, count):
    require(len(packed)==count*ROW.size, 'invalid fixed transport record size')
    return ROW.iter_unpack(packed)


def decode(raw, numer, denom, *, block_type='F372 B', read_rows=fixed_rows, thread_cap=THREADS,
           allow_refused_prefix=False):
    fields = ('count','capacity','sent','send_capacity','copied','missed','busy','evicted','failed','start')
    mark = dict(zip(fields,map(int,one(COMPACT_HEADER,raw,'compact transport header')),strict=True))
    start,end = map(int,one(r'^SWEET F344 H: .* start=(\d+) end=(\d+) numer=\d+ denom=\d+$',
                           raw,'frame capture window'))
    footers = re.findall(r'^SWEET F372 F: count=(\d+) threads=(\d+)$',raw,re.M)
    refusals = re.findall(r'^SWEET F372: refused.*$',raw,re.M)
    missing_export = 0
    if refusals and allow_refused_prefix:
        require(len(refusals)==1 and not footers,'ambiguous compact transport refusal')
        refused = re.fullmatch(r'SWEET F372: refused row=(\d+)',refusals[0])
        require(refused is not None and 0<int(refused[1])<mark['count'],'invalid transport refusal ordinal')
        count = int(refused[1])//BLOCK*BLOCK
        missing_export = mark['count']-count
        threads = None
    else:
        require(not refusals and len(footers)==1,'compact transport footer or refusal differs')
        count,threads = map(int,footers[0])
    require(0<start<end and
            end-start<=0xffffffff and numer>0 and denom>0 and start==mark['start'] and
            mark['capacity']==CAP and mark['send_capacity']==MAX_SENDS and
            0<=count+missing_export==mark['count']==min(mark['copied'],CAP) and
            mark['copied']+mark['failed']<=min(mark['sent'],MAX_SENDS) and
            (threads is None or 0<=threads<=thread_cap),
            'compact transport clock, cap, receipt or export differs')
    mapping = {}
    used_threads = set()
    for i,tid in re.findall(r'^SWEET F372 D: index=(\d+) tid=(\d+)$',raw,re.M):
        index,thread = int(i),int(tid)
        require(index==len(mapping)<thread_cap and 0<thread<1<<64 and thread not in used_threads,
                'malformed compact transport thread dictionary')
        mapping[index] = thread
        used_threads.add(thread)
    require(threads is None or len(mapping)==threads, 'thread dictionary length differs')
    missed = [int(tick) for tick in re.findall(r'^SWEET F372 M: tick=(\d+)$',raw,re.M)]
    require(len(missed)==min(mark['missed'],MISSES) and all(start<=t<end for t in missed),
            'unmatched delivery timing differs')
    result = []
    serials = set()
    ns = lambda tick:tick*numer//denom
    for index,size,wire in re.findall(rf'^SWEET {re.escape(block_type)} (\d+) (\d+) ([A-Za-z0-9+/=]+)$',raw,re.M):
        slot,n = int(index),int(size)
        require(slot==len(result) and n==min(BLOCK,count-slot) and 0<n<=BLOCK,
                'compact transport block order or length differs')
        try:
            packed = base64.b64decode(wire,validate=True)
        except (ValueError,binascii.Error) as error:
            raise ValueError('invalid compact transport base64') from error
        require(base64.b64encode(packed).decode()==wire,
                'invalid compact transport block bytes or padding')
        for serial,post_id,offset,post,done,source,dest in read_rows(packed,n):
            send_tick = start+offset
            require(0<serial<=min(mark['sent'],MAX_SENDS) and serial not in serials and
                source in mapping and dest in mapping and 0<=post<=done and send_tick+done<end,
                'invalid compact serial, thread index or interval')
            serials.add(serial)
            result.append(dict(serial=serial,message_id=post_id,send_tick=send_tick,
                post_tick=send_tick+post,copyout_tick=send_tick+done,send_ns=ns(send_tick),
                post_ns=ns(send_tick+post),copyout_ns=ns(send_tick+done),
                sender_thread=mapping[source],receiver_thread=mapping[dest]))
    require(len(result)==count,'missing compact transport records')
    losses = dict(cap_saturation=mark['copied']>CAP or mark['sent']>MAX_SENDS,
        tagging_errors=bool(mark['evicted'] or mark['busy'] or mark['failed']),
        unmatched_without_timestamp=max(0,mark['missed']-len(missed)),
        outstanding_at_close=mark['sent']-mark['copied'])
    if missing_export:
        losses['unexported_tail'] = missing_export
    return dict(counters=mark,paired_exact_receipts=len(result),window_ticks=[start,end],
        unmatched_ticks=missed,losses=losses,
        full_scope_observed=not any(losses.values()) and not missed,
        pairs=sorted(result,key=lambda r:(r['copyout_tick'],r['serial'])))


def workload_scope(capture, strokes, motion):
    windows = [(f'stroke_{i}',a,b) for i,(a,b) in enumerate(strokes,1)]
    windows.append(('fixed_drag',motion['samples'][0][1],motion['samples'][-1][2]))
    start,end = capture['window_ticks']
    require(all(start<=lo<=hi<end for _,lo,hi in windows),'input workload outside transport clock window')
    pairs = capture['pairs']
    kept = []
    for name,lo,hi in windows:
        missing = sum(lo<=t<=hi for t in capture['unmatched_ticks'])
        messages = [p for p in pairs if lo<=p['copyout_tick']<=hi]
        ca_packets = [p for p in messages if p['message_id'] in PACKET_FAMILY]
        kept.append(dict(scope=name,window_ticks=[lo,hi],receives_in_window=len(messages),
            ca_encoder_packets=len(ca_packets),unmatched_copyouts=missing,
            receive_threads=dict(Counter(p['receiver_thread'] for p in ca_packets))))
    first,last = windows[0][1],windows[-1][2]
    missing = [t for t in capture['unmatched_ticks'] if first<=t<=last]
    return dict(windows=kept,complete_13_and_fixed_drag=not any(capture['losses'].values()) and not missing,
        unmatched_during_workload=missing,
        missing_timestamps_are_kept_even_between_strokes=True)


SMP_IMAGE = re.compile(r'^SMP backboardd\[\d+\] slide (0x[0-9a-f]+) mh 0x[0-9a-f]+$')
SMP_REGS = re.compile(r'^SMP backboardd t\d+ tid (\d+) st \d+ ev 0x[0-9a-f]+ wr -?\d+ '
                      r'pc (0x[0-9a-f]+) lr (0x[0-9a-f]+) sp 0x[0-9a-f]+$')
SMP_STAMP = re.compile(r'^SWEET F372 S: tid=(\d+) serial=(\d+) epoch=(\d+) read=(\d+),(\d+)$')


def snapshot_handoff(raw, capture, swaps, ranges):
    """Identify existing samples without treating a last copyout as an active CA transaction."""
    pairs = {row['serial']:row for row in capture['pairs']}
    begin_threads = {row['begin_thread'] for row in swaps if row.get('begin_thread')}
    receive_threads = {row['receiver_thread'] for row in pairs.values() if row['message_id'] in PACKET_FAMILY}
    by_thread,receipts = {},[]
    slide = None
    def label(address):
        current = address-slide
        matches = [row for row in ranges if row['start']<=current<row['end']]
        return matches[0]['stage'] if len(matches)==1 else None
    for line in raw.splitlines():
        if match := SMP_IMAGE.fullmatch(line):
            slide = int(match[1],16)
            by_thread.clear()
        elif match := SMP_REGS.fullmatch(line):
            by_thread[int(match[1])] = (int(match[2],16),int(match[3],16))
        elif match := SMP_STAMP.fullmatch(line):
            thread,serial,epoch,start,end = map(int,match.groups())
            require(slide is not None and thread in by_thread and 0<epoch and
                    capture['window_ticks'][0]<=start<=end<capture['window_ticks'][1],
                    'register sample receipt has no exact original clock or thread')
            pc,lr = by_thread.pop(thread)
            pair = pairs.get(serial)
            require(pair is None or pair['receiver_thread']==thread and pair['copyout_tick']<=start,
                    'last receipt belongs to another thread or occurred after the sample')
            receipts.append(dict(thread=thread,serial=serial,epoch=epoch,read_ticks=[start,end],
                match=bool(pair),pc_stage=label(pc),lr_stage=label(lr)))
    ca = [row for row in pairs.values() if row['message_id'] in PACKET_FAMILY]
    return dict(CA_encoder_packets=len(ca),CA_receiver_threads=sorted(receive_threads),
        exact_SwapBegin_threads=sorted(begin_threads),same_thread_intersection=sorted(receive_threads&begin_threads),
        transport= dict(send_to_post=phases(row['post_ns']-row['send_ns'] for row in ca),
                        post_to_copyout=phases(row['copyout_ns']-row['post_ns'] for row in ca)),
        register_samples=receipts,register_pc_stage_counts=dict(Counter(row['pc_stage'] or 'other' for row in receipts)),
        continuous_transaction_identity_verified=False,
        interpretation='A stable receipt stamps the last completed kernel copyout through the existing register '
                       'sample. Decode/apply and IOMFB scheduling can consume batches. The shared next-update '
                       'deadline contains no per-packet token, and the samples cannot identify a rendered transaction.')
