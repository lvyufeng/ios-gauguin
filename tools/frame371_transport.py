"""Place exact kernel transport receipts alongside, without assigning CA transactions."""

from collections import Counter
from importlib import import_module
import re

from frame344_log import one, quantile, require
from frame365_analysis import parse as parse_CA


MAX_PAIRS = 1536
MAX_SENDS = 16384
HEADER = (r'^SWEET F371 H: count=(\d+) cap=(\d+) sent=(\d+) sent_cap=(\d+) copied=(\d+) '
          r'missed=(\d+) busy=(\d+) evicted=(\d+) failed=(\d+)$')


def decode(text, numer, denom):
    names = ('count','capacity','sent','send_capacity','copied','missed','busy','evicted','failed')
    counts = dict(zip(names,map(int,one(HEADER,text,'producer transport header')),strict=True))
    footer = int(one(r'^SWEET F371 F: count=(\d+)$',text,'producer transport footer'))
    start,end = map(int,one(r'^SWEET F344 H: .* start=(\d+) end=(\d+) numer=\d+ denom=\d+$',
                           text,'frame capture window'))
    require(numer>0 and denom>0 and start<end and counts['capacity']==MAX_PAIRS and
        counts['send_capacity']==MAX_SENDS and
        counts['count']==footer==min(counts['copied'],MAX_PAIRS) and
        counts['copied']+counts['failed']<=min(counts['sent'],MAX_SENDS),
        'transport counter scope or completion differs')
    pairs = []
    identities = set()
    ns = lambda tick: tick*numer//denom
    for line in re.findall(r'^SWEET F371 E (.*)$',text,re.M):
        fields = line.split()
        require(len(fields)==7 and all(re.fullmatch(r'[0-9a-f]{1,16}',v) for v in fields),
                'invalid producer transport record')
        serial,mid,send,post,copyout,sender,receiver = [int(v,16) for v in fields]
        require(0<serial<=min(counts['sent'],MAX_SENDS) and serial not in identities and
            mid<=0xffffffff and 0<sender and 0<receiver and start<=send<=post<=copyout<end,
            'duplicate or inconsistent producer transport receipt')
        identities.add(serial)
        pairs.append(dict(serial=serial,message_id=mid,send_ns=ns(send),post_ns=ns(post),
            copyout_ns=ns(copyout),sender_thread=sender,receiver_thread=receiver))
    require(len(pairs)==counts['count'],'producer transport row count differs')
    complete = (counts['copied']<=MAX_PAIRS and counts['sent']<=MAX_SENDS and
                not any(counts[k] for k in ('missed','busy','evicted','failed')))
    return dict(counters=counts,paired_exact_receipts=len(pairs),full_scope_observed=complete,
        pairs=sorted(pairs,key=lambda r:(r['copyout_ns'],r['serial'])))


def phases(values):
    values = list(values)
    return dict(count=len(values),p50_ns=quantile(values,.5),p95_ns=quantile(values,.95))


def classify(pair, cutoff):
    if cutoff < pair['send_ns']:
        return 'before_send'
    if cutoff < pair['post_ns']:
        return 'send_before_post'
    if cutoff < pair['copyout_ns']:
        return 'post_before_copyout'
    return 'copyout_before_SwapBegin'


def deadline_transport(frontend, swaps, capture, ca, exact_core, to_ns):
    by_generation = {row['generation']:row for row in swaps}
    core_by_scan = {row['frame']:row for row in exact_core}
    details = []
    for miss in frontend['details']:
        returned = miss['returned_main_callback']
        upcoming = miss['next_swap']
        swap = by_generation.get(upcoming['generation']) if upcoming and miss['next_swap_within_stroke_tail'] else None
        cutoff = miss['deadline_ns']
        begin = to_ns(swap['begin_tick']) if swap and swap['begin_tick'] else None
        lower = returned['returned_us']*1000 if returned else None
        if lower is not None:
            require(lower<=cutoff, 'returned touch occurs after its cutoff')
        candidates = []
        ca_calls = []
        if lower is None:
            stage = 'no_returned_touch'
        elif begin is None:
            stage = 'missing_SwapBegin'
        elif begin<=cutoff:
            stage = 'SwapBegin_before_cutoff'
        else:
            ca_calls = [row for row in ca if row['entered_ns']<=begin and lower<=row['left_ns']]
            eligible = [p for p in capture['pairs'] if lower<=p['copyout_ns']<=begin]
            candidates = [dict(p,stage=classify(p,cutoff),
                copyout_to_SwapBegin_ns=begin-p['copyout_ns'],send_before_touch_return=p['send_ns']<lower)
                for p in eligible]
            same = {p['stage'] for p in candidates if p['receiver_thread']==swap['begin_thread']}
            stage = (next(iter(same)) if len(same)==1 else 'multiple_same_thread_stages' if same else
                     'different_receiver_thread_only' if candidates else 'no_scoped_copyout')
        details.append(dict(stroke=miss['stroke'],scan=miss['scan'],cutoff_ns=cutoff,
            touch_return_ns=lower,CA_observer_ns=(miss['CA_observer']['after_ca_us']*1000
                if miss['CA_observer'] else None),observed_CA_calls=ca_calls,
            begin_ns=begin,begin_thread=swap['begin_thread'] if swap else None,
            accepted_generation=swap['generation'] if swap else None,exact_next_Core=core_by_scan.get(miss['scan']),
            same_thread_deadline_stage=stage,candidate_transports=candidates))
    return details


def summarize(details):
    return dict(no_swap_deadlines=len(details),
        stages=dict(Counter(row['same_thread_deadline_stage'] for row in details)),
        with_return=sum(row['touch_return_ns'] is not None for row in details),
        same_thread_any=sum(any(p['receiver_thread']==row['begin_thread'] for p in row['candidate_transports'])
            for row in details),
        return_to_SwapBegin=phases(row['begin_ns']-row['touch_return_ns'] for row in details
            if row['touch_return_ns'] is not None and row['begin_ns'] is not None),
        before_cutoff_with_exact_Core=sum(row['exact_next_Core'] is not None and
            row['exact_next_Core']['Core_creation_after_cutoff_ns']<=0 for row in details))


def analyze_transport(path, report, raw, events, numer, denom, load, *, capture=None):
    capture = decode(raw,numer,denom) if capture is None else capture
    ca = parse_CA((path/'springboard-new.log').read_text())
    core = load(path/'core-wait-execution-analysis.json')
    io = load(path/'kernel-IO-identity-analysis.json')
    require(core['coverage_qualified'] and io['coverage_qualified'],'Core and IO identity require a qualified capture')
    to_ns = lambda tick: tick*numer//denom
    audit = import_module('audit-frame364-deadlines')
    exact = audit.producer_budget({'frontend':report['frontend_cutoffs']},events,core['rows'],io['submits'],to_ns)
    details = deadline_transport(report['frontend_cutoffs'],report['swap_timing']['swap_timing'],
        capture,ca['calls'],exact['exact_next_writers'],to_ns)
    pairs = capture['pairs']
    return dict(capture=capture,timing=dict(send_to_post=phases(p['post_ns']-p['send_ns'] for p in pairs),
        post_to_copyout=phases(p['copyout_ns']-p['post_ns'] for p in pairs)),
        all_strokes=summarize(details),warm_strokes_3_to_13=summarize([d for d in details if d['stroke']>=3]),
        cutoff_details=details,exact_next_core=exact,
        interpretation=('Each receipt is the same live kmsg across send, post entry and successful kernel '
            'rights/body copyout. Matching the SwapBegin receive thread places the events on that thread. '
            'The packet role, CA transaction and any user-space cross-thread dispatch require separate evidence.'))
