"""Nonzero interval placement and identity tests for the read-only report."""
import importlib.util
from pathlib import Path
import sys
import unittest

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
spec=importlib.util.spec_from_file_location('program341_report',TOOLS/'summarize-program-io341-results.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)


def row(queue=1,ticket=1,job=10,begin=12000,end=18000,lower=2000,upper=4000):
    duration=end-begin
    r=dict(queue=queue,ticket=ticket,job=job,enq_ns=0,start_ns=10000,end_ns=11000,
        core_queue_wait_us=10,io_begin_ns=begin,io_end_ns=end,io_ns=duration,
        cpu_counts=[1,1,2],cpu_ns=[0,(lower+upper)//2,begin-100,end+100,200,
            lower,upper,duration-upper,duration-lower],
        exec_ns=[0,0,1000,0,0,0,1000,0],wait_ns=[0]*8,program_counts=[0]*14)
    for key,parts in R.CORE.PARTS.items():
        r[key+'_counts']=[0,0,0];r[key+'_ns']=[0]*len(parts);r[key+'_max']=[0]*(len(parts)+3)
    return r


class ReportIntervals(unittest.TestCase):
    def test_full_interval_preserves_nonzero_bounds(self):
        self.assertEqual(R.partial_bounds(10000,4000,7000,10000),((4000,7000),(3000,6000)))

    def test_partial_interval_uses_adversarial_placement(self):
        self.assertEqual(R.partial_bounds(10000,4000,7000,9000),((3000,7000),(2000,6000)))
        self.assertEqual(R.partial_bounds(10000,4000,7000,2000),((0,2000),(0,2000)))

    def test_zero_and_invalid_intervals(self):
        self.assertEqual(R.partial_bounds(10000,4000,7000,0),((0,0),(0,0)))
        with self.assertRaises(AssertionError):R.partial_bounds(10,8,7,5)
        with self.assertRaises(AssertionError):R.partial_bounds(10,4,7,11)

    def test_exact_phase_placement_not_duration_scaling(self):
        self.assertEqual(R.phase_overlaps(100,[20,30,0,50],125,165),[0,25,0,15])
        self.assertEqual(R.phase_overlaps(100,[20,30],0,100),[0,0])

    def test_IO_intersection_respects_queue_and_predecessor_identity(self):
        prior=row();other=row(queue=2);later=row(job=30)
        waiting=row(job=20,ticket=2,begin=19000,end=20000,lower=200,upper=600)
        waiting.update(enq_ns=14000,start_ns=19000,core_queue_wait_us=5,wait_ns=[0,0,0,0,0,0,5000,0])
        result=R.weighted_wait({'rows':[prior,other,later,waiting]},[waiting])
        self.assertEqual(result['known_IO_overlap_sum_us'],4)
        self.assertEqual(result['known_IO_CPU_sum_bounds_us'],[0,4])
        self.assertEqual(result['known_IO_off_CPU_sum_bounds_us'],[0,4])
        self.assertEqual([r['job'] for r in result['longest_waits'][0]['known_IO']],[10])

    def test_whole_window_CPU_and_offCPU_complement(self):
        a=row();b=row(ticket=2,job=20,lower=1000,upper=3000)
        result=R.detail([a,b])['IO']
        self.assertEqual(result['wall_sum_us'],12)
        self.assertEqual(result['CPU_sum_bounds_us'],[3,7])
        self.assertEqual(result['off_CPU_sum_bounds_us'],[5,9])
        self.assertEqual(result['CPU_sum_bounds_us'][0]+result['off_CPU_sum_bounds_us'][1],12)

    def test_nested_program_groups_are_not_summed(self):
        a=row();a['address_counts']=[1,1,0];a['address_ns']=[100,500,100,100]
        a['address_max']=[3,1000,1800,100,500,100,100]
        a['resident_counts']=[1,1,0];a['resident_ns']=[10,20,30,40,0]
        a['resident_max']=[3,1100,1200,10,20,30,40,0]
        result=R.detail([a]);self.assertTrue(result['nested_scopes_not_additive'])
        self.assertEqual(result['program_scopes']['address']['wall_sum_us'],.8)
        self.assertEqual(result['program_scopes']['resident']['wall_sum_us'],.1)
        self.assertEqual(result['program_scopes']['address']['longest_calls'][0]['job'],3)

    def test_burst_requires_consecutive_tickets_and_reports_growth(self):
        rows=[]
        for i in range(12):
            r=row(ticket=i+1,job=2*i+10,begin=5000+12000*i,end=6000+12000*i,lower=400,upper=600)
            r.update(enq_ns=i*10000,start_ns=5000+12000*i,end_ns=6000+12000*i,
                core_queue_wait_us=5+2*i)
            rows.append(r)
        result=R.bursts(rows)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['average_commit_arrival_interval_us'],10)
        self.assertEqual(result[0]['average_commit_start_interval_us'],12)
        self.assertEqual(result[0]['queue_wait_growth_us'],22)
        rows[-1]['ticket']+=1
        self.assertEqual(R.bursts(rows),[])


if __name__=='__main__':unittest.main()
