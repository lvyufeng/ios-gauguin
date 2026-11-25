"""Parse the 0297 all-caller fault-check timings without repairing evidence."""
import re

PREFIX = 'SWEET GPU FAULT PERF:'
ROW = re.compile(r'SWEET GPU FAULT PERF: group=(\d+) calls=(\d+) ns=(\d+); all callers, CPU wall')
NAMES = ('global', 'settle', 'bank0', 'bank1', 'host', 'ao')
MAX_U64 = (1 << 64) - 1


def parse_fault_profile(text):
    groups = {}
    for line in text.splitlines():
        if PREFIX not in line:
            continue
        match = ROW.fullmatch(line)
        if match is None:
            raise ValueError('malformed or interleaved fault timing record')
        group, calls, ns = map(int, match.groups())
        if (group >= len(NAMES) or group in groups or
                calls > MAX_U64 or ns > MAX_U64 or (calls == 0 and ns != 0)):
            raise ValueError('inconsistent or duplicate fault timing record')
        groups[group] = {'group': group, 'name': NAMES[group], 'calls': calls, 'wall_ns': ns}
    if set(groups) != set(range(len(NAMES))):
        raise ValueError('incomplete fault timing records')
    return {
        'groups': [groups[group] for group in range(len(NAMES))],
        'scope': 'CPU wall intervals from all gfw_faults callers; includes diagnostic overhead',
        'runtime_only_qualified': False,
        'GPU_overlap_qualified': False,
        'per_submit_attribution_qualified': False,
        'hardware_performance_qualified': False,
    }
