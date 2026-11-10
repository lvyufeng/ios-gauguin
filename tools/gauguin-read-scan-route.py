#!/usr/bin/env python3
"""Validate a saved 4 KiB Gauguin mode-4 scan receipt."""
import argparse
import json
from pathlib import Path
import re


RECORD = re.compile(
    r"GAUGUIN_SCAN2 run=(\d+) mode=4 done=([01]) status=(\d+) stage=(\d+)\n"
    r"gcc=([0-9a-f]{8}(?:/[0-9a-f]{8}){2}) disp=([0-9a-f]{8}(?:/[0-9a-f]{8}){3}) "
    r"timing=([0-9a-f]{8}) count=([0-9a-f]{8})\n"
    r"attempts=(\d+) samples=(\d+) crossed=(\d+) frame=(\d+/\d+) line=(\d+/\d+) "
    r"advances=(\d+) start_ns=(\d+) end_ns=(\d+) millihz=(\d+) nominal=(\d+)\n"
    r"route=(\d+) samples=(\d+) frame=(\d+/\d+) pipe_mask=([0-9a-f]) ctl_mask=([0-9a-f]) "
    r"fb=([0-9a-f]{1,16}) geometry=(\d+/\d+/\d+) size=([0-9a-f]{8}) "
    r"stride=([0-9a-f]{8}) format=([0-9a-f]{8}) op=([0-9a-f]{8})\n"
    r"source=([0-9a-f]{8}(?:/[0-9a-f]{8}){3}) interface=([0-9a-f]{8}(?:/[0-9a-f]{8}){3}) "
    r"stages=([0-9a-f](?:/[0-9a-f]){3}) virtual=([0-9a-f](?:/[0-9a-f]){3})\n"
    r"END_GAUGUIN_SCAN2 run=(\d+)\n", re.ASCII,
)
ROUTE_STATUS = (
    "not-run", "bad-framebuffer", "map-failed", "scan-lost", "unstable",
    "no-match", "ambiguous", "not-staged", "unsupported-layout", "matched",
)


def words(text, base=10):
    return [int(word, base) for word in text.split("/")]


def read_route_receipt(block, run_id):
    text, separator, pad = block.partition(b"\0")
    if len(block) != 4096 or not separator or any(pad):
        raise ValueError("invalid receipt block or zero padding")
    match = RECORD.fullmatch(text.decode("ascii"))
    if not match:
        raise ValueError("unrecognized mode-4 receipt")
    (run, done, status, stage, gcc, disp, timing, count, attempts, samples, crossed, frames, lines,
     advances, start, end, millihz, nominal, route, route_samples, route_frames, pipe, ctl,
     fb, geometry, size, stride, pixel_format, op_mode, sources, interfaces, stages, virtual,
     footer) = match.groups()
    if not 0 < run_id < 1 << 32 or int(run) != run_id or int(footer) != run_id:
        raise ValueError("diagnostic run ID mismatch")
    scan = list(map(int, (status, stage, attempts, samples, crossed, advances, start, end, millihz, nominal)))
    cadence_status, scan_stage, tries, accepted, crossed_frames, steps, start_ns, end_ns, rate, nominal_hz = scan
    route_status, distinct = int(route), int(route_samples)
    scan_frames, scan_lines, route_span, dims = map(words, (frames, lines, route_frames, geometry))
    numeric_registers = [int(value, 16) for value in (timing, count, pipe, ctl, fb, size, stride, pixel_format, op_mode)]
    timing_enable, counter_enable, pipe_mask, ctl_mask, framebuffer, packed_size, pitch, fmt, op = numeric_registers
    gcc, disp, sources, interfaces, stages, virtual = (words(value, 16) for value in (gcc, disp, sources, interfaces, stages, virtual))
    if (not 0 <= cadence_status <= 11 or not 0 <= scan_stage <= 2 or not 0 <= route_status < len(ROUTE_STATUS)
            or not 0 <= distinct <= 3 or not 0 <= accepted + crossed_frames <= tries <= 160
            or nominal_hz not in (0, 60, 90, 120)
            or any(value >= 1 << 32 for value in scan_frames + scan_lines + route_span + dims + [steps, rate])
            or not 0 <= start_ns <= end_ns < 1 << 64):
        raise ValueError("out-of-range scan fields")
    if done == "0" and any(scan + [route_status, distinct] + scan_frames + scan_lines + route_span + dims
                          + numeric_registers + gcc + disp + sources + interfaces + stages + virtual):
        raise ValueError("incomplete worker contains results")
    if (route_status and cadence_status != 3) or (distinct and route_status < 4):
        raise ValueError("route result precedes scan qualification")
    if cadence_status == 3:
        span = end_ns - start_ns
        if (scan_stage != 2 or accepted < 64 or not 1_000_000_000 <= span <= 1_251_000_000
                or steps < 24 or (scan_frames[1] - scan_frames[0]) % (1 << 32) != steps
                or rate != (steps * 1_000_000_000_000 + span // 2) // span):
            raise ValueError("inconsistent measured cadence")
    if route_status == 9:
        source_hits = [i for i, address in enumerate(sources) if address == framebuffer]
        control_hits = [i for i, value in enumerate(interfaces) if value & 2]
        unsupported_format = (3 << 30) | (1 << 22) | (3 << 19) | (1 << 11)
        if (distinct != 3 or not 2 <= (route_span[1] - route_span[0]) % (1 << 32) <= 24
                or dims != [1080, 2400, 4320] or not 0 < framebuffer <= (1 << 32) - 10368000
                or framebuffer & 0x3fff or packed_size != ((2400 << 16) | 1080) or pitch != 4320
                or fmt & unsupported_format or (fmt >> 9) & 3 != 3 or op & 1
                or len(source_hits) != 1 or len(control_hits) != 1):
            raise ValueError("inconsistent matched route")
        source, control = source_hits[0], control_hits[0]
        if (pipe_mask != 1 << source or ctl_mask != 1 << control or interfaces[control] != 2
                or stages[control] != pipe_mask or virtual[control]):
            raise ValueError("matched source is not uniquely staged on INTF1")
    return {
        "run_id": run_id, "done": done == "1", "scan_status": cadence_status,
        "scan_stage": scan_stage, "scan_millihz": rate, "nominal_hz": nominal_hz,
        "route_status": ROUTE_STATUS[route_status], "distinct_frames_sampled": distinct,
        "sampled_frames": route_span, "framebuffer": framebuffer, "geometry": dims,
        "source_mask": pipe_mask, "control_mask": ctl_mask,
        "source_addresses": sources, "control_interfaces": interfaces,
        "control_stages": stages, "virtual_stages": virtual,
        "source_format": fmt, "source_operation_mode": op,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("block", type=Path)
    parser.add_argument("--run-id", required=True, type=int)
    args = parser.parse_args()
    try:
        with args.block.open("rb") as stream:
            receipt = read_route_receipt(stream.read(4097), args.run_id)
    except (OSError, ValueError) as error:
        parser.exit(1, f"gauguin scan route: {error}\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
