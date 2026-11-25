import importlib.util
import ast
from pathlib import Path
import sys
import unittest

WORK=Path(__file__).resolve().parents[1];sys.path.insert(0,str(WORK/'tools'))
import core340_log as LOG
spec=importlib.util.spec_from_file_location('original339_sample340',WORK/'tests/test_core_prof339_log.py')
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)


def suffix(tick=None,draw=True):
    x={k:(0 if n==1 else [0]*n) for k,n in LOG.FIELDS}
    if tick is None:
        x.update(gpu_calls=1,gpu_ok=1,gpu_begin_ns=225000621000,gpu_end_ns=225000629000,
            gpu_ns=[1000,2000,500,4000,500],submit_reuse=[1,0,0,0],io_calls=1,
            io_begin_ns=225000625000,io_end_ns=225000628000,io_ns=3000,bo_uses=2,bo_unique=2,bo_comparisons=1,bo_mode=1)
        if draw:
            phases=[2000,5000,5000,4000,4000,15000,3000,2000]
            x.update(draw_calls=1,draw_ok=1,render_calls=1,render_ok=1,draw_ns=phases,
                render_ns=[1000,1000,2000,3000,5000,1000,1000,1000],draw_reuse=[1,0,4,0],
                draw_max_job=3,draw_max_start_ns=225000250000,draw_max_end_ns=225000290000,draw_max_ns=40000,draw_max_phases=phases)
    else:
        x.update(draw_calls=1,draw_ok=1,render_calls=1,render_ok=1,draw_reuse=[1,0,0,0],draw_max_job=1,
            draw_max_start_ns=tick,draw_max_end_ns=tick,gpu_calls=1,gpu_ok=1,gpu_begin_ns=tick,gpu_end_ns=tick,
            submit_reuse=[1,0,0,0],io_calls=1,io_begin_ns=tick,io_end_ns=tick,bo_unique=1,bo_mode=1)
    return ''.join(' '+k+'='+(','.join(map(str,x[k])) if n!=1 else str(x[k])) for k,n in LOG.FIELDS)


def sample(draw=True):
    text=OLD.sample().replace('339','340')
    if draw:
        text=text.replace(' counts=0,0,0,0,0,1,1,0',' counts=0,0,1,0,0,0,1,0')
        text=text.replace(' exec_ns=0,0,0,0,0,50000,150000,0',' exec_ns=0,0,50000,0,0,0,150000,0')
        text=text.replace(' max_exec_ns=0,0,0,0,0,50000,150000,0',' max_exec_ns=0,0,50000,0,0,0,150000,0')
    return '\n'.join(s+suffix(draw=draw) if s.startswith(LOG.PREFIX+'object=') else s for s in text.splitlines())+'\n'


class Core340Log(unittest.TestCase):
    def test_nested_scopes_and_actual_IO(self):
        r=LOG.analyze(sample());self.assertTrue(r['coverage_qualified'],r['errors'])
        self.assertTrue(r['worker_reuse']['observed'])
        for key,value in [('io_connect_us',3),('gpu_BO_list_us',2),('transport_outside_IO_us',1),('render_job_outside_common_us',10),('draw_render_body_us',15)]:
            self.assertEqual(r['metrics'][key]['p95'],value)

    def test_zero_draw_CB_keeps_independent_activation_gate(self):
        r=LOG.analyze(sample(False));self.assertTrue(r['coverage_qualified'],r['errors']);self.assertFalse(r['worker_reuse']['observed'])

    def test_local_and_oversize_fallbacks_are_explicit(self):
        for text in [sample().replace('bo_mode=1','bo_mode=0').replace('submit_reuse=1,0,0,0','submit_reuse=0,1,1,0'),
            sample().replace('bo_mode=1','bo_mode=2').replace('bo_unique=2','bo_unique=1025').replace('bo_uses=2','bo_uses=2000').replace('submit_reuse=1,0,0,0','submit_reuse=1,0,1,1')]:
            r=LOG.analyze(text);self.assertTrue(r['coverage_qualified'],r['errors'])

    def test_contract_mutations(self):
        mutations=[('draw_calls=1','draw_calls=2'),('draw_ok=1','draw_ok=0'),('render_calls=1','render_calls=2'),
            ('render_ok=1','render_ok=0'),('draw_max_job=3','draw_max_job=4'),('draw_max_ns=40000','draw_max_ns=40001'),
            ('draw_max_end_ns=225000290000','draw_max_end_ns=225000590000'),('draw_reuse=1,0,4,0','draw_reuse=0,0,4,0'),
            ('draw_reuse=1,0,4,0','draw_reuse=1,0,8,0'),('gpu_calls=1','gpu_calls=2'),('gpu_ok=1','gpu_ok=0'),
            ('gpu_end_ns=225000629000','gpu_end_ns=225000630000'),('gpu_ns=1000,2000,500,4000,500','gpu_ns=1000,2001,500,4000,500'),
            ('io_calls=1','io_calls=0'),('io_calls=1','io_calls=2'),('io_ns=3000','io_ns=2999'),
            ('io_begin_ns=225000625000','io_begin_ns=225000623000'),('io_end_ns=225000628000','io_end_ns=225000629000'),
            ('bo_unique=2','bo_unique=0'),('bo_unique=2','bo_unique=4'),('bo_mode=1','bo_mode=3'),
            ('bo_mode=1','bo_mode=2'),('submit_reuse=1,0,0,0','submit_reuse=0,1,0,0'),
            ('submit_reuse=1,0,0,0','submit_reuse=1,0,2,0'),('reserve_failures=0','reserve_failures=2'),
            ('fine_flags=0','fine_flags=1'),('draw_ns=2000,','draw_ns=200000,'),('render_ns=1000,','render_ns=100000,'),
            ('bo_uses=2','bo_uses=18446744073709551616')]
        self.assertEqual(len(mutations),29)
        for old,new in mutations:
            with self.subTest(old=old):self.assertFalse(LOG.analyze(sample().replace(old,new))['coverage_qualified'])

    def test_dropped_or_overlong_or_duplicate_rows(self):
        base=sample()
        for text in [base.replace(' fine_flags=0',''),base+'GAUGUIN CR340: limit=4096 coverage=incomplete\n',
            base+next(s for s in base.splitlines() if s.startswith(LOG.PREFIX))+'\n',base.replace(' fine_flags=0',' fine_flags=0'+'x'*4096)]:
            self.assertFalse(LOG.analyze(text)['coverage_qualified'])

    def test_completion_can_precede_notice(self):
        r=LOG.analyze(sample().replace('tick_us=225000750 state=3','tick_us=225001050 state=4'))
        self.assertTrue(r['coverage_qualified'],r['errors'])

    def test_inherited_339_error_contracts(self):
        tree=ast.parse((WORK/'tests/test_core_prof339_log.py').read_text().replace('339','340'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='test_contract_faults_are_rejected')
        assignment=next(n for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mutations' for t in n.targets))
        context={'base':sample(False)};exec(compile(ast.Module(body=[assignment],type_ignores=[]),'inherited339contracts','exec'),context)
        self.assertEqual(len(context['mutations']),21)
        for text in context['mutations']:self.assertFalse(LOG.analyze(text)['coverage_qualified'])
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='test_category_and_submit_faults')
        loop=next(n for n in fn.body if isinstance(n,ast.For))
        pairs=ast.literal_eval(loop.iter);self.assertEqual(len(pairs),12)
        for old,new in pairs:self.assertFalse(LOG.analyze(sample(False).replace(old,new))['coverage_qualified'])
        self.assertFalse(LOG.analyze(sample(False).replace('submit_ns=10000,','submit_ns=18446744073709551616,'))['coverage_qualified'])

    def test_actual339_is_not340_evidence(self):
        p=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-core-prof-worktree-20261117/research/tmp/core-prof-339/execution/backboardd.log.current')
        self.assertFalse(LOG.analyze(p.read_text())['coverage_qualified'])

    def test_actual_CXX_formatter_field_shape(self):
        p=WORK/'research/tmp/draw-submit-340/core-host-v2/phase340-success.log'
        rows=[s for s in p.read_text().splitlines() if s.startswith(LOG.PREFIX+'object=')]
        self.assertEqual(len(rows),1);x=LOG.parse_extra(rows[0]);self.assertIsNotNone(x)
        self.assertEqual(x['gpu_calls'],1);self.assertEqual(x['gpu_ok'],1);self.assertEqual(x['io_calls'],0)
        self.assertEqual(x['fine_flags'],0);self.assertLessEqual(len(rows[0].encode())+1,4096)


if __name__=='__main__':unittest.main()
