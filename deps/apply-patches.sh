#!/bin/bash
# Apply xnu/patches to an xnu checkout exactly like deps/build-local.sh and
# the CI (deps/mirror staging instead of the scripts that download):
#
#   deps/apply-patches.sh XNU_CHECKOUT MIRROR_DIR [MACHINE_CONFIG] [STATE_ROOT]
#
# MIRROR_DIR holds libpthread/, hfs/ and BearSSL/ (deps/mirror/fetch_deps.py
# or the blobs branch, see deps/README.md).
set -euo pipefail
root=${1:?usage: apply-patches.sh XNU_CHECKOUT MIRROR_DIR [MACHINE_CONFIG]}
mirror=${2:?usage: apply-patches.sh XNU_CHECKOUT MIRROR_DIR [MACHINE_CONFIG]}
machine=${3:-GAUGUIN}
machine=$(echo "$machine" | tr '[:lower:]' '[:upper:]')
repo=$(cd "$(dirname "$0")/.." && pwd)
state_root=${4:-$repo/.deps-cache/source-state}
state_root=$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$state_root")
root=$(cd "$root" && pwd)
mirror=$(cd "$mirror" && pwd)
cd "$root"
export MACHINE_CONFIG=$machine MACOS_VERSION=13.5
# Stage providers first; the pinned SDK header is supplied after the series.
SKIP_TARGET_MACROS=1 bash "$repo/deps/mirror/xnu/prepare.sh" "$root" "$mirror"
bash "$repo/deps/mirror/xnu/prepare-bearssl.sh" "$root" "$mirror"
python3 "$repo/tools/xnu-patches.py" apply "$PWD"
python3 "$repo/tools/xnu-stage-sdk.py" "$PWD" --cache "$(dirname "$state_root")/sdk-inputs"
python3 "$repo/tools/xnu-post-patch.py" "$PWD"
bash "$repo/deps/sync-watchdog.sh" "$PWD"
python3 "$repo/tools/xnu-source-state.py" record "$PWD" --state-root "$state_root"
