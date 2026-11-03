#!/usr/bin/env python3
"""Decide what a bisection run means, from two logs.

  python3 tools/bisect-verdict.py OFF_LOG ON_LOG

Read by tools/bisect-keys.sh, and testable on its own (tests/test_bisect.py):
the decision is pure - two console logs in, one verdict out - so the cases that
matter can be pinned without a phone.
"""
import re
import sys

# Phases in the order the init tail reaches them. Each is matched against the
# console text; the LAST one found in a log is where that boot got to.
PHASES = [
    ("keys_init",      r"SWEET UFS: keys_init done"),
    ("touch_init",     r"SWEET UFS: touch_init done"),
    ("usb_probe",      r"SWEET UFS: init complete"),
    ("root_mounted",   r"BSD root: ufsroot0"),
    ("userland",       r"exec launchd|libignition: 1: hello"),
]


def phase_of(text):
    """Return the name of the furthest phase present, or None."""
    best = None
    for name, pat in PHASES:
        if re.search(pat, text or ""):
            best = name
    return best


def reached_keys_init_prefix(text):
    """Did this boot print the keys_init line, or anything at or after it?

    A log that got past keys_init obviously did; a truncated log that stops on
    'SWEET UFS: keys_init' did too. Only a log that never mentions the step at
    all - or stops before it - counts as "did not reach".
    """
    text = text or ""
    if re.search(r"SWEET UFS: keys_init", text):
        return True
    if phase_of(text) is not None:
        return True     # it reached a later phase, so it passed keys_init
    return False


def verdict(off_text, on_text):
    """Compare the sweetkeys=0 run against the default run.

    Returns (code, lines). Codes name the four outcomes so callers and tests
    can assert on them instead of on prose.
    """
    off = phase_of(off_text)
    on = phase_of(on_text)
    lines = []

    def show(tag, text):
        p = phase_of(text)
        lines.append(f"  {tag:12} reached: {p or 'nothing past sample_start'}")
        if not reached_keys_init_prefix(text):
            lines.append(f"  {tag:12} (did not even reach the keys_init line)")

    show("sweetkeys=0", off_text)
    show("default", on_text)
    lines.append("")

    # Order matters: check "both succeeded" before either single success, or
    # the first match would wrongly blame keys when nothing is blocking.
    mounted = ("root_mounted", "userland")
    off_mount = off in mounted
    on_mount = on in mounted
    if off_mount and on_mount:
        lines.append(f"Both runs mounted the root (phases: {off}, {on}).")
        lines.append("The earlier 'stops at keys_init' runs were not reproducing this "
                     "configuration. Compare the boot lines before concluding "
                     "anything - and if the images really are the bisect pair, the "
                     "stall is not reproducible right now.")
        return "both_mount", lines
    if off_mount:
        lines.append(f"ROOT MOUNTED with sweetkeys=0 (phase: {off}) but not with the "
                     f"default (phase: {on or 'nothing past keys_init'}). The keys "
                     f"driver is what blocks the boot.")
        return "keys_blocks", lines
    if on_mount:
        lines.append(f"ROOT MOUNTED with the default image (phase: {on}) but not with "
                     f"sweetkeys=0 ({off or 'nothing past keys_init'}). That makes no "
                     f"sense unless the runs saw different hardware state. Re-run.")
        return "inconsistent", lines

    # Neither mounted. Where did the difference appear?
    if reached_keys_init_prefix(off_text) and not reached_keys_init_prefix(on_text):
        lines.append("sweetkeys=0 got as far as the keys_init line and the default "
                     "did not: the stall is BEFORE sweet_keys_init(), so the "
                     "boot-arg is not the variable. Look at the UFS/log path.")
        return "before_keys", lines
    if reached_keys_init_prefix(on_text) and not reached_keys_init_prefix(off_text):
        lines.append("The default image reached the keys_init line and sweetkeys=0 "
                     "did not. Since sweetkeys=0 only skips hardware access, the two "
                     "runs saw different hardware state - re-run before drawing a "
                     "conclusion.")
        return "inconsistent", lines
    if not reached_keys_init_prefix(off_text) and not reached_keys_init_prefix(on_text):
        lines.append("Neither run reached the keys_init line. The stall is in the UFS "
                     "init path itself, not in keys. Start bisecting there.")
        return "before_keys_both", lines
    # Compare depth first: "off passed keys_init" only means keys is the
    # blocker if the default did NOT get further than that point.
    order = [n for n, _ in PHASES]
    off_depth = order.index(off) if off in order else -1
    on_depth = order.index(on) if on in order else -1
    if off_depth > on_depth:
        lines.append(f"sweetkeys=0 got further ({off}) than the default "
                     f"({on or 'nothing past the keys_init line'}): the keys driver "
                     f"is the blocker, and the marks name the step it dies in.")
        return "keys_blocks", lines
    if on_depth > off_depth:
        lines.append(f"The default image got further ({on}) than sweetkeys=0 "
                     f"({off or 'nothing'}), which makes no sense unless the two runs "
                     f"saw different hardware state. Re-run before trusting it.")
        return "inconsistent", lines
    if off == "keys_init":
        lines.append("Both stopped at the same point, so sweetkeys is not the "
                     "difference. Look at the mark blocks.")
        return "same_phase", lines
    if off == on:
        lines.append(f"Both runs stopped at the same phase ({off or 'pre-keys'}), so "
                     f"sweetkeys is not the difference. Look at the mark blocks: if "
                     f"both stopped on the same mark, the stall is before "
                     f"sweet_keys_init() or in the log path.")
        return "same_phase", lines
    if off is None or (on and off and PHASES.index(
            next(p for p in PHASES if p[0] == on)) >
            PHASES.index(next(p for p in PHASES if p[0] == off))):
        lines.append("The default image got further than sweetkeys=0, which makes no "
                     "sense unless the two runs saw different hardware state. "
                     "Re-run before trusting it.")
        return "inconsistent", lines
    lines.append(f"sweetkeys=0 reached {off}, the default reached {on or 'nothing'}: "
                 f"the keys driver helps rather than blocks, or the runs differ in "
                 f"something else. Re-run to confirm.")
    return "unclear", lines


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: bisect-verdict.py OFF_LOG ON_LOG\n")
        return 2
    texts = []
    for path in argv[1:]:
        try:
            with open(path, errors="replace") as f:
                texts.append(f.read())
        except OSError:
            texts.append("")
    code, lines = verdict(*texts)
    print("\n".join(lines))
    print(f"verdict: {code}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))