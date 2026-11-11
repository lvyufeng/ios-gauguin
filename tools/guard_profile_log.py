"""Strictly parse 0296 guard timing records without changing raw evidence."""
import re

PREFIX = "SWEET GPU GUARD PERF:"
ROW = re.compile(
    r"SWEET GPU GUARD PERF: group=(\d+) calls=(\d+) ns=(\d+) "
    r"pending_end_calls=(\d+) pending_end_ns=(\d+); "
    r"CPU wall, pending sampled at end"
)
NAMES = ("owner", "lease", "unsecured", "clock", "irq", "faults")
MAX_U64 = (1 << 64) - 1


def parse_guard_profile(text):
    groups = {}
    for line in text.splitlines():
        if PREFIX not in line:
            continue
        match = ROW.fullmatch(line)
        if match is None:
            raise ValueError("malformed or interleaved guard timing record")
        group, calls, ns, pending_calls, pending_ns = map(int, match.groups())
        if (group >= len(NAMES) or group in groups or
                any(value > MAX_U64 for value in (calls, ns, pending_calls, pending_ns)) or
                pending_calls > calls or pending_ns > ns or
                (calls == 0 and ns != 0) or (pending_calls == 0 and pending_ns != 0)):
            raise ValueError("inconsistent or duplicate guard timing record")
        groups[group] = {
            "group": group, "name": NAMES[group], "calls": calls, "wall_ns": ns,
            "pending_at_end_calls": pending_calls, "pending_at_end_wall_ns": pending_ns,
        }
    if set(groups) != set(range(len(NAMES))):
        raise ValueError("incomplete guard timing records")
    return {
        "groups": [groups[group] for group in range(len(NAMES))],
        "scope": "CPU wall intervals; global pending flag sampled at each guard end",
        "GPU_overlap_qualified": False,
        "per_submit_attribution_qualified": False,
        "hardware_performance_qualified": False,
    }
