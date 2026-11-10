"""Validate a read-only device scan and reconstruct a full independent clone.

Every chunk is checked, including chunks already present in the clone. Only
mismatching bytes cross USB. The final Python whole-file SHA must equal the
device's independently computed whole-prefix SHA; metadata alone cannot pass.
"""
import hashlib
import os
import struct


def decode(raw, *, volume, partition, chunk=1048576):
    if type(volume) is not int or type(partition) is not int or type(chunk) is not int or \
            not 0 < volume <= 17179869184 or chunk != 1048576 or volume % chunk or partition < volume:
        raise ValueError('invalid fixed scan geometry')
    count = volume // chunk
    if len(raw) != 64 + 32 * count or raw[:8] != b'GGSCAN1\0':
        raise ValueError('incomplete, extra or unknown scan protocol')
    if struct.unpack_from('<QQQ', raw, 8) != (volume, chunk, partition):
        raise ValueError('scan geometry differs')
    return dict(volume=volume, partition=partition, chunk=chunk,
                chunks=[raw[32+i*32:64+i*32] for i in range(count)], whole=raw[-32:])


def reconstruct(target, scan, fetch, *, max_changed_bytes=1073741824, reserve=lambda n: True):
    volume, chunk = scan['volume'], scan['chunk']
    if target.seek(0, 2) != volume:
        raise ValueError('independent clone size differs')
    changed = []
    for i, want in enumerate(scan['chunks']):
        target.seek(i*chunk); data = target.read(chunk)
        if len(data) != chunk:
            raise ValueError('short clone')
        if hashlib.sha256(data).digest() != want:
            changed.append(i)
    if len(changed)*chunk > max_changed_bytes:
        raise ValueError('local COW change budget exceeded before fetch/write')
    groups = []
    for i in changed:
        if groups and groups[-1][0]+groups[-1][1] == i and groups[-1][1] < 32:
            groups[-1][1] += 1
        else:
            groups.append([i, 1])
    for first, count in groups:
        n = count*chunk
        if not reserve(n):
            raise ValueError('host reserve reached before fetch/write')
        data = fetch(first*chunk, n)
        if len(data) != n:
            raise ValueError('short changed-chunk read')
        # Validate the ENTIRE group before writing its first byte.
        for j in range(count):
            if hashlib.sha256(data[j*chunk:(j+1)*chunk]).digest() != scan['chunks'][first+j]:
                raise ValueError('device bytes changed since scan')
        target.seek(first*chunk)
        if target.write(data) != n:
            raise ValueError('short local clone write')
    target.flush(); os.fsync(target.fileno()); target.seek(0)
    full = hashlib.file_digest(target, 'sha256').digest()
    if full != scan['whole']:
        raise ValueError('complete reconstructed volume differs from device digest')
    return dict(fresh_bytes_at_device=volume, reconstructed_bytes=volume,
                USB_changed_bytes=len(changed)*chunk, changed_chunks=len(changed),
                changed_groups=len(groups), sha256=full.hex(), all_chunks_verified=len(scan['chunks']))
