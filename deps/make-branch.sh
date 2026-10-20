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
SWEET_GUARD=1 bash "$repo/deps/mirror/xnu/prepare.sh" "$PWD" "$repo/deps/mirror"
bash "$repo/deps/mirror/xnu/prepare-bearssl.sh" "$PWD" "$repo/deps/mirror"
n=0
for p in "$repo"/xnu/patches/*.patch; do
	if git apply --check "$p"; then
		git apply "$p"
		n=$((n + 1))
	else
		echo "FAILED: $(basename "$p")" >&2
		git apply --check "$p" 2>&1 | head -5 >&2
		exit 1
	fi
done
git add -A
git commit -qm "gauguin: sweet/gauguin kernel sources (xnu-$base + $(ls "$repo"/xnu/patches/*.patch | wc -l) patches)"
echo "$branch: $n patches applied on $base ($(git rev-parse --short HEAD))"
echo "push: git push -u origin HEAD:refs/heads/$branch" >&2
