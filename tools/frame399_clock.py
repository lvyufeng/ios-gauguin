"""Decode the sampled CPUFreq-HW rows and exact GPU issue/completion joins."""

import re

import frame344_log as trace

ROW = re.compile(r'^SWEET CPU399: fence=(\d+) cpu=([0-7]) issue=([0-9a-f:]+) done=([0-9a-f:]+)$')
MAX_SAMPLES = 24
XO_HZ = 19_200_000
MAX_INTERVAL_NS = 40_000_000


def snapshot(text):
    words = text.split(':')
    trace.require(len(words) == 9, 'invalid CPUFreq reading fields')
    tick,end,mask = map(int,words[:3])
    trace.require(0 <= tick <= end and 0 <= mask <= 3 and (tick or not end and not mask),
                  'invalid CPUFreq reading bounds')
    domains = []
    for domain,at in enumerate((3,6)):
        index,raw,cycles = int(words[at]),int(words[at+1],16),int(words[at+2])
        valid = bool(mask & 1 << domain)
        trace.require(len(words[at+1]) == 8 and 0 <= cycles <= 0xffffffff and
                      (valid and index < 40 and raw != 0xffffffff and (not raw >> 30 or raw & 0xff)
                       or not valid and index == raw == cycles == 0), 'invalid CPUFreq domain sample')
        domains.append(dict(index=index,row=raw,cycles=cycles,pll_selected=bool(raw >> 30),
                            nominal_pll_hz=(raw & 0xff)*XO_HZ if raw >> 30 else None) if valid else None)
    return dict(start=tick,end=end,domains=domains)


def observe(raw, rows, n, d, moving):
    lines = [line for line in raw.splitlines() if line.startswith('SWEET CPU399: ')]
    trace.require(len(lines) <= MAX_SAMPLES, 'CPU frequency sample bound exceeded')
    issued,visible = (trace.indexed(rows[kind],lambda r:r.id,'native fence stage')
                      for kind in (trace.ISSUE,trace.READY))
    edges = trace.indexed(rows[trace.VBLANK],lambda r:r.id,'physical scan')
    windows = [(edges[w['first_scan']].tick,edges[w['last_scan']].tick)
               for w in moving['ordinary']['windows']]
    samples,previous = [],0
    for line in lines:
        match = ROW.fullmatch(line)
        trace.require(match and len(line) < 256, 'invalid CPU frequency receipt')
        fence,cpu = map(int,match.groups()[:2])
        start,done = (snapshot(value) for value in match.groups()[2:])
        trace.require(fence > previous and start['start'] > 0, 'CPU frequency fences are out of order')
        previous = fence
        issue,ready = issued.get(fence),visible.get(fence)
        in_warm = bool(issue and any(begin <= issue.tick < end for begin,end in windows))
        if issue:
            trace.require(issue.tick <= start['start'], 'clock sampling preceded native issue')
        if done['start'] and ready:
            trace.require(start['end'] <= ready.tick <= done['start'], 'completion sample preceded cache visibility')
        load_bounds = []
        span_min = (done['start']-start['end'])*n//d
        span_max = (done['end']-start['start'])*n//d
        for left,right in zip(start['domains'],done['domains'],strict=True):
            if left and right and ready and 0 < span_min <= span_max <= MAX_INTERVAL_NS:
                delta = (right['cycles']-left['cycles']) & 0xffffffff
                load_bounds.append([delta*1_000_000_000//span_max,
                                    delta*1_000_000_000//span_min])
            else:
                load_bounds.append(None)
        samples.append(dict(fence=fence,cpu=cpu,ordinary_warm=in_warm,issue=start,completion=done,
                            observed_domain_cycle_rates_per_s_bounds=load_bounds,
                            issue_receipt=bool(issue),ready_receipt=bool(ready and done['start'])))
    warm = [sample for sample in samples if sample['ordinary_warm']]
    return dict(samples=samples,warm_samples=len(warm),
                warm_with_two_domain_pairs=sum(all(row['observed_domain_cycle_rates_per_s_bounds']) for row in warm),
                qualified=any(all(row['observed_domain_cycle_rates_per_s_bounds']) for row in warm),
                scope='The selected LUT row estimates the requested PLL frequency. Each counter is shared '
                      'by a domain and can reflect idle residency. Counter rates do not attest per-core frequency.')
