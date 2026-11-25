#!/bin/bash
# Make the gauguin branch of the xnu fork: upstream xnu-8796.141.3 + the whole
# xnu/patches series, committed with the user's identity so CI can take it.
#
#   deps/make-branch.sh WORKDIR [BRANCH]
#
# WORKDIR is a fresh clone of the fork (any depth) at rel/xnu-8796. CI then
# runs dxb from that branch, which also means dxb's own bootstrap VMAPPLE
# kernel builds from the same (patched) tree.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
work=${1:?usage: deps/make-branch.sh WORKDIR [BRANCH]}
branch=${2:-gauguin}
cd "$work"
[ -z "$(git status --porcelain)" ] || {
	echo "make-branch requires a clean fresh checkout; existing files were preserved" >&2
	exit 1
}

# Base: the upstream xnu commit the series is written against, with the one
# fix the series needs for non-SWEET machine configs: bsd/dev/sweet_sample.c
# is listed as `standard` (every config) but only builds for the SWEET board,
# so its body is compiled out elsewhere (ARM64_BOARD_CONFIG_SWEET).
base=$(grep '^XNU_REV=' "$repo/deps/versions.env" | cut -d= -f2)
git checkout -q -B "$branch" "$base"
for f in bsd/dev/sweet_sample.c bsd/dev/sweet_ufs.c; do
	if [ ! -f "$f" ]; then
		git show b6ed483:"$f" > /dev/null 2>&1 || true
	fi
done

# Apply the series exactly as CI/deps/apply-patches.sh does: the mirror
# staging, then git apply of every patch.
bash "$repo/deps/apply-patches.sh" "$PWD" "$repo/deps/mirror" gauguin
n=$(python3 "$repo/tools/xnu-patches.py" list | wc -l | tr -d ' ')
git add -A -- . ':!bsd/pthread/sweet_libpthread/TargetConditionals.h' \
    ':!bsd/sweet_hfs/TargetConditionals.h'
git commit -qm "gauguin: sweet/gauguin kernel sources (xnu-$base + $n patches)"
echo "$branch: $n patches applied on $base ($(git rev-parse --short HEAD))"
echo "push: git push -u origin HEAD:refs/heads/$branch" >&2
