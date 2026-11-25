#!/usr/bin/env python3
"""Host tests for xnu/sweet_init_watchdog.h.

  python3 tests/test_watchdog.py

Compiles the real header with the host C compiler and drives
sweet_wd_should_report() over simulated timelines, so the tests exercise the
same code the kernel runs - not a Python re-implementation.

Two defects were found this way in NOTES 2026-11-03 (20): the watchdog warned
on healthy boots, and it could name a stale step. Both have a test here.
"""
import ctypes
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HEADER = os.path.join(REPO, "xnu", "sweet_init_watchdog.h")

SHIM = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sweet_init_watchdog.h"

/* Replays a timeline: steps arrive at given ticks, done at done_tick (0=never).
 * Prints one line per tick where the watchdog would warn. */
int main(int argc, char **argv)
{
	if (argc < 3) {
		fprintf(stderr, "usage: %s done_tick step:tick [step:tick...]\n", argv[0]);
		return 2;
	}
	int done_tick = atoi(argv[1]);
	int total = 400;
	struct sweet_wd_state st = { 0 };
	/* Split each "name:tick" once, up front, and keep both halves. */
	const char *names[64];
	int at[64];
	int n = 0;
	for (int i = 2; i < argc && n < 64; i++) {
		char *colon = strrchr(argv[i], ':');
		if (!colon) continue;
		*colon = '\0';
		names[n] = argv[i];
		at[n] = atoi(colon + 1);
		n++;
	}
	for (int t = 1; t <= total; t++) {
		if (done_tick > 0 && t >= done_tick) break;
		const char *step = "not started";
		for (int i = 0; i < n; i++) {
			if (t >= at[i]) step = names[i];
		}
		if (sweet_wd_should_report(&st, step)) {
			printf("tick %d %s\n", t, step);
		}
	}
	return 0;
}
"""


def build(tmpdir):
    src = os.path.join(tmpdir, "wd.c")
    exe = os.path.join(tmpdir, "wd")
    with open(src, "w") as f:
        f.write(SHIM)
    cmd = [os.environ.get("CC", "cc"), "-O1", "-Wall", "-Wextra", "-std=c11",
           "-I", os.path.dirname(HEADER), src, "-o", exe]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("header did not compile")
    return exe


def run(exe, done_tick, steps):
    args = [exe, str(done_tick)] + [f"{n}:{t}" for n, t in steps]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("shim failed")
    return [line.split() for line in r.stdout.splitlines()]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        exe = build(tmp)
        failures = 0

        def check(name, cond, detail=""):
            nonlocal failures
            if cond:
                print(f"  ok   {name}")
            else:
                failures += 1
                print(f"  FAIL {name} {detail}")

        # 1. A healthy tail - finishes at tick 16 (3.2 s at 200 ms) - is silent.
        out = run(exe, 16, [("sample_start", 8), ("keys_init", 10),
                            ("touch_init", 12), ("usb_probe", 15)])
        check("healthy boot is silent", out == [], f"got {out}")

        # 2. A tail that finishes just after the grace period is also silent.
        out = run(exe, 41, [("keys_init", 10)])
        check("tail finishing just past grace is silent", out == [], f"got {out}")

        # 3. Stalled in keys_init: first warning names keys_init, at tick 40.
        out = run(exe, 0, [("sample_start", 8), ("keys_init", 10)])
        check("stall reports the stalled step", bool(out) and out[0][2] == "keys_init",
              f"got {out[:2]}")
        # Strictly after the grace period: at exactly SWEET_WD_GRACE_TICKS a
        # tail may be one tick from finishing (see the header's comment).
        check("first warning comes after the grace period",
              bool(out) and int(out[0][1]) == 41, f"got {out[:2]}")

        # 4. Same step keeps being reported every SWEET_WD_REPEAT_TICKS.
        ticks = [int(o[1]) for o in out if o[2] == "keys_init"]
        check("repeats steadily while stuck",
              len(ticks) > 3 and all(b - a == 50 for a, b in zip(ticks, ticks[1:])),
              f"ticks {ticks[:6]}")

        # 5. A step change after the grace period is reported immediately.
        out = run(exe, 0, [("keys_init", 10), ("touch_init", 95)])
        moved = [o for o in out if o[2] == "touch_init"]
        check("step change is reported at once", bool(moved) and int(moved[0][1]) == 95,
              f"got {[ (o[1],o[2]) for o in out[:5] ]}")

        # 6. Regression: the old bug printed before the grace period.
        out = run(exe, 0, [("sample_start", 1), ("keys_init", 2), ("usb_probe", 3)])
        early = [o for o in out if int(o[1]) < 40]
        check("nothing is printed before the grace period", early == [], f"got {early}")

        # 7. Regression: the reported step must be the current one, never a
        #    type-adjacent stale name.
        out = run(exe, 0, [("touch_init", 10), ("usb_probe", 120)])
        last = out[-1][2] if out else None
        check("last report names the current step", last == "usb_probe", f"got {last}")

    print()
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print("all watchdog checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())