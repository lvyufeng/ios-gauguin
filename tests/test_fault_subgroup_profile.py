#!/usr/bin/env python3
"""Host checks for the 0297 fault-subgroup timing instrumentation.

The instrumentation must only observe the existing fault reads. Removing the
timing blocks and unwrapping every GFW_FAULT_TIMED call must reproduce the
pinned 0296 applied source exactly, and the actual helper/macro must preserve
result and short-circuit behavior under ASan+UBSan.

XNU_SOURCE may name a patched source root or file. When it is absent, the test
applies the 0297 patch to the pinned baseline in memory; it never edits the
worktree or talks to a device.
"""
import hashlib
import os
import re
from functools import lru_cache
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
NAME = "bsd/dev/gauguin_gmu_board.c"
DEFAULT_BASELINE = Path(
    "/Users/baai/Project/ios-gauguin/research/tmp/"
    "gauguin-guard296-worktree-20261111/.deps-cache/p0-20261105/source296"
)
EXPECTED_BASELINE_SHA256 = (
    "5deaa9bd953e02f9279c22d2668efe6bcda9db7e8a56e0c02c5ba9b1eb311dd8"
)
GROUPS = [
    "GFW_FAULT_GLOBAL",
    "GFW_FAULT_SETTLE",
    "GFW_FAULT_BANK0",
    "GFW_FAULT_BANK1",
    "GFW_FAULT_HOST",
    "GFW_FAULT_AO",
    "GFW_FAULT_GROUPS",
]
BLOCK_BEGIN = "/* BEGIN GFW FAULT PROFILE:"
BLOCK_END = "/* END GFW FAULT PROFILE */"
DUMP_BEGIN = "/* BEGIN GFW FAULT PROFILE DUMP */"
DUMP_END = "/* END GFW FAULT PROFILE DUMP */"


def _env_board(name):
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value)
    return path if path.is_file() else path / NAME


def _baseline_path():
    return _env_board("FAULT_PROFILE_BASE") or _env_board("GUARD_PROFILE_BASE") \
        or (DEFAULT_BASELINE / NAME)


@lru_cache(maxsize=None)
def _baseline():
    path = _baseline_path()
    if not path.is_file():
        raise unittest.SkipTest("0296 baseline source not found: %s" % path)
    return path, path.read_text()


def _find_patch():
    override = os.environ.get("FAULT_PROFILE_PATCH")
    if override:
        path = Path(override)
        return path if path.is_file() else None
    matches = sorted((ROOT / "xnu/patches").glob("*fault-subgroup-profiling*.patch"))
    return matches[-1] if matches else None


def _find_applied_source():
    override = _env_board("XNU_SOURCE")
    if override:
        candidates = [override]
    else:
        candidates = sorted(
            ROOT.glob(".deps-cache/**/gauguin_gmu_board.c"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    for path in candidates:
        if not path.is_file():
            continue
        text = path.read_text()
        if "GFW_FAULT_TIMED(" in text and BLOCK_BEGIN in text:
            return path, text
    return None


def _apply_unified_diff(baseline, patch):
    """Apply this single-file unified diff, checking every removed line."""
    base_lines = baseline.splitlines(keepends=True)
    patch_lines = patch.splitlines(keepends=True)
    hunk = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    result = []
    position = 0
    index = 0
    while index < len(patch_lines):
        match = hunk.match(patch_lines[index])
        if not match:
            index += 1
            continue
        old_start = int(match.group(1))
        old_count = int(match.group(2) or "1")
        start = old_start - 1
        if start < position:
            raise AssertionError("overlapping hunk at patch line %d" % (index + 1))
        result.extend(base_lines[position:start])
        position = start
        consumed = 0
        index += 1
        while index < len(patch_lines):
            line = patch_lines[index]
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
                if position >= len(base_lines):
                    raise AssertionError("patch removes past end of baseline")
                expected = line[1:].rstrip("\n")
                actual = base_lines[position].rstrip("\n")
                if actual != expected:
                    raise AssertionError(
                        "patch removes different baseline line %d:\n  patch %r\n  base  %r"
                        % (position + 1, expected, actual)
                    )
                consumed += 1
                if line[0] == " ":
                    result.append(base_lines[position])
                position += 1
            else:
                result.append(line[1:])
            index += 1
        if consumed != old_count:
            raise AssertionError(
                "hunk at patch line %d consumed %d baseline lines, expected %d"
                % (index + 1, consumed, old_count)
            )
    result.extend(base_lines[position:])
    return "".join(result)


@lru_cache(maxsize=None)
def _source():
    applied = _find_applied_source()
    if applied is not None:
        return applied[1], str(applied[0])
    baseline_path, baseline = _baseline()
    patch_path = _find_patch()
    if patch_path is None:
        raise unittest.SkipTest(
            "no applied 0297 source or fault-subgroup patch found; "
            "set XNU_SOURCE or FAULT_PROFILE_PATCH"
        )
    patched = _apply_unified_diff(baseline, patch_path.read_text())
    return patched, "%s applied in memory to %s" % (patch_path, baseline_path)


def _matching_paren(text, opening):
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
                raise AssertionError("unterminated comment in wrapper")
            index = close + 1
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise AssertionError("unbalanced parentheses in wrapper")


def _top_level_comma(content):
    depth = 0
    index = 0
    while index < len(content):
        char = content[index]
        if char in "\"'":
            quote = char
            index += 1
            while index < len(content):
                if content[index] == "\\":
                    index += 2
                    continue
                if content[index] == quote:
                    break
                index += 1
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            return index
        index += 1
    raise AssertionError("GFW_FAULT_TIMED wrapper has no argument comma")


def _wrappers(text):
    needle = "GFW_FAULT_TIMED("
    found = []
    position = 0
    while True:
        start = text.find(needle, position)
        if start < 0:
            return found
        line_start = text.rfind("\n", 0, start) + 1
        if text[line_start:start].lstrip().startswith("#define"):
            position = start + len(needle)
            continue
        opening = start + len(needle) - 1
        closing = _matching_paren(text, opening)
        content = text[opening + 1:closing]
        comma = _top_level_comma(content)
        found.append((start, closing + 1, content[:comma].strip(), content[comma + 1:]))
        position = closing + 1


def _group_key(token):
    compact = re.sub(r"\s+", "", token)
    if compact == "GFW_FAULT_GLOBAL":
        return "global"
    if compact == "GFW_FAULT_SETTLE":
        return "settle"
    if compact == "GFW_FAULT_HOST":
        return "host"
    if compact == "GFW_FAULT_AO":
        return "ao"
    if compact in ("GFW_FAULT_BANK0", "GFW_FAULT_BANK1"):
        return "bank"
    if compact.startswith("GFW_FAULT_BANK0+") or compact.startswith("GFW_FAULT_BANK1+"):
        return "bank"
    raise AssertionError("unknown fault profile group %r" % token)


def _expression_variants(expression):
    stripped = expression.strip()
    variants = [stripped]
    if stripped.startswith("(") and _matching_paren(stripped, 0) == len(stripped) - 1:
        variants.append(stripped[1:-1].strip())
    return variants


def _expected_expressions(baseline):
    start = baseline.index("static bool gfw_faults(bool gpu_probe)\n{")
    end = baseline.index("\n}\n", start) + 3
    body = baseline[start:end]
    spans = {
        "global": (
            "!gfw_observe32(NULL,0x48,&gfw_work.gfsr)||gfw_work.gfsr",
            "!gfw_observe32(NULL,0x6000,&v)",
        ),
        "settle": (
            "ggrb_micro_settle(gpu_probe,s->micro_after,micro_mask,v,&wait)",
            "ggrb_micro_settle(gpu_probe,s->micro_after,micro_mask,v,&wait)",
        ),
        "bank": (
            "!gfw_observe32(NULL,cb+0x58,&gfw_work.fsr[n])",
            "!gfw_observe64(NULL,cb+0x28,&ttbr)||ttbr!=s->ttbr1[n]",
        ),
        "host": (
            "gfw_observe_load(1,0x2648,gmb_reset+0x2648)",
            "gfw_observe_load(1,0x2648,gmb_reset+0x2648)",
        ),
        "ao": (
            "gfw_observe_load(2,0x2c14,gfw_map[GMF_AO]+0x2c14)",
            "gfw_observe_load(2,0x2c14,gfw_map[GMF_AO]+0x2c14)",
        ),
    }
    expressions = {}
    for name, (first, last) in spans.items():
        begin = body.index(first)
        complete = body[begin:body.index(last, begin) + len(last)]
        if baseline.count(complete) != 1:
            raise AssertionError(
                "expected fault expression %s is not unique in baseline" % name
            )
        expressions[name] = complete
    return expressions


def _remove_marked_block(text, begin_marker, end_marker):
    if text.count(begin_marker) != 1 or text.count(end_marker) != 1:
        raise AssertionError(
            "expected one %r and one %r marker" % (begin_marker, end_marker)
        )
    begin = text.index(begin_marker)
    end = text.index(end_marker, begin) + len(end_marker)
    line_begin = text.rfind("\n", 0, begin) + 1
    if text[line_begin:begin].strip():
        raise AssertionError("instrumentation marker does not start its line")
    line_end = text.find("\n", end)
    line_end = len(text) if line_end < 0 else line_end + 1
    return text[:line_begin] + text[line_end:]


def _without_instrumentation(source):
    source = _remove_marked_block(source, BLOCK_BEGIN, BLOCK_END)
    return _remove_marked_block(source, DUMP_BEGIN, DUMP_END)


def _unwrap_fault_wrappers(source, expected):
    wrappers = _wrappers(source)
    if len(wrappers) != 5:
        raise AssertionError(
            "expected five GFW_FAULT_TIMED call sites (bank loop covers two groups), "
            "found %d" % len(wrappers)
        )
    replacements = []
    seen = set()
    for start, end, token, expression in wrappers:
        key = _group_key(token)
        if key in seen:
            raise AssertionError("duplicate fault profile wrapper for %s" % key)
        seen.add(key)
        wanted = expected[key]
        variants = _expression_variants(expression)
        if wanted not in variants:
            raise AssertionError(
                "wrapper %s does not contain the baseline expression:\n"
                "  wanted %r\n  found  %r"
                % (token, wanted, variants)
            )
        replacements.append((start, end, wanted))
    if seen != set(expected):
        raise AssertionError(
            "wrapped fault paths %r do not cover %r" % (sorted(seen), sorted(expected))
        )
    for start, end, wanted in reversed(replacements):
        source = source[:start] + wanted + source[end:]
    return source


def _marked_block(source, begin_marker, end_marker):
    begin = source.index(begin_marker)
    end = source.index(end_marker, begin) + len(end_marker)
    return source[begin:end]


class FaultSubgroupSourceTests(unittest.TestCase):
    def test_baseline_is_the_pinned_0296_applied_source(self):
        _, baseline = _baseline()
        actual = hashlib.sha256(baseline.encode()).hexdigest()
        self.assertEqual(actual, EXPECTED_BASELINE_SHA256)

    def test_enum_names_all_six_subgroups(self):
        source, origin = _source()
        self.assertIn(
            "enum { GFW_FAULT_GLOBAL, GFW_FAULT_SETTLE, GFW_FAULT_BANK0,\n"
            "       GFW_FAULT_BANK1, GFW_FAULT_HOST, GFW_FAULT_AO, GFW_FAULT_GROUPS };",
            source,
            origin,
        )
        enum = source[
            source.index("enum { GFW_FAULT_GLOBAL"):
            source.index("GFW_FAULT_GROUPS };") + len("GFW_FAULT_GROUPS };")
        ]
        self.assertEqual(re.findall(r"GFW_FAULT_[A-Z0-9]+", enum), GROUPS)

    def test_each_existing_fault_expression_is_wrapped_exactly_once(self):
        source, origin = _source()
        _, baseline = _baseline()
        expected = _expected_expressions(baseline)
        wrappers = _wrappers(source)
        self.assertEqual(len(wrappers), 5, origin)
        self.assertEqual(source.count("GFW_FAULT_TIMED("), 6, origin)  # five calls + define
        seen = set()
        for _, _, token, expression in wrappers:
            key = _group_key(token)
            self.assertNotIn(key, seen, origin)
            seen.add(key)
            self.assertIn(expected[key], _expression_variants(expression), origin)
        self.assertEqual(seen, set(expected), origin)

    def test_fault_dump_covers_every_group_and_call(self):
        source, origin = _source()
        dump = _marked_block(source, DUMP_BEGIN, DUMP_END)
        self.assertIn(
            "for(unsigned group=0;group<GFW_FAULT_GROUPS;group++)", dump, origin
        )
        self.assertIn("SWEET GPU FAULT PERF: group=%u calls=%llu ns=%llu", dump, origin)
        self.assertIn("gfw_fault_perf[group].calls", dump, origin)
        self.assertIn("gfw_fault_perf[group].ticks", dump, origin)
        self.assertIn("gmb_record(line)", dump, origin)

    def test_removing_only_0297_instrumentation_restores_baseline(self):
        source, origin = _source()
        _, baseline = _baseline()
        expected = _expected_expressions(baseline)
        restored = _without_instrumentation(source)
        self.assertNotIn(BLOCK_BEGIN, restored)
        self.assertNotIn(DUMP_BEGIN, restored)
        restored = _unwrap_fault_wrappers(restored, expected)
        if restored != baseline:
            mismatch = next(
                (
                    number
                    for number, (old, new) in enumerate(
                        zip(baseline.splitlines(), restored.splitlines()), 1
                    )
                    if old != new
                ),
                min(len(baseline.splitlines()), len(restored.splitlines())) + 1,
            )
            self.fail(
                "restored source differs from baseline near line %d (%s)"
                % (mismatch, origin)
            )


class FaultSubgroupHarnessTests(unittest.TestCase):
    def test_actual_helper_and_macro_survive_true_false_short_circuit_and_bad_inputs(self):
        source, origin = _source()
        actual = _marked_block(source, BLOCK_BEGIN, BLOCK_END)
        prefix = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
static uint64_t fake_now;
static unsigned clock_reads;
static uint64_t mach_absolute_time(void)
{
    ++clock_reads;
    return fake_now += 10;
}
"""
        main = r"""
static unsigned evaluations;
static bool probe(bool answer)
{
    ++evaluations;
    return answer;
}
int main(void)
{
    _Static_assert(GFW_FAULT_GROUPS == 6, "six fault subgroups");
    for (unsigned group = 0; group < GFW_FAULT_GROUPS; ++group) {
        uint64_t calls = gfw_fault_perf[group].calls;
        uint64_t ticks = gfw_fault_perf[group].ticks;
        clock_reads = 0;
        evaluations = 0;
        assert(GFW_FAULT_TIMED(group, probe(true)));
        assert(evaluations == 1);
        assert(clock_reads == 2);
        assert(gfw_fault_perf[group].calls == calls + 1);
        assert(gfw_fault_perf[group].ticks == ticks + 10);
        assert(!GFW_FAULT_TIMED(group, probe(false)));
        assert(evaluations == 2);
        assert(clock_reads == 4);
        assert(gfw_fault_perf[group].calls == calls + 2);
        assert(gfw_fault_perf[group].ticks == ticks + 20);
    }

    evaluations = 0;
    assert(!GFW_FAULT_TIMED(GFW_FAULT_GLOBAL, (probe(false) && probe(true))));
    assert(evaluations == 1);
    assert(GFW_FAULT_TIMED(GFW_FAULT_GLOBAL, (probe(true) || probe(false))));
    assert(evaluations == 2);

    {
        uint64_t calls = gfw_fault_perf[GFW_FAULT_GLOBAL].calls;
        uint64_t ticks = gfw_fault_perf[GFW_FAULT_GLOBAL].ticks;
        gfw_fault_profile_time(GFW_FAULT_GROUPS, 10, 20);
        gfw_fault_profile_time(GFW_FAULT_GROUPS + 1000u, 10, 20);
        gfw_fault_profile_time(GFW_FAULT_GLOBAL, 20, 10);
        gfw_fault_profile_time(GFW_FAULT_AO, UINT64_MAX, 0);
        assert(gfw_fault_perf[GFW_FAULT_GLOBAL].calls == calls);
        assert(gfw_fault_perf[GFW_FAULT_GLOBAL].ticks == ticks);
    }

    {
        uint64_t calls = gfw_fault_perf[GFW_FAULT_AO].calls;
        uint64_t ticks = gfw_fault_perf[GFW_FAULT_AO].ticks;
        gfw_fault_profile_time(GFW_FAULT_AO, 100, 125);
        assert(gfw_fault_perf[GFW_FAULT_AO].calls == calls + 1);
        assert(gfw_fault_perf[GFW_FAULT_AO].ticks == ticks + 25);
        gfw_fault_profile_time(GFW_FAULT_AO, 100, 100);
        assert(gfw_fault_perf[GFW_FAULT_AO].calls == calls + 2);
        assert(gfw_fault_perf[GFW_FAULT_AO].ticks == ticks + 25);
    }
    puts("fault subgroup helper/macro: true/false, once, short-circuit, invalid, reversed");
    return 0;
}
"""
        with tempfile.TemporaryDirectory(prefix="fault-subgroup-") as folder:
            folder = Path(folder)
            path = folder / "test.c"
            path.write_text(prefix + actual + main)
            executable = folder / "test"
            env = dict(
                os.environ,
                ASAN_OPTIONS="halt_on_error=1:detect_leaks=0",
                UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1",
            )
            subprocess.run(
                [
                    "clang",
                    "-std=gnu11",
                    "-O1",
                    "-g",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-fsanitize=address,undefined",
                    "-fno-omit-frame-pointer",
                    str(path),
                    "-o",
                    str(executable),
                ],
                env=env,
                check=True,
            )
            subprocess.run([str(executable)], env=env, check=True, timeout=30)


if __name__ == "__main__":
    unittest.main()