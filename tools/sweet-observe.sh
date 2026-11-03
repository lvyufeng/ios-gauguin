#!/bin/bash
# Boot an image and watch it for a long time before recovering.
#
#   tools/sweet-observe.sh IMAGE OUT.txt [SECONDS]
#
# tools/fastboot-cycle.sh assumes the kernel dies early: it sleeps 20 s and then
# waits for TWRP. That is right for a kernel that panics during boot, and it is
# exactly wrong for one that reaches userland - SpringBoard needs far longer
# than 20 s, and the cycle's "TWRP showed up" is indistinguishable from "the
# kernel kept running".
#
# This script boots the image and then polls the panel counters over the
# persistent log ring until either
#   * the phone returns to TWRP by itself (the kernel really did stop), or
#   * SECONDS (default 180) elapse.
# The log is pulled at the end either way.
set -uo pipefail
img=${1:?usage: sweet-observe.sh IMAGE OUT.txt [SECONDS]}
out=${2:?usage: sweet-observe.sh IMAGE OUT.txt [SECONDS]}
observe=${3:-180}
here=$(cd "$(dirname "$0")" && pwd)
export PATH=/opt/homebrew/bin:$PATH

say() { printf '== %s\n' "$*"; }

adb devices | grep -q recovery || { echo "phone is not in TWRP" >&2; exit 1; }

# Arm recovery so that whatever happens, the phone comes back to TWRP.
adb shell 'printf "boot-recovery" | dd of=/dev/block/by-name/misc bs=1 seek=0 conv=notrunc 2>/dev/null'
say "misc armed; rebooting to the bootloader"
adb reboot bootloader

for i in $(seq 1 30); do
	fastboot devices | grep -q fastboot && break
	sleep 2
done
fastboot devices | grep -q fastboot || { echo "fastboot did not come up" >&2; exit 1; }

say "booting $img"
fastboot boot "$img"
start=$(date +%s)

# USB drops while the kernel owns the device; do not treat that as failure.
sleep 10
last_seen=""
while :; do
	now=$(date +%s); elapsed=$((now - start))
	if adb devices | grep -q recovery; then
		say "back in TWRP after ${elapsed}s"
		break
	fi
	if [ "$elapsed" -ge "$observe" ]; then
		say "still running after ${elapsed}s (no TWRP) - that is the good case"
		break
	fi
	sleep 5
done

# Pull whatever the ring holds. When the kernel is still running this reads the
# ring as it stands, which is what the panel counters below are taken from.
sh "$here/sweet-log-pull.sh" "$out" >/dev/null 2>&1 || true

echo
say "progress markers"
for pat in "init complete" "BSD root" "mounted iOSRoot" "exec launchd" \
           "ignition sequence complete" "exec SpringBoard" "exec backboardd"; do
	if grep -q "$pat" "$out" 2>/dev/null; then
		printf '  yes  %s\n' "$pat"
	else
		printf '  no   %s\n' "$pat"
	fi
done

echo
say "panel counters (last three)"
grep "SWEET FB: vsync=" "$out" 2>/dev/null | tail -3 | sed 's/^/  /'
say "swaps: $(grep -c 'SWEET FB: swap' "$out" 2>/dev/null)"

echo
say "GPU lookups: $(grep -c 'IOAcceleratorES' "$out" 2>/dev/null)"
say "log lines: $(wc -l < "$out" 2>/dev/null)"