#!/usr/bin/env python3
"""Follow the SWEET persistent console log (patch 0047) while the kernel runs.

  live-log.py OUT.txt [--secs N] [--area-blocks 1025]

The phone is in TWRP (adb) and the kernel under test is running on it. TWRP's
adbd serves USB, so the last blocks of the userdata partition - the console
ring the kernel keeps appending to - can be read in order while the kernel is
alive. Nothing is written.

The userdata partition is found by the "SWEETLOG" header in its last block, not
by name: /dev/by-name/userdata points at a different partition in this recovery
build than in the one from 2026-10-20.

Files left next to OUT.txt: OUT.txt.bin (the raw area, same format as
tools/sweet-log-pull.sh) and OUT.txt.live (what was seen while running, with
ring wrap handled - the part a reset can still lose).
"""
import os, struct, subprocess, sys, time

BLK = 4096
MAGIC = b'SWEETLOG'


def adb_shell(cmd):
    return subprocess.run(['adb', 'shell', cmd], capture_output=True, timeout=30).stdout


def adb_exec(cmd, timeout):
    return subprocess.run(['adb', 'exec-out', cmd], capture_output=True,
                          timeout=timeout).stdout


def find_area(blocks):
    """Path + size of a whole block device whose last block holds the header."""
    names = adb_shell("ls -l /dev/block/sd* 2>/dev/null").decode().split('\n')
    cands = []
    for line in names:
        if 'brw' not in line:
            continue
        path = line.split()[-1]
        cands.append(path)
    hits = []
    for path in cands:
        size = adb_shell('blockdev --getsize64 %s 2>/dev/null' % path).decode().strip()
        if not size.isdigit():
            continue
        size = int(size)
        skip = size // BLK - blocks
        raw = adb_exec('dd if=%s bs=4096 skip=%d count=1 2>/dev/null' % (path, skip), 20)
        if raw[:8] == MAGIC:
            hits.append((path, size))
    if not hits:
        sys.exit('no partition with a SWEETLOG header in its last block')
    if len(hits) > 1:
        print('warning: several candidates, using %s' % hits[0][0], file=sys.stderr)
    return hits[0]


def main():
    out = sys.argv[1]
    secs = 60
    blocks = 1025
    a = sys.argv[2:]
    while a:
        if a[0] == '--secs':
            secs = int(a[1]); a = a[2:]
        elif a[0] == '--area-blocks':
            blocks = int(a[1]); a = a[2:]
        else:
            sys.exit('unknown argument %s' % a[0])

    path, size = find_area(blocks)
    skip = size // BLK - blocks
    print('area: %s (%d blocks from %d)' % (path, blocks, skip), file=sys.stderr)

    area = bytearray()
    pos = skip                 # next device block to read
    ring_total = None          # last "total" seen while running
    stream = open(out + '.live', 'w')
    end = time.time() + secs
    while time.time() < end:
        try:
            raw = adb_exec('dd if=%s bs=4096 skip=%d count=32 2>/dev/null' % (path, pos), 20)
        except subprocess.TimeoutExpired:
            continue
        if not raw:
            time.sleep(0.3)
            continue
        area += raw
        pos += (len(raw) + BLK - 1) // BLK
        if pos >= skip + blocks:      # full ring seen: decode what we have
            data = bytes(area)
            if data[:8] == MAGIC:
                _, _, rsize, total, seq = struct.unpack_from('<8sIIQQ', data, 0)
                text = decode(data, rsize, total)
                stream.seek(0)
                stream.write(text)
        time.sleep(0.2)

    # One more pass: the newest state of the ring, saved as a pull-compatible area.
    data = adb_exec('dd if=%s bs=4096 skip=%d count=%d 2>/dev/null' % (path, skip, blocks),
                    60)
    with open(out + '.bin', 'wb') as f:
        f.write(data)
    if data[:8] == MAGIC:
        _, _, rsize, total, seq = struct.unpack_from('<8sIIQQ', data, 0)
        text = decode(data, rsize, total)
        open(out, 'w').write(text.replace('\r', ''))
        if ring_total is not None and total != ring_total:
            print('note: on-disk total %d != last live %d' % (total, ring_total),
                  file=sys.stderr)
        print('# ring %d, total %d, flush #%d' % (rsize, total, seq), file=sys.stderr)
    stream.close()


def decode(area, rsize, total):
    ring = area[BLK:BLK + rsize]
    if len(ring) < rsize:
        return ''
    if total <= rsize:
        return ring[:total].decode('latin1')
    start = total % rsize
    return (ring[start:] + ring[:start]).decode('latin1')


if __name__ == '__main__':
    main()