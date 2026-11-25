#!/usr/bin/env python3
"""Recover legacy BO event types in the exact, independently restored 0342 capture."""
import argparse
from collections import defaultdict
import importlib.util
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace

from core342_scope import BASE, IMAGE, WORK, load, sha
import kernel342_log as kernel
import ui_trace_log as ui


UI_EVENT = "SWEET UI254 E: "
ROW = re.compile(UI_EVENT + " ".join(rf"{key}=(?P<{key}>[0-9]+)" for key in ui.FIELDS["E"]))
KNOWN_IMAGE_STATE = "SpringBoard-cadence-window-missing-root-restored"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def module(file_name):
    spec = importlib.util.spec_from_file_location(file_name, WORK / "tools" / file_name)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def event_rows(text):
    lines = text.splitlines(keepends=True)
    events = {}
    locations = {}
    for index, line in enumerate(lines):
        start = line.find(UI_EVENT)
        if start < 0:
            continue
        match = ROW.fullmatch(line.rstrip("\n"), pos=start)
        require(match is not None, "malformed UI event")
        row = {key: int(value) for key, value in match.groupdict().items()}
        seq = row["seq"]
        require(seq == len(events) + 1, "UI event sequence discontinuity")
        events[seq] = row
        locations[seq] = (index, *match.span("kind"))
    return lines, events, locations


def correct_event_types(text):
    """BO rows require an enclosing GemNew API token; HID requires its enqueue."""
    lines, events, locations = event_rows(text)
    begins = {}
    ends = {}
    identity = lambda row: (row["pid"], row["id"])
    for row in events.values():
        if row["kind"] == 10 and row["flags"] == 66:
            table = begins
        elif row["kind"] == 11 and row["b"] == 66:
            table = ends
        else:
            continue
        key = identity(row)
        require(key not in table and all(key), "duplicate or invalid GemNew identity")
        table[key] = row
    require(bool(begins) and begins.keys() == ends.keys(), "incomplete GemNew envelope")

    phases = defaultdict(list)
    reuse = {}
    hid = []
    changes = {}
    for seq, row in events.items():
        kind = row["kind"]
        require(kind != 33, "unexpected already-canonical BO reuse event")
        if kind not in (31, 32):
            continue
        key = identity(row)
        if key in begins:
            begin, end = begins[key], ends[key]
            require(begin["seq"] < seq < end["seq"] and begin["tick"] <= row["tick"] <= end["tick"],
                    "BO event outside its GemNew envelope")
            if kind == 31:
                phases[key].append(row["flags"])
            else:
                require(key not in reuse and row["flags"] == 1, "duplicate or malformed BO reuse event")
                reuse[key] = seq
            changes[seq] = (kind, kind + 1)
        else:
            enqueue = events.get(seq - 1)
            require(kind == 31 and row["id"] >= 1 << 32 and row["pid"] and row["flags"] <= 3
                    and enqueue is not None and enqueue["kind"] == 5 and enqueue["tick"] <= row["tick"]
                    and (row["flags"] & 1) == enqueue["flags"],
                    "event cannot be uniquely identified as BO or HID")
            hid.append(seq)
    require(phases.keys() == begins.keys() and all(p == list(range(1, 7)) for p in phases.values()),
            "GemNew does not contain exactly six ordered BO phases")
    require(bool(hid) and bool(reuse), "expected HID and BO reuse records absent")

    for seq, (original, canonical) in changes.items():
        index, start, end = locations[seq]
        line = lines[index]
        require(line[start:end] == str(original), "unexpected event replacement location")
        lines[index] = line[:start] + str(canonical) + line[end:]
    canonical = "".join(lines)
    parsed = ui.parse(canonical)
    expected = [dict(row, kind=changes.get(seq, (row["kind"], row["kind"]))[1])
                for seq, row in events.items()]
    require(parsed["events"] == expected, "unexpected change to UI event fields")
    require(parsed["header"]["lost"] == 0 and not parsed["truncated_by_capacity"],
            "legacy UI stream recorded a loss")
    require([row["seq"] for row in parsed["queue_state_samples"]] == hid
            and all(row["state_consistent"] for row in parsed["queue_state_summary"]),
            "HID queue state qualification failed")
    for seq, (original, _) in changes.items():
        index, start, end = locations[seq]
        lines[index] = lines[index][:start] + str(original) + lines[index][end:]
    require("".join(lines) == text, "wire view is not reversible")
    return canonical, parsed, changes


def corroborate_bo_allocations(trace, allocation, driver):
    events = defaultdict(dict)
    for row in trace["events"]:
        if row["kind"] == 32:
            events[row["pid"], row["id"]][row["flags"]] = row
    header = trace["header"]
    ns = lambda tick: tick * header["numer"] // header["denom"]
    requests = defaultdict(list)
    for row in driver["rows"]:
        if row["selector"] == 66:
            key = (row["pid"], row["tid"], row["handle"], row["bytes"], row["result"])
            requests[key].append(row)
    used = set()
    require(allocation["coverage_qualified"] and not allocation["partial_count"],
            "legacy BO payload or capture did not qualify")
    for row in allocation["rows"]:
        stages = events[row["pid"], row["token"]]
        start, end = ns(stages[1]["tick"]), ns(stages[6]["tick"])
        key = (row["pid"], row["thread_id"], row["handle"], row["requested_bytes"], row["result"])
        matches = [call for call in requests[key] if call["first_ns"] <= start <= end <= call["last_ns"]]
        require(len(matches) == 1 and matches[0]["token"] not in used,
                "legacy BO event does not match one independent IO342 request")
        used.add(matches[0]["token"])
    require(len(used) == len(events) == allocation["complete_count"],
            "not every retyped allocation corroborated against IO342")
    return len(used)


def verify_image_wire():
    header = BASE / "kernel-prepared-v8/kernel-source/bsd/dev/gauguin_ui_trace.h"
    text = header.read_text()
    require(re.search(r"\bGUT_BO_ALLOC333=31,\s*GUT_BO_REUSE335=32\b", text),
            "frozen 0342 header does not declare the affected wire values")
    for variant, values in (("candidate", (31, 32)), ("baseline", (32, 33))):
        listing = (BASE / f"kernel-native-v4/{variant}-disassembly.log").read_text()
        for kind in values:
            pattern = rf"\bmov\s+w0, #0x{kind:x}\n(?:[^\n]+\n){{1,10}}[^\n]*\bb(?:l)?\s+_sweet_ui_trace_record\b"
            require(re.search(pattern, listing), f"{variant} object lacks the expected kind {kind} call")


def verify_receipts(execution, plan, result, ready):
    proof = load(execution / "independent-restore.json")
    claim = load(execution / "claim.json")
    observer = load(execution / "observer-process.json")
    require(result["state"] == KNOWN_IMAGE_STATE and result["ui_trace_error"] ==
            "ValueError('invalid HID queue snapshot flags/capacity')", "capture differs from the affected 0342 run")
    require(result["observer_exit"] == 0 and result["observer_group_clear"] and result["boot_attempts"] == 1
            and result["restored"] and result["independent_restore_verified"], "incomplete original execution or restoration")
    require(proof["state"] == "independently-verified-six-original-files-misc-and-empty-journal"
            and proof["install_plan_sha256"] == ready["install_plan_sha256"] == plan["install_plan_sha256"]
            and len(proof["files"]) == 6 and proof["journal_empty"] and proof["all_original_slot_bits_allocated"]
            and proof["misc_original_4096_bytes_match"], "independent restoration proof is incomplete")
    require(claim["approval_sha256"] == sha(BASE / "approval.json")
            and claim["trial_plan_sha256"] == sha(BASE / "trial-plan.json") == ready["trial_plan_sha256"]
            and observer["image_sha256"] == plan["image_sha256"] == IMAGE == sha(plan["image"]),
            "execution claim, grant or image mismatch")
    review = load(BASE / "final-review.json")
    require(review["ready_sha256"] == sha(BASE / "ready.json"), "review/ready mismatch")
    for item in (ready, review):
        for path, expected in item["input_pins"].items():
            require(sha(path) == expected, f"frozen input changed: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    out = parser.parse_args().out.resolve()
    require(out.is_relative_to(BASE) and not out.exists(), "output must be a new private directory")
    execution = BASE / "execution"
    plan = load(BASE / "trial-plan.json")
    result = load(execution / "result.json")
    ready = load(BASE / "ready.json")
    verify_receipts(execution, plan, result, ready)
    verify_image_wire()

    analyzer = module("analyze-core342.py")
    before = load(execution / "fresh-before/result.json")
    after = load(execution / "post-capture/result.json")
    restored = load(execution / "restored-capture/result.json")
    analyzer.LEGACY.static_compare(before, restored)
    tails = {}
    for path in analyzer.LEGACY.LOG_PATHS:
        old = (execution / "fresh-before" / before["files"][path]["output"]).read_bytes()
        new = (execution / "post-capture" / after["files"][path]["output"]).read_bytes()
        name = before["files"][path]["output"] + ".current"
        require(new.startswith(old) and (execution / name).read_bytes() == new[len(old):], "retained log prefix differs")
        tails[path] = name
    require((execution / tails[analyzer.LEGACY.SPRINGBOARD_LOG]).read_bytes() ==
            (execution / "springboard-new.log").read_bytes(), "SpringBoard tail alias differs")
    text = (execution / "kernel.log").read_text()
    raw = (execution / "kernel.log.bin").read_bytes()
    require(text.splitlines().count(plan["kernel_banner"]) == 1, "captured kernel identity differs")
    driver = kernel.parse(text, raw)
    require(driver["coverage_qualified"], "unaltered IO342 stream did not qualify")
    canonical, trace, changes = correct_event_types(text)
    allocation = module("analyze-bo-reuse-log.py").analyze(canonical, ui)
    corroborated = corroborate_bo_allocations(trace, allocation, driver)

    out.mkdir()
    outputs = ("kernel.log.bin", "independent-restore.json", "springboard-new.log",
               tails["/private/var/log/backboardd.log"])
    for name in outputs:
        os.link(execution / name, out / name)
    (out / "kernel.log").write_text(canonical)

    def parse_unaltered(view, captured):
        require(view == canonical and captured == raw, "unexpected replay input")
        return driver

    # Legacy parsers read the corrected view. IO342 uses its verified original
    # raw ring. All other frozen analyzer gates and phase arithmetic run unchanged.
    analyzer.KERNEL = SimpleNamespace(parse=parse_unaltered, join=kernel.join, summarize=kernel.summarize)
    reanalysis = {key: result[key] for key in ("restored", "independent_restore_verified",
        "springboard_log_prefix_preserved", "other_log_prefix_preserved", "observer_exit",
        "observer_group_clear", "boot_attempts", "attempted_userdata_bytes", "attempted_misc_bytes",
        "recovery_fallbacks")}
    analyzer.analyze_saved(out, plan, reanalysis, before, result["observer_exit"])
    reanalysis["read_only_redecode"] = {
        "original_result_sha256": sha(execution / "result.json"),
        "original_result_state": result["state"],
        "original_ring_sha256": sha(execution / "kernel.log.bin"),
        "original_text_sha256": sha(execution / "kernel.log"),
        "canonical_view_sha256": sha(out / "kernel.log"),
        "changed_kind_fields": len(changes),
        "preserved_HID_rows": len(trace["queue_state_samples"]),
        "allocation_calls_independently_corroborated": corroborated,
        "changes": {str(seq): pair for seq, pair in changes.items()},
        "device_commands": 0,
    }
    with (out / "result.json").open("x") as report:
        json.dump(reanalysis, report, indent=2)
        report.write("\n")
    print(json.dumps({key: reanalysis[key] for key in ("state", "collection_analysis",
        "legacy_observation_state", "kernel_IO_identity_analysis")}, indent=2))
    return 0 if reanalysis["state"] == "CR342-lossless-wait-execution-observed-root-restored" else 1


if __name__ == "__main__":
    raise SystemExit(main())
