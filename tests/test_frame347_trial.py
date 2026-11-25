"""Capture bounds and non-overlapping timing from synthetic inputs."""

from importlib import import_module
import unittest


capture = import_module('capture-core342-root').BASE
Refused = import_module('write_root_delta175v2').Refused
runner = import_module('run-frame347-trial')


class Frame347Trial(unittest.TestCase):
    def setUp(self):
        self.logs = dict(zip(sorted(capture.LOG_PATHS), (
            {'type':2,'flags':0,'data':{'logical':size}}
            for size in (35_572_424,50_910_668,2_742_485,80_491))))

    def test_combined_cap_accepts_observed_large_springboard(self):
        self.assertEqual(capture.combined_log_bytes(self.logs,134_217_728),89_306_068)
        self.assertEqual(capture.combined_log_bytes(self.logs,89_306_068),89_306_068)

    def test_combined_cap_refuses_oversize_or_unexpected_log_forks(self):
        with self.assertRaises(Refused):
            capture.combined_log_bytes(self.logs,89_306_067)
        path = '/private/var/log/springboard.log'
        for entry in (None,dict(self.logs[path],flags=0x20),dict(self.logs[path],type=1)):
            with self.subTest(entry=entry), self.assertRaises(Refused):
                capture.combined_log_bytes(dict(self.logs,**{path:entry}),134_217_728)

    def test_total_already_includes_commit(self):
        row = dict(own_exec_ns=15_000_000,exec_ns=[0,0,9_000_000,0,0,0,6_000_000,0],
                   newbo_counts=[0],program_slab_reuses=1)
        report = runner.job_times([row])
        self.assertEqual(report['recording_and_commit_ns']['p95'],15_000_000)
        self.assertEqual(report['recording_only_ns']['p95'],9_000_000)
        self.assertEqual(report['commit_only_ns']['p95'],6_000_000)
        self.assertEqual(report['warm_jobs_above_60_fps_budget'],0)
        with self.assertRaises(ValueError):
            runner.job_times([dict(row,own_exec_ns=21_000_000)])


if __name__ == '__main__':
    unittest.main()
