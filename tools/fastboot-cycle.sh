#!/bin/bash
# One debugging cycle without touching the phone.
#
#   tools/fastboot-cycle.sh IMAGE OUT.txt [--boot-now]
#
# The kernel under test dies early and the bootloader then boots UEFI on the
# boot partition, which needs a human. `boot-recovery` in the misc partition
# makes ABL boot the recovery partition (TWRP) instead, and TWRP has adb, so
# the whole cycle runs unattended:
#
#   TWRP: arm misc -> reboot bootloader -> fastboot boot IMAGE
#   kernel runs, dies; ABL reads misc and boots recovery
#   TWRP: pull the SWEET persistent log (tools/sweet-log-pull.sh) -> ready
#
# Run it with the phone already in TWRP (or in fastboot with --boot-now).
set -euo pipefail
img=${1:?usage: fastboot-cycle.sh IMAGE OUT.txt [--boot-now]}
out=${2:?usage: fastboot-cycle.sh IMAGE OUT.txt [--boot-now]}
here=$(cd "$(dirname "$0")" && pwd)
export PATH=/opt/homebrew/bin:$PATH

adb_wait() {  # wait until adb sees a device, up to $1 seconds (also TWRP's adbd)
	local limit=$1 i=0
	while [ $i -lt "$limit" ]; do
		if adb devices | tail -n +2 | grep -q .; then return 0; fi
		sleep 2; i=$((i + 2))
	done
	return 1
}

fastboot_wait() {
	local limit=$1 i=0
	while [ $i -lt "$limit" ]; do
		if fastboot devices | grep -q fastboot; then return 0; fi
		sleep 2; i=$((i + 2))
	done
	return 1
}

arm_recovery() {
	# bootloader_message.command: ABL boots the recovery partition next time.
	adb shell 'printf "boot-recovery" | dd of=/dev/block/by-name/misc bs=1 seek=0 conv=notrunc 2>/dev/null'
	adb shell 'dd if=/dev/block/by-name/misc bs=1 count=13 2>/dev/null'
	echo
}

if ! adb devices | grep -q recovery; then
	[ "${3:-}" = "--boot-now" ] || { echo "phone is not in TWRP" >&2; exit 1; }
	fastboot_wait 30 || { echo "phone is not in fastboot either" >&2; exit 1; }
else
	arm_recovery
	adb reboot bootloader
	fastboot_wait 60 || { echo "fastboot did not come up" >&2; exit 1; }
fi

echo "== booting $img"
fastboot boot "$img"
start=$(date +%s)

# The device drops off USB while the kernel runs, then ABL boots recovery.
sleep 20
if ! adb_wait 150; then
	echo "no recovery after $(( $(date +%s) - start ))s: is misc armed?" >&2
	exit 1
fi
echo "== TWRP after $(( $(date +%s) - start ))s"

sh "$here/sweet-log-pull.sh" "$out" 2>&1 | tail -2

# Refuse to present a log from an older kernel: the ring keeps the previous boot
# when this one died before logging started (NOTES 23:50).
python3 - "$img" "$out" <<'PYCHK'
import sys
img, log = sys.argv[1], sys.argv[2]
d = open(img, 'rb').read()
i = d.find(b'Darwin Kernel Version')
want = d[i + 22:i + 75] if i >= 0 else b''
try:
    got = open(log, 'rb').readline()[22:75]
except OSError:
    got = b''
if want and got != want:
    print('STALE LOG: image kernel is %r but the log is %r'
          % (want.decode('utf8', 'replace'), got.decode('utf8', 'replace')),
          file=sys.stderr)
    sys.exit(3)
PYCHK
rc=$?
[ "$rc" = 3 ] && exit 3
tail -25 "$out"

# Leave misc armed for the next cycle: the phone may be sitting in UEFI by now
# (TWRP runs "boot-recovery" a few seconds after start, which clears that
# string), and an unarmed misc would send the next reset to UEFI instead.
if [ "${ARM_AFTER:-1}" = 1 ] && adb devices | grep -q recovery; then
	arm_recovery > /dev/null 2>&1 && echo "== misc re-armed for the next cycle"
fi