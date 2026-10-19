#!/bin/bash
# Build the SWEET/gauguin XNU kernel on Linux without CI and without a Mac.
#
#   deps/build-local.sh [gauguin|sweet] [--xnu PATH] [--out DIR]
#
# Why not GitHub Actions: every run re-clones apple-oss-distributions xnu,
# dtrace, Libsystem, libdispatch, libplatform, AvailabilityVersions and the
# BearSSL/hfs/libpthread trees (macOS runners keep no state), which is slow
# and breaks entirely where GitHub's codeload/blob hosts are rate limited.
# Here everything is downloaded once into .deps-cache/ and reused.
#
# Two layers:
#   1. cache: the dependency trees, patched source and built headers.
#      Apple's large trees come from the pinned tags in deps/versions.env.
#   2. toolchain: osxcross (cctools-port + ld64 + the Apple SDK), also cached.
#
# The steps mirror blacktop/darwin-xnu-build (dxb) at DXB_SHA: same patches
# and .sh staging, same make invocations. What dxb does with xcodebuild
# (bootstrap_cmds/mig, dtrace) needs host macOS and is flagged:
# osxcross-built host tools are a separate work item (see deps/README.md).
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
MACHINE=${1:-gauguin}
shift || true
OUT=$REPO/xnu/out-$MACHINE
XNU_DIR=
while [ $# -gt 0 ]; do
	case "$1" in
	--out) OUT=$2; shift 2;;
	--xnu) XNU_DIR=$2; shift 2;;
	*) echo "unknown argument $1" >&2; exit 2;;
	esac
done
# shellcheck source=deps/versions.env
. "$REPO/deps/versions.env"
CACHE=$REPO/.deps-cache
SRC=$CACHE/xnu-${XNU_TAG}
LOG=$CACHE/logs
mkdir -p "$CACHE" "$LOG" "$OUT"

say() { printf '\n== %s\n' "$*"; }

# ---------------------------------------------------------------- sources
# fetch(name, url, revision, destination)
#   Reuses destination when it already points at the revision.
fetch() {
	local name=$1 url=$2 rev=$3 dst=$4
	if [ -e "$dst/.git" ] && [ "$(git -C "$dst" rev-parse HEAD 2>/dev/null)" = "$rev" ]; then
		echo "  $name: cached ($(git -C "$dst" rev-parse --short HEAD))"
		return
	fi
	echo "  $name: fetching $rev"
	rm -rf "$dst"
	mkdir -p "$dst"
	git -C "$dst" init -q
	git -C "$dst" remote add origin "$url"
	git -C "$dst" -c protocol.version=2 fetch -q --depth 1 origin "$rev"
	git -C "$dst" checkout -q FETCH_HEAD
	[ "$(git -C "$dst" rev-parse HEAD)" = "$rev" ] || {
		echo "  $name: got $(git -C "$dst" rev-parse HEAD), expected $rev" >&2
		exit 1
	}
}

say "sources (pinned in deps/versions.env)"
fetch xnu "https://github.com/apple-oss-distributions/xnu.git" "$XNU_REV" "$SRC"
for tree in dtrace dtrace-$DTRACE_TAG AvailabilityVersions AvailabilityVersions-$AVV_TAG \
	Libsystem Libsystem-$LIBSYSTEM_TAG libplatform libplatform-$LIBPLATFORM_TAG \
	libdispatch libdispatch-$LIBDISPATCH_TAG; do
	[ -d "$CACHE/$tree/.git" ] && echo "  $tree: cached"
done

say "deps mirror (tiny trees, from the 'blobs' branch)"
MIRROR=$CACHE/mirror
if [ ! -d "$MIRROR/libpthread/kern" ] || [ ! -d "$MIRROR/hfs/core" ] || [ ! -d "$MIRROR/BearSSL/inc" ]; then
	rm -rf "$MIRROR"
	mkdir -p "$MIRROR"
	git -C "$MIRROR" init -q
	git -C "$MIRROR" remote add origin "$REPO_URL"
	git -C "$MIRROR" -c protocol.version=2 fetch -q --depth 1 origin blobs
	git -C "$MIRROR" archive FETCH_HEAD deps/mirror | tar -x -C "$MIRROR" --strip-components=2
else
	echo "  mirror: cached"
fi

# ---------------------------------------------------------------- patches
PATCHED=$CACHE/xnu-patched-$XNU_TAG-$PATCH_SET
if [ ! -e "$PATCHED/.patch-set" ] || [ "$(cat "$PATCHED/.patch-set")" != "$PATCH_SET" ]; then
	say "applying the patch series ($(ls "$REPO"/xnu/patches/*.patch | wc -l) patches)"
	rm -rf "$PATCHED"
	git clone -q "$SRC" "$PATCHED"
	cd "$PATCHED"
	git checkout -q "$XNU_REV"
	export MACHINE_CONFIG=$MACHINE MACOS_VERSION=13.5
	n=0
	for s in "$REPO"/xnu/patches/*.sh; do
		# The two downloads dxb runs here are served by deps/mirror instead.
		case "$(basename "$s")" in
		*stage-*) if grep -q "apple-oss-distributions\|bearssl.org" "$s"; then continue; fi;;
		esac
		bash "$s" > "$LOG/$(basename "$s").log" 2>&1 || {
			echo "  $(basename "$s") failed (see $LOG/$(basename "$s").log)" >&2; exit 1; }
	done
	bash "$REPO"/deps/mirror/xnu/prepare.sh "$PATCHED" "$MIRROR"
	bash "$REPO"/deps/mirror/xnu/prepare-bearssl.sh "$PATCHED" "$MIRROR"
	for p in "$REPO"/xnu/patches/*.patch; do
		if git apply --check "$p" 2> "$LOG/apply-$(basename "$p").err"; then
			git apply "$p"
			n=$((n + 1))
		else
			echo "  FAILED: $(basename "$p") (see $LOG/apply-$(basename "$p").err)" >&2
			exit 1
		fi
	done
	git add -A
	git -c user.email=build@local -c user.name=build commit -qm "sweet/gauguin patch set $PATCH_SET" >/dev/null
	echo "$PATCH_SET" > .patch-set
	echo "  $n patches applied"
	cd "$REPO"
else
	echo "patched tree cached: $PATCHED"
fi

# ---------------------------------------------------------------- build
say "build: MACHINE_CONFIG=$MACHINE (osxcross make, see deps/README.md)"
if [ -z "${OSXCROSS_TARGET_DIR:-}" ]; then
	echo "  OSXCROSS_TARGET_DIR is not set: build the toolchain first (deps/osxcross.sh)." >&2
	echo "  The patched source is ready in $PATCHED." >&2
	exit 3
fi
SRCROOT=${XNU_DIR:-$PATCHED}
(cd "$SRCROOT" && make SDKROOT=macosx TARGET_CONFIGS="DEVELOPMENT ARM64 $MACHINE" \
	BUILD_LTO=0 OBJROOT="$CACHE/obj-$MACHINE" SYMROOT="$CACHE/sym-$MACHINE" \
	DSTROOT="$OUT" install) 2>&1 | tee "$LOG/build-$MACHINE.log"