#!/bin/bash
# Build the SWEET/gauguin XNU kernel natively on macOS.
#
#   deps/build-macos.sh [gauguin|sweet] [--out DIR] [--xnu PATH] [--jobs N]
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
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD
MACHINE=${1:-gauguin}
shift || true
OUT=$REPO/xnu/out-$MACHINE-macos
XNU_DIR=
JOBS=$(sysctl -n hw.ncpu)
while [ $# -gt 0 ]; do
	case "$1" in
	--out) OUT=$2; shift 2;;
	--xnu) XNU_DIR=$2; shift 2;;
	--jobs) JOBS=$2; shift 2;;
	*) echo "unknown argument $1" >&2; exit 2;;
	esac
done
# shellcheck source=deps/versions.env
. "$REPO/deps/versions.env"
CACHE=$REPO/.deps-cache
SRC=${XNU_DIR:-$CACHE/xnu-patched-$PATCH_SET}
LOG=$CACHE/logs
SDK=$CACHE/sdkroot-macos
mkdir -p "$LOG" "$OUT"

say() { printf '\n== %s\n' "$*"; }

[ -d "$SRC" ] || { echo "patched source tree missing: $SRC (deps/apply-patches.sh)" >&2; exit 1; }
[ -d /Applications/Xcode.app ] || { echo "Xcode required (iig, xcodebuild)" >&2; exit 1; }
export DEVELOPER_DIR=${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}
export PATH=$DEVELOPER_DIR/usr/bin:$PATH

# ---------------------------------------------------------------- SDK root
if [ ! -x "$SDK/usr/local/libexec/availability.pl" ]; then
	say "preparing $SDK (writable SDK copy + availability.pl)"
	BASE_SDK=$(xcrun --sdk macosx --show-sdk-path)
	AVV=$CACHE/AvailabilityVersions-$AVV_TAG
	[ -f "$AVV/availability.pl" ] || {
		echo "missing $AVV/availability.pl (clone apple-oss-distributions/AvailabilityVersions)" >&2; exit 1; }
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
	(cd "$SRC" && SDKROOT_RESOLVED="$SDK" HOST_SDKROOT_RESOLVED="$SDK" SDKVERSION="$SDKVERSION" PLATFORM=MacOSX \
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

# ---------------------------------------------------------------- kernel
say "build: MACHINE_CONFIG=$MACHINE, $(clang --version | head -1)"
say "source $SRC"
say "sdk    $SDK"
say "out    $OUT"
set +e
(cd "$SRC" && SDKROOT_RESOLVED="$SDK" HOST_SDKROOT_RESOLVED="$SDK" SDKVERSION="$SDKVERSION" PLATFORM=MacOSX \
	make install -j"$JOBS" -k \
	VERBOSE=NO CONCISE=0 \
	BUILD_WERROR=0 BUILD_LTO=0 \
	TARGET_CONFIGS="DEVELOPMENT ARM64 $MACHINE" \
	KDKROOT= \
	RC_DARWIN_KERNEL_VERSION="${RC_DARWIN_KERNEL_VERSION:-23.5.0}" \
	OBJROOT="$CACHE/obj-$MACHINE-macos" \
	SYMROOT="$CACHE/sym-$MACHINE-macos" \
	DSTROOT="$OUT" \
	KERNEL_BUILDS_IN_PARALLEL=1 \
	SYSCTL_HW_PHYSICALCPU="$(sysctl -n hw.physicalcpu)" \
	SYSCTL_HW_LOGICALCPU="$(sysctl -n hw.logicalcpu)" \
	MEMORY_SIZE="$(sysctl -n hw.memsize)") \
	2>&1 | tee "$LOG/build-$MACHINE-macos.log"
rc=${PIPESTATUS[0]}
set -e
echo "  make exit $rc (log $LOG/build-$MACHINE-macos.log)"
# -k: the tail of `make install` installs the lldb python macros, whose syntax
# check shadows the stdlib `collections` module and fails on any python; that
# has nothing to do with the kernel. The kernel binary is the success criterion
# (the same rule the CI uses for dxb), so install it here when make did not.
OBJ_KERNEL=$CACHE/obj-$MACHINE-macos/DEVELOPMENT_ARM64_$(echo "$MACHINE" | tr a-z A-Z)/kernel.development.$MACHINE
if [ ! -f "$OUT/System/Library/Kernels/kernel.development.$MACHINE" ] && [ -f "$OBJ_KERNEL" ]; then
	mkdir -p "$OUT/System/Library/Kernels"
	cp "$OBJ_KERNEL" "$OUT/System/Library/Kernels/kernel.development.$MACHINE"
	echo "  installed $OUT/System/Library/Kernels/kernel.development.$MACHINE (make rc=$rc)"
fi
grep -nE "error:|Error [0-9]|Undefined symbols|No rule" "$LOG/build-$MACHINE-macos.log" | head -20 || true
ls -la "$OUT/System/Library/Kernels" 2>/dev/null || true
if [ -f "$OUT/System/Library/Kernels/kernel.development.$MACHINE" ]; then
	echo "  kernel: $(shasum -a 256 "$OUT/System/Library/Kernels/kernel.development.$MACHINE")"
	exit 0
fi
exit $rc