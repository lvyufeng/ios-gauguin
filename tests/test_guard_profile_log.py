import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from guard_profile_log import parse_guard_profile


def record(group, calls=8, ns=240, pending=3, pending_ns=90):
    return (f"SWEET GPU GUARD PERF: group={group} calls={calls} ns={ns} "
            f"pending_end_calls={pending} pending_end_ns={pending_ns}; "
            "CPU wall, pending sampled at end")


class GuardProfileLogTests(unittest.TestCase):
    def test_complete_unordered_snapshot(self):
        result = parse_guard_profile("\n".join(record(group) for group in reversed(range(6))))
        self.assertEqual([row["name"] for row in result["groups"]],
                         ["owner", "lease", "unsecured", "clock", "irq", "faults"])
        self.assertFalse(result["per_submit_attribution_qualified"])

    def test_incomplete_interleaved_duplicate_and_impossible_data_fail(self):
        good = [record(group) for group in range(6)]
        cases = [
            good[:-1], good + [good[0]],
            ["other log " + good[0], *good[1:]],
            [record(6), *good[1:]], [record(0, pending=9), *good[1:]],
            [record(0, ns=10, pending_ns=11), *good[1:]],
            [record(0, calls=0, ns=1, pending=0, pending_ns=0), *good[1:]],
            [record(0, calls=1 << 64), *good[1:]],
        ]
        for number, rows in enumerate(cases):
            with self.subTest(number=number), self.assertRaises(ValueError):
                parse_guard_profile("\n".join(rows))

    def test_no_new_records_does_not_promote_older_trial(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            parse_guard_profile("unrelated 0294 log\n")


if __name__ == "__main__":
    unittest.main()
