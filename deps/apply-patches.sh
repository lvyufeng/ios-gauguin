#!/bin/bash
# Apply xnu/patches to an xnu checkout exactly like deps/build-local.sh and
# the CI (deps/mirror staging instead of the scripts that download):
#
#   deps/apply-patches.sh XNU_CHECKOUT MIRROR_DIR [MACHINE_CONFIG]
#
# MIRROR_DIR holds libpthread/, hfs/ and BearSSL/ (deps/mirror/fetch_deps.py
# or the blobs branch, see deps/README.md).
set -euo pipefail
root=${1:?usage: apply-patches.sh XNU_CHECKOUT MIRROR_DIR [MACHINE_CONFIG]}
mirror=${2:?usage: apply-patches.sh XNU_CHECKOUT MIRROR_DIR [MACHINE_CONFIG]}
machine=${3:-GAUGUIN}
repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
export MACHINE_CONFIG=$machine MACOS_VERSION=13.5
bash "$repo/deps/mirror/xnu/prepare.sh" "$root" "$mirror"
bash "$repo/deps/mirror/xnu/prepare-bearssl.sh" "$root" "$mirror"
for p in "$repo"/xnu/patches/*.patch; do
	if ! git apply --check "$p" 2> /tmp/apply-err.txt; then
		echo "FAILED: $(basename "$p")" >&2
		head -3 /tmp/apply-err.txt >&2
		exit 1
	fi
	git apply "$p"
done
echo "applied $(ls "$repo"/xnu/patches/*.patch | wc -l) patches to $root as $machine"
