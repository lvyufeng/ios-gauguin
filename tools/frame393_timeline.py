"""Connect exact member versions and their source transactions to first visible frames."""

from base64 import b64decode
from collections import defaultdict
from importlib import import_module
import re
from struct import Struct

from frame344_log import indexed,quantile,require
import frame374_native_ca as native
from frame369_swap_timing import decode as swap_timing
from frame376_capture import packet_lane
from frame390_build import CAP,load_ca_port
from frame390_timeline import BLOCK,FOOTER

WIRE = Struct('<8IQQ2IQIIQ')
SUMMARY = re.compile(r'Q (\d+) (\d+) (\d+) (\d+) (\d+)')
MAX_RECEIPTS = 32
MAX_CONSOLE_BYTES = 85_000


def decode(raw, start, end, packets):
    load_ca_port()
    member = import_module('frame390_membership')
    prefix = 'SWEET F393 '
    snapshots,transactions = [],[]
    for line in raw.splitlines():
        if line.startswith('SWEET F390 '): snapshots.append(line)
        if line.startswith(prefix): transactions.append(line)
    require(0<sum(len(line)+2 for line in snapshots+transactions)<=MAX_CONSOLE_BYTES,
        'CA membership console bound exceeded')
    stats,snapshots = member.decode('\n'.join(snapshots),start,end)
    lanes = defaultdict(list)
    for snap in snapshots:
        lanes[snap.stroke].append(snap)
    transport = indexed(packets,lambda row:row['serial'],'CA kernel IPC receipt')
    by_swap, summaries = defaultdict(list),{}
    stroke = count = emitted = 0
    missing_ipc = 0
    footer = None
    seen = set()
    for line in transactions:
        require(footer is None,'CA transaction footer precedes data')
        body = line[len(prefix):]
        if match := SUMMARY.fullmatch(body):
            number,retained,lost,amount,omitted = map(int,match.groups())
            require(emitted==count and number==stroke+1<=member.STROKES and retained<=CAP and
                amount<=MAX_RECEIPTS and (not omitted or amount==MAX_RECEIPTS) and
                (not lost or (retained==CAP and amount==omitted==0)) and
                (not stats[number]['lost'] or amount==omitted==0),'invalid CA retention or overflow count')
            stroke,count,emitted = number,amount,0
            seen = set()
            summaries[stroke] = dict(retained=retained,lost=lost,emitted=count,omitted=omitted)
            continue
        if match := FOOTER.fullmatch(body):
            armed,number,dropped = map(int,match.groups())
            require(stroke==number==member.STROKES and emitted==count,'incomplete CA transaction lanes')
            footer = dict(armed=bool(armed),receipt_contention=dropped)
            continue
        match = BLOCK.fullmatch(body)
        require(match and stroke>0,'invalid CA member receipt block')
        number,at,amount = map(int,match.groups()[:3])
        raw_data = b64decode(match[4],validate=True)
        require(number==stroke and at==emitted and 0<amount<=member.BLOCK and
                emitted+amount<=count and len(raw_data)==amount*WIRE.size,'invalid CA member receipt stride')
        emitted += amount
        lane = lanes[stroke]
        for fields in WIRE.iter_unpack(raw_data):
            index,identity,commit,encoded,send,receive,command,apply,sender,receiver,before,after,ptr,cid,version,mask = fields
            serial,msg = identity&0xffff,identity>>16
            require(index<len(lane) and mask&(1<<index) and mask>>len(lane)==0 and ptr>0 and cid>0 and
                    (ptr,cid,version) not in seen and serial>0 and 40002<=msg<=40005 and
                    0<=commit<send<encoded<end-start and send<=receive<command<apply<lane[index].tick-start and
                    sender>0 and receiver>0 and ((before==after==0) or apply<=before<after<lane[index].tick-start),
                    'invalid CA member identity, first observation, or transaction order')
            seen.add((ptr,cid,version))
            linked = [snap for i,snap in enumerate(lane) if mask&(1<<i)]
            first = lane[index]
            require(first.tick==min(snap.tick for snap in linked) and all(
                snap.observed==member.AMBIGUOUS or (snap.observed==member.PRESENT and
                (snap.context,snap.context_id,snap.version)==(ptr,cid,version)) for snap in linked),
                'membership mask links a missing or different context version')
            packet = transport.get(serial)
            if packet is None or (packet['message_id'],packet['sender_thread'],packet['receiver_thread'],packet['send_tick']) != (
                    msg,sender,receiver,start+send) or not start+send<=packet['copyout_tick']<=start+receive:
                missing_ipc += 1
                continue
            receipt = dict(context=cid,version=version,serial=serial,commit=start+commit,encoded=start+encoded,
                send=start+send,delivered=packet['copyout_tick'],receive=start+receive,apply=start+apply,
                first_membership=first.key,inclusion=(start+before,start+after) if before else None)
            for snap in linked:
                by_swap[snap.key].append(receipt)
    require(footer is not None,'CA member footer is absent')
    return dict(snapshots=stats,retention=summaries,missing_IPC=missing_ipc,**footer),snapshots,dict(by_swap)


def measure(execution, raw, rows, n, d, latches, scans, *, allow_refused_prefix=False):
    start,end,native_n,native_d = native.envelope(raw)
    require((n,d)==(native_n,native_d),'CA and display clock domains differ')
    packets = packet_lane(raw,n,d,allow_refused_prefix=allow_refused_prefix)
    stats,snapshots,receipts = decode(raw,start,end,packets['pairs'])
    if missing := packets['losses'].get('unexported_tail'):
        stats.update(transport_exact_prefix=packets['paired_exact_receipts'],transport_unexported_tail=missing)
    observed = indexed(snapshots,lambda snap:snap.key,'annotated CA snapshot')
    render_events = native.decode(raw,start,end)
    accepted = swap_timing(rows,n,d,begin_threads=True)
    rendered = native.link_swaps(render_events,accepted,start,end,n,d)
    begin_thread = {row['generation']:row['begin_thread'] for row in accepted}
    annotations = {(event.tick,event.thread,*event.args) for event in render_events if event.kind==native.ANNOTATION}
    first = import_module('run-frame385-trial').first_after_touch(
        scans,import_module('frame384_stage').parse(raw)[1],execution,n,d)
    scale = lambda tick:tick*n//d
    result = []
    for frame in first:
        stroke,scan,returned = (frame[key] for key in ('stroke','first_scan','touch_callback_return_ns'))
        vis = dict(stroke=stroke,scan=scan,callback_return_ns=returned,transactions=[])
        result.append(vis)
        latch = latches.get(scan)
        link = rendered.get(latch['generation']) if latch else None
        if not link or not link['render']:
            continue
        render = link['render']
        key = (render['annotation_tick'],begin_thread[latch['generation']],latch['swap'],render['frame_seed'])
        snap = observed.get(key)
        if not snap or key not in annotations or snap.stroke!=stroke or not render['begin_tick']<=snap.tick<=latch['issued_tick']:
            continue
        retention = stats['retention'][stroke]
        vis.update(swap=latch['swap'],swap_membership=snap.observed,gate=snap.gate,
            receipt_enumeration_capped=bool(retention['lost'] or retention['omitted'] or stats['snapshots'][stroke]['lost']),
            swap_to_visible_ns=[scale(tick-latch['swap_tick']) for tick in frame['first_vblank_ticks']])
        for item in receipts.get(key,()):
            if returned is None or scale(item['commit'])<returned:
                continue
            earliest = item['first_membership'][0]
            hit = dict(context=item['context'],version=item['version'],serial=item['serial'],
                callback_to_commit_ns=scale(item['commit'])-returned,
                commit_to_send_ns=scale(item['send']-item['commit']),send_to_apply_ns=scale(item['apply']-item['send']),
                apply_to_first_observed_membership_ns=scale(earliest-item['apply']),
                apply_to_visible_render_begin_ns=scale(render['begin_tick']-item['apply']),
                visible_render_begin_to_swap_ns=scale(link['begin_tick']-render['begin_tick']))
            if item['inclusion']:
                hit['apply_to_first_inclusion_ns'] = [scale(tick-item['apply']) for tick in item['inclusion']]
            vis['transactions'].append(hit)
    warm = result[2:]
    candidates = [item for row in warm for item in row['transactions']]
    keys = ('callback_to_commit_ns','commit_to_send_ns','send_to_apply_ns',
            'apply_to_first_observed_membership_ns','apply_to_visible_render_begin_ns','visible_render_begin_to_swap_ns')
    return dict(coverage=stats,strokes=result,warm_strokes_with_exact_member=sum(bool(row['transactions']) for row in warm),
        warm_strokes_with_multiple_exact_members=sum(len(row['transactions'])>1 for row in warm),
        warm_exact_members=len(candidates),warm_members_with_native_inclusion=sum('apply_to_first_inclusion_ns' in row for row in candidates),
        warm_member_p50_p95_ns={key:[quantile([row[key] for row in candidates],q) for q in (.5,.95)] for key in keys},
        scope='Membership times are the earliest complete matching annotations in the retained swipe. Results enumerate exact candidate versions in the first visible update.')
