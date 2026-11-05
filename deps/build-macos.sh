#!/bin/bash
# Build the SWEET/gauguin XNU kernel natively on macOS.
#
#   deps/build-macos.sh [gauguin|sweet] [--out DIR] [--xnu PATH] [--jobs N]
#                       [--build-root DIR]
# --build-root isolates SDK, dependencies, objects, symbols, logs and installation.
# Its default source is DIR/xnu-patched-$PATCH_SET; pass --xnu for another staged tree.
#
# The Linux path (deps/build-local.sh) needs osxcross; on a Mac the same
# `make install` runs with Xcode's clang, ld and mig. What is still prepared
# here is the part of blacktop/darwin-xnu-build the kernel needs:
#
#   .deps-cache/sdkroot-macos   writable copy of the macOS SDK, plus
#                               usr/local/libexec/availability.pl (from
#                               AvailabilityVersions) that the SDK omits,
#                               libplatform's usr/local/include, the xnu
#                               headers (installhdrs) and libfirehose_kernel.a
#                               (libdispatch, KERNEL=1)
#   .deps-cache/xnu-patched-*   upstream checkout with xnu/patches applied
#   xnu/out-<machine>-macos     the kernel(s)
#
# KDKROOT is empty on purpose: the SWEET series stubs the closed KDK libs
# (0007/0008), so nothing links against Apple's kernel support libraries.
#
# For the A/B variant of the keys barrier (NOTES 2026-11-03 (25)) XNU's build
# has no "extra CFLAGS" variable that reaches bsd/dev, so the switch is done by
# editing the #ifdef in sweet_keys.c; deps/ab-keys-barrier.sh does that and
# restores it.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
MACHINE=${1:-gauguin}
shift || true
OUT=
XNU_DIR=
BUILD_ROOT=
JOBS=$(sysctl -n hw.ncpu)
while [ $# -gt 0 ]; do
	case "$1" in
	--out) OUT=$2; shift 2;;
	--xnu) XNU_DIR=$2; shift 2;;
		--build-root) BUILD_ROOT=$2; shift 2;;
	--jobs) JOBS=$2; shift 2;;
	*) echo "unknown argument $1" >&2; exit 2;;
	esac
done
# shellcheck source=deps/versions.env
. "$REPO/deps/versions.env"
case "$MACHINE" in gauguin|sweet) ;; *) echo "unsupported machine: $MACHINE" >&2; exit 2;; esac
CACHE=${BUILD_ROOT:-$REPO/.deps-cache}
CACHE=$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$CACHE")
if [ -z "$OUT" ]; then
	if [ -n "$BUILD_ROOT" ]; then OUT=$CACHE/out-$MACHINE-macos; else OUT=$REPO/xnu/out-$MACHINE-macos; fi
fi
OUT=$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$OUT")
SRC=${XNU_DIR:-$CACHE/xnu-patched-$PATCH_SET}
SRC=$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$SRC")
LOG=$CACHE/logs
SDK=$CACHE/sdkroot-macos
mkdir -p "$LOG" "$CACHE/runs"
RUN=$(mktemp -d "$CACHE/runs/$MACHINE.XXXXXX")
STAGING=$RUN/install
mkdir "$STAGING"
MANIFEST=$RUN/build-manifest.json

say() { printf '\n== %s\n' "$*"; }

[ -d "$SRC" ] || { echo "patched source tree missing: $SRC (deps/apply-patches.sh)" >&2; exit 1; }
python3 "$REPO/tools/xnu-source-state.py" check "$SRC" --state-root "$CACHE/source-state"
export DEVELOPER_DIR=${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}
[ -d "$DEVELOPER_DIR" ] || { echo "Xcode required: $DEVELOPER_DIR" >&2; exit 1; }
export PATH=$DEVELOPER_DIR/usr/bin:$PATH

# ---------------------------------------------------------------- SDK root
# installhdrs replaces libc-facing headers in the kernel SDK. SETUP executables
# run on the host and must always use Xcode's unmodified SDK, including retries.
BASE_SDK=$(xcrun --sdk macosx --show-sdk-path)
HOST_SDK=$BASE_SDK
[ -d "$HOST_SDK" ] || { echo "host SDK missing: $HOST_SDK" >&2; exit 1; }
if [ ! -x "$SDK/usr/local/libexec/availability.pl" ]; then
	say "preparing $SDK (writable SDK copy + availability.pl)"
	AVV=$CACHE/AvailabilityVersions-$AVV_TAG
	[ -f "$AVV/availability.pl" ] || git clone -q --depth 1 --branch "$AVV_TAG" \
		https://github.com/apple-oss-distributions/AvailabilityVersions.git "$AVV"
	rm -rf "$SDK"
	mkdir -p "$SDK"
	rsync -a "$BASE_SDK"/ "$SDK"/
	chmod -R u+w "$SDK"
	mkdir -p "$SDK/usr/local/libexec"
	cp "$AVV/availability.pl" "$SDK/usr/local/libexec/"
	chmod +x "$SDK/usr/local/libexec/availability.pl"
fi
export SDKVERSION=${SDKVERSION:-$(xcrun --sdk macosx --show-sdk-version)}
export PLATFORM=MacOSX

# ---------------------------------------------------------------- libplatform
if [ ! -f "$SDK/usr/local/include/_simple.h" ]; then
	say "staging libplatform headers"
	[ -d "$CACHE/libplatform" ] || git clone -q --depth 1 --branch "$LIBPLATFORM_TAG" \
		https://github.com/apple-oss-distributions/libplatform.git "$CACHE/libplatform"
	mkdir -p "$SDK/usr/local/include"
	ditto "$CACHE/libplatform/include" "$SDK/usr/local/include"
	ditto "$CACHE/libplatform/private" "$SDK/usr/local/include"
fi

# ---------------------------------------------------------------- xnu headers
# libfirehose_kernel builds against Kernel.framework/PrivateHeaders and
# usr/local/include/{os,firehose}; this is dxb's xnu_headers step.
if [ ! -f "$SDK/System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders/os/atomic_private.h" ]; then
	say "installing xnu headers (installhdrs)"
	(cd "$SRC" && SDKROOT_RESOLVED="$SDK" HOST_SDKROOT_RESOLVED="$HOST_SDK" SDKVERSION="$SDKVERSION" PLATFORM=MacOSX \
		make installhdrs -j"$JOBS" ARCH_CONFIGS="ARM64" TARGET_CONFIGS="DEVELOPMENT ARM64 $MACHINE" \
		OBJROOT="$CACHE/obj-hdrs" SYMROOT="$CACHE/sym-hdrs" DSTROOT="$SDK" KDKROOT= BUILD_WERROR=0) \
		> "$LOG/installhdrs.log" 2>&1 || { tail -20 "$LOG/installhdrs.log" >&2; exit 1; }
fi

# ---------------------------------------------------------------- firehose
if [ ! -f "$SDK/usr/local/lib/kernel/libfirehose_kernel.a" ]; then
	say "building libfirehose_kernel (libdispatch, KERNEL=1)"
	[ -d "$CACHE/libdispatch" ] || git clone -q --depth 1 --branch "$LIBDISPATCH_TAG" \
		https://github.com/apple-oss-distributions/libdispatch.git "$CACHE/libdispatch"
	# the project resolves its kernel headers through $(SDKROOT); point them at
	# our SDK copy instead of Xcode's (dxb patches the same two lines)
	sed -i '' 's|\$(SDKROOT)|'"$SDK"'|g' "$CACHE/libdispatch/xcodeconfig/libfirehose_kernel.xcconfig"
	(cd "$CACHE/libdispatch" && xcodebuild install -target libfirehose_kernel -sdk macosx \
		ARCHS=arm64 VALID_ARCHS=arm64 \
		OBJROOT="$CACHE/obj-firehose" SYMROOT="$CACHE/sym-firehose" DSTROOT="$SDK") \
		> "$LOG/firehose.log" 2>&1 || { tail -20 "$LOG/firehose.log" >&2; exit 1; }
	mv "$SDK/usr/local/lib/kernel/liblibfirehose_kernel.a" "$SDK/usr/local/lib/kernel/libfirehose_kernel.a"
fi

# ---------------------------------------------------------------- fix-ups
# Same fix-ups the CI applies to dxb's tree after the patch series: the
# sweet_sample.c guard, the SWEET|GAUGUIN gates, the SDK's usr/include on the
# kernel include path and MASTER.arm64.gauguin (nos_arm_asm/nos_arm_pmap). The
# patch series leaves them to this script so the patch context does not rot.
say "post-patch fix-ups"
python3 "$REPO/tools/xnu-post-patch.py" "$SRC"

# The header that sweet_ufs.c includes is a project file, not part of any
# patch, so the staged tree needs a copy before every build.
"$REPO/deps/sync-watchdog.sh" "$SRC"

# Host tests for the diagnostic tools (watchdog decision, bisection verdict,
# mark parser). They are cheap and they have already caught nine defects; a
# build that ships a broken one would mislead the next boot. Skip with SKIP_TESTS=1.
if [ "${SKIP_TESTS:-0}" != 1 ]; then
	say "host tests"
	if ! XNU_SOURCE="$SRC" bash "$REPO/tests/run-all.sh" > "$LOG/host-tests.log" 2>&1; then
		cat "$LOG/host-tests.log" >&2
		echo "host tests failed (SKIP_TESTS=1 to build anyway)" >&2
		exit 1
	fi
	grep -E "^(all|.* checks? passed)" "$LOG/host-tests.log"
fi

# ---------------------------------------------------------------- kernel
say "build: MACHINE_CONFIG=$MACHINE, $(clang --version | head -1)"
say "source $SRC"
say "sdk    $SDK"
say "host sdk $HOST_SDK"
say "out    $OUT"
export RC_DARWIN_KERNEL_VERSION=${RC_DARWIN_KERNEL_VERSION:-23.5.0}
INPUTS=(--input "versions=$REPO/deps/versions.env" --input "patches=$REPO/xnu/patches"
	--input "mirror=$REPO/deps/mirror" --input "build-script=$REPO/deps/build-macos.sh"
	--input "post-patch=$REPO/tools/xnu-post-patch.py" --input "watchdog=$REPO/xnu/sweet_init_watchdog.h"
	--input "provenance-tool=$REPO/tools/xnu-build-manifest.py" --input "staging-state=$CACHE/source-state")
for dependency in "AvailabilityVersions-$AVV_TAG" libplatform libdispatch; do
	[ ! -d "$CACHE/$dependency" ] || INPUTS+=(--input "$dependency=$CACHE/$dependency")
done
python3 "$REPO/tools/xnu-build-manifest.py" capture --source "$SRC" --sdk "$SDK" --host-sdk "$HOST_SDK" \
	--build-root "$CACHE" --staging "$STAGING" --output "$MANIFEST" --machine "$MACHINE" "${INPUTS[@]}"
set +e
(cd "$SRC" && SDKROOT_RESOLVED="$SDK" HOST_SDKROOT_RESOLVED="$HOST_SDK" SDKVERSION="$SDKVERSION" PLATFORM=MacOSX \
	make install -j"$JOBS" -k \
	VERBOSE=NO CONCISE=0 \
	BUILD_WERROR=0 BUILD_LTO=0 \
	TARGET_CONFIGS="DEVELOPMENT ARM64 $MACHINE" \
	KDKROOT= \
	RC_DARWIN_KERNEL_VERSION="${RC_DARWIN_KERNEL_VERSION:-23.5.0}" \
	OBJROOT="$CACHE/obj-$MACHINE-macos" \
	SYMROOT="$CACHE/sym-$MACHINE-macos" \
		DSTROOT="$STAGING" \
	KERNEL_BUILDS_IN_PARALLEL=1 \
	SYSCTL_HW_PHYSICALCPU="$(sysctl -n hw.physicalcpu)" \
	SYSCTL_HW_LOGICALCPU="$(sysctl -n hw.logicalcpu)" \
	MEMORY_SIZE="$(sysctl -n hw.memsize)") \
	2>&1 | tee "$LOG/build-$MACHINE-macos.log"
rc=${PIPESTATUS[0]}
set -e
echo "  make exit $rc (log $LOG/build-$MACHINE-macos.log)"
cp "$LOG/build-$MACHINE-macos.log" "$RUN/build.log"
grep -nE "error:|Error [0-9]|Undefined symbols|No rule" "$LOG/build-$MACHINE-macos.log" | head -20 || true
python3 "$REPO/tools/xnu-build-manifest.py" finish --manifest "$MANIFEST" --make-exit "$rc" \
	--kernel "$STAGING/System/Library/Kernels/kernel.development.$MACHINE"
# Publish only after this invocation's build and ARM64 image validation succeed.
mkdir -p "$OUT"
cp -R "$STAGING/." "$OUT/"
cp "$MANIFEST" "$OUT/build-manifest.json"
echo "  build manifest: $MANIFEST"
