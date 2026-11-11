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


def analyze_planes(log):
    records = [line.split() for line in log.splitlines() if line.startswith("GDRM ")]
    for record in records:
        if record[1:2] == ["error"]:
            raise ValueError("probe reported " + " ".join(record[2:]))
    if (not 3 <= len(records) <= 34 or records[0][:2] != ["GDRM", "route"]
            or len(records[0]) != 8 or records[-1][:2] != ["GDRM", "planes-complete"]
            or len(records[-1]) != 3 or int(records[-1][2]) != len(records) - 2):
        raise ValueError("incomplete or repeated DRM plane observation")
    connector, encoder, crtc, pipe, hz, crtc_fb = map(int, records[0][2:])
    if (not all(0 < item < 1 << 32 for item in (connector, encoder, crtc))
            or not 0 <= pipe < 32 or not 0 < hz <= 240 or not 0 <= crtc_fb < 1 << 32):
        raise ValueError("invalid DRM route")
    types = {0: "overlay", 1: "primary", 2: "cursor"}
    planes = []
    seen = set()
    for record in records[1:-1]:
        if record[:2] != ["GDRM", "plane"] or len(record) != 5:
            raise ValueError("malformed DRM plane")
        plane, fb, kind = map(int, record[2:])
        if (plane in seen or not 0 < plane < 1 << 32 or not 0 < fb < 1 << 32
                or kind not in types):
            raise ValueError("invalid DRM plane")
        seen.add(plane)
        planes.append({"plane_id": plane, "framebuffer_id": fb, "type": types[kind]})
    primary = [plane for plane in planes if plane["type"] == "primary"]
    if len(primary) != 1 or (crtc_fb and crtc_fb != primary[0]["framebuffer_id"]):
        raise ValueError("primary plane disagrees with CRTC")
    return {
        "connector_id": connector, "encoder_id": encoder, "crtc_id": crtc,
        "crtc_index": pipe, "reported_mode_hz": hz, "crtc_framebuffer_id": crtc_fb,
        "active_planes": planes,
    }


def analyze_modes(log):
    records = [line.split() for line in log.splitlines() if line.startswith("GDRM ")]
    for record in records:
        if record[1:2] == ["error"]:
            raise ValueError("probe reported " + " ".join(record[2:]))
    if (not 4 <= len(records) <= 35 or records[0][:2] != ["GDRM", "mode-route"]
            or len(records[0]) != 6 or records[-1][:2] != ["GDRM", "modes-complete"]
            or len(records[-1]) != 3 or int(records[-1][2]) != len(records) - 3):
        raise ValueError("incomplete or repeated DRM mode catalog")
    connector, encoder, crtc, pipe = map(int, records[0][2:])
    if not all(0 < value < 1 << 32 for value in (connector, encoder, crtc)) or not 0 <= pipe < 32:
        raise ValueError("invalid mode-catalog route")

    def timing(record, expected):
        if record[:2] != ["GDRM", expected] or len(record) != 16:
            raise ValueError("malformed DRM timing")
        clock, width, hs, he, ht, skew, height, vs, ve, vt, scan, rate, flags, kind = map(int, record[2:])
        if ((width, height) != (1080, 2400) or not 0 < clock <= 1_000_000
                or not width <= hs < he <= ht < 1 << 16 or not height <= vs < ve <= vt < 1 << 16
                or not all(0 <= value < 1 << 16 for value in (skew, scan)) or not 0 < rate <= 240
                or not all(0 <= value < 1 << 32 for value in (flags, kind))):
            raise ValueError("invalid DSI timing geometry")
        return {"reported_clock_khz": clock, "reported_hz": rate, "width": width, "height": height,
                "horizontal_total": ht, "horizontal_front_porch": hs - width,
                "horizontal_sync": he - hs, "horizontal_back_porch": ht - he, "horizontal_skew": skew,
                "vertical_total": vt, "vertical_front_porch": vs - height,
                "vertical_sync": ve - vs, "vertical_back_porch": vt - ve, "vertical_scan": scan,
                "flags": flags, "type": kind}

    active = timing(records[1], "active-timing")
    modes = [timing(record, "advertised-timing") for record in records[2:-1]]
    keys = [(mode["reported_hz"], mode["reported_clock_khz"]) for mode in modes]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate or ambiguous advertised DRM timing")
    active_payload = {key: value for key, value in active.items() if key != "type"}
    matches = [i for i, mode in enumerate(modes)
               if {key: value for key, value in mode.items() if key != "type"} == active_payload]
    return {"connector_id": connector, "encoder_id": encoder, "crtc_id": crtc, "crtc_index": pipe,
            "active_timing": active, "advertised_timings": modes,
            "matching_active_timing_index": matches[0] if matches else None}


def analyze_tests(log):
    records = [line.split() for line in log.splitlines() if line.startswith("GDRM ")]
    for record in records:
        if record[1:2] == ["error"]:
            raise ValueError("probe reported " + " ".join(record[2:]))
    if len(records) != 4 or records[-1] != ["GDRM", "tests-complete", "3"]:
        raise ValueError("incomplete or repeated DRM mode tests")
    results = []
    clocks = set()
    for expected, record in zip((60, 90, 120), records[:-1]):
        if record[:2] != ["GDRM", "test-only"] or len(record) != 5:
            raise ValueError("malformed DRM mode test")
        rate, clock, status = map(int, record[2:])
        if rate != expected or not 0 < clock <= 1_000_000 or not -4095 <= status <= 0:
            raise ValueError("invalid DRM mode test result")
        clocks.add(clock)
        results.append({"reported_hz": rate, "kernel_check_status": status})
    if len(clocks) != 1:
        raise ValueError("mode tests changed clock families")
    return {"reported_clock_khz": clocks.pop(), "test_only_results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--planes", action="store_true")
    group.add_argument("--modes", action="store_true")
    group.add_argument("--test-modes", action="store_true")
    args = parser.parse_args()
    try:
        if args.test_modes:
            reader = analyze_tests
        elif args.modes:
            reader = analyze_modes
        elif args.planes:
            reader = analyze_planes
        else:
            reader = analyze
        print(json.dumps(reader(args.log.read_text()), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f"gauguin DRM timing: {error}\n")


if __name__ == "__main__":
    main()
