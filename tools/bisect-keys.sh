#!/bin/bash
# Bisect the gauguin init stall with two prepared images.
#
#   tools/bisect-keys.sh
#
# The phone must already be in TWRP (or fastboot with --boot-now). Root access
# and adb are the only requirements; the script never flashes a partition, it
# only does `fastboot boot` of temporary images and reads the log ring and the
# mark blocks back afterwards.
#
# Why these two images differ by exactly one boot-arg:
#   shim-bisect-on.img   ... sweetkeys=1 (default, the driver runs)
#   shim-bisect-off.img  ... sweetkeys=0 (sweet_keys_init() returns before any
#                            MMIO access at all)
#
# The working boot (boot-journaled-userland.txt) shows the init tail reaching
# `init complete` and `BSD root: ufsroot0`. A failing run stops on the
# `SWEET UFS: keys_init` line. If `-off` gets past `init complete` while `-on`
# does not, the stall is provably in the keys/PMIC path and nowhere else.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/.." && pwd)
out=${1:-$repo/research/tmp/bisect}
mkdir -p "$out"

run_one() {
	local tag=$1 img=$2
	echo "=== $tag : $(basename "$img")"
	sh "$here/fastboot-cycle.sh" "$img" "$out/$tag.log.txt" > "$out/$tag.cycle.txt" 2>&1
	local rc=$?
	grep -E "^== |STALE|no recovery" "$out/$tag.cycle.txt" 2>/dev/null | sed 's/^/    /'
	sh "$here/sweet-mark-pull.sh" "$out/$tag.marks.txt" > "$out/$tag.marks.stdout" 2>&1
	echo "    --- marks ---"
	grep -E "^MARK " "$out/$tag.marks.txt" 2>/dev/null | sed 's/^/    /' || echo "    (none)"
	echo "    --- last console line ---"
	tail -1 "$out/$tag.log.txt" 2>/dev/null | sed 's/^/    /'
	echo "    --- init phase reached ---"
	if grep -q "BSD root: ufsroot0" "$out/$tag.log.txt" 2>/dev/null; then
		echo "    MOUNTED ROOT (vfs_mountroot reached)"
	elif grep -q "init complete" "$out/$tag.log.txt" 2>/dev/null; then
		echo "    init complete, root not mounted yet"
	elif grep -q "keys_init done" "$out/$tag.log.txt" 2>/dev/null; then
		echo "    keys_init done, later step stalled"
	elif grep -q "keys_init" "$out/$tag.log.txt" 2>/dev/null; then
		echo "    STALLED IN keys_init"
	else
		echo "    did not reach keys_init"
	fi
	return $rc
}

echo "bisecting the init stall: $(date)"
run_one off "$repo/shim/out/shim-bisect-off.img"
sleep 3
run_one on  "$repo/shim/out/shim-bisect-on.img"

echo
echo "=== verdict (tools/bisect-verdict.py, tested by tests/test_bisect.py)"
python3 "$here/bisect-verdict.py" "$out/off.log.txt" "$out/on.log.txt"
