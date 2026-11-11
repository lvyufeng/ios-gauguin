#!/usr/bin/env python3
"""Replay the private handset DTB/catalog; mutate legal but incorrect timings."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gauguin_mode_contract import TIMING_FIELDS, validate_catalog


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class ModeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dtb = Path(os.environ["MODE_CONTRACT_DTB"])
        cls.log_path = Path(os.environ["MODE_CONTRACT_LOG"])
        cls.log = cls.log_path.read_text()
        cls.profile_tool = module("profile295", "gauguin-display-profile.py")
        cls.reader = module("reader295", "gauguin-drm-timing.py")
        tree = cls.profile_tool.Tree(cls.dtb, "fdtget")
        cls.profile = cls.profile_tool.display_inventory(tree)
        cls.profile["refresh_timing_catalog"] = cls.profile_tool.refresh_catalog(tree, cls.profile)
        parent = cls.profile_tool.MDP + "/" + cls.profile["selected_panel_node"] + "/qcom,mdss-dsi-display-timings"
        cls.skew = tree.cell(parent + "/" + tree.children(parent)[0], "qcom,mdss-dsi-h-sync-skew")
        cls.catalog = cls.reader.analyze_modes(cls.log)

    def check(self, catalog):
        return validate_catalog(self.profile, catalog, self.skew)

    def old_four_field_check(self, catalog):
        # The actual 0272 gate's matching policy, retained to expose the gap.
        models = {(r["reported_hz"], r["reported_clock_khz"]): r
                  for r in self.profile["refresh_timing_catalog"]["modeled_modes"]}
        observed = {(r["reported_hz"], r["reported_clock_khz"]): r for r in catalog["advertised_timings"]}
        self.assertEqual(models.keys(), observed.keys())
        for key, row in models.items():
            for field in ("horizontal_front_porch", "vertical_front_porch", "horizontal_total", "vertical_total"):
                self.assertEqual(row[field], observed[key][field])
        self.assertEqual(catalog["matching_active_timing_index"], 0)

    def test_actual_twelve_modes_and_active_match(self):
        result = self.check(self.catalog)
        self.assertEqual(result["matched_modes"], 12)
        self.assertEqual(result["active_mode_key"], [60, 136659])
        self.assertFalse(result["physical_refresh_qualified"])
        self.assertFalse(result["modeset_qualified"])

    def test_legal_sync_changes_pass_old_gate_but_fail_contract(self):
        for column in (5, 10):  # Raw GDRM hsync_end/vsync_end, prefix included.
            for index in range(12):
                rows = [line.split() for line in self.log.splitlines()]
                rows[index + 2][column] = str(int(rows[index + 2][column]) + 1)
                if index == 0:
                    rows[1][column] = str(int(rows[1][column]) + 1)
                changed = self.reader.analyze_modes("\n".join(" ".join(row) for row in rows))
                self.old_four_field_check(changed)
                with self.subTest(column=column, index=index), self.assertRaises(ValueError):
                    self.check(changed)

    def test_every_expanded_timing_field_and_active_are_bound(self):
        for field in TIMING_FIELDS:
            for target in ("active", "advertised"):
                changed = copy.deepcopy(self.catalog)
                row = changed["active_timing"] if target == "active" else changed["advertised_timings"][1]
                row[field] += 1
                with self.subTest(field=field, target=target), self.assertRaises(ValueError):
                    self.check(changed)

    def test_type_is_metadata_and_catalog_order_is_not_identity(self):
        rows = [line.split() for line in self.log.splitlines()]
        for row in rows[1:-1]:
            row[-1] = str(int(row[-1]) ^ 64)
        rows[2:-1] = reversed(rows[2:-1])
        result = self.check(self.reader.analyze_modes("\n".join(" ".join(row) for row in rows)))
        self.assertEqual(result["matching_active_timing_index"], 11)
        self.assertEqual(result["selection_metadata"]["active_type"], 72)

    def test_incomplete_ambiguous_or_forged_active_match_is_rejected(self):
        cases = []
        missing = copy.deepcopy(self.catalog); missing["advertised_timings"].pop(); cases.append(missing)
        duplicate = copy.deepcopy(self.catalog); duplicate["advertised_timings"][1] = duplicate["advertised_timings"][0]; cases.append(duplicate)
        forged = copy.deepcopy(self.catalog); forged["matching_active_timing_index"] = 1; cases.append(forged)
        boolean = copy.deepcopy(self.catalog); boolean["active_timing"]["horizontal_skew"] = False; cases.append(boolean)
        for index, value in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.check(value)

    def test_cli_rejects_mismatch_and_preserves_existing_output(self):
        command = [sys.executable, str(ROOT / "tools/gauguin-display-profile.py"), str(self.dtb)]
        legacy = Path(os.environ["MODE_CONTRACT_LEGACY_PROFILE"])
        for options in ([], ["--refresh-catalog"]):
            old = subprocess.check_output([sys.executable, str(legacy), str(self.dtb), *options])
            self.assertEqual(subprocess.check_output(command + options), old)
        output = subprocess.check_output(command + ["--drm-mode-log", str(self.log_path)])
        self.assertEqual(json.loads(output)["drm_timing_contract"]["matched_modes"], 12)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.log"
            path.write_text(self.log.replace("1130 1142 1182", "1130 1143 1182"))
            result = subprocess.run(command + ["--drm-mode-log", str(path)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("horizontal_sync differs", result.stderr)


if __name__ == "__main__":
    unittest.main()
