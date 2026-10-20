#!/usr/bin/env python3
"""Convert a raw disk image to Android's sparse format, chunk by chunk.

    tools/img2simg.py IN.img OUT.simg [--block 4096] [--chunk 4M]

fastboot's `flash` refuses huge raw images: copy_avb_footer() reads the whole
file into a std::string before sending anything, so a 16 GiB userdata image
dies with "Failed reading from userdata". Sparse images skip that path, and
only the non-zero blocks cross the wire.

The encoder streams: it writes a placeholder header, emits one chunk per
--chunk slice (RAW, or FILL/DONT_CARE when the slice is uniform), then patches
total_chunks into the header.
"""
import argparse
import os
import struct
import sys

MAGIC = 0xED26FF3A
CHUNK_RAW = 0xCAC1
CHUNK_FILL = 0xCAC2
CHUNK_DONT_CARE = 0xCAC3
FILE_HDR = 28
CHUNK_HDR = 12


def human(n):
    for unit in ('B', 'K', 'M', 'G'):
        if n < 1024 or unit == 'G':
            return f'{n:.1f}{unit}'
        n /= 1024.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--block', type=int, default=4096)
    ap.add_argument('--chunk', default='4M')
    args = ap.parse_args()

    c = args.chunk
    mult = {'K': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3}.get(c[-1].upper(), 1)
    chunk_bytes = int(c[:-1]) * mult if c[-1].isalpha() else int(c)
    per_chunk = chunk_bytes // args.block
    if per_chunk * args.block != chunk_bytes or per_chunk == 0:
        sys.exit('--chunk must be a non-zero multiple of --block')

    size = os.path.getsize(args.src)
    total_blks = (size + args.block - 1) // args.block

    nchunks = 0
    raw_bytes = 0
    with open(args.src, 'rb') as f, open(args.dst, 'wb') as out:
        out.write(b'\0' * FILE_HDR)          # placeholder, patched below
        blk = 0
        while blk < total_blks:
            want = min(per_chunk, total_blks - blk)
            data = f.read(want * args.block)
            if len(data) < want * args.block:  # pad a short tail
                data += b'\0' * (want * args.block - len(data))
            first = data[0:1]
            if data.count(first) == len(data):
                if first == b'\0':
                    kind, payload = CHUNK_DONT_CARE, b''
                else:
                    kind, payload = CHUNK_FILL, struct.pack('<I', first[0])
            else:
                kind, payload = CHUNK_RAW, data
                raw_bytes += len(data)
            out.write(struct.pack('<HHII', kind, 0, want, CHUNK_HDR + len(payload)))
            out.write(payload)
            nchunks += 1
            blk += want
            if blk % (per_chunk * 256) == 0:
                print(f'  {human(blk * args.block)} / {human(size)}', file=sys.stderr)
        out.seek(0)
        out.write(struct.pack('<IHHHHIIII', MAGIC, 1, 0, FILE_HDR, CHUNK_HDR,
                              args.block, total_blks, nchunks, 0))

    print(f'{args.dst}: {nchunks} chunks, {human(raw_bytes)} raw of {human(size)}, '
          f'file {human(os.path.getsize(args.dst))}', file=sys.stderr)


if __name__ == '__main__':
    main()