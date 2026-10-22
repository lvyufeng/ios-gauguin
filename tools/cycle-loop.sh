#!/bin/bash
# Run debugging cycles forever-ish without a human in the loop.
#
#   tools/cycle-loop.sh IMAGE [--runs N] [--prefix DIR]
#
# Unlike tools/auto-cycle.sh this one survives the messy cases:
#
#   * the phone is not in TWRP right now -> wait for it (it comes back on its
#     own after most resets; the script polls adb and fastboot forever);
#   * a cycle fails (kernel hang, device off USB) -> wait for the phone again
#     and retry, instead of giving up;
#   * every successful run's log is kept (PREFIX-runN.txt) and a one-line
#     summary is appended to PREFIX/summary.txt, so the loop can be left
#     running while it is analysed from another shell.
#
# It never flashes anything and never touches a partition other than `misc`
# (which is how ABL is told to boot recovery).
set -uo pipefail
img=${1:?usage: cycle-loop.sh IMAGE [--runs N] [--prefix DIR]}
shift
runs=0
prefix=/tmp/cycleloop
while [ $# -gt 0 ]; do
	case "$1" in
	--runs) runs=$2; shift 2 ;;
	--prefix) prefix=$2; shift 2 ;;
	*) echo "unknown argument $1" >&2; exit 2 ;;
	esac
done
[ -f "$img" ] || { echo "no image $img" >&2; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)
export PATH=/opt/homebrew/bin:$PATH
mkdir -p "$prefix"

log() { echo "$(date +%H:%M:%S) $*"; }

# Wait until the phone answers on adb (TWRP) or fastboot. Never gives up: the
# caller may leave this running across a power cycle.
wait_device() {
	local n=0
	while :; do
		if adb devices 2>/dev/null | tail -n +2 | grep -q .; then
			return 0
		fi
		if fastboot devices 2>/dev/null | grep -q fastboot; then
			return 0
		fi
		n=$((n + 1))
		[ $((n % 30)) -eq 0 ] && log "still waiting for the phone (${n}0s)"
		sleep 10
	done
}

# TWRP comes up with adbd a couple of seconds late; wait for recovery proper.
wait_recovery() {
	local n=0
	while [ $n -lt 60 ]; do
		adb devices 2>/dev/null | grep -q recovery && return 0
		sleep 5; n=$((n + 1))
	done
	return 1
}

i=0
while :; do
	i=$((i + 1))
	if [ "$runs" -gt 0 ] && [ "$i" -gt "$runs" ]; then
		log "completed $runs runs"
		break
	fi
	log "run $i: waiting for the phone"
	wait_device

	if adb devices | grep -q recovery; then
		log "run $i: in TWRP"
	elif fastboot devices | grep -q fastboot; then
		# In fastboot: boot TWRP over the wire, then continue normally.
		log "run $i: in fastboot, booting TWRP"
		fastboot boot /tmp/part-recovery.img >/dev/null 2>&1
		wait_recovery || { log "run $i: TWRP did not come up, retrying"; continue; }
	else
		log "run $i: device appeared but not usable, retrying"
		sleep 10
		continue
	fi

	if sh "$here/fastboot-cycle.sh" "$img" "$prefix/run$i.txt" \
			> "$prefix/run$i.log" 2>&1; then
		summary=$(grep -oE "swrst=[0-9a-f]+|swwd=[0-9a-f]+" "$prefix/run$i.txt" |
			tail -2 | tr '\n' ' ')
		lines=$(wc -l < "$prefix/run$i.txt")
		log "run $i ok: $summary lines=$lines"
		echo "$(date +%s) run$i ok $summary lines=$lines" >> "$prefix/summary.txt"
	else
		reason=$(tail -2 "$prefix/run$i.log" | tr '\n' ' ')
		log "run $i failed: $reason"
		echo "$(date +%s) run$i failed $reason" >> "$prefix/summary.txt"
		# The phone may have wedged (kernel hang keeps it off USB). Give it a
		# moment, then the loop goes back to waiting for it.
		sleep 30
	fi
done