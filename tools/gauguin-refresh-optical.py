#!/usr/bin/env python3
"""Summarize distinct IDs observed in a cropped recording of the refresh marker."""

import argparse
import json
import math
from pathlib import Path


BITS = 12
CELLS = 2 + BITS * 2
MAX_CAMERA_FRAMES = 20_000


def decode(row):
    white, black = row[:2]
    contrast = white - black
    if contrast < 64:
        return None
    midpoint = (white + black) / 2
    margin = contrast * 0.15
    gray = 0
    for bit in range(BITS):
        first, inverse = row[2 + 2 * bit:4 + 2 * bit]
        if first >= midpoint + margin and inverse <= midpoint - margin:
            gray |= 1 << bit
        elif not (inverse >= midpoint + margin and first <= midpoint - margin):
            return None

    frame = gray
    while gray:
        gray >>= 1
        frame ^= gray
    return frame


def analyze(data, timestamps, first_id, last_id):
    if not 0 < first_id < last_id < 1 << BITS:
        raise ValueError("invalid callback ID window")
    if not 2 <= len(timestamps) <= MAX_CAMERA_FRAMES or len(data) != CELLS * len(timestamps):
        raise ValueError("camera frames and timestamps do not match")
    if (any(not math.isfinite(value) for value in timestamps)
            or any(new <= old for old, new in zip(timestamps, timestamps[1:]))):
        raise ValueError("camera timestamps must be finite and strictly increasing")

    previous = None
    first_seen, last_seen = None, None
    first_index, last_index = None, None
    distinct = duplicates = invalid = outside = 0
    for index in range(len(timestamps)):
        start = index * CELLS
        frame = decode(data[start:start + CELLS])
        if frame is None:
            invalid += 1
            continue
        if not first_id <= frame <= last_id:
            outside += 1
            continue
        if previous is not None and frame < previous:
            raise ValueError("frame IDs regressed inside one callback window")
        if frame == previous:
            duplicates += 1
            continue
        if first_seen is None:
            first_seen, first_index = frame, index
        previous = last_seen = frame
        last_index = index
        distinct += 1
    if distinct < 2:
        raise ValueError("fewer than two distinct IDs observed")

    camera_gaps = [timestamps[i] - timestamps[i - 1] for i in range(first_index + 1, last_index + 1)]
    duration = timestamps[last_index] - timestamps[first_index]
    return {
        "first_observed_id": first_seen,
        "last_observed_id": last_seen,
        "distinct_ids_observed": distinct,
        "ids_unobserved_between_endpoints": last_seen - first_seen + 1 - distinct,
        "camera_frames_repeating_id": duplicates,
        "camera_frames_undecodable": invalid,
        "camera_frames_outside_id_window": outside,
        "span_seconds": round(duration, 6),
        "observed_id_advances_per_second": round((distinct - 1) / duration, 3),
        "longest_camera_gap_ms": round(max(camera_gaps) * 1000.0, 3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", type=Path, help="raw gray video with 26 columns and one row")
    parser.add_argument("timestamps", type=Path, help="camera frame times in seconds, one per line")
    parser.add_argument("--first-id", type=int, required=True)
    parser.add_argument("--last-id", type=int, required=True)
    args = parser.parse_args()
    try:
        if args.samples.stat().st_size > CELLS * MAX_CAMERA_FRAMES or args.timestamps.stat().st_size > 1_000_000:
            raise ValueError("recording exceeds the decoder's input limit")
        data = args.samples.read_bytes()
        times = [float(line) for line in args.timestamps.read_text().splitlines() if line.strip()]
        result = analyze(data, times, args.first_id, args.last_id)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
