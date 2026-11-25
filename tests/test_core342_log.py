"""Synthetic contracts only; never 0342 device performance evidence."""
import copy
import importlib.util
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

WORK=Path(__file__).resolve().parents[1];sys.path.insert(0,str(WORK/'tools'))
import core342_log as LOG
import collection342 as COLLECTION
import kernel342_log as KERNEL
from phase342_log import partition
spec=importlib.util.spec_from_file_location('sample341_for342',WORK/'tests/test_core341_log.py')
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)


def values(draw=True,tick=None,job=3,index=1,program_miss=None):
    x={k:(0 if n==1 else [0]*n) for k,n in LOG.FIELDS}
    x['io_identity']=[1234,1,200+index,0,16,index]
    miss=draw if program_miss is None else program_miss
    if not miss:return x
    first=tick if tick is not None else 225000272230
    query=0 if tick is not None else 10;work=0 if tick is not None else 10
    begin=[0]*6;end=[0]*6;at=first
    for i in range(5):begin[i]=at+query;end[i]=begin[i]+work;at=end[i]
    last=at+query;cpu=[work//2]*5+[0];env=[2*query]*5+[0]
    x.update(newbo_counts=[1,1,0,6,6*query],newbo_wall=[work]*5+[0],newbo_cpu=cpu,newbo_envelope=env,
        newbo_max=[job,1234,100,4096,first,last,31,6,6*query,0],newbo_begin=begin,newbo_end=end,
        newbo_max_cpu=cpu,newbo_max_envelope=env)
    return x


def suffix(draw=True,tick=None,job=3,index=1,program_miss=None):
    x=values(draw,tick,job,index,program_miss)
    return ''.join(' '+k+'='+(','.join(map(str,x[k])) if n!=1 else str(x[k])) for k,n in LOG.FIELDS)


def sample(draw=True):
    text=OLD.sample(draw)
    for tag in ('C4Q','Q','CR','N'):text=text.replace('GAUGUIN '+tag+'341:','GAUGUIN '+tag+'342:')
    return '\n'.join(s+suffix(draw) if s.startswith(LOG.PREFIX+'object=') else s for s in text.splitlines())+'\n'


def kernel_row(selector,first,handle,size,queue=0,fence=0,bos=0,cmds=0,zero=False):
    mask={66:4095,67:2063,70:4095,256:2111}[selector];begin=[0]*12;end=[0]*12;cpu=[0]*12;envelope=[0]*12
    at=first;indices=[i for i in range(12) if mask>>i&1]
    for i in indices:
        begin[i]=at+(0 if zero else 1);end[i]=begin[i]+(0 if zero else 1);at=end[i]
        cpu[i]=0;envelope[i]=0 if zero else 2
    last=at+(0 if zero else 1)
    return dict(index=0,token=1,pid=57,tid=1234,selector=selector,queue=queue,fence=fence,handle=handle,
        bytes=size,bos=bos,cmds=cmds,result=0,first_ns=first,last_ns=last,query_ns=0 if zero else len(indices)+1,
        queries=len(indices)+1,mask=mask,flags=0,wait_ns=0,waits=0,begin=begin,end=end,cpu=cpu,envelope=envelope)


def kernel_stream(rows,prefix=''):
    lines=[]
    for i,r in enumerate(rows):
        r=dict(r,index=i,token=i+1)
        lines.append(KERNEL.PREFIX+'row '+ ' '.join(k+'='+(','.join(map(str,r[k])) if n!=1 else str(r[k])) for k,n in KERNEL.FIELDS))
    n=len(rows);size=sum(len(s.encode())+2 for s in lines)
    first=f'SWEET IO342: begin version=1 first_ns=210000000000 last_ns=270000000000 count={n} capacity=4096 lost=0 pending=0 invalid=0 row_bytes={size} byte_limit=2097152 byte_limited=0'
    end=f'SWEET IO342: end count={n} lost=0 pending=0 invalid=0 emitted={n} byte_limited=0'
    text=prefix+'\n'+first+'\n\n'+'\n\n'.join(lines)+'\n\n'+end+'\n';raw=text.encode();assert len(raw)<=4194304
    return text,ring_for(text)


def ring_for(text):
    raw=text.encode();assert len(raw)<=4194304
    header=struct.pack('<8sIIQQ',b'SWEETLOG',1,4194304,len(raw),1)
    return header+bytes(4096-len(header))+raw+bytes(4194304-len(raw))


def matching(core):
    rows=[]
    for r in core['rows']:
        tid,q,h,offset,words,fence=r['io_identity']
        rows.append(kernel_row(70,r['io_begin_ns']+1,h,4*words,q,fence,r['bo_unique'],1))
        if r['newbo_counts'][0]:
            for i,selector in ((1,66),(2,67),(3,256)):
                # Tiny synthetic parent phase: use zero-width child callback.
                rows.append(kernel_row(selector,r['newbo_begin'][i],r['newbo_max'][2],
                    0 if selector==67 else r['newbo_max'][3],zero=True))
    return rows


class Core342Log(unittest.TestCase):
    def test_program_slab_miss_preserves_exact_join(self):
        text=sample().replace(suffix(),suffix(program_miss=False)+' program_slab_reuses=1')
        result=LOG.analyze(text,program_slabs=True)
        self.assertTrue(result['coverage_qualified'],result['errors'])
        self.assertEqual(result['newbo_detail']['slab_reuses'],1)
        self.assertEqual(result['newbo_detail']['calls'],0)
        self.assertFalse(LOG.analyze(text)['coverage_qualified'])
        self.assertFalse(LOG.analyze(text.replace('program_slab_reuses=1','program_slab_reuses=0'),
                                     program_slabs=True)['coverage_qualified'])
        wire,raw=kernel_stream(matching(result))
        joined=KERNEL.join(KERNEL.parse(wire,raw),result,(225000000,226000000))
        self.assertTrue(joined['coverage_qualified'],joined['errors'])
        self.assertEqual(joined['program_maximum_join_count'],0)

    def test_collection_requires_program_activity_for_selected_wire(self):
        text = sample().replace(suffix(), suffix(program_miss=False) + ' program_slab_reuses=1')
        core = LOG.analyze(text, program_slabs=True)
        wire, raw = kernel_stream(matching(core))
        stream = KERNEL.parse(wire, raw)
        join = KERNEL.join(stream, core, (225000000, 226000000))
        c4 = {'complete_cb_count': core['complete_count']}

        def collect(core, *, program_slabs=False, kernel_join=join):
            with patch.object(COLLECTION.BASE, 'analyze', side_effect=lambda *_: {'errors': []}):
                return COLLECTION.analyze(wire, text, '', True, {}, c4, {}, core, stream, kernel_join,
                                          program_slabs=program_slabs)

        result = collect(core, program_slabs=True)
        self.assertTrue(result['coverage_qualified'], result['errors'])
        self.assertFalse(collect(core)['coverage_qualified'])
        self.assertFalse(collect(core, program_slabs=True, kernel_join={})['coverage_qualified'])
        for reuse in (0, None, True):
            without_reuse = dict(core, newbo_detail=dict(core['newbo_detail'], slab_reuses=reuse))
            self.assertFalse(collect(without_reuse, program_slabs=True)['coverage_qualified'])
        damaged = dict(core, coverage_qualified=False)
        self.assertFalse(collect(damaged, program_slabs=True)['coverage_qualified'])
        legacy = LOG.analyze(sample())
        self.assertTrue(collect(legacy)['coverage_qualified'])

    def test_nonzero_newbo_and_IO_identity(self):
        r=LOG.analyze(sample());self.assertTrue(r['coverage_qualified'],r['errors']);self.assertTrue(r['newbo_detail']['observed'])
        self.assertEqual(r['metrics']['newbo_GemNew_us']['p95'],.01)
        r=LOG.analyze(sample(False));self.assertTrue(r['coverage_qualified'],r['errors']);self.assertFalse(r['newbo_detail']['observed'])

    def test_each_new_field_mutations(self):
        base=sample();x=values()
        changes=0
        for key,n in LOG.FIELDS:
            for i in range(n):
                v=copy.deepcopy(x);old=copy.deepcopy(v[key])
                if n==1:v[key]=1
                else:v[key][i]+=1 if key not in ('newbo_cpu','newbo_max_cpu') else 100000
                a=' '+key+'='+(','.join(map(str,old)) if n!=1 else str(old))
                b=' '+key+'='+(','.join(map(str,v[key])) if n!=1 else str(v[key]))
                if a==b:continue
                # Legal numeric identity changes are rejected by the kernel join,
                # not by invented relationships in the user-only decoder.
                if key=='io_identity' or (key=='newbo_max' and i in (1,2,3)):continue
                self.assertFalse(LOG.analyze(base.replace(a,b))['coverage_qualified'],(key,i));changes+=1
        self.assertGreater(changes,40)

    def test_inherited_errors_and_prior_wires(self):
        for a,b in [('cpu_counts=1,1,2','cpu_counts=0,0,0'),('detail_flags=0','detail_flags=1'),
            ('fine_flags=0','fine_flags=1'),('bo_unique=2','bo_unique=0'),('address_counts=2,1,1','address_counts=0,0,0'),
            ('submit_mask=255','submit_mask=254'),('io_identity_flags=0','io_identity_flags=1')]:
            self.assertFalse(LOG.analyze(sample().replace(a,b))['coverage_qualified'])
        for prior in (OLD.sample(),sample()+'GAUGUIN N341: limit=4096 coverage=incomplete\n'):
            self.assertFalse(LOG.analyze(prior)['coverage_qualified'])
        base=sample();row=next(s for s in base.splitlines() if s.startswith(LOG.PREFIX))
        for text in (base+row+'\n',base.replace(' newbo_flags=0',''),base+LOG.PREFIX+'limit=4096 coverage=incomplete\n',base.replace(' newbo_flags=0',' newbo_flags=0'+'x'*8192)):
            self.assertFalse(LOG.analyze(text)['coverage_qualified'])

    def test_phase_CPU_nonzero_and_query_reconstruction(self):
        p=partition(100,100020,1,2,20,0,[110],[100010],[50000],[20])[0]
        self.assertGreater(p['CPU_lower_ns'],47000);self.assertGreater(p['off_CPU_lower_ns'],47000)
        for kw in ([21],[19]):
            with self.assertRaises(ValueError):partition(100,100020,1,2,20,0,[110],[100010],[50000],kw)

    def test_complete_kernel_and_identity_joins(self):
        core=LOG.analyze(sample());text,raw=kernel_stream(matching(core))
        k=KERNEL.parse(text,raw);self.assertTrue(k['coverage_qualified'],k['errors'])
        j=KERNEL.join(k,core,(220000000,270000000));self.assertTrue(j['coverage_qualified'],j['errors'])
        self.assertEqual(j['complete_submit_count'],1);self.assertEqual(j['program_maximum_join_count'],1)

    def test_kernel_identity_or_missing_calls_refuse(self):
        core=LOG.analyze(sample());original=matching(core)
        for key in ('tid','queue','fence','handle','bytes','bos','cmds','result'):
            rows=copy.deepcopy(original);rows[0][key]+=1;text,raw=kernel_stream(rows)
            self.assertFalse(KERNEL.join(KERNEL.parse(text,raw),core,(220000000,270000000))['coverage_qualified'],key)
        for rows in (original[:-1],original+[original[0]],original[1:]):
            text,raw=kernel_stream(rows);self.assertFalse(KERNEL.join(KERNEL.parse(text,raw),core,(220000000,270000000))['coverage_qualified'])

    def test_kernel_wire_loss_bounds_and_raw_ring(self):
        core=LOG.analyze(sample());base,raw=kernel_stream(matching(core))
        for a,b in [('lost=0','lost=1'),('pending=0','pending=1'),('invalid=0','invalid=1'),('byte_limited=0','byte_limited=1'),
            ('capacity=4096','capacity=4095'),('index=0','index=1'),('token=1','token=2'),('mask=4095','mask=4094'),
            ('query_ns=13','query_ns=14'),('flags=0','flags=1'),('emitted=4','emitted=3'),('byte_limit=2097152','byte_limit=4194304')]:
            text=base.replace(a,b);self.assertNotEqual(text,base,(a,b));self.assertFalse(KERNEL.parse(text,ring_for(text))['coverage_qualified'],a)
        wrapped=bytearray(raw);struct.pack_into('<Q',wrapped,16,4194305)
        self.assertFalse(KERNEL.parse(base,wrapped)['coverage_qualified']);self.assertFalse(KERNEL.parse(base,None)['coverage_qualified'])

    def test_actual_CXX_formatter_shape(self):
        path=WORK/'research/tmp/io-path-342/core-host-v2/program342-success.log'
        lines=[s for s in path.read_text().splitlines() if s.startswith(LOG.PREFIX+'object=')]
        self.assertEqual(len(lines),1);self.assertIsNotNone(LOG.parse_extra(lines[0]));self.assertLessEqual(len(lines[0])+1,8192)
        self.assertFalse(LOG.analyze(lines[0])['coverage_qualified'])

    def test_partial_predecessor_CPU_is_bounded_without_proportional_placement(self):
        empty=dict(wall_ns=0,CPU_lower_ns=0,CPU_upper_ns=0,off_CPU_lower_ns=0,off_CPU_upper_ns=0,begin_ns=0,end_ns=0)
        phases=[dict(empty) for _ in range(12)]
        phases[5]=dict(wall_ns=10000,CPU_lower_ns=5000,CPU_upper_ns=7000,off_CPU_lower_ns=3000,off_CPU_upper_ns=5000,begin_ns=10000,end_ns=20000)
        joined=dict(coverage_qualified=True,scope='synthetic interval test',program_maxima=[],submits=[
            dict(queue=1,ticket=1,phases=phases,IO_wall_ns=10000),
            dict(queue=1,ticket=2,phases=[dict(empty) for _ in range(12)],IO_wall_ns=0)])
        core=dict(coverage_qualified=True,rows=[dict(queue=1,ticket=1,job=2,enq_ns=100,start_ns=100,core_queue_wait_us=0),
            dict(queue=1,ticket=2,job=4,enq_ns=15000,start_ns=18000,core_queue_wait_us=3)])
        report=KERNEL.summarize(joined,core);r=report['longest_wait_predecessor_phases'][0]['prior_commit_phase_intersections'][0]
        self.assertEqual((r['CPU_lower_ns'],r['CPU_upper_ns']),(0,3000));self.assertEqual(r['overlap_ns'],3000)
        self.assertFalse(report['CPU_utilization_claim'])

    def test_sustained_queue_growth_preserves_window_identities(self):
        empty=dict(wall_ns=0,CPU_lower_ns=0,CPU_upper_ns=0,off_CPU_lower_ns=0,off_CPU_upper_ns=0,begin_ns=0,end_ns=0)
        rows=[dict(queue=1,ticket=i+1,job=2*i+2,enq_ns=220000000000+i*16000000,
            start_ns=220000000000+i*20000000,core_queue_wait_us=i*4000,newbo_counts=[0,0,0,0,0],io_ns=0) for i in range(12)]
        joined=dict(coverage_qualified=True,scope='synthetic consecutive-ticket test',program_maxima=[],submits=[
            dict(queue=1,ticket=r['ticket'],phases=[dict(empty) for _ in range(12)],IO_wall_ns=0) for r in rows])
        report=KERNEL.summarize(joined,dict(coverage_qualified=True,rows=rows));window=report['sustained_windows'][0]
        self.assertEqual(window['queue_wait_growth_us'],44000);self.assertEqual(window['mean_arrival_interval_us'],16000)
        self.assertEqual(window['mean_commit_start_interval_us'],20000);self.assertEqual(window['program_new_BO_calls'],0)
        broken=copy.deepcopy(rows);broken[-1]['ticket']=14
        self.assertFalse(KERNEL.summarize(joined,dict(coverage_qualified=True,rows=broken))['sustained_windows'])


if __name__=='__main__':unittest.main()
