"""Connect compact CA commit receipts to actual vblank and CRC outcomes."""

from base64 import b64decode
from importlib import import_module
from struct import Struct
import re

from frame344_log import indexed, quantile, require
import frame374_native_ca as native
from frame369_swap_timing import decode as swap_timing
from frame376_capture import packet_lane
from frame390_build import CAP, load_ca_port

TX = Struct('<8IQQ2I')
SUMMARY = re.compile(r'Q (\d+) (\d+) (\d+) (\d+)')
BLOCK = re.compile(r'B (\d+) (\d+) (\d+) ([A-Za-z0-9+/]+={0,2})')
FOOTER = re.compile(r'F ([01]) (\d+) (\d+)')
MAX_CONSOLE_BYTES = 88_000


def decode(raw, start, end, packets):
    load_ca_port()
    member = import_module('frame390_membership')
    prefix = 'SWEET F390 TX '
    witness = [line for line in raw.splitlines() if line.startswith('SWEET F390 ')]
    require(0<sum(len(line)+2 for line in witness)<=MAX_CONSOLE_BYTES,'CA timeline console bound exceeded')
    windows, snapshots = member.decode('\n'.join(line for line in witness if not line.startswith(prefix)),start,end)
    lanes = {}
    for row in snapshots:
        lanes.setdefault(row.stroke,[]).append(row)
    transport = indexed(packets,lambda row:row['serial'],'CA kernel IPC receipt')
    summaries, by_swap = {}, {}
    stroke = 0
    count = emitted = 0
    missing_IPC = 0
    footer = None
    for line in witness:
        if not line.startswith(prefix):
            continue
        require(footer is None,'CA timeline footer precedes data')
        text = line[len(prefix):]
        summary = SUMMARY.fullmatch(text)
        if summary:
            number, retained, lost, count_next = map(int,summary.groups())
            require(emitted==count and number==stroke+1<=member.STROKES and retained<=CAP and
                (not lost or (retained==CAP and count_next==0)) and count_next<=len(lanes.get(number,())),
                'CA compact receipt stroke or retention count differs')
            stroke,count,emitted = number,count_next,0
            summaries[stroke] = dict(retained=retained,lost=lost,receipts=count)
            continue
        if match := FOOTER.fullmatch(text):
            armed, windows_written, dropped = map(int,match.groups())
            require(stroke==windows_written==member.STROKES and emitted==count,'incomplete CA transaction lanes')
            footer = dict(armed=bool(armed),receipt_contention=dropped)
            continue
        block = BLOCK.fullmatch(text)
        require(block and stroke>0,'invalid compact CA receipt block')
        ordinal, at, amount = map(int,block.groups()[:3])
        packed = b64decode(block[4],validate=True)
        require(ordinal==stroke and at==emitted and 0<amount<=member.BLOCK and
                emitted+amount<=count and len(packed)==amount*TX.size,'invalid compact CA receipt stride')
        emitted += amount
        for index, identity, commit, encoded, send, receive, command, apply, sender, receiver, before, after in TX.iter_unpack(packed):
            require(index<len(lanes[stroke]),'CA receipt snapshot index is outside the stroke')
            snap = lanes[stroke][index]
            serial, msg = identity&0xffff,identity>>16
            require(snap.observed==member.PRESENT and serial>0 and 40002<=msg<=40005 and
                0<=commit<send<encoded<end-start and send<=receive<command<apply<snap.tick-start and
                sender>0 and receiver>0 and ((before==after==0) or apply<=before<after<snap.tick-start) and
                snap.key not in by_swap,'compact CA receipt violates stage order or identity')
            packet = transport.get(serial)
            if packet is None or (packet['message_id'],packet['sender_thread'],packet['receiver_thread'],packet['send_tick']) != (
                    msg,sender,receiver,start+send) or not start+send<=packet['copyout_tick']<=start+receive:
                missing_IPC += 1
                by_swap[snap.key] = None
                continue
            by_swap[snap.key] = dict(snapshot=snap,serial=serial,commit=start+commit,encoded=start+encoded,send=start+send,
                delivered=packet['copyout_tick'],receive=start+receive,apply=start+apply,
                inclusion=[start+before,start+after] if before else None)
    require(footer is not None,'CA timeline footer is absent')
    return dict(windows=windows,retention=summaries,missing_IPC=missing_IPC,**footer),snapshots,by_swap


def measure(execution, raw, rows, n, d, latches, scans):
    start,end,native_n,native_d = native.envelope(raw)
    require((n,d)==(native_n,native_d),'CA and DPU clocks differ')
    stats,snapshots,receipts = decode(raw,start,end,packet_lane(raw,n,d)['pairs'])
    render_events = native.decode(raw,start,end)
    accepted = swap_timing(rows,n,d,begin_threads=True)
    rendered = native.link_swaps(render_events,accepted,start,end,n,d)
    annotations = {(event.tick,event.thread,*event.args) for event in render_events if event.kind==native.ANNOTATION}
    for row in accepted:
        if row['generation'] in rendered:
            rendered[row['generation']]['begin_thread'] = row['begin_thread']
    observed = {row.key:row for row in snapshots}
    first = import_module('run-frame385-trial').first_after_touch(
        scans,import_module('frame384_stage').parse(raw)[1],execution,n,d)
    result = []
    for frame in first:
        stroke,scan = frame['stroke'],frame['first_scan']
        vis = dict(stroke=stroke,scan=scan,callback_return_ns=frame['touch_callback_return_ns'])
        result.append(vis)
        latch = latches.get(scan)
        link = rendered.get(latch['generation']) if latch else None
        if not link or not link['render']:
            continue
        render = link['render']
        key = (render['annotation_tick'],link['begin_thread'],latch['swap'],render['frame_seed'])
        snap = observed.get(key)
        if not snap or key not in annotations or snap.stroke!=stroke or not render['begin_tick']<=snap.tick<=latch['issued_tick']:
            continue
        vis.update(swap_membership=snap.observed,gate=snap.gate)
        receipt = receipts.get(key)
        returned = frame['touch_callback_return_ns']
        if not receipt or returned is None or returned>receipt['commit']*n//d:
            continue
        scale = lambda tick:tick*n//d
        vis.update(swap=latch['swap'],serial=receipt['serial'],context=snap.context_id,version=snap.version,
            callback_to_commit_ns=scale(receipt['commit'])-returned,
            commit_to_send_ns=scale(receipt['send']-receipt['commit']),
            send_to_apply_ns=scale(receipt['apply']-receipt['send']),
            apply_to_swap_annotation_ns=scale(snap.tick-receipt['apply']),
            apply_to_render_begin_ns=scale(render['begin_tick']-receipt['apply']),
            render_begin_to_swap_ns=scale(link['begin_tick']-render['begin_tick']),
            swap_to_visible_ns=[scale(tick-latch['swap_tick']) for tick in frame['first_vblank_ticks']])
        if receipt['inclusion']:
            vis['apply_to_first_inclusion_ns'] = [scale(tick-receipt['apply']) for tick in receipt['inclusion']]
    exact = [row for row in result[2:] if 'callback_to_commit_ns' in row]
    return dict(coverage=stats,strokes=result,warm_matched=len(exact),
        warm_with_first_inclusion=sum('apply_to_first_inclusion_ns' in row for row in exact),
        stage_p50_p95_ns={key:[quantile([row[key] for row in exact],q) for q in (.5,.95)]
                         for key in ('callback_to_commit_ns','commit_to_send_ns','send_to_apply_ns',
                                     'apply_to_swap_annotation_ns','apply_to_render_begin_ns','render_begin_to_swap_ns')},
        scope='A matching CA version was observed in the annotated update and linked to the first CRC-changing latch.')
