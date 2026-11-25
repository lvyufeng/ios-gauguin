#!/usr/bin/env python3
"""Check instrumentation preserves the actual kernel source and predicates."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

TREE = Path(os.environ["XNU_SOURCE"])
BASE = Path(os.environ["GUARD_PROFILE_BASE"])
FILE = "bsd/dev/gauguin_gmu_board.c"
EXPRESSIONS = [
    ("GGRB_GUARD_OWNER", "sweet_pas_zap_owner_authenticated(gmb_stage.pa)"),
    ("GGRB_GUARD_LEASE", "gauguin_wdt_lease_check_budget(GMB_MIN)"),
    ("GGRB_GUARD_UNSECURED", "ggwb_unsecured()"),
    ("GGRB_GUARD_CLOCK", "sweet_gmu_clock_live_snapshot(&sample.gx)"),
    ("GGRB_GUARD_IRQ", "sweet_gmu_irq_quiet(sample.irq)"),
    ("GGRB_GUARD_FAULTS", "gfw_faults(false)"),
]


class GuardProfileTests(unittest.TestCase):
    def test_all_other_source_and_guard_order_are_unchanged(self):
        old, new = ((tree / FILE).read_text() for tree in (BASE, TREE))
        base_start = old.index("struct ggrb_perf_sample {")
        base_end = old.index("static bool ggrb_micro_settle", base_start)
        new_start = new.index("enum { GGRB_GUARD_OWNER")
        new_end = new.index("static bool ggrb_micro_settle", new_start)
        restored = new[:new_start] + old[base_start:base_end] + new[new_end:]
        for group, expression in EXPRESSIONS:
            wrapped = "GGRB_TIMED_GUARD(" + group + "," + expression + ")"
            self.assertEqual(restored.count(wrapped), 1)
            restored = restored.replace(wrapped, expression)
        restored = restored.replace("__atomic_store_n(&ggrb_perf.pending,1,__ATOMIC_RELEASE);",
                                    "ggrb_perf.pending=1;")
        restored = restored.replace("__atomic_store_n(&ggrb_perf.pending,0,__ATOMIC_RELEASE);",
                                    "ggrb_perf.pending=0;")
        restored = restored.replace("__atomic_load_n(&ggrb_perf.pending,__ATOMIC_ACQUIRE));gmb_record(line);",
                                    "ggrb_perf.pending);gmb_record(line);")
        start = restored.index("    for(unsigned group=0;group<GGRB_GUARD_GROUPS;group++)")
        end = restored.index("    GauguinGPUProfileDump(gmb_record);", start)
        restored = restored[:start] + restored[end:]
        self.assertEqual(restored, old)

    def test_actual_macro_evaluates_once_and_preserves_success_and_failure(self):
        source = (TREE / FILE).read_text()
        start = source.index("enum { GGRB_GUARD_OWNER")
        end = source.index("static bool ggrb_micro_settle", start)
        actual = source[start:end]
        prefix = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
static uint64_t tick;
static uint64_t mach_absolute_time(void) { return tick += 10; }
"""
        main = r"""
static unsigned evaluations;
static bool probe(bool answer) { ++evaluations; return answer; }
int main(void) {
    for (unsigned group=0; group<GGRB_GUARD_GROUPS; ++group) {
        __atomic_store_n(&ggrb_perf.pending,0,__ATOMIC_RELEASE);
        assert(GGRB_TIMED_GUARD(group,probe(true)));
        __atomic_store_n(&ggrb_perf.pending,1,__ATOMIC_RELEASE);
        assert(!GGRB_TIMED_GUARD(group,probe(false)));
        struct ggrb_guard_perf *g=&ggrb_perf.groups[group];
        assert(g->calls==2 && g->ticks==20);
        assert(g->overlap_calls==1 && g->overlap_ticks==10);
    }
    assert(evaluations==2*GGRB_GUARD_GROUPS);
    ggrb_guard_time(0,20,10);
    assert(ggrb_perf.groups[0].calls==2);
    return 0;
}
"""
        with tempfile.TemporaryDirectory(prefix="guard-profile-") as folder:
            path = Path(folder) / "test.c"
            path.write_text(prefix + actual + main)
            executable = path.with_suffix("")
            subprocess.run(["clang", "-std=gnu11", "-O1", "-Wall", "-Wextra", "-Werror",
                            "-fsanitize=address,undefined", str(path), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    unittest.main()
