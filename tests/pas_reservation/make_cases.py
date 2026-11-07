#!/usr/bin/env python3
"""Synthetic metadata only; no actual physical memory or device access."""
import ctypes as C
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
import shlex
from pathlib import Path
import struct as S
import subprocess
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'tools'))
import adt

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
pack=load('pas_candidate',REPO/'tools/mkpayload.py')
LEGACY=json.loads((HERE/'default_payload.json').read_text())
assets=load('pas_fixtures',REPO/'tests/test_payload_nvt_asset.py')
OUT=Path(os.environ['PAS_TEST_OUT']);OUT.mkdir(exist_ok=True)
CC=shlex.split(os.environ.get('CC','cc'))
LIB=OUT/'pas.so'
PA=0x90000000 # synthetic logical address, never dereferenced as PA
FDT_PA=0x92000000
SHIM_PA=0x93000000

def fdt_node(name,props=(),children=()):return (name,list(props),list(children))
def make_fdt(start,size,reserves=(),fixed=(),cells=(2,2),compatible=b'qcom,lagoon\0'):
    be=lambda *v:S.pack('>'+str(len(v))+'I',*v)
    q=lambda *v:S.pack('>'+str(len(v))+'Q',*v)
    root=fdt_node('',[('#address-cells',be(cells[0])),('#size-cells',be(cells[1])),('compatible',compatible)],[
        fdt_node('chosen',[('linux,initrd-start',q(start)),('linux,initrd-end',q(start+size))]),
        fdt_node('memory',[('reg',q(0x80000000,0x80000000,0x180000000,0x100000000))]),
        fdt_node('reserved-memory',[('#address-cells',be(2)),('#size-cells',be(2)),('ranges',b'')],
             [fdt_node('fixed'+str(i),[('reg',q(a,z))]) for i,(a,z) in enumerate(fixed)]+
             [fdt_node('dynamic',[('size',q(0x100000))])])])
    return encode_fdt(root,reserves)

def encode_fdt(root,reserves=()):
    strings=bytearray(); offsets={}
    def walk(n):
        name,props,children=n; out=bytearray(S.pack('>I',1)+name.encode()+b'\0');out+=bytes(-len(out)%4)
        for key,value in props:
            if key not in offsets:offsets[key]=len(strings);strings.extend(key.encode()+b'\0')
            out+=S.pack('>3I',3,len(value),offsets[key])+value;out+=bytes(-len(out)%4)
        for child in children:out+=walk(child)
        return out+S.pack('>I',2)
    tokens=walk(root)+S.pack('>I',9)
    rsv=b''.join(S.pack('>2Q',*r) for r in reserves)+bytes(16)
    so=40+len(rsv); ss=so+len(tokens); total=ss+len(strings)
    return S.pack('>10I',0xd00dfeed,total,so,ss,40,17,16,0,len(strings),len(tokens))+rsv+tokens+strings

class Context(C.Structure):
    _fields_=[('payload',C.c_void_p),('fdt',C.c_void_p),('payload_bytes',C.c_size_t),('fdt_bytes',C.c_size_t)]+[(k,C.c_uint64) for k in ('payload_pa','fdt_pa','shim_pa','shim_bytes')]
class Plan(C.Structure):
    _fields_=[(k,C.c_uint64) for k in ('pa','bytes','tail_offset','payload_pa','payload_bytes','fdt_pa','fdt_bytes','shim_pa','shim_bytes','managed_pa','managed_bytes')]+[(k,C.c_uint32) for k in ('adt_offset','adt_bytes','request_name','request_value','io_name','io_value','exact_initrd_reservations','fixed_reservations','dynamic_pools')]

def u64(b,off,v):b=bytearray(b);S.pack_into('<Q',b,off,v);return bytes(b)
def u32(b,off,v):b=bytearray(b);S.pack_into('<I',b,off,v);return bytes(b)
def be32(b,off,v):b=bytearray(b);S.pack_into('>I',b,off,v);return bytes(b)

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore',ResourceWarning)
        subprocess.run([*CC,'-std=c11','-O2','-Wall','-Wextra','-Werror','-pedantic','-shared','-fPIC',str(REPO/'shim/pas_reservation.c'),'-o',str(LIB)],check=True,timeout=60)
        cls.lib=C.CDLL(str(LIB));cls.lib.pas_prepare.argtypes=[C.POINTER(Context),C.POINTER(Plan)]
        cls.lib.pas_commit.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(Plan)]
        cls.lib.pas_initrd.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_uint64),C.POINTER(C.c_uint64)]
        cls.cases=[];cls.metrics={}
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name)
        self.k=self.dir/'kernel';self.a=self.dir/'adt';self.k.write_bytes(assets.kernel());self.a.write_bytes(adt.serialize(assets.tree()))
        self.default,_=pack.build(self.k,self.a,'')
        self.blob,self.info=pack.build(self.k,self.a,'',pas_reservation=True)
        self.ao,self.az=S.unpack_from('<2Q',self.blob,32)
        self.ro=self.blob.index(b'LPASREQ1',self.ao)
    def tearDown(self):self.tmp.cleanup()
    def run_case(self,name,payload=None,fdt=None,expected=1,pa=PA,fp=FDT_PA,sp=SHIM_PA,sz=0x30000):
        payload=self.blob if payload is None else payload
        fdt=make_fdt(pa,len(payload)) if fdt is None else fdt
        pb=C.create_string_buffer(payload);fb=C.create_string_buffer(fdt)
        c=Context(C.addressof(pb),C.addressof(fb),len(payload),len(fdt),pa,fp,sp,sz)
        p=Plan();C.memset(C.addressof(p),0xa5,C.sizeof(p));old=bytes(p)
        status=self.lib.pas_prepare(C.byref(c),C.byref(p))
        if expected<0:self.assertLess(status,0,name)
        else:self.assertEqual(status,expected,name)
        self.assertEqual(pb.raw[:len(payload)],payload)
        if status!=1:self.assertEqual(bytes(p),old,name)
        else:
            copy=C.create_string_buffer(payload[p.adt_offset:p.adt_offset+p.adt_bytes]);before=copy.raw
            self.assertEqual(self.lib.pas_commit(copy,p.adt_bytes,C.byref(p)),1,name)
            after=copy.raw
            self.assertEqual(after[p.request_value:p.request_value+8],b'LPASOWN1')
            self.assertEqual(S.unpack_from('<QQII',after,p.io_value),(p.pa,0x100000,0xd0000006,0x50415331))
            allowed=set(range(p.request_name,p.request_name+32))|set(range(p.io_name,p.io_name+32))|set(range(p.request_value,p.request_value+128))|set(range(p.io_value,p.io_value+24))
            self.assertTrue(all(i in allowed for i,(a,b) in enumerate(zip(before,after)) if a!=b))
            self.assertLess(self.lib.pas_commit(copy,p.adt_bytes,C.byref(p)),0)
            self.assertEqual(copy.raw,after,'failed second commit mutated ADT')
            # Corrupt request/plan after prepare: all checks before publication.
            for offset in (0,8,12,16,24,32,40,48,56,64,120):
                bad=bytearray(before);bad[p.request_value+offset]^=1
                buf=C.create_string_buffer(bytes(bad));saved=buf.raw
                self.assertLess(self.lib.pas_commit(buf,p.adt_bytes,C.byref(p)),0)
                self.assertEqual(buf.raw,saved)
            for field in ('pa','bytes','tail_offset','payload_bytes','managed_pa','adt_offset','adt_bytes','request_value','io_value'):
                bp=Plan.from_buffer_copy(bytes(p));setattr(bp,field,getattr(bp,field)+8)
                buf=C.create_string_buffer(before);saved=buf.raw
                if field=='adt_offset':continue # not consumed by copied-ADT commit
                self.assertLess(self.lib.pas_commit(buf,p.adt_bytes,C.byref(bp)),0,field)
                self.assertEqual(buf.raw,saved)
        suffix=len(self.cases);path=OUT/f'{suffix:03d}-{name}.case'
        path.write_bytes(S.pack('<iI6Q',expected,1 if status==1 else 0,len(payload),len(fdt),pa,fp,sp,sz)+payload+fdt)
        self.cases.append(dict(name=name,path=str(path),status=status))
        return p
    def test_01_default_bytes_and_nvt_ramdisk_compatibility(self):
        rd=self.dir/'rd';rd.write_bytes(b'R'*17001)
        fw=self.dir/'fw';image=bytes(range(256))*(139264//256);fw.write_bytes(image)
        pin=hashlib.sha256(image).hexdigest()
        with patch.object(pack,'NVT_FIRMWARE_SHA256',pin):
            for ramdisk in (None,rd):
                for firmware in (None,fw):
                    for cl in ('','a'*800):
                        blob,info=pack.build(self.k,self.a,cl,ramdisk,firmware)
                        golden=next(r for r in LEGACY if (r['ramdisk'],r['firmware'],r['command_bytes'])==(bool(ramdisk),bool(firmware),len(cl)))
                        self.assertEqual(hashlib.sha256(blob).hexdigest(),golden['sha256'])
                        self.assertEqual(json.loads(json.dumps(info)),golden['info'])
                    before,old=pack.build(self.k,self.a,'',ramdisk,firmware)
                    after,new=pack.build(self.k,self.a,'',ramdisk,firmware,True)
                    oldlayout=assets.layout(before);newlayout=assets.layout(after)
                    self.assertEqual(oldlayout['segs'],newlayout['segs'])
                    self.assertEqual((oldlayout['virt'],oldlayout['entry'],oldlayout['end']),(newlayout['virt'],newlayout['entry'],newlayout['end']))
                    for va,vm,o,n in oldlayout['segs']:self.assertEqual(before[o:o+n],after[o:o+n])
                    self.run_case('asset-layout-'+str(bool(ramdisk))+'-'+str(bool(firmware)),payload=after)
        self.run_case('default',self.default,expected=0)
        self.metrics['default_exact_variants']=8
    def test_02_five_asset_layout(self):
        images=[('nvt_firmware_path','NVT_FIRMWARE_SHA256',bytes(range(256))*544),
                ('zap_mdt_path','ZAP_MDT_SHA256',bytes(range(256))*26+bytes(range(204))),
                ('gmu_firmware_path','GMU_FIRMWARE_SHA256',bytes((i*19+7)%251 for i in range(32768))),
                ('sqe_firmware_path','SQE_FIRMWARE_SHA256',bytes((i*23+11)%251 for i in range(32304))),
                ('zap_code_path','ZAP_CODE_SHA256',bytes((i*31+5)%251 for i in range(1984)))]
        rd=self.dir/'rd';rd.write_bytes(b'R'*17001)
        with ExitStack() as stack:
            options={'ramdisk_path':rd}
            for name,key,data in images:
                p=self.dir/name;p.write_bytes(data);options[name]=p
                stack.enter_context(patch.object(pack,key,hashlib.sha256(data).hexdigest()))
            plain,_=pack.build(self.k,self.a,'',**options)
            reserved,info=pack.build(self.k,self.a,'',**options,pas_reservation=True)
        self.run_case('five-assets',payload=plain,expected=0)
        p=self.run_case('five-assets-pas',payload=reserved)
        self.assertEqual(len(reserved),info['low_pas_request']['tail_offset']+0x200000)
        self.assertEqual(p.pa%0x100000,0)

    def test_02_ready_tail_guard_and_exact_reservation(self):
        self.assertEqual(self.blob[-0x200000:],bytes(0x200000))
        self.assertEqual(len(self.blob),self.info['low_pas_request']['tail_offset']+0x200000)
        p=self.run_case('ready');self.assertEqual(p.pa%0x100000,0)
        p=self.run_case('exact-input',fdt=make_fdt(PA,len(self.blob),[(PA,len(self.blob))]));self.assertEqual(p.exact_initrd_reservations,1)
        p=self.run_case('adjacent-reserved',fdt=make_fdt(PA,len(self.blob),[(PA-0x1000,0x1000),(PA+len(self.blob),0x1000)],[(PA-0x8000,0x4000)]));self.assertEqual(p.fixed_reservations,1)
        self.assertEqual(p.dynamic_pools,1)
    def test_03_payload_mutations(self):
        changes=[('magic',0,'Q',0),('version',8,'I',2),('nseg0',12,'I',0),('nseg491',12,'I',491),('adtoutside',32,'Q',len(self.blob)),('adtunaligned',32,'Q',self.ao+1),('adtsize',40,'Q',0x100001),('vbmisaligned',16,'Q',0xfffffe0006000001),('entryoutside',24,'Q',0xfffffe0006000000),('kebefore',48,'Q',0xfffffe0006000000),('badpa',56,'Q',0x180004000),('badram',64,'Q',1),('vmsize',pack.SEG_TABLE+8,'Q',0xffffffffffffffff),('fileoutside',pack.SEG_TABLE+16,'Q',self.ao),('filesize',pack.SEG_TABLE+24,'Q',0x4001),('fileoverlap',pack.SEG_TABLE+32+16,'Q',pack.SEG_TABLE+64),('vaoverlap',pack.SEG_TABLE+32,'Q',assets.VA),('badrequestversion',self.ro+8,'I',2),('badrequestflag',self.ro+12,'I',1),('tailunaligned',self.ro+16,'Q',1),('tailsize',self.ro+24,'Q',1),('regionsize',self.ro+32,'Q',1),('alignment',self.ro+40,'Q',0x4000),('totalsize',self.ro+48,'Q',len(self.blob)-1),('runtimepresent',self.ro+64,'Q',1)]
        for name,off,fmt,value in changes:
            b=bytearray(self.blob);S.pack_into('<'+fmt,b,off,value);self.run_case(name,bytes(b),expected=-1)
        b=bytearray(self.default);S.pack_into('<I',b,12,0xffffffff);self.run_case('bad-default-table',bytes(b),expected=-1)
        self.run_case('non-xnu',b'not-XNU\0'*100,expected=-1)
        self.run_case('truncated',self.blob[:100],expected=-1)
    def test_04_fdt_and_ownership_failures(self):
        for name,resv in [('partial',[(PA+0x100,0x1000)]),('broad',[(PA-0x1000,len(self.blob)+0x2000)]),('duplicate',[(PA,len(self.blob))]*2)]:
            self.run_case(name,fdt=make_fdt(PA,len(self.blob),resv),expected=-1)
        p=self.run_case('for-selection')
        for name,fixed in [('fixed-input',[(PA,0x1000)]),('fixed-selected',[(p.pa+8,1)]),('fixed-dest',[(assets.PA+0x1004000,0x1000)])]:
            self.run_case(name,fdt=make_fdt(PA,len(self.blob),fixed=fixed),expected=-1)
        self.run_case('above4g',pa=0x110000000,expected=-1)
        self.run_case('managed-input',pa=0x180000000,expected=-1)
        self.run_case('fdt-input',fp=PA+0x100,expected=-1)
        self.run_case('shim-input',sp=PA+0x100,expected=-1)
        self.run_case('fdt-shim',fp=SHIM_PA+0x100,expected=-1)
        self.run_case('fdt-high-load',fp=assets.PA+0x1004000,expected=-1)
        self.run_case('wrong-initrd',fdt=make_fdt(PA+0x1000,len(self.blob)),expected=-1)
        self.run_case('onecell',fdt=make_fdt(PA,len(self.blob),cells=(1,1)),expected=-1)
        good=make_fdt(PA,len(self.blob))
        for name,off,value in [('fdtmagic',0,0),('totalsize',4,len(good)+1),('structoff',8,len(good)),('stringsoff',12,0xffffffff),('rsvunaligned',16,41),('version',20,16),('stringsize',32,0xffffffff),('structsize',36,0xffffffff)]:
            self.run_case(name,fdt=be32(good,off,value),expected=-1)
    def test_05_adt_rejects_duplicate_or_actual_metadata(self):
        for mode in range(6):
            root=assets.tree();ch=root.children[0];defaults=assets.node('defaults');root.children.append(defaults)
            if mode==0:ch.props.append(('LowPASRequest',0,bytes(128)))
            if mode==1:ch.props.append(('LowPASReservation',0,bytes(128)))
            if mode==2:defaults.props.append(('pmap-io-ranges',0,bytes(24)))
            if mode==3:defaults.props.append(('LowPASIOPending',0,bytes(24)))
            if mode==4:ch.props.append(ch.props[-1])
            if mode==5:root.children.append(defaults)
            self.a.write_bytes(adt.serialize(root))
            with self.assertRaises(ValueError):pack.build(self.k,self.a,'',pas_reservation=True)
        b=bytearray(self.blob);off=b.index(b'LowPASRequest\0',self.ao);b[off:off+32]=b'LowPASReservation'.ljust(32,b'\0');self.run_case('orphan-owner',bytes(b),expected=-1)
        for off in (self.ao,self.ao+4,self.ao+40):
            self.run_case('adt-count-or-len',u32(self.blob,off,0x7fffffff),expected=-1)
    def test_06_bounded_ambiguous_fdt(self):
        be=lambda *v:S.pack('>'+str(len(v))+'I',*v)
        q=lambda *v:S.pack('>'+str(len(v))+'Q',*v)
        def tree():
            return fdt_node('',[('#address-cells',be(2)),('#size-cells',be(2)),('compatible',b'qcom,lagoon\0')],[
                fdt_node('chosen',[('linux,initrd-start',q(PA)),('linux,initrd-end',q(PA+len(self.blob)))]),
                fdt_node('memory',[('reg',q(0x80000000,0x80000000))]),
                fdt_node('reserved-memory',[('#address-cells',be(2)),('#size-cells',be(2)),('ranges',b'')])])
        for mode in range(11):
            root=tree()
            if mode==0:root[1].append(('#address-cells',be(2)))
            if mode==1:root[2][0][1].append(('linux,initrd-start',q(PA)))
            if mode==2:root[2].append(root[2][0])
            if mode==3:root[2].append(root[2][1])
            if mode==4:root[2][1][1][0]=('reg',q(0xfffffffffffff000,0x2000))
            if mode==5:root[2][2][1][2]=('ranges',be(0))
            if mode==6:root[2][2][2].append(fdt_node('unknown'))
            if mode==7:root[2][2][2].append(fdt_node('empty-fixed',[('reg',q(PA-0x1000,0))]))
            if mode==8:root[1].append(('a'*128,b''))
            if mode==9:root[2].append(fdt_node('x'*256))
            if mode==10:root[1].append(('compatible',b'other,board\0'))
            self.run_case('ambiguous-fdt-'+str(mode),fdt=encode_fdt(root),expected=-1)
        root=tree();last=root
        for i in range(17):
            child=fdt_node('nested');last[2].append(child);last=child
        self.run_case('fdt-depth',fdt=encode_fdt(root),expected=-1)
        self.run_case('reserve-count',fdt=make_fdt(PA,len(self.blob),[(0x70000000+i*0x1000,0x1000) for i in range(128)]),expected=-1)
        root=tree();root[2][2][2].extend(fdt_node('d'+str(i),[('size',q(0x4000))]) for i in range(129))
        self.run_case('dynamic-count',fdt=encode_fdt(root),expected=-1)
        root=tree();root[2][2][2].extend(fdt_node('r'+str(i),[('reg',q(0x70000000+i*0x1000,0x1000))]) for i in range(129))
        self.run_case('fixed-count',fdt=encode_fdt(root),expected=-1)

    def test_compatibility_matches_tested_wrapper(self):
        identity=b'xiaomi,gauguin\0qcom,sm7225\0'
        fdt=make_fdt(PA,len(self.blob),compatible=identity)
        fb=C.create_string_buffer(fdt);start=C.c_uint64();end=C.c_uint64()
        self.assertEqual(self.lib.pas_initrd(fb,len(fdt),C.byref(start),C.byref(end)),0)
        self.assertEqual((start.value,end.value),(PA,PA+len(self.blob)))
        self.run_case('wrapper-identity',fdt=make_fdt(PA,len(self.blob),compatible=identity))
        self.run_case('wrapper-default',payload=self.default,fdt=make_fdt(PA,len(self.default),compatible=identity),expected=0)
        for identity in (b'qcom,sm7225\0',b'xiaomi,gauguin\0',b'other,board\0',b'xiaomi,gauguin\0qcom,sm72250\0',b'xiaomi,gauguin\0qcom,sm7225',b''):
            self.run_case('unsupported-identity',fdt=make_fdt(PA,len(self.blob),compatible=identity),expected=-1)
            fdt=make_fdt(PA,len(self.blob),compatible=identity);fb=C.create_string_buffer(fdt)
            start=C.c_uint64(0x55);end=C.c_uint64(0x66)
            self.assertLess(self.lib.pas_initrd(fb,len(fdt),C.byref(start),C.byref(end)),0)
            self.assertEqual((start.value,end.value),(0x55,0x66))

    @classmethod
    def tearDownClass(cls):
        (OUT/'cases.json').write_text(json.dumps(cls.cases,indent=2)+'\n')
        (OUT/'metrics.json').write_text(json.dumps(cls.metrics,indent=2)+'\n')

if __name__=='__main__':unittest.main(verbosity=2)
