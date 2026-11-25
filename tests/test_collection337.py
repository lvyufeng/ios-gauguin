#!/usr/bin/env python3
"""Collection faults must prevent interpretation, including whole-group loss."""
from pathlib import Path
import copy,importlib.util,unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
C=load('collection337',ROOT/'tools/collection337.py')
B=load('backlog337',ROOT/'tools/queue337_backlog.py')

class Collection(unittest.TestCase):
    def setUp(self):
        self.args=dict(trace=dict(header=dict(version=2,reason=1,lost=0,count=100),clock_valid=True,truncated_by_capacity=False),
            springboard=dict(lost_rows_in_log_tail=0,input=dict(hook_active=True,watch_covers_window=True,
                metadata_errors_in_tail=0,write_errors_in_tail=0,unpaired_entry_ids=[],unpaired_end_ids=[],
                callbacks_with_original_exception=0,entries_in_window=1,entries=[dict(flags=0)])),
            c4=dict(coverage_qualified=True,complete_cb_count=1),identity=dict(coverage_qualified=True,records=3),
            allocation=dict(coverage_qualified=True,complete_count=5,partial_count=1),prefix_ok=True,bounds=[226000000,259000000])
    def test_valid_bounded_capture(self):self.assertTrue(C.assess(**self.args)['coverage_qualified'])
    def test_mutations_withhold_interpretation(self):
        changes=[('trace.header.version',1),('trace.header.lost',1),('trace.header.reason',2),('trace.header.reason',3),
            ('trace.header.count',4096),('trace.clock_valid',False),('trace.truncated_by_capacity',True),
            ('allocation.coverage_qualified',False),('c4.coverage_qualified',False),('identity.coverage_qualified',False),
            ('identity.records',2),('identity.queues',[dict(unobserved_ticket_ranges=[[1,3]])]),
            ('prefix_ok',False),('bounds',None),('bounds',[219999999,259000000]),
            ('springboard.lost_rows_in_log_tail',1),('springboard.input.hook_active',False),
            ('springboard.input.watch_covers_window',False),('springboard.input.metadata_errors_in_tail',1),
            ('springboard.input.write_errors_in_tail',1),('springboard.input.unpaired_entry_ids',[1]),
            ('springboard.input.unpaired_end_ids',[1]),('springboard.input.entries_in_window',0),
            ('springboard.input.callbacks_with_original_exception',1),('springboard.input.entries',[dict(flags=8)])]
        for path,value in changes:
            args=copy.deepcopy(self.args);d=args;parts=path.split('.')
            for part in parts[:-1]:d=d[part]
            d[parts[-1]]=value;result=C.assess(**args)
            self.assertFalse(result['coverage_qualified'],path)
            self.assertEqual(B.analyze(result,None,None)['state'],'Q337-backlog-interpretation-withheld')
    def test_actual336_is_not_requalified(self):
        prior=ROOT.parent/'gauguin-cache-adapt-worktree-20261116/research/tmp/bo-reuse-336/execution'
        import json
        c4=json.loads((prior/'c4-queue-analysis.json').read_text())
        q=load('identity337',ROOT/'tools/analyze-queue337.py').analyze((prior/'backboardd.log.current').read_text())
        result=C.analyze((prior/'kernel.log').read_text(),(prior/'backboardd.log.current').read_text(),
            (prior/'springboard-new.log').read_text(),True,json.loads((prior/'bo-allocation-analysis.json').read_text()),c4,q)
        self.assertFalse(result['coverage_qualified']);self.assertIn('kernel-record-loss',result['errors'])
        self.assertIn('SpringBoard-record-loss',result['errors']);self.assertIn('queue-identity-coverage',result['errors'])

class QueueAttribution(unittest.TestCase):
    def test_other_queue_body_cannot_explain_wait(self):
        # The independent metadata says queue2 was busy during queue1's wait.
        # Only queue1's own predecessor may be attributed to that wait.
        c4=[];ids=[]
        for obj,made,queue,ticket,admit,entry,retire in [
            ('0x1',220000001,1,1,220000002,220000010,220000050),
            ('0x2',220000003,1,2,220000020,220000060,220000090),
            ('0x3',220000004,2,1,220000005,220000011,220000059)]:
            t={0:admit,1:entry,2:entry+1,3:entry+2,4:retire-1,5:retire+1,6:retire+2,7:retire+4}
            c4.append(dict(object=obj,made_us=made,times_us=t,existing_timeline=dict(done_us=retire+3)))
            ids.append(dict(object=obj,made_us=made,queue=queue,ticket=ticket,admit_us=admit,
                entry_us=entry+1,retire_us=retire,earlier_unretired_at_admission=ticket-1))
        r=B.analyze(dict(coverage_qualified=True,script_window_us=[220000000,220000100]),
                    dict(coverage_qualified=True,buffers=c4),dict(coverage_qualified=True,buffers=ids))
        q1=r['queues'][0]['longest_queues'][0]
        self.assertEqual(q1['ticket'],2);self.assertEqual(q1['observed_same_queue_body_us'],30)
        self.assertEqual(q1['uncovered_wait_us'],10)
        self.assertEqual(sum(q1['wait_components_us'].values()),30)
        self.assertEqual(r['script_buffers'],3)

if __name__=='__main__':unittest.main()
