import copy
import importlib.util
from pathlib import Path
import sys
import unittest

WORK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(WORK/'tools'))


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


REPORT=module('host_report339',WORK/'tools/summarize-core339-results.py')
SAMPLE=module('codec_sample339',WORK/'tests/test_core_prof339_log.py')
BOUNDS=(225000000,225002000)


class Core339Report(unittest.TestCase):
    def test_nonzero_independent_partitions(self):
        core=REPORT.CORE.analyze(SAMPLE.sample());summary,rows,tail=REPORT.timeline(core,BOUNDS)
        self.assertEqual(summary['other_metrics']['done_us']['p95'],850)
        self.assertEqual(sum(summary['p95_buffer']['components'].values()),850)
        split=REPORT.attribution(core,rows,tail)['full_script']
        self.assertEqual(split['queue_wait_sum_us'],200)
        self.assertEqual(split['observed_body_sum_us'],150)
        self.assertEqual(split['uncovered_sum_us'],50)
        self.assertEqual(split['wait_category_sums_us']['render'],150)
        self.assertEqual(split['own_body_category_sums_us']['transfer_append'],50)
        self.assertEqual(sum(split['submit_phase_sums_us'].values()),80)
        self.assertEqual(split['commit_outside_submit_sum_us'],70)

    def test_signed_completion_overlap_is_preserved(self):
        text=SAMPLE.sample().replace('end_ns=225000700000','end_ns=225001200000')
        text=text.replace('own_exec_ns=200000','own_exec_ns=700000').replace('50000,150000,0','50000,650000,0')
        text=text.replace('tick_us=225000750 state=3','tick_us=225001250 state=4')
        core=REPORT.CORE.analyze(text);self.assertTrue(core['coverage_qualified'],core['errors'])
        summary,_,_=REPORT.timeline(core,BOUNDS)
        self.assertEqual(summary['p95_buffer']['components']['body_end_to_timeline_us'],-250)
        self.assertEqual(summary['signed_body_end_after_timeline_count'],1)
        self.assertEqual(sum(summary['p95_buffer']['components'].values()),850)

    def test_known_job_is_only_partial_wait_evidence(self):
        core=REPORT.CORE.analyze(SAMPLE.sample());_,rows,tail=REPORT.timeline(core,BOUNDS)
        # Minimal known-interval fixture for arithmetic only, never device evidence.
        fake=copy.deepcopy(core)
        fake['rows'].append(dict(queue=1,max_job=2,max_class=2,max_start_ns=225000360000,max_end_ns=225000460000))
        split=REPORT.attribution(fake,rows,tail)['full_script']
        self.assertEqual(split['known_worst_job_covered_wait_us']['render'],100)
        self.assertTrue(split['known_job_evidence_is_partial'])
        fake['rows'][-1]['queue']=2
        self.assertEqual(sum(REPORT.attribution(fake,rows,tail)['full_script']['known_worst_job_covered_wait_us'].values()),0)

    def test_impossible_known_coverage_refused(self):
        core=REPORT.CORE.analyze(SAMPLE.sample());_,rows,tail=REPORT.timeline(core,BOUNDS)
        fake=copy.deepcopy(core)
        fake['rows'].append(dict(queue=1,max_job=2,max_class=2,max_start_ns=225000350000,max_end_ns=225000550000))
        with self.assertRaises(AssertionError):REPORT.attribution(fake,rows,tail)


if __name__=='__main__':unittest.main()
