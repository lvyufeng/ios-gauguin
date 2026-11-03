#!/bin/sh
# Read the SWEET mark blocks: the 64 blocks just below the persistent log ring
# at the end of userdata (sweet_log_mark() in bsd/dev/sweet_ufs.c).
#
#   tools/sweet-mark-pull.sh OUT.txt
#
# The ring (tools/sweet-log-pull.sh) is overwritten by userland output within
# minutes, so anything printed on the init tail has to be read from here.
set -eu
out=${1:?usage: sweet-mark-pull.sh OUT.txt}
dev=$(adb shell 'for d in /dev/block/by-name/userdata /dev/block/bootdevice/by-name/userdata; do [ -e $d ] && readlink -f $d && break; done' | tr -d '\r')
[ -n "$dev" ] || { echo "userdata block device not found" >&2; exit 1; }
bytes=$(adb shell blockdev --getsize64 "$dev" | tr -d '\r')
# ring = 1 header + 1024 blocks; marks = the 64 blocks before the ring.
skip=$((bytes / 4096 - 1025 - 64))
adb exec-out "dd if=$dev bs=4096 skip=$skip count=64 2>/dev/null" > "$out.bin"
echo "$dev: $bytes bytes, read blocks $skip.. (64 blocks)" >&2
: > "$out"
python3 - "$out.bin" >> "$out" <<'PY'
import sys
d = open(sys.argv[1], 'rb').read()
seen = []
for n in range(len(d) // 4096):
    blk = d[n * 4096:(n + 1) * 4096]
    if not blk.startswith(b'MARK '):
        continue
    line = blk.split(b'\n')[0].decode('utf8', 'replace')
    seq = line.split(' ')[1]
    seen.append((int(seq), line))
for seq, line in sorted(seen):
    print(line)
if not seen:
    print('(no MARK blocks: the kernel did not reach sweet_log_mark)')
PY
cat "$out"