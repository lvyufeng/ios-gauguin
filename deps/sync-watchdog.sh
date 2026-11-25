#!/bin/bash
# Keep the build tree's copy of sweet_init_watchdog.h identical to the repo's.
#
#   deps/sync-watchdog.sh [XNU_ROOT]
#
# The patched XNU tree lives in .deps-cache/ (git-ignored) and is rebuilt from
# xnu/patches + deps/mirror; the header is a project file, not part of any
# patch, so it has to be copied in before a kernel build. tools/ and the host
# tests read the repo copy directly.
set -euo pipefail
XNU_SOURCE=${1:-${XNU_SOURCE:-}}
if [ -n "$XNU_SOURCE" ]; then
	XNU_SOURCE=$(cd "$XNU_SOURCE" && pwd)
fi
cd "$(dirname "$0")/.."
SRC=xnu/sweet_init_watchdog.h
XNU_SOURCE=${XNU_SOURCE:-$PWD/.deps-cache/xnu-patched-0082-2}
DST=$XNU_SOURCE/bsd/dev/sweet_init_watchdog.h
[ -f "$SRC" ] || { echo "missing $SRC" >&2; exit 1; }
[ -d "$(dirname "$DST")" ] || { echo "patched tree not staged yet: $(dirname "$DST")" >&2; exit 1; }
if cmp -s "$SRC" "$DST"; then
	echo "  watchdog header already in sync"
else
	cp "$SRC" "$DST"
	echo "  copied $SRC -> $DST"
fi
