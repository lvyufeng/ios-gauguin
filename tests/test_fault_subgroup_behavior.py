#!/usr/bin/env python3
"""Host behavioral comparison of the 0296 and 0297 gfw_faults bodies.

The real ``gfw_faults``, its real observation helpers, and the real
``ggrb_micro_settle``/``ggrb_ns`` pair are extracted verbatim from the pinned
0296 source and from the 0297 source (or from the 0297 patch applied in
memory).  Two independent executables are built: the baseline body and the
body compiled with the actual ``GFW_FAULT_TIMED`` macro/helper.  Every
hardware read, settle attempt, settle poll, logical clock read and delay is a
deterministic stub, so the test compares result, ordered event trace, and the
recorded software mutations over a finite case matrix.

This is mock behavior.  It makes no claim about real MMIO, real micro-settle
timing, real deadlines, or hardware safety.  The instrumented variant's two
measurement clock reads per timed expression use a separate clock, so they do
not appear in the hardware trace; the test only asserts their recorded
per-group call/tick counters.
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "bsd/dev/gauguin_gmu_board.c"
DEFAULT_BASELINE = Path(
    "/Users/baai/Project/ios-gauguin/research/tmp/"
    "gauguin-guard296-worktree-20261111/.deps-cache/p0-20261105/source296"
)
BASELINE_SHA256 = "5deaa9bd953e02f9279c22d2668efe6bcda9db7e8a56e0c02c5ba9b1eb311dd8"
DEFAULT_PATCHED = (
    ROOT / ".deps-cache/p0-20261105/source297"
)
PROFILE_BEGIN = "/* BEGIN GFW FAULT PROFILE:"
PROFILE_END = "/* END GFW FAULT PROFILE */"


def _env_board(name):
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value)
    return path if path.is_file() else path / NAME


def _baseline_path():
    return _env_board("FAULT_PROFILE_BASE") or (DEFAULT_BASELINE / NAME)


def _patched_candidates():
    override = _env_board("XNU_SOURCE")
    if override is not None:
        return [override]
    return [
        DEFAULT_PATCHED / NAME,
        ROOT / ".deps-cache/p0-20261105/source297-bsd-dev/gauguin_gmu_board.c",
    ]


def _apply_unified_diff(baseline, patch):
    """Apply a single-file unified diff, checking every context/removed line."""
    base = baseline.splitlines(keepends=True)
    lines = patch.splitlines(keepends=True)
    hunk = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    out = []
    position = 0
    index = 0
    while index < len(lines):
        match = hunk.match(lines[index])
        if not match:
            index += 1
            continue
        old_start = int(match.group(1))
        old_count = int(match.group(2) or "1")
        start = old_start - 1
        if start < position:
            raise AssertionError("overlapping hunk at patch line %d" % (index + 1))
        out.extend(base[position:start])
        position = start
        consumed = 0
        index += 1
        while index < len(lines):
            line = lines[index]
            if line.startswith("@@"):
                break
            if line.startswith("\\"):
                index += 1
                continue
            if not line or line[0] not in " +-":
                raise AssertionError(
                    "unexpected patch line %d: %r" % (index + 1, line)
                )
            if line[0] in " -":
                if position >= len(base):
                    raise AssertionError("patch removes past end of baseline")
                expected = line[1:].rstrip("\n")
                actual = base[position].rstrip("\n")
                if actual != expected:
                    raise AssertionError(
                        "patch removes different baseline line %d:\n"
                        "  patch %r\n  base  %r" % (position + 1, expected, actual)
                    )
                consumed += 1
                if line[0] == " ":
                    out.append(base[position])
                position += 1
            else:
                out.append(line[1:])
            index += 1
        if consumed != old_count:
            raise AssertionError(
                "hunk at patch line %d consumed %d baseline lines, expected %d"
                % (index + 1, consumed, old_count)
            )
    out.extend(base[position:])
    return "".join(out)


def _brace_end(text, opening):
    depth = 0
    index = opening
    while index < len(text):
        char = text[index]
        if char in "\"'":
            quote = char
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    index += 2
                    continue
                if text[index] == quote:
                    break
                index += 1
        elif char == "/" and text.startswith("//", index):
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline
            continue
        elif char == "/" and text.startswith("/*", index):
            close = text.find("*/", index + 2)
            if close < 0:
                raise AssertionError("unterminated comment while extracting")
            index = close + 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise AssertionError("unbalanced braces while extracting")


def _extract_function(source, name):
    pattern = re.compile(
        r"^\s*[A-Za-z_][A-Za-z0-9_ \t*]*\b" + re.escape(name)
        + r"\s*\([^\n;]*\)\s*\{", re.MULTILINE
    )
    match = pattern.search(source)
    if not match:
        raise AssertionError("function %s not found in source" % name)
    opening = source.index("{", match.start())
    closing = _brace_end(source, opening)
    return source[match.start():closing + 1]


def _external(function):
    return re.sub(r"^static\s+", "", function, count=1)


def _without_storage(function):
    return re.sub(r"\bstatic\s+", "", function)


def _marked(source):
    begin = source.find(PROFILE_BEGIN)
    end = source.find(PROFILE_END, begin)
    if begin < 0 or end < 0:
        raise AssertionError("0297 fault profile block not found")
    end += len(PROFILE_END)
    line_end = source.find("\n", end)
    return source[begin:len(source) if line_end < 0 else line_end + 1]


def _find_patch():
    override = os.environ.get("FAULT_PROFILE_PATCH")
    if override:
        path = Path(override)
        return path if path.is_file() else None
    matches = sorted((ROOT / "xnu/patches").glob("*fault-subgroup-profiling*.patch"))
    return matches[-1] if matches else None


class _Sources:
    def __init__(self):
        path = _baseline_path()
        if not path.is_file():
            raise unittest.SkipTest("0296 baseline source not found: %s" % path)
        self.baseline = path.read_text()
        actual = hashlib.sha256(self.baseline.encode()).hexdigest()
        if actual != BASELINE_SHA256:
            raise AssertionError("baseline is not the pinned 0296 source")
        self.baseline_origin = str(path)
        self.patched = None
        self.patched_origin = None
        for candidate in _patched_candidates():
            if candidate.is_file():
                text = candidate.read_text()
                if PROFILE_BEGIN in text and "GFW_FAULT_TIMED(" in text:
                    self.patched = text
                    self.patched_origin = str(candidate)
                    break
        if self.patched is None:
            patch = _find_patch()
            if patch is None:
                raise unittest.SkipTest(
                    "no 0297 source and no fault-subgroup patch found"
                )
            self.patched = _apply_unified_diff(self.baseline, patch.read_text())
            self.patched_origin = "%s applied to %s" % (patch, path)
        if PROFILE_BEGIN not in self.patched or "GFW_FAULT_TIMED(" not in self.patched:
            raise AssertionError("0297 source lacks the fault profile block")


def _receipt():
    return {
        "cr0_after": 0x12345678,
        "micro_after": 0x2370,
        "bank": [0, 1],
        "slot": [0, 1],
        "sctlr": [0x30d00800, 0x30d00801],
        "actlr": [0x10, 0x11],
        "tcr2": 0x20,
        "tcr": 0x30,
        "mair0": 0x40,
        "mair1": 0x50,
        "s2cr_after": [0x60, 0x61],
        "smr_after": [0x70, 0x71],
        "ttbr0": [0x100000000, 0x200000000],
        "ttbr1": [0x300000000, 0x400000000],
        "stream_match": 1,
    }


def _base_case(name):
    receipt = _receipt()
    return {
        "name": name,
        "s": receipt,
        "gfsr": 0,
        "cr0": receipt["cr0_after"],
        "micro_after": receipt["micro_after"],
        "micro_seq": [receipt["micro_after"]],
        "fsr": [0, 0],
        "gpu_probe": 0,
        "ggb_state": 0,
        "ggb_halt": 0,
        "ggb_phase": 0,
        "ggb_probe_active": 0,
        "ggb_probe_hole": 0,
        "ggb_probe_bank": 0,
        "ggrb_started": 0,
        "ggrb_state": 0,
        "board_state": 2,  # GMB_READY
        "wdt_ok": 1,
        "thread_ok": 1,
        "ao_present": 1,
        "host_value": 0x12345678,
        "ao_value": 0,
        "ggrb_end": (1 << 64) - 1,
        "operation_end_ns": 10 ** 9,
        "clock_start_ns": 0,
        "clock_step_ns": 0,
        "read_step_ns": 0,
        "clock_tick_ns": 0,
        "fail_ordinal": -1,
        "override_ordinal": -1,
        "override_value": 0,
    }


def _read_layout(case):
    """Return (kind, offset, expected-value) for the no-settle success path."""
    s = case["s"]
    layout = [
        ("r32", 0x48, case["gfsr"]),
        ("r32", 0x0, case["cr0"]),
        ("r32", 0x6000, case["micro_after"]),
    ]
    for n in range(2):
        cb = 0x8000 + 0x1000 * s["bank"][n]
        layout.extend(
            [
                ("r32", cb + 0x58, case["fsr"][n]),
                ("r32", cb, s["sctlr"][n]),
                ("r32", cb + 4, s["actlr"][n]),
                ("r32", cb + 0x10, s["tcr2"]),
                ("r32", cb + 0x30, s["tcr"]),
                ("r32", cb + 0x38, s["mair0"]),
                ("r32", cb + 0x3C, s["mair1"]),
                ("r32", 0x1000 + 4 * s["bank"][n], 0x1F300),
                ("r32", 0x1800 + 4 * s["bank"][n], 1),
                ("r32", 0xC00 + 4 * s["slot"][n], s["s2cr_after"][n]),
            ]
        )
        if s["stream_match"]:
            layout.append(("r32", 0x800 + 4 * s["slot"][n], s["smr_after"][n]))
        layout.extend(
            [
                ("r64", cb + 0x20, s["ttbr0"][n]),
                ("r64", cb + 0x28, s["ttbr1"][n]),
            ]
        )
    return layout


def _cases():
    cases = []

    success = _base_case("success_full")
    cases.append(success)

    absent = _base_case("success_absent_ao")
    absent["ao_present"] = 0
    absent["ao_value"] = 0xFFFFFFFF
    cases.append(absent)

    no_stream = _base_case("success_without_stream_match")
    no_stream["s"]["stream_match"] = 0
    cases.append(no_stream)

    probe_ok = _base_case("gpu_probe_own_halt_accepts_bit4")
    probe_ok.update(
        {
            "gpu_probe": 1,
            "ggb_state": 1,
            "ggb_halt": 1,
            "ggb_phase": 5,
            "ggb_probe_active": 1,
            "ggb_probe_hole": 1,
            "ggb_probe_bank": 0,
            "micro_after": 0x2274,
            "micro_seq": [0x2274],
            "fsr": [2, 0],
        }
    )
    cases.append(probe_ok)

    probe_other = _base_case("gpu_probe_own_tf_other_bank_fails")
    probe_other.update(
        {
            "gpu_probe": 1,
            "ggb_state": 1,
            "ggb_halt": 1,
            "ggb_phase": 5,
            "ggb_probe_active": 1,
            "ggb_probe_hole": 1,
            "ggb_probe_bank": 0,
            "micro_after": 0x2274,
            "micro_seq": [0x2274],
            "fsr": [0, 2],
        }
    )
    cases.append(probe_other)

    # Every hardware reader on the full success path, failed once.
    layout = _read_layout(success)
    for ordinal in range(len(layout)):
        case = _base_case("read_fail_%02d" % ordinal)
        case["fail_ordinal"] = ordinal
        cases.append(case)

    # Every checked field, with one invalid value in each bank and globally.
    s = success["s"]
    checks = [
        (0, "global_gfsr_fault", 1),
        (1, "global_cr0_mismatch", 0xDEADBEEF),
        (2, "global_micro_mismatch_no_settle", 0x2270),
        (3, "bank0_fsr_fault", 0x2),
        (4, "bank0_sctlr_mismatch", s["sctlr"][0] ^ 1),
        (5, "bank0_actlr_mismatch", s["actlr"][0] ^ 1),
        (6, "bank0_tcr2_mismatch", s["tcr2"] ^ 1),
        (7, "bank0_tcr_mismatch", s["tcr"] ^ 1),
        (8, "bank0_mair0_mismatch", s["mair0"] ^ 1),
        (9, "bank0_mair1_mismatch", s["mair1"] ^ 1),
        (10, "bank0_idr_mismatch", 0),
        (11, "bank0_scr_mismatch", 0),
        (12, "bank0_s2cr_mismatch", s["s2cr_after"][0] ^ 1),
        (13, "bank0_smr_mismatch", s["smr_after"][0] ^ 1),
        (14, "bank0_ttbr0_mismatch", 0),
        (15, "bank0_ttbr1_mismatch", 0),
        (16, "bank1_fsr_fault", 0x2),
        (17, "bank1_sctlr_mismatch", s["sctlr"][1] ^ 1),
        (18, "bank1_actlr_mismatch", s["actlr"][1] ^ 1),
        (19, "bank1_tcr2_mismatch", s["tcr2"] ^ 3),
        (20, "bank1_tcr_mismatch", s["tcr"] ^ 3),
        (21, "bank1_mair0_mismatch", s["mair0"] ^ 3),
        (22, "bank1_mair1_mismatch", s["mair1"] ^ 3),
        (23, "bank1_idr_mismatch", 0),
        (24, "bank1_scr_mismatch", 0),
        (25, "bank1_s2cr_mismatch", s["s2cr_after"][1] ^ 1),
        (26, "bank1_smr_mismatch", s["smr_after"][1] ^ 1),
        (27, "bank1_ttbr0_mismatch", 0),
        (28, "bank1_ttbr1_mismatch", 0),
    ]
    for ordinal, name, value in checks:
        case = _base_case(name)
        case["override_ordinal"] = ordinal
        case["override_value"] = value
        cases.append(case)

    for name, field, index, value in [
        ("bank0_invalid_bank", "bank", 0, 8),
        ("bank1_invalid_bank", "bank", 1, 8),
        ("bank0_invalid_slot", "slot", 0, 128),
        ("bank1_invalid_slot", "slot", 1, 128),
    ]:
        case = _base_case(name)
        case["s"][field][index] = value
        cases.append(case)

    for name, key, value in [
        ("host_all_ones", "host_value", 0xFFFFFFFF),
        ("host_bit15", "host_value", 0x8000),
        ("ao_all_ones", "ao_value", 0xFFFFFFFF),
        ("ao_bit0", "ao_value", 0x1),
        ("ao_bit3", "ao_value", 0x8),
        ("ao_bit5", "ao_value", 0x20),
    ]:
        case = _base_case(name)
        case[key] = value
        cases.append(case)

    # Real settle helper paths.  ggrb_micro_settle only engages for a
    # non-probe BUSY runtime with the exact 0x2270 -> 0x2370 predicate.
    settle = _base_case("settle_transient_success")
    settle.update(
        {
            "micro_seq": [0x2270, 0x2370, 0x2370],
            "ggrb_started": 1,
            "ggrb_state": 2,
        }
    )
    cases.append(settle)

    recheck = _base_case("settle_transient_recheck_success")
    recheck.update(
        {
            "micro_seq": [0x2270, 0x2370, 0x2270, 0x2370, 0x2370],
            "ggrb_started": 1,
            "ggrb_state": 2,
        }
    )
    cases.append(recheck)

    unexpected = _base_case("settle_unexpected_value_fails")
    unexpected.update(
        {
            "micro_seq": [0x2270, 0x2274],
            "ggrb_started": 1,
            "ggrb_state": 2,
        }
    )
    cases.append(unexpected)

    failing_read = _base_case("settle_poll_read_fails")
    failing_read.update(
        {
            "micro_seq": [0x2270, 0x2270],
            "ggrb_started": 1,
            "ggrb_state": 2,
            "fail_ordinal": 3,
        }
    )
    cases.append(failing_read)

    exhausted = _base_case("settle_deadline_exhausted_inside")
    exhausted.update(
        {
            "micro_seq": [0x2270, 0x2270, 0x2270],
            "ggrb_started": 1,
            "ggrb_state": 2,
            "clock_step_ns": 4000,
            "operation_end_ns": 10000,
        }
    )
    cases.append(exhausted)

    final_expiry = _base_case("settle_final_deadline_after_recovery")
    final_expiry.update(
        {
            "micro_seq": [0x2270, 0x2370, 0x2370],
            "ggrb_started": 1,
            "ggrb_state": 2,
            "read_step_ns": 100,
            "operation_end_ns": 1000,
        }
    )
    cases.append(final_expiry)

    # The clock ticks on each logical mach_absolute_time() read.  The settle
    # loop observes 0x2370 before its last deadline check, then the restart
    # label's own check observes the next tick and expires.
    top_expiry = _base_case("settle_top_deadline_after_recovery")
    top_expiry.update(
        {
            "micro_seq": [0x2270, 0x2370],
            "ggrb_started": 1,
            "ggrb_state": 2,
            "clock_tick_ns": 1,
            "operation_end_ns": 8,
        }
    )
    cases.append(top_expiry)

    return cases


def _c_uint64(value):
    return "UINT64_MAX" if value == (1 << 64) - 1 else "UINT64_C(%d)" % value


def _c_int_array(values):
    return "{" + ",".join(str(v) for v in values) + "}"


def _c_case(case):
    s = case["s"]
    receipt = (
        ".s={.cr0_after=UINT32_C(%d),.micro_after=UINT32_C(%d),"
        ".bank=%s,.slot=%s,.sctlr=%s,.actlr=%s,"
        ".tcr2=UINT32_C(%d),.tcr=UINT32_C(%d),"
        ".mair0=UINT32_C(%d),.mair1=UINT32_C(%d),"
        ".s2cr_after=%s,.smr_after=%s,"
        ".ttbr0={UINT64_C(%d),UINT64_C(%d)},"
        ".ttbr1={UINT64_C(%d),UINT64_C(%d)},.stream_match=%d}"
        % (
            s["cr0_after"],
            s["micro_after"],
            _c_int_array(s["bank"]),
            _c_int_array(s["slot"]),
            _c_int_array(s["sctlr"]),
            _c_int_array(s["actlr"]),
            s["tcr2"],
            s["tcr"],
            s["mair0"],
            s["mair1"],
            _c_int_array(s["s2cr_after"]),
            _c_int_array(s["smr_after"]),
            s["ttbr0"][0],
            s["ttbr0"][1],
            s["ttbr1"][0],
            s["ttbr1"][1],
            s["stream_match"],
        )
    )
    fields = [
        ".name=\"%s\"" % case["name"],
        receipt,
        ".gfsr=UINT32_C(%d)" % case["gfsr"],
        ".cr0=UINT32_C(%d)" % case["cr0"],
        ".micro_after=UINT32_C(%d)" % case["micro_after"],
        ".micro_seq=%s" % _c_int_array(case["micro_seq"]),
        ".micro_len=%d" % len(case["micro_seq"]),
        ".fsr=%s" % _c_int_array(case["fsr"]),
        ".gpu_probe=%d" % case["gpu_probe"],
        ".ggb_state=%d" % case["ggb_state"],
        ".ggb_halt=%d" % case["ggb_halt"],
        ".ggb_phase=%d" % case["ggb_phase"],
        ".ggb_probe_active=%d" % case["ggb_probe_active"],
        ".ggb_probe_hole=%d" % case["ggb_probe_hole"],
        ".ggb_probe_bank=%d" % case["ggb_probe_bank"],
        ".ggrb_started=%d" % case["ggrb_started"],
        ".ggrb_state=%d" % case["ggrb_state"],
        ".board_state=%d" % case["board_state"],
        ".wdt_ok=%d" % case["wdt_ok"],
        ".thread_ok=%d" % case["thread_ok"],
        ".ao_present=%d" % case["ao_present"],
        ".host_value=UINT32_C(%d)" % case["host_value"],
        ".ao_value=UINT32_C(%d)" % case["ao_value"],
        ".ggrb_end=%s" % _c_uint64(case["ggrb_end"]),
        ".operation_end_ns=%s" % _c_uint64(case["operation_end_ns"]),
        ".clock_start_ns=%s" % _c_uint64(case["clock_start_ns"]),
        ".clock_step_ns=%s" % _c_uint64(case["clock_step_ns"]),
        ".read_step_ns=%s" % _c_uint64(case["read_step_ns"]),
        ".clock_tick_ns=%s" % _c_uint64(case["clock_tick_ns"]),
        ".fail_ordinal=%d" % case["fail_ordinal"],
        ".override_ordinal=%d" % case["override_ordinal"],
        ".override_value=UINT32_C(%d)" % case["override_value"],
    ]
    return "    {" + ",".join(fields) + "},\n"


HARNESS_H = r'''
#ifndef FAULT_BEHAVIOR_H
#define FAULT_BEHAVIOR_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define GSM_BANKS 8u
#define GSM_STREAMS 128u
#define GSM_FSR_FAULT_MASK UINT32_C(0xc00001fe)
#define GMF_AO 1
#define GMF_WINDOWS 6
#define GMB_READY 2
#define GGR_BUSY 2
#define GAUGUIN_WDT_CLOCK_HZ 19200000u
#define GMB_MIN (3u * GAUGUIN_WDT_CLOCK_HZ)

typedef uint64_t vm_offset_t;

enum ggs_phase {
    GGS_IDLE, GGS_CAPTURE, GGS_RESOLVE, GGS_PREPARE, GGS_HALT,
    GGS_BANK, GGS_ATOS, GGS_RESTORE, GGS_FINAL, GGS_DONE
};

struct gsm_receipt {
    uint32_t id0,id1,id2,cr0_before,cr0_after,micro_before,micro_after;
    uint32_t groups,banks,s2banks,ias,oas,stream_match;
    uint32_t slot[2],bank[2],asid[2],smr_before[2],s2cr_before[2];
    uint32_t smr_after[2],s2cr_after[2],sctlr[2],actlr[2];
    uint64_t ttbr0[2],ttbr1[2];
    uint32_t tcr,tcr2,mair0,mair1,writes,polls,translations,mapped_pages;
};
struct gmb_receipt_min { struct gsm_receipt smmu; };
struct gfw_micro_wait { uint64_t start_ns,end_ns;uint32_t delays;bool started; };
struct gfw_micro_sample {
    uint32_t attempts,recovered,polls,initial,current,expected,mask,elapsed_us;
    uint32_t rechecks,expired;
};
struct gfw_read_sample {
    uint32_t kind,space,offset,ok;
    uint64_t value;
};
struct gmb_firmware_receipt {
    uint32_t reset,gx,irq[3],gfsr,fsr[2],ao_status,host_info;
    uint32_t release_attempted,oob_attempted,phase;
};
struct ggb_context_min {
    uint32_t state,phase,halt_attempted,probe_active,probe_hole,probe_bank;
};
struct ggrb_context_min {
    uint32_t state;
    uint64_t operation_end_ns;
};

struct fault_case {
    const char *name;
    struct gsm_receipt s;
    uint32_t gfsr,cr0,micro_after;
    uint32_t micro_seq[8];
    uint32_t micro_len;
    uint32_t fsr[2];
    uint32_t gpu_probe,ggb_state,ggb_halt,ggb_phase;
    uint32_t ggb_probe_active,ggb_probe_hole,ggb_probe_bank;
    uint32_t ggrb_started,ggrb_state,board_state,wdt_ok,thread_ok,ao_present;
    uint32_t host_value,ao_value;
    uint64_t ggrb_end,operation_end_ns,clock_start_ns;
    uint64_t clock_step_ns,read_step_ns,clock_tick_ns;
    int fail_ordinal;
    int override_ordinal;
    uint32_t override_value;
};

extern struct gmb_receipt_min gmb_work;
extern struct gmb_firmware_receipt gfw_work;
extern struct gfw_micro_sample gfw_micro_sample;
extern struct gfw_read_sample gfw_read_sample;
extern struct ggb_context_min ggb_context;
extern struct ggrb_context_min ggrb_context;
extern vm_offset_t gmb_reset;
extern vm_offset_t gfw_map[GMF_WINDOWS];
extern unsigned ggrb_started;
extern uint64_t ggrb_end;

bool gmb_read32(void *cookie,uint32_t off,uint32_t *out);
bool gmb_read64(void *cookie,uint32_t off,uint64_t *out);
uint32_t gfw_load32(vm_offset_t address);
uint64_t mach_absolute_time(void);
void absolutetime_to_nanoseconds(uint64_t ticks,uint64_t *ns);
void IODelay(unsigned us);
bool gmb_thread(void);
int sweet_gmu_board_state(void);
bool gauguin_wdt_lease_check_budget(uint64_t minimum);
bool gfw_observe32(void *cookie,uint32_t off,uint32_t *out);
bool gfw_observe64(void *cookie,uint32_t off,uint64_t *out);
uint32_t gfw_observe_load(uint32_t space,uint32_t off,vm_offset_t address);
void trace_load(uint32_t space,uint32_t off,uint32_t value);
bool gfw_faults(bool gpu_probe);
bool ggrb_micro_settle_impl(bool gpu_probe,uint32_t expected,uint32_t mask,
    uint32_t current,struct gfw_micro_wait *wait);
bool ggrb_micro_settle(bool gpu_probe,uint32_t expected,uint32_t mask,
    uint32_t current,struct gfw_micro_wait *wait);
uint64_t ggrb_ns(void *cookie);
uint64_t gfw_profile_clock(void);
uint64_t fault_profile_calls(unsigned group);
uint64_t fault_profile_ticks(unsigned group);
unsigned fault_profile_groups(void);
void fault_profile_reset(void);
void fault_profile_invalid_checks(void);
#endif
'''


HARNESS_C = r'''
#include "fault_harness.h"
#include <inttypes.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include "cases.h"

struct gmb_receipt_min gmb_work;
struct gmb_firmware_receipt gfw_work;
struct gfw_micro_sample gfw_micro_sample;
struct gfw_read_sample gfw_read_sample;
struct ggb_context_min ggb_context;
struct ggrb_context_min ggrb_context;
vm_offset_t gmb_reset = UINT64_C(0x10000000);
vm_offset_t gfw_map[GMF_WINDOWS];
unsigned ggrb_started;
uint64_t ggrb_end;

static const struct fault_case *current;
static uint64_t logical_ns;
static uint64_t profile_ns;
static unsigned hw_ordinal;
static unsigned micro_occurrence;
static unsigned settle_depth;
static bool trace_on;

static void trace(const char *format,...)
{
    va_list args;
    if(!trace_on)return;
    va_start(args,format);
    vprintf(format,args);
    va_end(args);
    putchar('\n');
}

void trace_load(uint32_t space,uint32_t off,uint32_t value)
{
    trace("LOAD space=%u off=%04x val=%08x",space,off,value);
}

static uint64_t next_profile_clock(void)
{
    profile_ns += 10;
    return profile_ns;
}

uint64_t gfw_profile_clock(void)
{
    return next_profile_clock();
}

static uint32_t micro_value(void)
{
    unsigned index=micro_occurrence++;
    if(index<current->micro_len)return current->micro_seq[index];
    if(current->micro_len)return current->micro_seq[current->micro_len-1];
    return current->micro_after;
}

static uint32_t default_read32(uint32_t off)
{
    const struct gsm_receipt *s=&current->s;
    if(off==UINT32_C(0x48))return current->gfsr;
    if(off==0)return current->cr0;
    if(off==UINT32_C(0x6000))return micro_value();
    for(unsigned n=0;n<2;n++){
        uint32_t cb=UINT32_C(0x8000)+UINT32_C(0x1000)*s->bank[n];
        if(off==cb+UINT32_C(0x58))return current->fsr[n];
        if(off==cb)return s->sctlr[n];
        if(off==cb+4)return s->actlr[n];
        if(off==cb+UINT32_C(0x10))return s->tcr2;
        if(off==cb+UINT32_C(0x30))return s->tcr;
        if(off==cb+UINT32_C(0x38))return s->mair0;
        if(off==cb+UINT32_C(0x3c))return s->mair1;
        if(off==UINT32_C(0x1000)+4*s->bank[n])return UINT32_C(0x1f300);
        if(off==UINT32_C(0x1800)+4*s->bank[n])return 1;
        if(off==UINT32_C(0xc00)+4*s->slot[n])return s->s2cr_after[n];
        if(s->stream_match&&off==UINT32_C(0x800)+4*s->slot[n])
            return s->smr_after[n];
    }
    return 0;
}

static uint64_t default_read64(uint32_t off)
{
    const struct gsm_receipt *s=&current->s;
    for(unsigned n=0;n<2;n++){
        uint32_t cb=UINT32_C(0x8000)+UINT32_C(0x1000)*s->bank[n];
        if(off==cb+UINT32_C(0x20))return s->ttbr0[n];
        if(off==cb+UINT32_C(0x28))return s->ttbr1[n];
    }
    return 0;
}

static bool read_fails(unsigned ordinal)
{
    return current->fail_ordinal>=0&&ordinal==(unsigned)current->fail_ordinal;
}

bool gmb_read32(void *cookie,uint32_t off,uint32_t *out)
{
    (void)cookie;
    unsigned ordinal=hw_ordinal++;
    bool ok=!read_fails(ordinal);
    uint32_t value=0;
    if(off==UINT32_C(0x6000)||ok){
        if(ok){
            if(ordinal==(unsigned)current->override_ordinal)
                value=current->override_value;
            else
                value=default_read32(off);
        }
    }
    if(ok&&out)*out=value;
    trace("R32 off=%08x ok=%u val=%08x",off,ok?1u:0u,value);
    logical_ns+=current->read_step_ns;
    return ok;
}

bool gmb_read64(void *cookie,uint32_t off,uint64_t *out)
{
    (void)cookie;
    unsigned ordinal=hw_ordinal++;
    bool ok=!read_fails(ordinal);
    uint64_t value=0;
    if(ok){
        if(ordinal==(unsigned)current->override_ordinal)
            value=current->override_value;
        else
            value=default_read64(off);
        if(out)*out=value;
    }
    trace("R64 off=%08x ok=%u val=%016" PRIx64,off,ok?1u:0u,value);
    logical_ns+=current->read_step_ns;
    return ok;
}

uint32_t gfw_load32(vm_offset_t address)
{
    if(address==gmb_reset+UINT64_C(0x2648)){
        trace_load(1,UINT32_C(0x2648),current->host_value);
        return current->host_value;
    }
    if(gfw_map[GMF_AO]&&address==gfw_map[GMF_AO]+UINT64_C(0x2c14)){
        trace_load(2,UINT32_C(0x2c14),current->ao_value);
        return current->ao_value;
    }
    return UINT32_C(0xdeadbeef);
}

uint64_t mach_absolute_time(void)
{
    uint64_t now=logical_ns;
    trace("CLOCK ns=%" PRIu64,now);
    logical_ns+=current->clock_tick_ns;
    return now;
}

void absolutetime_to_nanoseconds(uint64_t ticks,uint64_t *ns)
{
    *ns=ticks;
}

void IODelay(unsigned us)
{
    trace("DELAY us=%u ns=%" PRIu64,us,logical_ns);
    logical_ns+=current->clock_step_ns;
}

bool gmb_thread(void)
{
    return current->thread_ok!=0;
}

int sweet_gmu_board_state(void)
{
    return (int)current->board_state;
}

bool gauguin_wdt_lease_check_budget(uint64_t minimum)
{
    (void)minimum;
    trace("WDT ok=%u",current->wdt_ok?1u:0u);
    return current->wdt_ok!=0;
}

bool ggrb_micro_settle(bool gpu_probe,uint32_t expected,uint32_t mask,
    uint32_t current_value,struct gfw_micro_wait *wait)
{
    (void)settle_depth;
    trace("SETTLE_ENTER expected=%08x mask=%08x current=%08x",
        expected,mask,current_value);
    bool recovered=ggrb_micro_settle_impl(gpu_probe,expected,mask,
        current_value,wait);
    trace("SETTLE_EXIT recovered=%u",recovered?1u:0u);
    return recovered;
}

static void print_mutations(void)
{
    printf("MUT gfsr=%08x fsr0=%08x fsr1=%08x host=%08x ao=%08x\n",
        gfw_work.gfsr,gfw_work.fsr[0],gfw_work.fsr[1],
        gfw_work.host_info,gfw_work.ao_status);
    printf("READ kind=%u space=%u off=%04x ok=%u val=%016" PRIx64 "\n",
        gfw_read_sample.kind,gfw_read_sample.space,gfw_read_sample.offset,
        gfw_read_sample.ok,gfw_read_sample.value);
    printf("MICRO attempts=%u recovered=%u polls=%u initial=%08x current=%08x "
        "expected=%08x mask=%08x elapsed_us=%u rechecks=%u expired=%u\n",
        gfw_micro_sample.attempts,gfw_micro_sample.recovered,
        gfw_micro_sample.polls,gfw_micro_sample.initial,
        gfw_micro_sample.current,gfw_micro_sample.expected,
        gfw_micro_sample.mask,gfw_micro_sample.elapsed_us,
        gfw_micro_sample.rechecks,gfw_micro_sample.expired);
}

static void reset_case(const struct fault_case *case_data)
{
    current=case_data;
    gmb_work.smmu=case_data->s;
    gfw_work=(struct gmb_firmware_receipt){0};
    gfw_micro_sample=(struct gfw_micro_sample){0};
    gfw_read_sample=(struct gfw_read_sample){0};
    ggb_context=(struct ggb_context_min){
        .state=case_data->ggb_state,
        .phase=case_data->ggb_phase,
        .halt_attempted=case_data->ggb_halt,
        .probe_active=case_data->ggb_probe_active,
        .probe_hole=case_data->ggb_probe_hole,
        .probe_bank=case_data->ggb_probe_bank,
    };
    ggrb_started=case_data->ggrb_started;
    ggrb_context=(struct ggrb_context_min){
        .state=case_data->ggrb_state,
        .operation_end_ns=case_data->operation_end_ns,
    };
    ggrb_end=case_data->ggrb_end;
    gmb_reset=UINT64_C(0x10000000);
    for(unsigned i=0;i<GMF_WINDOWS;i++)gfw_map[i]=0;
    if(case_data->ao_present)
        gfw_map[GMF_AO]=UINT64_C(0x20000000);
    logical_ns=case_data->clock_start_ns;
    profile_ns=0;
    hw_ordinal=0;
    micro_occurrence=0;
    settle_depth=0;
    trace_on=false;
#ifdef PATCHED
    fault_profile_reset();
#endif
}

int main(void)
{
    for(unsigned i=0;i<CASE_COUNT;i++){
        const struct fault_case *case_data=&cases[i];
        reset_case(case_data);
        printf("CASE %s\n",case_data->name);
        trace_on=true;
        bool result=gfw_faults(case_data->gpu_probe!=0);
        trace_on=false;
        printf("RESULT %u\n",result?1u:0u);
        print_mutations();
#ifdef PATCHED
        for(unsigned group=0;group<fault_profile_groups();group++)
            printf("PROFILE group=%u calls=%" PRIu64 " ticks=%" PRIu64 "\n",
                group,fault_profile_calls(group),fault_profile_ticks(group));
        fault_profile_invalid_checks();
#endif
    }
    return 0;
}
'''


SETTLE_C = r'''
#include "fault_harness.h"
@@GGRB_NS@@
@@SETTLE@@
'''


FAULT_C = r'''
#include "fault_harness.h"
#include <inttypes.h>
#include <stdio.h>
#ifdef PATCHED
uint64_t fault_profile_calls(unsigned group)
{
    return group<GFW_FAULT_GROUPS?gfw_fault_perf[group].calls:0;
}
uint64_t fault_profile_ticks(unsigned group)
{
    return group<GFW_FAULT_GROUPS?gfw_fault_perf[group].ticks:0;
}
unsigned fault_profile_groups(void)
{
    return GFW_FAULT_GROUPS;
}
void fault_profile_reset(void)
{
    for(unsigned group=0;group<GFW_FAULT_GROUPS;group++)
        gfw_fault_perf[group]=(struct gfw_fault_perf){0};
}
void fault_profile_invalid_checks(void)
{
    unsigned group=GFW_FAULT_AO;
    uint64_t calls=gfw_fault_perf[group].calls;
    uint64_t ticks=gfw_fault_perf[group].ticks;
    gfw_fault_profile_time(GFW_FAULT_GROUPS,10,20);
    gfw_fault_profile_time(GFW_FAULT_GROUPS+1000u,10,20);
    gfw_fault_profile_time(group,20,10);
    gfw_fault_profile_time(group,UINT64_MAX,0);
    uint64_t invalid_calls=gfw_fault_perf[group].calls-calls;
    uint64_t invalid_ticks=gfw_fault_perf[group].ticks-ticks;
    gfw_fault_profile_time(group,100,100);
    uint64_t equal_calls=gfw_fault_perf[group].calls-calls-invalid_calls;
    uint64_t equal_ticks=gfw_fault_perf[group].ticks-ticks-invalid_ticks;
    gfw_fault_profile_time(group,100,125);
    uint64_t normal_calls=gfw_fault_perf[group].calls-calls
        -invalid_calls-equal_calls;
    uint64_t normal_ticks=gfw_fault_perf[group].ticks-ticks
        -invalid_ticks-equal_ticks;
    printf("PROFILE_INVALID invalid_calls=%" PRIu64 " invalid_ticks=%" PRIu64
        " equal_calls=%" PRIu64 " equal_ticks=%" PRIu64
        " normal_calls=%" PRIu64 " normal_ticks=%" PRIu64 "\n",
        invalid_calls,invalid_ticks,equal_calls,equal_ticks,
        normal_calls,normal_ticks);
}
#endif
'''


def _build_and_run(sources, cases, work):
    baseline_faults = _extract_function(sources.baseline, "gfw_faults")
    observe32 = _extract_function(sources.baseline, "gfw_observe32")
    observe64 = _extract_function(sources.baseline, "gfw_observe64")
    observe_load = _extract_function(sources.baseline, "gfw_observe_load")
    settle_body = _extract_function(sources.baseline, "ggrb_micro_settle")
    ns_body = _extract_function(sources.baseline, "ggrb_ns")
    settle_body = _without_storage(settle_body).replace(
        "ggrb_micro_settle(", "ggrb_micro_settle_impl(", 1
    )
    ns_body = _without_storage(ns_body)

    patched_faults = _external(_extract_function(sources.patched, "gfw_faults"))
    baseline_faults = _external(baseline_faults)

    files = {
        "fault_harness.h": HARNESS_H,
        "harness.c": HARNESS_C,
        "observe.c": (
            "#include \"fault_harness.h\"\n"
            + _without_storage(observe32) + "\n"
            + _without_storage(observe64) + "\n"
            + _without_storage(observe_load) + "\n"
        ),
        "settle.c": SETTLE_C
        .replace("@@GGRB_NS@@", ns_body)
        .replace("@@SETTLE@@", settle_body),
        "cases.h": "#include \"fault_harness.h\"\nstatic const struct fault_case cases[] = {\n"
        + "".join(_c_case(case) for case in cases)
        + "};\n#define CASE_COUNT (sizeof(cases)/sizeof(cases[0]))\n",
    }
    files["baseline_fault.c"] = (
        "#include \"fault_harness.h\"\n" + baseline_faults + "\n"
    )
    profile = _marked(sources.patched)
    files["patched_fault.c"] = (
        "#include \"fault_harness.h\"\n"
        + profile
        + "\n"
        + patched_faults
        + "\n"
        + FAULT_C
    )
    for name, content in files.items():
        (work / name).write_text(content)

    common = [
        "-std=gnu11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
        "-Wno-missing-field-initializers", "-fsanitize=address,undefined",
        "-fno-omit-frame-pointer", "-I", str(work),
    ]
    env = dict(
        os.environ,
        ASAN_OPTIONS="halt_on_error=1:detect_leaks=0",
        UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1",
    )

    def checked(command):
        try:
            return subprocess.run(
                command, env=env, check=True, capture_output=True, text=True,
                timeout=120,
            )
        except subprocess.CalledProcessError as error:
            raise AssertionError(
                "command failed: %s\n%s\n%s"
                % (" ".join(command), error.stdout, error.stderr)
            )

    outputs = {}
    for variant in ("baseline", "patched"):
        folder = work / variant
        folder.mkdir()
        objects = []
        fault_source = "patched_fault.c" if variant == "patched" else "baseline_fault.c"
        fault_extra = (
            ["-DPATCHED", "-Dmach_absolute_time=gfw_profile_clock"]
            if variant == "patched" else []
        )
        for source_name in ("harness.c", "observe.c", "settle.c"):
            extra = ["-DPATCHED"] if variant == "patched" and source_name == "harness.c" else []
            obj = folder / (Path(source_name).stem + ".o")
            checked(
                [shutil.which("clang"), *common, *extra, "-c",
                 str(work / source_name), "-o", str(obj)],
            )
            objects.append(str(obj))
        obj = folder / "fault.o"
        checked(
            [shutil.which("clang"), *common, *fault_extra, "-c",
             str(work / fault_source), "-o", str(obj)],
        )
        objects.append(str(obj))
        exe = folder / "behavior"
        checked(
            [shutil.which("clang"), *common, *objects, "-o", str(exe)],
        )
        outputs[variant] = checked([str(exe)]).stdout
    return outputs


def _parse(text):
    cases = {}
    current = None
    for line in text.splitlines():
        if line.startswith("CASE "):
            current = {"name": line[5:], "trace": [], "mut": {}, "profile": {}}
            cases[current["name"]] = current
        elif line.startswith("RESULT ") and current is not None:
            current["result"] = int(line[7:])
        elif line.startswith("MUT "):
            current["mut"]["work"] = line
        elif line.startswith("READ "):
            current["mut"]["read"] = line
        elif line.startswith("MICRO "):
            current["mut"]["micro"] = line
        elif line.startswith("PROFILE "):
            parts = dict(p.split("=", 1) for p in line.split()[1:])
            current["profile"][int(parts["group"])] = (
                int(parts["calls"]), int(parts["ticks"])
            )
        elif line.startswith("PROFILE_INVALID "):
            current["invalid"] = line
        elif current is not None:
            current["trace"].append(line)
    return cases


def _profile_expected(case):
    trace = case["trace"]
    expected = {}
    expected[0] = sum(1 for event in trace if event.startswith("R32 off=00000048 "))
    expected[1] = sum(1 for event in trace if event.startswith("SETTLE_ENTER "))
    expected[2] = sum(1 for event in trace if event.startswith("R32 off=00008058 "))
    expected[3] = sum(1 for event in trace if event.startswith("R32 off=00009058 "))
    expected[4] = sum(1 for event in trace if event.startswith("LOAD space=1 "))
    expected[5] = sum(1 for event in trace if event.startswith("LOAD space=2 "))
    return expected


class FaultSubgroupBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("clang") is None:
            raise unittest.SkipTest("clang not available")
        sources = _Sources()
        cases = _cases()
        cls.cases = cases
        cls.tmp = tempfile.TemporaryDirectory(prefix="fault297-behavior-")
        work = Path(cls.tmp.name)
        outputs = _build_and_run(sources, cases, work)
        cls.base = _parse(outputs["baseline"])
        cls.patched = _parse(outputs["patched"])
        cls.origins = (sources.baseline_origin, sources.patched_origin)
        cls.sources = sources

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_cases_produced_both_variants(self):
        names = [case["name"] for case in self.cases]
        self.assertEqual(list(self.base), names, self.origins)
        self.assertEqual(list(self.patched), names, self.origins)

    def test_only_the_fault_body_is_instrumented(self):
        baseline = self.sources.baseline
        patched = self.sources.patched
        self.assertNotIn("GFW_FAULT_TIMED(", baseline)
        self.assertNotIn(PROFILE_BEGIN, baseline)
        self.assertEqual(patched.count("GFW_FAULT_TIMED("), 6)  # define + 5 sites
        self.assertIn(PROFILE_BEGIN, patched)
        for helper in (
            "gfw_observe32", "gfw_observe64", "gfw_observe_load",
            "ggrb_micro_settle", "ggrb_ns",
        ):
            self.assertEqual(
                _extract_function(baseline, helper),
                _extract_function(patched, helper),
                helper,
            )
        self.assertNotEqual(
            _extract_function(baseline, "gfw_faults"),
            _extract_function(patched, "gfw_faults"),
        )

    def test_result_and_hardware_trace_are_identical(self):
        for name in self.base:
            with self.subTest(case=name):
                self.assertEqual(
                    self.base[name]["result"],
                    self.patched[name]["result"],
                )
                self.assertEqual(
                    self.base[name]["trace"],
                    self.patched[name]["trace"],
                    "hardware read/settle/clock trace diverged",
                )

    def test_recorded_mutations_are_identical(self):
        for name in self.base:
            with self.subTest(case=name):
                self.assertEqual(
                    self.base[name]["mut"],
                    self.patched[name]["mut"],
                )

    def test_success_path_reaches_every_observation(self):
        case = self.base["success_full"]
        self.assertEqual(case["result"], 1)
        reads = [event for event in case["trace"] if event[:3] in ("R32", "R64")]
        self.assertEqual(len(reads), 29)
        self.assertTrue(any(event.startswith("LOAD space=1 ") for event in case["trace"]))
        self.assertTrue(any(event.startswith("LOAD space=2 ") for event in case["trace"]))

    def test_absent_ao_is_not_read(self):
        case = self.base["success_absent_ao"]
        self.assertEqual(case["result"], 1)
        self.assertFalse(any(event.startswith("LOAD space=2 ") for event in case["trace"]))

    def test_every_read_failure_short_circuits_identically(self):
        layout = _read_layout(self.cases[0])
        for ordinal in range(len(layout)):
            name = "read_fail_%02d" % ordinal
            case = self.base[name]
            self.assertEqual(case["result"], 0, name)
            reads = [e for e in case["trace"] if e[:3] in ("R32", "R64")]
            self.assertEqual(len(reads), ordinal + 1, name)
            self.assertIn("ok=0", reads[-1], name)
        first = self.base["read_fail_00"]
        self.assertEqual(len([e for e in first["trace"] if e[:3] in ("R32", "R64")]), 1)

    def test_global_bank_host_and_ao_rejections(self):
        for name in [
            "global_gfsr_fault", "global_cr0_mismatch",
            "global_micro_mismatch_no_settle", "bank0_fsr_fault",
            "bank1_fsr_fault", "bank0_sctlr_mismatch", "bank1_sctlr_mismatch",
            "bank0_ttbr1_mismatch", "bank1_ttbr1_mismatch",
            "host_all_ones", "host_bit15", "ao_all_ones", "ao_bit0",
            "ao_bit3", "ao_bit5", "bank0_invalid_bank", "bank1_invalid_bank",
            "bank0_invalid_slot", "bank1_invalid_slot",
        ]:
            self.assertEqual(self.base[name]["result"], 0, name)

    def test_settle_success_recheck_and_failure(self):
        success = self.base["settle_transient_success"]
        self.assertEqual(success["result"], 1)
        self.assertIn("SETTLE_ENTER", "\n".join(success["trace"]))
        self.assertIn("SETTLE_EXIT recovered=1", "\n".join(success["trace"]))
        recheck = self.base["settle_transient_recheck_success"]
        self.assertEqual(recheck["result"], 1)
        self.assertEqual(
            sum(1 for e in recheck["trace"] if e.startswith("SETTLE_ENTER")), 2
        )
        self.assertIn("rechecks=1", recheck["mut"]["micro"])
        invalid = self.base["settle_unexpected_value_fails"]
        self.assertEqual(invalid["result"], 0)
        self.assertIn("SETTLE_EXIT recovered=0", "\n".join(invalid["trace"]))
        failed = self.base["settle_poll_read_fails"]
        self.assertEqual(failed["result"], 0)
        self.assertIn("ok=0", "\n".join(failed["trace"]))

    def test_settle_deadline_exhaustion_is_recorded(self):
        inside = self.base["settle_deadline_exhausted_inside"]
        self.assertEqual(inside["result"], 0)
        self.assertIn("expired=1", inside["mut"]["micro"])
        final = self.base["settle_final_deadline_after_recovery"]
        self.assertEqual(final["result"], 0)
        self.assertIn("expired=1", final["mut"]["micro"])
        top = self.base["settle_top_deadline_after_recovery"]
        self.assertEqual(top["result"], 0)
        self.assertIn("SETTLE_EXIT recovered=1", "\n".join(top["trace"]))
        self.assertIn("expired=1", top["mut"]["micro"])

    def test_instrumented_profile_counters_match_executed_wrappers(self):
        for name, case in self.patched.items():
            with self.subTest(case=name):
                expected = _profile_expected(case)
                actual = case["profile"]
                self.assertEqual(set(actual), set(expected), name)
                for group, calls in expected.items():
                    self.assertEqual(actual[group][0], calls, (name, group))
                    self.assertEqual(actual[group][1], calls * 10, (name, group))

    def test_invalid_and_reversed_profile_timestamps_are_ignored(self):
        case = self.patched["success_full"]
        self.assertIn(
            "invalid_calls=0 invalid_ticks=0 equal_calls=1 equal_ticks=0 "
            "normal_calls=1 normal_ticks=25",
            case["invalid"],
        )


if __name__ == "__main__":
    unittest.main()