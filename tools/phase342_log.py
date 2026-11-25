"""Strict wall/CPU/wall partition contract shared by both 0342 codecs."""
SLOP=2000
U64=2**64


def bounds(wall,cpu,envelope,slop=SLOP):
    if min(wall,cpu,envelope)<0 or cpu>wall+envelope+slop:
        raise ValueError('incoherent CPU interval')
    lo=max(0,cpu-envelope-slop);hi=min(wall,cpu+slop)
    if not 0<=lo<=hi<=wall:raise ValueError('CPU bounds')
    return dict(wall_ns=wall,CPU_lower_ns=lo,CPU_upper_ns=hi,
        off_CPU_lower_ns=wall-hi,off_CPU_upper_ns=wall-lo)


def partition(first,last,mask,queries,query_ns,flags,begin,end,cpu,envelope):
    n=len(begin)
    if not n==len(end)==len(cpu)==len(envelope):raise ValueError('phase vector widths')
    if flags or not (0<first<=last<U64 and 0<mask<2**n and queries==mask.bit_count()+1):
        raise ValueError('phase flags, span, mask or query count')
    if any(not isinstance(v,int) or not 0<=v<U64 for a in (begin,end,cpu,envelope) for v in a):
        raise ValueError('phase integer range')
    indices=[i for i in range(n) if mask>>i&1]
    if any(any(a[i] for a in (begin,end,cpu,envelope)) for i in range(n) if i not in indices):
        raise ValueError('nonzero skipped phase')
    widths=[];previous=first
    for i in indices:
        if not previous<=begin[i]<=end[i]<=last:raise ValueError('phase order')
        widths.append(begin[i]-previous);previous=end[i]
    widths.append(last-previous)
    if sum(widths)!=query_ns:raise ValueError('unique query envelope partition')
    phases=[dict(wall_ns=0,CPU_lower_ns=0,CPU_upper_ns=0,off_CPU_lower_ns=0,off_CPU_upper_ns=0) for _ in range(n)]
    for j,i in enumerate(indices):
        if envelope[i]!=widths[j]+widths[j+1]:raise ValueError('adjacent query envelope')
        phases[i]=bounds(end[i]-begin[i],cpu[i],envelope[i])
    if sum(p['wall_ns'] for p in phases)+query_ns!=last-first:raise ValueError('whole phase partition')
    return phases
