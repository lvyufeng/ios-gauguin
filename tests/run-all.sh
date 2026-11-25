#!/bin/bash
# Run host tests from the project directory.
#
# --checkout selects build, display and input checks supported by a clean
# checkout and its staged XNU source. The full suite also uses trial archives.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
cd "$here/.."
repo=$PWD
export PYTHONPATH="$repo:$repo/tools${PYTHONPATH:+:$PYTHONPATH}"

case "${1:-}" in
	--checkout)
		tests=(
			"$here"/test_{build_identity,build_provenance,patch_series,sdk_inputs}.py
			"$here"/test_{frame344_log,frame345_log,frame349_log,frame350_log,frame359_frontend,frame369_swap_timing,frame370_swap_wait}.py
			"$here"/test_{present_stats,sb_input_log,storage_budget,watchdog}.py
		)
		;;
	"") tests=("$here"/test_*.py) ;;
	*) echo "usage: $0 [--checkout]" >&2; exit 2 ;;
esac

fail=0
for t in "${tests[@]}"; do
	printf '\n== %s\n' "$(basename "$t")"
	if ! python3 "$t"; then
		fail=$((fail + 1))
	fi
done

if [ "${1:-}" = --checkout ] && [ -n "${XNU_SOURCE:-}" ]; then
	printf '\n== gauguin-display-deadline.cpp\n'
	deadline_test=$(mktemp) || exit 1
	trap 'rm -f "$deadline_test"' EXIT
	if ! "${CXX:-c++}" -std=c++17 -Wall -Wextra -Werror -I "$XNU_SOURCE/bsd/dev" \
	    "$here/gauguin-display-deadline.cpp" -o "$deadline_test" || ! "$deadline_test"; then
		fail=$((fail + 1))
	fi
fi

printf '\n'
if [ "$fail" -ne 0 ]; then
	echo "$fail test file(s) failed"
	exit 1
fi
echo "all host tests passed"
