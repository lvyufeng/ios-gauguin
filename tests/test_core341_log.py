import ast
import importlib.util
from pathlib import Path
import sys
import unittest

WORK=Path(__file__).resolve().parents[1];sys.path.insert(0,str(WORK/'tools'))
import core341_log as LOG
spec=importlib.util.spec_from_file_location('base340_sample341',WORK/'tests/test_core340_log.py')
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)


def extra_values(draw=True,tick=None,job=3):
    x={k:(0 if k=='detail_flags' else [0]*n) for k,n in LOG.FIELDS}
    x['cpu_counts']=[1,1,2]
    if tick is not None:
        x['cpu_ns']=[0,0,tick,tick,0,0,0,0,0]
        if draw:
            x.update(address_counts=[2,0,2],table_counts=[1,1,0],piece_counts=[1,1,0],program_counts=[2,0,2,0,0,0,1,0,0,0,0,0,0,0])
            for k in ('address','table','piece'):x[k+'_max']=[job,tick,tick]+[0]*len(LOG.PARTS[k])
        return x
    x['cpu_ns']=[1000000,1003100,225000624600,225000628400,800,300,3000,0,2700]
    if draw:
        x.update(address_counts=[2,1,1],address_ns=[700,500,100,200],address_max=[3,225000272100,225000273000,100,500,100,200],
            resident_counts=[1,1,0],resident_ns=[50,50,200,150,50],resident_max=[3,225000272200,225000272700,50,50,200,150,50],
            table_counts=[1,1,0],table_ns=[300],table_max=[3,225000273700,225000274000,300],
            piece_counts=[1,1,0],piece_ns=[10,130,10,130],piece_max=[3,225000273710,225000273990,10,130,10,130],
            pool_counts=[1,1,0],pool_ns=[10,20,40,10,10,10],pool_max=[3,225000273740,225000273840,10,20,40,10,10,10],
            program_counts=[1,1,1,0,1,0,0,1,0,0,1,256,256,0])
    return x


def suffix(draw=True,tick=None,job=3):
    x=extra_values(draw,tick,job)
    return ''.join(' '+k+'='+ (str(x[k]) if k=='detail_flags' else ','.join(map(str,x[k]))) for k,_n in LOG.FIELDS)


def sample(draw=True):
    text=OLD.sample(draw)
    for tag in ('C4Q','Q','CR','N'):text=text.replace('GAUGUIN '+tag+'340:','GAUGUIN '+tag+'341:')
    return '\n'.join(line+suffix(draw) if line.startswith(LOG.PREFIX+'object=') else line for line in text.splitlines())+'\n'


class Core341Log(unittest.TestCase):
    def test_nonzero_nested_scopes_and_CPU_bounds(self):
        r=LOG.analyze(sample());self.assertTrue(r['coverage_qualified'],r['errors'])
        self.assertTrue(r['CPU_accounting']['observed']);self.assertTrue(r['program_detail']['observed'])
        self.assertEqual(r['metrics']['address_lookup_us']['p95'],.7)
        self.assertEqual(r['metrics']['resident_new_BO_us']['p95'],.2)
        self.assertEqual(r['metrics']['IO_CPU_lower_us']['p95'],.3)
        self.assertEqual(r['metrics']['IO_off_CPU_upper_us']['p95'],2.7)
        self.assertEqual(r['metrics']['IO_sampling_envelope_us']['p95'],.8)

    def test_zero_draw_and_zero_duration_fixtures(self):
        r=LOG.analyze(sample(False));self.assertTrue(r['coverage_qualified'],r['errors']);self.assertFalse(r['program_detail']['observed'])
        # Exercise the builder shape used only in synthetic pipeline fixtures.
        x=extra_values(tick=225000550000,job=3);self.assertEqual(x['address_counts'],[2,0,2])

    def test_program_mutations(self):
        changes=[('address_counts=2,1,1','address_counts=3,1,1'),('address_counts=2,1,1','address_counts=2,2,0'),
            ('resident_counts=1,1,0','resident_counts=0,0,0'),('resident_counts=1,1,0','resident_counts=1,0,1'),
            ('table_counts=1,1,0','table_counts=2,2,0'),('piece_counts=1,1,0','piece_counts=0,0,0'),
            ('pool_counts=1,1,0','pool_counts=2,2,0'),('pool_counts=1,1,0','pool_counts=1,0,1'),
            ('address_ns=700,500,100,200','address_ns=1000,500,100,200'),
            ('address_max=3,','address_max=4,'),('address_max=3,225000272100','address_max=3,225000260000'),
            ('225000273000,100,500','225000273001,100,500'),
            ('resident_ns=50,50,200,150,50','resident_ns=50,50,201,150,50'),
            ('table_ns=300','table_ns=301'),('table_max=3,','table_max=0,'),
            ('piece_max=3,','piece_max=4,'),('pool_max=3,','pool_max=4,'),
            ('program_counts=1,1,1,0,1,0,0,1,0,0,1,256,256,0','program_counts=0,1,1,0,1,0,0,1,0,0,1,256,256,0'),
            ('program_counts=1,1,1,0,1,0,0,1,0,0,1,256,256,0','program_counts=1,1,0,0,1,0,0,1,0,0,1,256,256,0'),
            ('program_counts=1,1,1,0,1,0,0,1,0,0,1,256,256,0','program_counts=1,1,1,0,1,0,0,0,0,0,1,256,256,0'),
            ('program_counts=1,1,1,0,1,0,0,1,0,0,1,256,256,0','program_counts=1,1,1,0,1,0,0,1,0,0,1,256,257,0'),
            ('program_counts=1,1,1,0,1,0,0,1,0,0,1,256,256,0','program_counts=1,1,1,0,1,0,0,1,0,1,0,256,256,0'),
            ('detail_flags=0','detail_flags=1'),('table_ns=300','table_ns=-1'),('table_ns=300','table_ns=18446744073709551616')]
        self.assertEqual(len(changes),25)
        for a,b in changes:
            with self.subTest(a=a,b=b):
                self.assertIn(a,sample());self.assertFalse(LOG.analyze(sample().replace(a,b))['coverage_qualified'])

    def test_aggregate_gap_is_not_invented_as_a_complete_job_trace(self):
        r=LOG.analyze(sample().replace('address_ns=700,500,100,200','address_ns=701,500,100,200'))
        self.assertTrue(r['coverage_qualified'],r['errors'])

    def test_CPU_mutations(self):
        original=extra_values()['cpu_ns']
        variants=[]
        for index,value in [(0,1003101),(1,1010000),(2,225000624499),(3,225000628501),(4,801),(5,301),(6,2999),(7,1),(8,2699)]:
            x=list(original);x[index]=value;variants.append(x)
        for x in variants:
            a='cpu_ns='+','.join(map(str,original));b='cpu_ns='+','.join(map(str,x))
            self.assertFalse(LOG.analyze(sample().replace(a,b))['coverage_qualified'])
        for a,b in [('cpu_counts=1,1,2','cpu_counts=1,0,2'),('cpu_counts=1,1,2','cpu_counts=1,1,1'),('cpu_counts=1,1,2','cpu_counts=0,0,0')]:
            self.assertFalse(LOG.analyze(sample().replace(a,b))['coverage_qualified'])

    def test_missing_duplicate_prior_or_overlong(self):
        base=sample();core=next(s for s in base.splitlines() if s.startswith(LOG.PREFIX))
        for text in [base.replace(' detail_flags=0',''),base+'\n'+core+'\n',base+'GAUGUIN CR341: limit=4096 coverage=incomplete\n',base.replace(' detail_flags=0',' detail_flags=0'+'x'*8192),OLD.sample()]:
            self.assertFalse(LOG.analyze(text)['coverage_qualified'])

    def test_inherited_340_and_339_contracts(self):
        # Reuse all existing nonzero errors; keep341 detail and CPU otherwise valid.
        tree=ast.parse((WORK/'tests/test_core340_log.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef));fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='test_contract_mutations')
        assignment=next(n for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mutations' for t in n.targets))
        pairs=ast.literal_eval(assignment.value);self.assertEqual(len(pairs),29)
        for a,b in pairs:self.assertFalse(LOG.analyze(sample().replace(a,b))['coverage_qualified'])
        tree=ast.parse((WORK/'tests/test_core_prof339_log.py').read_text().replace('339','341'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef));fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='test_contract_faults_are_rejected')
        assignment=next(n for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mutations' for t in n.targets))
        context={'base':sample(False)};exec(compile(ast.Module(body=[assignment],type_ignores=[]),'inherited339','exec'),context)
        self.assertEqual(len(context['mutations']),21)
        for text in context['mutations']:self.assertFalse(LOG.analyze(text)['coverage_qualified'])
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='test_category_and_submit_faults');loop=next(n for n in fn.body if isinstance(n,ast.For))
        pairs=ast.literal_eval(loop.iter);self.assertEqual(len(pairs),12)
        for a,b in pairs:self.assertFalse(LOG.analyze(sample(False).replace(a,b))['coverage_qualified'])
        self.assertFalse(LOG.analyze(sample(False).replace('submit_ns=10000,','submit_ns=18446744073709551616,'))['coverage_qualified'])

    def test_actual340_cannot_qualify341(self):
        p=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-draw-submit-worktree-20261117/research/tmp/draw-submit-340/execution/backboardd.log.current')
        self.assertFalse(LOG.analyze(p.read_text())['coverage_qualified'])

    def test_actual_CXX_formatter_only(self):
        p=WORK/'research/tmp/program-io-341/core-host-v3/program341-success.log'
        rows=[s for s in p.read_text().splitlines() if s.startswith(LOG.PREFIX+'object=')]
        self.assertEqual(len(rows),1);r=LOG.parse_extra(rows[0]);self.assertIsNotNone(r)
        self.assertEqual(r['cpu_counts'],[0,0,0]);self.assertEqual(r['detail_flags'],0)
        self.assertEqual(r['table_ns'],[0]);self.assertLessEqual(len(rows[0].encode())+1,8192)


if __name__=='__main__':unittest.main()
