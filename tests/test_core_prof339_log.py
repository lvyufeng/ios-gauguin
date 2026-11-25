import importlib.util
from pathlib import Path
import unittest

WORK=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('core339_test',WORK/'tools/core339_log.py')
LOG=importlib.util.module_from_spec(spec);spec.loader.exec_module(LOG)


def sample():
    obj='0x1234';made=225000000;t=[225000100,225000200,225000300,225000400,225000500,225000850,225000900,225001000]
    rows=[f'GAUGUIN C4Q339: phase={i} object={obj} start_us={made} end_us={v} value=0' for i,v in enumerate(t)]
    rows += [f'tl: M made {made} committed {t[0]} done 225000950 gpu 500']
    rows += [f'GAUGUIN Q339: stage={i} object={obj} made_us={made} queue=1 ticket=1 retired={retired} tick_us={tick}'
             for i,retired,tick in [(0,0,225000150),(1,0,225000250),(2,1,225000650)]]
    rows += [f'GAUGUIN CR339: object={obj} made_us={made} queue=1 ticket=1 job=4 enq_ns=225000350000 start_ns=225000550000 end_ns=225000700000 busy_wait_ns=150000 jobs=2 own_exec_ns=200000 sum_queue_ns=300000 max_queue_ns=250000 state=3 failed=0',
             f'GAUGUIN N339: object={obj} made_us={made} tick_us=225000750 state=3']
    extra=' counts=0,0,0,0,0,1,1,0 exec_ns=0,0,0,0,0,50000,150000,0 wait_ns=0,0,150000,0,0,0,0,0 max_exec_ns=0,0,0,0,0,50000,150000,0 max_class=6 max_job=4 max_enq_ns=225000350000 max_start_ns=225000550000 max_end_ns=225000700000 submit_mask=255 submit_outcome=0 submit_begin_ns=225000560000 submit_end_ns=225000640000 submit_ns=10000,10000,10000,10000,10000,10000,10000,10000 flags=0'
    rows=[row+extra if row.startswith('GAUGUIN CR339: object=') else row for row in rows]
    return '\n'.join(rows)+'\n'


class Core339Log(unittest.TestCase):
    def test_wait_and_execution_split(self):
        r=LOG.analyze(sample());self.assertTrue(r['coverage_qualified'],r)
        row=r['rows'][0]
        self.assertEqual((row['core_queue_wait_us'],row['core_observed_busy_in_wait_us'],
                          row['core_uncovered_queue_wait_us'],row['core_commit_execution_us']),
                         (200,150,50,150))
        self.assertEqual(row['frontend_body_us'],450)
        self.assertNotIn('core_status_drain',r['lifecycle']['stage_us'])
        self.assertEqual(r['lifecycle']['stage_us']['notification_admission']['median'],100)
        self.assertFalse(r['physical_FPS_qualified'])

    def test_callback_branch_may_enter_before_notice(self):
        text=sample().replace('end_us=225000850','end_us=225000600')
        self.assertTrue(LOG.analyze(text)['coverage_qualified'])

    def test_notice_may_follow_entire_completion_and_frontend_retirement(self):
        text=sample().replace('tick_us=225000750 state=3','tick_us=225001050 state=4')
        self.assertTrue(LOG.analyze(text)['coverage_qualified'])

    def test_old_wire_not_accepted(self):
        text=sample().replace('C4Q339','C4Q321').replace('Q339:','Q337:')
        self.assertFalse(LOG.analyze(text)['coverage_qualified'])

    def test_contract_faults_are_rejected(self):
        base=sample()
        mutations=[
            base.replace('ticket=1 job=4','ticket=2 job=4'),
            base.replace('busy_wait_ns=150000','busy_wait_ns=300000'),
            base.replace('own_exec_ns=200000','own_exec_ns=100000'),
            base.replace('max_queue_ns=250000','max_queue_ns=100000'),
            base.replace('failed=0','failed=1'),
            base.replace('state=3 failed=0','state=5 failed=0'),
            base.replace('tick_us=225000750 state=3','tick_us=225000650 state=3'),
            base.replace('tick_us=225000750 state=3','tick_us=900000001 state=3'),
            base.replace('enq_ns=225000350000','enq_ns=225000450000'),
            base.replace('start_ns=225000550000','start_ns=225000100000'),
            base.replace('end_ns=225000700000','end_ns=901000000000'),
            base.replace('jobs=2','jobs=0'),
            base.replace('phase=4 object=0x1234 start_us=225000000 end_us=225000500 value=0',
                         'phase=4 object=0x1234 start_us=225000000 end_us=225000500 value=3'),
            base+'GAUGUIN CR339: limit=4096 coverage=incomplete\n',
            base+'GAUGUIN N339: limit=4096 coverage=incomplete\n',
            base+'GAUGUIN CR339: formatting=failed coverage=incomplete\n',
            base+'GAUGUIN N339: object=0x1234 made_us=225000000 tick_us=225000750 state=3\n',
            '\n'.join(l for l in base.splitlines() if not l.startswith('GAUGUIN CR339:')),
            '\n'.join(l for l in base.splitlines() if not l.startswith('GAUGUIN N339:')),
            '\n'.join(l for l in base.splitlines() if not l.startswith('GAUGUIN C4Q339: phase=6')),
            '\n'.join(l for l in base.splitlines() if not l.startswith('tl: M')),
        ]
        for n,text in enumerate(mutations):
            with self.subTest(n=n):self.assertFalse(LOG.analyze(text)['coverage_qualified'])

    def test_category_and_submit_faults(self):
        for old,new in [('counts=0,0,0,0,0,1,1,0','counts=0,0,0,0,0,2,1,0'),
            ('exec_ns=0,0,0,0,0,50000,150000,0','exec_ns=0,0,0,0,0,50001,150000,0'),
            ('wait_ns=0,0,150000,0,0,0,0,0','wait_ns=0,0,149999,0,0,0,0,0'),
            ('max_class=6','max_class=5'),('max_job=4','max_job=5'),
            ('max_job=4','max_job=3'),('max_enq_ns=225000350000','max_enq_ns=225000350001'),
            ('submit_mask=255','submit_mask=127'),('submit_outcome=0','submit_outcome=2'),
            ('submit_end_ns=225000640000','submit_end_ns=225000640001'),('flags=0','flags=1'),
            ('max_exec_ns=0,0,0,0,0,50000,150000,0','max_exec_ns=0,0,0,0,0,60000,150000,0')]:
            with self.subTest(old=old):self.assertFalse(LOG.analyze(sample().replace(old,new))['coverage_qualified'])
        self.assertFalse(LOG.analyze(sample().replace('submit_ns=10000,','submit_ns=18446744073709551616,'))['coverage_qualified'])

    def test_recording_job_can_be_longer_than_commit(self):
        text=sample().replace('own_exec_ns=200000','own_exec_ns=350000').replace('50000,150000,0','200000,150000,0')
        text=text.replace('max_class=6','max_class=5').replace('max_job=4','max_job=3')
        text=text.replace('max_enq_ns=225000350000','max_enq_ns=225000100000').replace('max_start_ns=225000550000','max_start_ns=225000200000').replace('max_end_ns=225000700000','max_end_ns=225000400000')
        result=LOG.analyze(text);self.assertTrue(result['coverage_qualified'],result['errors'])
        self.assertEqual(result['rows'][0]['max_transfer_append_us'],200)

    def test_mixed_categories_partition_busy_residence(self):
        text=sample().replace('wait_ns=0,0,150000,0,0,0,0,0','wait_ns=0,100000,0,0,50000,0,0,0')
        result=LOG.analyze(text);self.assertTrue(result['coverage_qualified'],result['errors'])
        self.assertEqual(result['rows'][0]['wait_bindings_us'],100)
        self.assertEqual(result['rows'][0]['wait_compute_us'],50)

    def test_actual338_is_not339_coverage(self):
        p=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-core-async-worktree-20261117/research/tmp/core-async-338/execution/backboardd.log.current')
        self.assertFalse(LOG.analyze(p.read_text())['coverage_qualified'])

    def test_actual337_is_not339_coverage(self):
        p=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337/execution/backboardd.log.current')
        self.assertFalse(LOG.analyze(p.read_text())['coverage_qualified'])


if __name__=='__main__':unittest.main()
