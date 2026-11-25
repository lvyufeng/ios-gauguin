#!/usr/bin/env python3
"""Qualify a fixed native performance request from its firmware receipts."""
import re


def analyze(kernel, *, perf_index=4, bw_index=None):
    frequency, default_index = {4:(565_000_000,9),5:(650_000_000,10),6:(800_000_000,12)}[perf_index]
    bw_index = default_index if bw_index is None else bw_index
    bandwidth = {(4,9):5_412_000_000,(5,10):6_220_000_000,(5,11):7_216_000_000,
                 (6,12):8_371_200_000}[perf_index,bw_index]
    bw_word = (bw_index << 12) | bw_index
    rows = [(i,line) for i,line in enumerate(kernel.splitlines())
            if line.startswith(('SWEET GMU PERF:', 'SWEET GMU BW:',
                                'SWEET GMU TEST:', 'SWEET GMU DCVS:'))]
    patterns = [
        r'SWEET GMU PERF: complete request=00302b04 words=43 ack=([0-9a-f]{8})/([0-9a-f]{8})/([0-9a-f]{8}); no BW/TEST/normal HFI_ON/GPU/Metal qualification',
        r'SWEET GMU BW: complete request=0040a003 words=160 levels=13 cnoc=1 ddr=3 waits=00000000/00000000 ack=([0-9a-f]{8})/([0-9a-f]{8})/([0-9a-f]{8})',
        r'SWEET GMU TEST: complete request=00500105 words=1 ack=([0-9a-f]{8})/([0-9a-f]{8})/([0-9a-f]{8}); native legacy startup only',
        (f'SWEET GMU DCVS: request perf_index={perf_index} hz={frequency} bw_index={bw_index} Bps={bandwidth} '
         f'option=00000000 perf={0x30000000 | perf_index:08x} bw={bw_word:08x}; requested, not measured'),
        r'SWEET GMU DCVS: complete before=00000000 ack=80000000 cleared=00000000 return=00000000; native register/OOB request only',
    ]
    matches = [re.fullmatch(p,row[1]) for p,row in zip(patterns,rows)]
    qualified = len(rows)==5 and all(matches)
    acks = []
    if qualified:
        for sequence,match in zip((3,4,5),matches[:3]):
            header,echo,status = [int(v,16) for v in match.groups()]
            accepted = (header&255)==126 and 3 <= ((header>>8)&255) <= 19 and ((header>>16)&15)==2 and (echo&0xfff00000)==sequence<<20 and status==0
            qualified = qualified and accepted
            acks.append(dict(sequence=sequence,header=header,echo=echo,status=status,accepted=accepted))
    return dict(active=bool(qualified),native_request_accepted=bool(qualified),
                frequency_hz_requested=frequency,perf_index=perf_index,bw_index=bw_index,
                bandwidth_bytes_per_second_requested=bandwidth,
                acknowledgments=acks,lines=[line for _i,line in rows],
                frequency_measured=False,physical_fps_qualified=False)
