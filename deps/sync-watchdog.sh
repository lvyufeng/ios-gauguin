#!/bin/bash
# Keep the build tree's copy of sweet_init_watchdog.h identical to the repo's.
#
#   deps/sync-watchdog.sh
#
# The patched XNU tree lives in .deps-cache/ (git-ignored) and is rebuilt from
# xnu/patches + deps/mirror; the header is a project file, not part of any
# patch, so it has to be copied in before a kernel build. tools/ and the host
# tests read the repo copy directly.
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=xnu/sweet_init_watchdog.h
DST=.deps-cache/xnu-patched-0082-2/bsd/dev/sweet_init_watchdog.h
[ -f "$SRC" ] || { echo "missing $SRC" >&2; exit 1; }
[ -d "$(dirname "$DST")" ] || { echo "patched tree not staged yet: $(dirname "$DST")" >&2; exit 1; }
if cmp -s "$SRC" "$DST"; then
	echo "  watchdog header already in sync"
else
	cp "$SRC" "$DST"
	echo "  copied $SRC -> $DST"
fi