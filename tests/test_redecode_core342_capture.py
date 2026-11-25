"""Collision regressions against the saved, independently restored 0342 run."""
import importlib.util
from pathlib import Path
import re
import sys
import unittest


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("redecode_342_capture", TOOLS / "redecode-core342-capture.py")
redecode = importlib.util.module_from_spec(spec)
spec.loader.exec_module(redecode)


class RedecodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        execution = redecode.BASE / "execution"
        proof = redecode.load(execution / "independent-restore.json")
        assert proof["journal_empty"] and proof["misc_original_4096_bytes_match"]
        cls.text = (execution / "kernel.log").read_text()
        cls.driver = redecode.kernel.parse(cls.text, (execution / "kernel.log.bin").read_bytes())
        assert cls.driver["coverage_qualified"]

    def test_both_producers_keep_their_own_rows(self):
        view, trace, changes = redecode.correct_event_types(self.text)
        self.assertEqual(len(changes), 541)
        self.assertEqual(len(trace["queue_state_samples"]), 68)
        self.assertEqual(trace["header"]["count"], 2873)
        allocation = redecode.module("analyze-bo-reuse-log.py").analyze(view, redecode.ui)
        self.assertEqual(redecode.corroborate_bo_allocations(trace, allocation, self.driver), 85)
        self.assertEqual(allocation["reused_mapping_requests"], 31)

    def test_reject_missing_or_unclassifiable_event(self):
        phase = re.search(r"^SWEET UI254 E: .*kind=31 id=[0-9]+ pid=[0-9]+ flags=4 a=0 b=0 c=0\n",
                          self.text, re.M)[0]
        mutations = (
            (self.text.replace(phase, "", 1), "sequence discontinuity"),
            (self.text.replace(phase, phase.replace("flags=4", "flags=3"), 1), "ordered BO phases"),
            (self.text.replace(phase, re.sub(r"id=[0-9]+", "id=0", phase), 1), "cannot be uniquely identified"),
        )
        for text, reason in mutations:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                redecode.correct_event_types(text)

    def test_reject_retyped_payload_that_disagrees_with_independent_request(self):
        view, trace, _ = redecode.correct_event_types(self.text)
        allocation = redecode.module("analyze-bo-reuse-log.py").analyze(view, redecode.ui)
        first = allocation["rows"][0]
        bad = dict(allocation, rows=[dict(first, thread_id=0), *allocation["rows"][1:]])
        with self.assertRaisesRegex(ValueError, "does not match one independent"):
            redecode.corroborate_bo_allocations(trace, bad, self.driver)


if __name__ == "__main__":
    unittest.main()
