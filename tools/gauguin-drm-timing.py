#!/usr/bin/env python3
"""Read the recovery DRM timing probe output and check the vblank cadence."""
import argparse
import json
from pathlib import Path
import statistics


def analyze(log):
    records = [line.split() for line in log.splitlines() if line.startswith("GDRM ")]
    for record in records:
        if record[1:2] == ["error"]:
            raise ValueError("probe reported " + " ".join(record[2:]))
    if (len(records) != 27 or records[0][:2] != ["GDRM", "mode"]
            or len(records[0]) != 8 or records[-1][:2] != ["GDRM", "complete"]
            or len(records[-1]) != 3):
        raise ValueError("incomplete or repeated DRM observation")
    method = records[-1][2]
    if method not in ("crtc-sequence", "wait-query"):
        raise ValueError("unrecognized timestamp method")
    width, height, reported, clock, htotal, vtotal = map(int, records[0][2:])
    if ((width, height) != (1080, 2400) or not 0 < reported <= 240
            or not 0 < clock <= 1_000_000 or not 0 < htotal <= 8192 or not height <= vtotal <= 16000):
        raise ValueError("invalid DSI mode")
    samples = []
    for record in records[1:-1]:
        if record[:2] != ["GDRM", "sample"] or len(record) != 5:
            raise ValueError("malformed vblank sample")
        count, stamp, observed = map(int, record[2:])
        if not 0 <= count < (1 << (32 if method == "wait-query" else 64)):
            raise ValueError("invalid vblank sequence")
        if not 0 < stamp <= observed < 1 << 63 or observed - stamp > 100_000_000:
            raise ValueError("stale or nonmonotonic timestamp domain")
        samples.append((count, stamp, observed))

    periods = []
    frames = 0
    for previous, current in zip(samples, samples[1:]):
        count, stamp, observed = current
        old_count, old_stamp, old_observed = previous
        if not 0 < observed - old_observed <= 250_000_000:
            raise ValueError("irregular sample window")
        delta = count - old_count
        if method == "wait-query":
            delta %= 1 << 32
        elapsed = stamp - old_stamp
        if delta == 0 and elapsed == 0:
            continue
        if not 0 < delta <= 60 or elapsed <= 0:
            raise ValueError("vblank sequence reset or inconsistent timestamp")
        period = elapsed / delta
        if not 3_500_000 <= period <= 40_000_000:
            raise ValueError("vblank period outside the supported measurement range")
        periods.append(period)
        frames += delta
    elapsed = samples[-1][1] - samples[0][1]
    if len(periods) < 16 or elapsed < 650_000_000:
        raise ValueError("insufficient vblank progress")
    median = statistics.median(periods)
    if max(abs(period - median) for period in periods) > median * 0.08:
        raise ValueError("unstable vblank cadence")
    measured = 1_000_000_000 * frames / elapsed
    return {
        "method": method, "reported_mode_hz": reported, "reported_clock_khz": clock,
        "mode_totals": [htotal, vtotal], "sample_count": len(samples),
        "vblank_advances": frames, "timestamp_span_ns": elapsed,
        "observed_vblank_hz": round(measured, 4),
        "reported_mode_matches_vblank": abs(measured - reported) <= reported * 0.025,
        "interval_period_ns": [round(min(periods)), round(median), round(max(periods))],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(analyze(args.log.read_text()), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f"gauguin DRM timing: {error}\n")


if __name__ == "__main__":
    main()
