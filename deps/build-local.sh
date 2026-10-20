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
#   2. toolchain: osxcross (LLVM flavour: clang + ld64.lld + the Apple SDK).
# The kernel only needs genassym (host clang), the arm64 cross compiler and
# ld; mig/Libsystem/Libsyscall headers are not part of the kernel build.
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
SRC=$CACHE/$XNU_TAG
LOG=$CACHE/logs
mkdir -p "$CACHE" "$LOG" "$OUT"

say() { printf '\n== %s\n' "$*"; }

# ---------------------------------------------------------------- sources
# fetch(name, url, revision, destination)
#   Reuses destination when it already points at the revision.
fetch() {
	local name=$1 url=$2 rev=$3 dst=$4
	if [ -e "$dst/.git" ]; then
		if ! git -C "$dst" cat-file -e "$rev^{commit}" 2>/dev/null; then
			git -C "$dst" -c protocol.version=2 fetch -q --depth 1 origin "$rev" || true
		fi
		if git -C "$dst" cat-file -e "$rev^{commit}" 2>/dev/null; then
			git -C "$dst" checkout -q --detach "$rev"
			echo "  $name: cached ($(git -C "$dst" rev-parse --short HEAD))"
			return
		fi
	fi
	echo "  $name: fetching $rev"
	rm -rf "$dst"
	mkdir -p "$dst"
	git -C "$dst" init -q
	# Fetch into a temporary bare store first: a fetch that dies half way
	# (the link to GitHub drops often) must not destroy a usable checkout.
	git init -q --bare "$dst.git"
	if ! git -C "$dst.git" -c protocol.version=2 fetch -q --depth 1 "$url" "$rev"; then
		echo "  $name: fetch failed (see deps/README.md: resume or copy a cache)" >&2
		exit 1
	fi
	git -C "$dst" fetch -q "$dst.git" "$rev:refs/build/$name"
	git -C "$dst" checkout -q --detach "$rev"
	rm -rf "$dst.git"
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
# $PATCHED/$SRC holds the upstream tag with the whole series applied (see
# deps/README.md for how it is seeded). Re-applying only happens when the
# checkout is clean at the tag again.
PATCHED=$CACHE/$XNU_TAG
if [ -e "$PATCHED/.patch-set" ] && [ "$(cat "$PATCHED/.patch-set")" = "$PATCH_SET" ]; then
	echo "patched tree cached: $PATCHED ($PATCH_SET)"
else
	say "applying the patch series ($(ls "$REPO"/xnu/patches/*.patch | wc -l) patches)"
	WORK=$CACHE/xnu-patched-$PATCH_SET
	rm -rf "$WORK"
	git clone -q "$SRC" "$WORK"
	cd "$WORK"
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
	bash "$REPO"/deps/mirror/xnu/prepare.sh "$WORK" "$MIRROR"
	bash "$REPO"/deps/mirror/xnu/prepare-bearssl.sh "$WORK" "$MIRROR"
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
	PATCHED=$WORK
	cd "$REPO"
fi

# ---------------------------------------------------------------- build
say "build: MACHINE_CONFIG=$MACHINE with osxcross (no Mac, no CI)"
OSX=$REPO/osxcross/osxcross-master/target
if [ ! -x "$OSX/bin/aarch64-apple-darwin20.4-clang" ]; then
	echo "  osxcross toolchain missing in $OSX (see deps/README.md)" >&2
	exit 3
fi
# osxcross tools; their runtime libraries include miniconda's libicu.
export PATH=$REPO/deps/toolchain/hostbin:$REPO/osxcross/bin2:$REPO/osxcross/llvmbin:/usr/lib/llvm-17/bin:$OSX/bin:$PATH
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}/home/lvyufeng/miniconda3/lib
# xnu's header generators look for DSTROOT/usr/local/libexec/availability.pl
# (dxb installs it with AvailabilityVersions): keep it beside the SDK and
# prepend it to the SDK root.
SDKROOT=$OSX/SDK/MacOSX11.3.sdk
DT=$REPO/osxcross/darwin-tools
mkdir -p "$DT/usr/local/libexec"
[ -f "$DT/usr/local/libexec/availability.pl" ] || \
	cp "$REPO/osxcross/dev/AvailabilityVersions/availability.pl" "$DT/usr/local/libexec/" 2>/dev/null || true
# make_symbol_aliasing.sh takes one SDK path; the scripts only resolve
# $SDKROOT/usr/local/libexec/availability.pl, so mirror the SDK into a
# combined root with that file added.
COMBINED=$REPO/.deps-cache/sdkroot
if [ ! -e "$COMBINED/usr/local/libexec/availability.pl" ]; then
	mkdir -p "$COMBINED"
	for e in "$OSX/SDK/MacOSX11.3.sdk"/*; do
		ln -sfn "$e" "$COMBINED/$(basename "$e")"
	done
	mkdir -p "$COMBINED/usr/local/libexec"
	cp "$DT/usr/local/libexec/availability.pl" "$COMBINED/usr/local/libexec/"
fi
export SDKROOT=$COMBINED
TC=aarch64-apple-darwin20.4
export CC=$OSX/bin/$TC-clang CXX=$OSX/bin/$TC-clang++ LD=$OSX/bin/$TC-ld
export LIPO=$OSX/bin/$TC-lipo NM=$OSX/bin/$TC-nm OTOOL=$OSX/bin/$TC-otool
export STRIP=$OSX/bin/$TC-strip AR=$OSX/bin/$TC-ar RANLIB=$OSX/bin/$TC-ranlib
export LIBTOOL=$OSX/bin/$TC-libtool
# host programs built by the kernel make (genassym): host clang
# Host tools for the build machine (xnu SETUP: config, installfile, ...):
# a wrapper adding the Darwin libc pieces glibc lacks (deps/toolchain).
export HOST_CC=$REPO/deps/toolchain/host-cc HOST_CXX=clang++ HOST_SDKROOT=$SDKROOT
# MakeInc.cmd resolves SDKROOT through xcrun unless these are set, and the
# recipes (bsd/sys/make_symbol_aliasing.sh) receive SDKROOT on the make line.
export SDKROOT_RESOLVED=$COMBINED HOST_SDKROOT_RESOLVED=$COMBINED
# bsd/sys/Makefile passes $(SDKROOT) on the recipe line: export it too
SDKROOT=$COMBINED
export HOST_FLEX=/usr/bin/flex HOST_BISON=/usr/bin/bison HOST_GM4=/usr/bin/m4
# xnu runs `codesign` after linking host tools; on Linux nothing to sign.
export HOST_CODESIGN=/bin/true HOST_CODESIGN_ALLOCATE=/bin/true
# xnu's Makefile asks the host for its CPU/RAM through sysctl and
# /usr/sbin/sysctl (absent on Linux); the overrides are read by MakeInc.top.
export SYSCTL_HW_PHYSICALCPU=$(nproc) SYSCTL_HW_LOGICALCPU=$(nproc)
export MEMORY_SIZE_OVERRIDE=$(( $(sed -n 's/^MemTotal:[[:space:]]*\([0-9]*\).*/\1/p' /proc/meminfo) * 1024 ))
export KERNEL_BUILDS_IN_PARALLEL=1
# mig/iig are only used to install libsyscall headers (not the kernel)
# installfile (SETUP) is rebuilt for Linux: the Darwin one uses fcopyfile
# with setattrlist semantics glibc does not provide (deps/toolchain/compat).
"$REPO/deps/toolchain/compat/build.sh" > /dev/null
export MIG=$REPO/deps/toolchain/mig/mig
# migcom (libsyscall) and iig (DriverKit) only install those frameworks'
# headers; the kernel does not use them. The stand-ins emit placeholders.
export MIGCOM= IIG=$REPO/deps/toolchain/mig/iig
SRCROOT=${XNU_DIR:-$PATCHED}
export SRCROOT OBJROOT="$CACHE/obj-$MACHINE" SYMROOT="$CACHE/sym-$MACHINE" DSTROOT="$OUT"
export RC_DARWIN_KERNEL_VERSION=${RC_DARWIN_KERNEL_VERSION:-23.5.0} RC_ProjectName=${RC_ProjectName:-xnu}
mkdir -p "$OUT"
# newvers.pl runs from the object directory and needs the stages' variables
# from the environment (xnu's Make invocations re-export them per sub-make).
cat > "$REPO/deps/toolchain/make-env.sh" <<ENVEOF
export SRCROOT="$SRCROOT" OBJROOT="$OBJROOT" SYMROOT="$SYMROOT" DSTROOT="$DSTROOT"
export SDKROOT="$SDKROOT" KDKROOT="" RC_DARWIN_KERNEL_VERSION="${RC_DARWIN_KERNEL_VERSION:-23.5.0}"
export CURRENT_KERNEL_CONFIG=DEVELOPMENT CURRENT_ARCH_CONFIG=ARM64 CURRENT_MACHINE_CONFIG=$MACHINE
export CURRENT_KERNEL_CONFIG_LC=$(echo DEVELOPMENT | tr A-Z a-z) CURRENT_ARCH_CONFIG_LC=$(echo ARM64 | tr A-Z a-z)
export CURRENT_MACHINE_CONFIG_LC=$(echo "$MACHINE" | tr A-Z a-z)
export BUILD_CONFIG=$MACHINE ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG=arm64
ENVEOF
# Some rules call SETUP programs by their source-tree path ($(SRCROOT)/SETUP/
# config/doconf); on a Mac dxb's installhdrs puts them there. Link the built
# ones next to the sources when the checkout is writable.
SE=$OBJROOT/SETUP
for t in installfile/installfile decomment/decomment \
	replacecontents/replacecontents setsegname/setsegname kextsymboltool/kextsymboltool; do
	[ -x "$SE/$t" ] && [ -d "$(dirname "$SRCROOT/SETUP/$t")" ] && \
		ln -sf "$SE/$t" "$SRCROOT/SETUP/$t"
done
# iokit/conf runs $SRCROOT/SETUP/config/doconf (a csh script needing a
# compiled `config`): use the Python port + stand-ins in deps/toolchain/mig
# (the patched checkout is ours, so replacing it is safe).
if ! head -1 "$SRCROOT/SETUP/config/doconf" | grep -q "python3"; then
	cp "$REPO/deps/toolchain/mig/doconf" "$SRCROOT/SETUP/config/doconf"
fi
chmod +x "$SRCROOT/SETUP/config/doconf"
set +e
(cd "$SRCROOT" && . "$REPO/deps/toolchain/make-env.sh" && make -j"$(nproc)" VERBOSE=YES CONCISE=0 BUILD_WERROR=0 BUILD_LTO=0 \
	SDKROOT="$SDKROOT" RC_DARWIN_KERNEL_VERSION=${RC_DARWIN_KERNEL_VERSION:-23.5.0} \
	SYSCTL_HW_PHYSICALCPU="$(nproc)" SYSCTL_HW_LOGICALCPU="$(nproc)" \
	MEMORY_SIZE="$MEMORY_SIZE_OVERRIDE" KERNEL_BUILDS_IN_PARALLEL=1 \
	TARGET_CONFIGS="DEVELOPMENT ARM64 $MACHINE" \
	OBJROOT="$CACHE/obj-$MACHINE" SYMROOT="$CACHE/sym-$MACHINE" DSTROOT="$OUT" install) \
	2>&1 | tee "$LOG/build-$MACHINE.log"
rc=${PIPESTATUS[0]}
set -e
echo "  make exit $rc (log $LOG/build-$MACHINE.log)"
grep -n -E "error:|Error [0-9]|No rule|not found" "$LOG/build-$MACHINE.log" | head -20 || true
ls -la "$OUT" || true
exit $rc
