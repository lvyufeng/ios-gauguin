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


REPORT=module('host_report340',WORK/'tools/summarize-core340-results.py')
SAMPLE=module('codec_sample340',WORK/'tests/test_core340_log.py')
BOUNDS=(225000000,225002000)


class Core340Report(unittest.TestCase):
    def test_nonzero_independent_partitions(self):
        core=REPORT.CORE.analyze(SAMPLE.sample());summary,rows,tail=REPORT.timeline(core,BOUNDS)
        self.assertEqual(summary['other_metrics']['done_us']['p95'],850)
        self.assertEqual(sum(summary['p95_buffer']['components'].values()),850)
        split=REPORT.attribution(core,rows,tail)['full_script']
        self.assertEqual(split['queue_wait_sum_us'],200)
        self.assertEqual(split['observed_body_sum_us'],150)
        self.assertEqual(split['uncovered_sum_us'],50)
        self.assertEqual(split['wait_category_sums_us']['render'],150)
        self.assertEqual(split['own_body_category_sums_us']['render'],50)
        self.assertEqual(sum(split['submit_phase_sums_us'].values()),80)
        self.assertEqual(split['commit_outside_submit_sum_us'],70)

    def test_signed_completion_overlap_is_preserved(self):
        text=SAMPLE.sample(False).replace('end_ns=225000700000','end_ns=225001200000')
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

    def test_nested_fine_sums_and_reuse_counters(self):
        core=REPORT.CORE.analyze(SAMPLE.sample());rows=core['rows'];r=REPORT.fine_aggregate(rows)
        self.assertEqual(r['draw_common_total_us'],40)
        self.assertEqual(r['render_body_total_us'],15)
        self.assertEqual(r['render_job_outside_common_us'],10)
        self.assertEqual(r['GPU_submit_total_us'],8)
        self.assertEqual(r['actual_IO_elapsed_sum_us'],3)
        self.assertEqual(r['transport_outside_IO_us'],1)
        self.assertEqual(r['native_submit_outside_GPU_probe_us'],2)
        self.assertEqual(r['draw_vector_growths'],4)
        self.assertEqual(r['submit_vector_growths'],0)
        self.assertEqual(r['warm_indexed_submits'],1)
        self.assertEqual(r['IO_share_of_GPU_submit'],.375)

    def wait_fixture(self):
        target=copy.deepcopy(REPORT.CORE.analyze(SAMPLE.sample())['rows'][0])
        target['wait_ns']=[0,0,100000,0,0,0,50000,0]
        known=copy.deepcopy(target)
        known.update(job=2,ticket=1,draw_max_job=1,draw_max_start_ns=225000360000,
            draw_max_end_ns=225000460000,draw_max_phases=[10000,20000,10000,10000,30000,10000,5000,5000],
            gpu_begin_ns=225000470000,gpu_end_ns=225000520000,gpu_ns=[10000,10000,10000,15000,5000],
            io_begin_ns=225000500000,io_end_ns=225000510000)
        # Explicit arithmetic-only intervals, not a parsed/device observation.
        return dict(rows=[known,target]),[target]

    def test_absolute_draw_and_IO_overlap_is_exact(self):
        core,rows=self.wait_fixture();r=REPORT.known_wait_evidence(core,rows)
        self.assertEqual(sum(r['draw_common_phase_covered_wait_us'].values()),100)
        self.assertEqual(r['draw_common_phase_covered_wait_us']['vertex_bindings'],20)
        self.assertEqual(r['BO_list_covered_wait_us'],10)
        self.assertEqual(r['IO_covered_wait_us'],10)
        self.assertEqual(r['other_GPU_submit_covered_wait_us'],30)
        self.assertTrue(r['evidence_is_partial'])
        core['rows'][0]['queue']=2
        r=REPORT.known_wait_evidence(core,rows)
        self.assertEqual(sum(r['draw_common_phase_covered_wait_us'].values()),0)
        self.assertEqual(r['IO_covered_wait_us'],0)

    def test_fine_overlap_cannot_exceed_recorded_category(self):
        core,rows=self.wait_fixture();rows[0]['wait_ns'][2]=99999
        with self.assertRaises(AssertionError):REPORT.known_wait_evidence(core,rows)

    def test_fine_nested_scope_cannot_exceed_outer_body(self):
        core=REPORT.CORE.analyze(SAMPLE.sample());rows=copy.deepcopy(core['rows'])
        rows[0]['io_ns']=5000
        with self.assertRaises(AssertionError):REPORT.fine_aggregate(rows)


if __name__=='__main__':unittest.main()
