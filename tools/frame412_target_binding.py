"""Join Metal attachment binding to qualified native renders and scan latches."""

from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
import re


COMMIT = re.compile(r"GAUGUIN C4Q342: phase=0 object=(0x[0-9a-f]+) start_us=(\d+) end_us=(\d+) value=0")
TARGET = re.compile(r"GAUGUIN C4 TARGET: object=(0x[0-9a-f]+) made_us=(\d+) commit_us=(\d+) "
                    r"surface=(\d+) bind_begin=(\d+) bind_end=(\d+) load=(\d+) store=(\d+) other_colors=(\d+)")
ROUNDING_NS = 500
MAX_TARGETS = 4096


@dataclass(frozen=True)
class TargetBinding:
    surface: int
    begin: int
    end: int
    load_action: int
    store_action: int
    other_colors: int


def decode(text, numer, denom):
    commits = Counter()
    observations = {}
    for line in text.splitlines():
        if match := COMMIT.fullmatch(line):
            obj, made, committed = match.groups()
            commits[int(made), int(committed), obj] += 1
            continue
        if not line.startswith("GAUGUIN C4 TARGET:"):
            continue
        match = TARGET.fullmatch(line)
        if not match or len(observations) >= MAX_TARGETS:
            raise ValueError("Malformed Metal target row or capture bound exceeded")
        obj, made, committed, *fields = match.groups()
        made, committed = int(made), int(committed)
        key = made, committed, obj
        binding = TargetBinding(*map(int, fields))
        if key in observations or not (
            0 < int(obj, 16) < 1 << 64 and 220_000_000 <= made <= committed <= 900_000_000
            and 0 < binding.surface < 1 << 32 and 0 < binding.begin <= binding.end < 1 << 64
            and made * 1000 - ROUNDING_NS <= binding.begin * numer // denom
            and binding.end * numer // denom <= committed * 1000 + ROUNDING_NS
            and binding.load_action <= 2 and binding.store_action <= 5 and binding.other_colors <= 7
        ):
            raise ValueError("Metal target identity, attachment actions or clock order differ")
        observations[key] = binding
    if any(commits[key] != 1 for key in observations):
        raise ValueError("Metal target does not have one unchanged command buffer commit")
    return commits, observations


def measure(commits, observations, renders, latches, windows, numer, denom):
    """Use only a unique frontend commit contained by an exact native render."""
    keys = sorted(commits)
    created_ns = [key[0] * 1000 for key in keys]
    ordered_latches = sorted(latches.items())
    result = {}
    for workload, spans in windows.items():
        counts = Counter()
        linked = []
        for index, (scan, latch) in enumerate(ordered_latches):
            if not any(span["first_scan"] <= scan <= span["last_scan"] for span in spans):
                continue
            counts["visible_writers"] += 1
            render = renders.get(latch["generation"], {}).get("render")
            if render is None:
                counts["missing_native_render"] += 1
                continue
            start = render["begin_tick"] * numer // denom - ROUNDING_NS
            end = min(render["end_tick"], latch["issue_tick"]) * numer // denom + ROUNDING_NS
            first = bisect_left(created_ns, start)
            last = bisect_right(created_ns, end)
            matches = [key for key in keys[first:last] if key[0] <= key[1] and key[1] * 1000 <= end]
            if len(matches) != 1 or commits[matches[0]] != 1:
                counts["frontend_commit_ambiguous_or_missing"] += 1
                continue
            counts["unique_frontend_commit"] += 1
            binding = observations.get(matches[0])
            if binding is None:
                counts["missing_target_observation"] += 1
                continue
            if binding.surface != latch["surface"] or not (
                render["begin_tick"] <= binding.begin <= binding.end <= min(render["end_tick"], latch["issue_tick"])
            ):
                counts["target_or_render_interval_differs"] += 1
                continue
            release = ordered_latches[index - 1][1]["confirmed_tick"] if index else None
            if release is None:
                availability = "previous_latch_missing"
            elif release <= binding.begin:
                availability = "previous_slot_released_before_binding"
            elif release > binding.end:
                availability = "previous_slot_held_through_binding"
            else:
                availability = "release_crosses_binding_interval"
            counts[availability] += 1
            linked.append(dict(scan=scan, generation=latch["generation"], surface=binding.surface,
                binding_ticks=[binding.begin, binding.end], native_issue_tick=latch["issue_tick"],
                previous_latch_tick=release, availability=availability, color_load_action=binding.load_action,
                color_store_action=binding.store_action, other_color_attachments=binding.other_colors))
        result[workload] = dict(counts=dict(counts), linked=linked)
    return result
