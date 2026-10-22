#!/bin/bash
# Repeat the unattended debug cycle: arm misc, boot IMAGE, wait for the reset to
# land in TWRP, pull the log, arm misc again - N times without touching the
# phone. One pass is ~3.5 minutes (2 minutes of userland + recovery).
#
#   tools/auto-cycle.sh IMAGE N [PREFIX]
#
# Stops early if the device never shows up (then a human is needed).
set -uo pipefail
img=${1:?usage: auto-cycle.sh IMAGE N [PREFIX]}
n=${2:-3}
prefix=${3:-/tmp/autoc}
here=$(cd "$(dirname "$0")" && pwd)

for i in $(seq 1 "$n"); do
	echo "=== cycle $i/$n $(date +%H:%M:%S)"
	if ! sh "$here/fastboot-cycle.sh" "$img" "${prefix}-$i.txt" > "${prefix}-$i.log" 2>&1; then
		echo "cycle $i failed; see ${prefix}-$i.log" >&2
		tail -5 "${prefix}-$i.log" >&2
		exit 1
	fi
	grep -oE "swrst=[0-9a-f]+|swwd=[0-9a-f]+" "${prefix}-$i.txt" | tail -2 | tr '\n' ' '
	echo " lines=$(wc -l < "${prefix}-$i.txt")"
	sleep 2
done
echo "=== done $(date +%H:%M:%S)"
