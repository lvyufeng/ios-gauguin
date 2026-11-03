#!/bin/sh
# Read the SWEET mark blocks: the 64 blocks just below the persistent log ring
# at the end of userdata (sweet_log_mark() in bsd/dev/sweet_ufs.c).
#
#   tools/sweet-mark-pull.sh OUT.txt
#
# The ring (tools/sweet-log-pull.sh) is overwritten by userdata output within
# minutes, so anything printed on the init tail has to be read from here - and
# since the init steps write their marks from the caller's own thread
# (sweet_log_mark_sync), the last mark on flash names the step that stalled.
#
# The parsing lives in tools/sweet-marks.py so it can be tested
# (tests/test_marks.py); this script only does the adb read.
set -eu
out=${1:?usage: sweet-mark-pull.sh OUT.txt}
here=$(cd "$(dirname "$0")" && pwd)
dev=$(adb shell 'for d in /dev/block/by-name/userdata /dev/block/bootdevice/by-name/userdata; do [ -e $d ] && readlink -f $d && break; done' | tr -d '\r')
[ -n "$dev" ] || { echo "userdata block device not found" >&2; exit 1; }
bytes=$(adb shell blockdev --getsize64 "$dev" | tr -d '\r')

# The mark area sits immediately below the log ring. Both sizes are defined by
# the driver; read them from its source when the patched tree is staged so the
# offset cannot drift if SWEET_LOG_SIZE or SWEET_MARK_BLOCKS change.
src=$(dirname "$here")/.deps-cache/xnu-patched-0082-2/bsd/dev/sweet_ufs.c
sizes=$(python3 "$here/sweet-marks.py" --sizes "$src")
log_blocks=$(echo "$sizes" | cut -d' ' -f1)
mark_blocks=$(echo "$sizes" | cut -d' ' -f2)

skip=$((bytes / 4096 - log_blocks - mark_blocks))
[ "$skip" -gt 0 ] || { echo "partition too small for a mark area ($bytes bytes)" >&2; exit 1; }
adb exec-out "dd if=$dev bs=4096 skip=$skip count=$mark_blocks 2>/dev/null" > "$out.bin"
echo "$dev: $bytes bytes, read $mark_blocks blocks at $skip" >&2
python3 "$here/sweet-marks.py" "$out.bin" > "$out" || true
cat "$out"