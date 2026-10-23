#!/bin/sh
# Read the SWEET console log (kernel patch 0047) from a phone booted into
# OrangeFox recovery (fastboot boot recovery/recovery.img; adb root shell).
#   tools/sweet-log-pull.sh OUT.txt
# Only reads: the last 1025 blocks (4 KiB) of the userdata partition.
set -eu
out=${1:?usage: sweet-log-pull.sh OUT.txt}
dev=$(adb shell 'for d in /dev/block/by-name/userdata /dev/block/bootdevice/by-name/userdata; do [ -e $d ] && readlink -f $d && break; done' | tr -d '\r')
[ -n "$dev" ] || { echo "userdata block device not found" >&2; exit 1; }
bytes=$(adb shell blockdev --getsize64 "$dev" | tr -d '\r')
skip=$((bytes / 4096 - 1025))
adb exec-out "dd if=$dev bs=4096 skip=$skip count=1025 2>/dev/null" > "$out.bin"
echo "$dev: $bytes bytes, read blocks $skip.. ($(stat -f %z "$out.bin") bytes)" >&2
python3 "$(dirname "$0")/sweet-log.py" "$out.bin" "$out"

# A boot that dies before sweet_log_start() leaves the PREVIOUS boot in the ring,
# and the puller then returns an old log that looks perfectly healthy. Print the
# banner so it can be compared with the image's own banner (NOTES 23:50).
banner=$(head -1 "$out" 2> /dev/null | cut -c1-80)
echo "boot banner: $banner" >&2
case "$banner" in
	Darwin\ Kernel\ Version*|*Kernel\ Version*) ;;
	*) echo "WARNING: no kernel banner - this is not a fresh boot log" >&2 ;;
esac
