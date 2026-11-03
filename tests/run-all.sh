#!/bin/bash
# Run every host test in the repo.
#
#   tests/run-all.sh
#
# These tests exist because the phone has not been reachable since
# 2026-11-03, and the diagnostic tools written to explain the next boot are
# the only things that could have gone wrong silently: the init watchdog, the
# bisection verdict, and the mark reader. Between them the tests have already
# found nine defects (see NOTES.md entries (20)-(23)).
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
cd "$here/.."

fail=0
for t in "$here"/test_*.py; do
	[ -f "$t" ] || continue
	printf '\n== %s\n' "$(basename "$t")"
	if ! python3 "$t"; then
		fail=$((fail + 1))
	fi
done

printf '\n'
if [ "$fail" -ne 0 ]; then
	echo "$fail test file(s) failed"
	exit 1
fi
echo "all host tests passed"