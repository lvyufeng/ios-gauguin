"""Place explicit main-thread CA call spans alongside producer deadlines."""

from collections import Counter
import re

from frame364_analysis import trace

PREFIX = 'SWEET SB CA365: '
ACTIVE = re.compile(r'active commit=([01]) flush=([01]) max_rows=8192')
CALL = re.compile(r'method=(commit|flush) entered_us=(\d{9}) left_us=(\d{9}) returned=([01]) depth=([1-9]\d{0,3}) caller=(\S+)')


def parse(text):
    configured = None
    calls = []
    for row in text.splitlines():
        _,prefix,body = row.partition(PREFIX)
        if not prefix:
            continue
        if match := ACTIVE.fullmatch(body):
            trace.require(configured is None and not calls,'repeated CA timing activation')
            configured = {method:value=='1' for method,value in zip(('commit','flush'),match.groups(),strict=True)}
            continue
        match = CALL.fullmatch(body)
        trace.require(configured and match and len(calls)<8192,'malformed or unbounded CA timing row')
        method,entered,left,returned,depth,caller = match.groups()
        entry,exit = int(entered),int(left)
        trace.require(configured[method] and 220_000_000<=entry<270_000_000 and entry<=exit and
                      returned=='1' and 0<int(depth)<=8192,'CA forwarding, clock or window is unqualified')
        calls.append(dict(method=method,entered_ns=entry*1000,left_ns=exit*1000,depth=int(depth),caller=caller))
    trace.require(configured and all(configured.values()),'CA method timing failed to install')
    return dict(configured=configured,calls=sorted(calls,key=lambda r:(r['entered_ns'],r['depth'],r['left_ns'])))


def attribute(ca, front, budget):
    exact = {row['frame']:row for row in budget['producer']['exact_next_writers']}
    details = []
    for miss in front['details']:
        callback = miss['returned_main_callback']
        if not (callback and miss['next_swap_within_stroke_tail']):
            continue
        returned = callback['returned_us']*1000
        cutoff = miss['deadline_ns']
        swap = cutoff+miss['next_swap']['late_ns']
        job = exact.get(miss['scan'])
        created = returned+job['return_to_Core_creation_ns'] if job else None
        related = [call for call in ca['calls'] if call['entered_ns']<=swap and returned<=call['left_ns']]
        details.append(dict(stroke=miss['stroke'],scan=miss['scan'],callback_id=callback['id'],cutoff_ns=cutoff,
            callback_return_ns=returned,accepted_swap_ns=swap,Core_created_ns=created,Core_job=job,
            explicit_CA_calls=related,CA_spans_cutoff=any(c['entered_ns']<=cutoff<c['left_ns'] for c in related),
            CA_spans_post_callback_before_Core=bool(created and any(
                max(c['entered_ns'],returned)<min(c['left_ns'],created) for c in related))))

    def summarize(rows):
        return dict(scans=len(rows),with_explicit_CA_calls=sum(bool(x['explicit_CA_calls']) for x in rows),
            CA_spanning_cutoff=sum(x['CA_spans_cutoff'] for x in rows),
            CA_between_return_and_Core=sum(x['CA_spans_post_callback_before_Core'] for x in rows))

    return dict(configured=ca['configured'],call_counts=dict(Counter(r['method'] for r in ca['calls'])),
        all=summarize(details),warm=summarize([r for r in details if r['stroke']>=3]),
        details=details,scope='Observed public main-thread commit and flush calls, compared on a common clock. '
        'Their wall spans do not identify implicit commits, backboard transaction identity or CPU use inside a call.')
