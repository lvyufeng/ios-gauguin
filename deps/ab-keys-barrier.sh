#!/bin/bash
# Build the two variants of the keys barrier for an A/B run.
#
#   deps/ab-keys-barrier.sh
#
# keys_read() in bsd/dev/sweet_keys.c issues EXT_READL and then needs an
# ordering barrier before it polls the status register. The tree uses DMB;
# the older sweet_spmi.c uses DSB. Nothing in the logs settles which one this
# SoC needs (NOTES 2026-11-03 (25)), so the cheap way to find out is to boot
# both and compare.
#
# XNU's build has no "extra CFLAGS" variable that reaches bsd/dev, so this
# flips the #ifdef in the source, builds, and restores the file even on
# failure.
#
# Outputs (leaving the normal images untouched):
#   shim/out/shim-ab-dmb.img
#   shim/out/shim-ab-dsb.img
set -uo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
SRC=.deps-cache/xnu-patched-0082-2/bsd/dev/sweet_keys.c
KERNEL=xnu/out-gauguin-macos/System/Library/Kernels/kernel.development.gauguin
CMD='debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 ufsrw=1 rootrw=1 launchd_unsecure_cache=1 sweetlog=1 sweetlogms=200 sweetfb_noconsole=1'

[ -f "$SRC" ] || { echo "missing $SRC (run deps/build-macos.sh once)" >&2; exit 1; }
cp "$SRC" "$SRC.ab-backup"
restore() { [ -f "$SRC.ab-backup" ] && mv "$SRC.ab-backup" "$SRC"; }
trap restore EXIT INT TERM

build_one() {
	local tag=$1 want=$2
	# want=dmb -> comment out the #define line; want=dsb -> define it
	if [ "$want" = dsb ]; then
		sed -i '' 's|^#ifdef SWEET_KEYS_USE_DSB|#define SWEET_KEYS_USE_DSB 1\n#ifdef SWEET_KEYS_USE_DSB|' "$SRC"
	else
		sed -i '' '/^#define SWEET_KEYS_USE_DSB 1$/d' "$SRC"
	fi
	if ! grep -q "dsb osh" "$SRC"; then
		echo "  source no longer contains the DSB variant - aborting" >&2
		return 1
	fi
	echo "== building $tag"
	# SKIP_TESTS=1: tests/test_ab_variants.py compares the two A/B kernels, so
	# it can only pass once BOTH exist. The script checks the pair at the end
	# instead (and fails if they are byte-identical).
	if ! SKIP_TESTS=1 bash deps/build-macos.sh gauguin > "research/tmp/ab-$tag.log" 2>&1; then
		echo "  build failed, see research/tmp/ab-$tag.log" >&2
		return 1
	fi
	cp "$KERNEL" "research/k-ab-$tag"
	python3 tools/mkpayload.py "$KERNEL" shim/out/sweet-gauguin-new.adt \
		"shim/out/payload-ab-$tag.bin" --cmdline "$CMD" > /dev/null || return 1
	bash deps/shim-macos.sh "shim/out/payload-ab-$tag.bin" > /dev/null 2>&1 || return 1
	cp shim/out/shim-boot.img "shim/out/shim-ab-$tag.img"
	echo "  shim/out/shim-ab-$tag.img  $(shasum -a 256 "shim/out/shim-ab-$tag.img" | cut -c1-16)"
}

build_one dmb dmb || exit 1
build_one dsb dsb || exit 1

echo
echo "the two kernels differ only in the barrier before the status poll:"
for t in dmb dsb; do
	printf '  %-4s ' "$t"
	shasum -a 256 "research/k-ab-$t" 2>/dev/null | cut -c1-16
done
if cmp -s research/k-ab-dmb research/k-ab-dsb; then
	echo "  WARNING: the two kernels are identical - the switch did not take effect"
	exit 1
fi
echo "run tools/bisect-keys.sh-style cycle on each and compare where they stop."