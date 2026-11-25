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
# This script boots the image and polls USB recovery availability until either
#   * the phone returns to TWRP by itself (the kernel really did stop), or
#   * SECONDS (default 180) elapse.
# It then attempts to pull the log. With XNU owning USB, recovery adb is absent;
# manual recovery is needed before a fresh log can be read. No recovery alone
# does not prove that the kernel is still making progress.
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
		say "no recovery detected after ${elapsed}s; screen and log confirmation needed"
		break
	fi
	sleep 5
done

# Pull the ring if recovery adb is available. If it is not, fail explicitly and
# retain the need for manual recovery; never substitute an earlier log.
#
# The pull used to end in `|| true`, so a failed pull left OUT holding the
# *previous* boot's log and every counter below was then computed from it -
# silently. Stale output is worse than none: it makes a run look like it
# produced evidence it did not. Remove OUT first, and fail loudly if it did
# not come back.
rm -f "$out"
if ! sh "$here/sweet-log-pull.sh" "$out" >/dev/null 2>&1; then
	echo "sweet-observe: log pull failed; OUT removed so a stale log cannot" >&2
	echo "  be mistaken for this run's output" >&2
	exit 4
fi
if [ ! -s "$out" ]; then
	echo "sweet-observe: pull produced an empty log" >&2
	exit 4
fi

# The banner must belong to the kernel inside IMAGE. Entry (68) found
# shim-proven.img carrying a kernel 40 minutes older than the tree, so a log
# that looks fine can still be from the wrong build.
if ! python3 "$here/kernel_banner.py" "$img" "$out"; then
	say "BANNER MISMATCH - missing, ambiguous or stale build identity"
	exit 3
fi
say "banner matches the image"

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
