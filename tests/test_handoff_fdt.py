#!/usr/bin/env python3
"""Original-FDT capture producer: execute actual loader/helpers with bounded host seams."""
from pathlib import Path
import importlib.util,json,os,struct,subprocess,sys,tempfile,warnings
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
import adt,mkpayload
from test_payload_nvt_asset import kernel,tree
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def loader_source(path):
    text=path.read_text()
    text=text.replace('extern const uint8_t _head[], _end[];','extern const uint8_t *test_image_start, *test_image_end;')
    text=text.replace('(uintptr_t)_head','(uintptr_t)test_image_start').replace('(uintptr_t)_end','(uintptr_t)test_image_end')
    text=text.replace('__asm__ volatile("wfe" ::: "memory");','test_stop();')
    text=text.replace('__asm__ volatile("dsb sy; ic iallu; dsb sy; isb" ::: "memory");','')
    text=text.replace('((xnu_entry_t)entry_pa)(ba_pa);','(void)entry_pa; test_jump(ba_pa);')
    text=text.replace('(const struct payload *)rd_start','(const struct payload *)test_payload_from_pa(rd_start)')
    text=text.replace('(struct payload *)rd_start','(struct payload *)test_payload_from_pa(rd_start)')
    text=text.replace('rd_start + s->file_off','(uintptr_t)p + s->file_off')
    text=text.replace('rd_start + p->adt_off','(uintptr_t)p + p->adt_off')
    return ('#include <stdint.h>\nextern void test_stop(void) __attribute__((noreturn));\n'
            'extern void test_jump(uint64_t) __attribute__((noreturn));\n'
            'extern const void *test_payload_from_pa(uint64_t);\n'+text)
def main():
    warnings.simplefilter('ignore',ResourceWarning)
    reference=Path(os.environ['HANDOFF_LOADER_REFERENCE'])
    with tempfile.TemporaryDirectory(prefix='handoff-fdt-')as directory:
        out=Path(directory);os.environ['PAS_TEST_OUT']=str(out)
        fdt=module('handoff_fixture_fdt',ROOT/'tests/pas_reservation/make_cases.py')
        k=out/'kernel';k.write_bytes(kernel());a=out/'adt';a.write_bytes(adt.serialize(tree()))
        plain,_=mkpayload.build(k,a,'')
        no,_=mkpayload.build(k,a,'',pas_reservation=True)
        old=module('old_handoff_packer',reference.parent.parent/'tools/mkpayload.py')
        assert old.build(k,a,'')[0]==plain and old.build(k,a,'',pas_reservation=True)[0]==no
        assert mkpayload.build(k,a,'',pas_reservation=True,handoff_fdt_capacity=0)[0]==no
        for cap,pas in [(True,True),(-1,True),(1,True),(16383,True),(16385,True),(0x84000,True),(16384,False)]:
            try:mkpayload.build(out/'missing-kernel',out/'missing-adt','',pas_reservation=pas,handoff_fdt_capacity=cap)
            except ValueError:pass
            else:raise AssertionError('bad capacity accepted')
        env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
        flags=['xcrun','clang','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-pedantic',
            '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(ROOT/'shim')]
        executables={}
        for name,source in [('old',reference),('candidate',ROOT/'shim/loader.c')]:
            p=out/(name+'.c');p.write_text(loader_source(source));exe=out/name
            subprocess.run([*flags,str(ROOT/'tests/pas_reservation/test_handoff.c'),str(p),
                            str(ROOT/'shim/pas_reservation.c'),'-o',str(exe)],env=env,check=True)
            executables[name]=exe
        cases=[]
        for cap in [16384,262144,524288]:
            blob,info=mkpayload.build(k,a,'handoff-test',pas_reservation=True,handoff_fdt_capacity=cap)
            assert info['handoff_fdt_request']['capacity']==cap
            dt=fdt.make_fdt(0x90000000,len(blob),fixed=[(0x88000000,0x100000)])
            cases.append(('capacity-'+str(cap),blob,dt,'capture'))
        normal=cases[1];raw=normal[1];ao,az=struct.unpack_from('<2Q',raw,32);vo=raw.index(b'GHFDREQ1',ao)
        root,_=adt.parse(raw[ao:ao+az]);ch=next(n for n in root.children if n.name=='chosen')
        assert sum(n=='GauguinHandoffPending'for n,_,_ in ch.props)==1
        a.write_bytes(mkpayload.handoff_request_adt(adt.serialize(tree()),16384))
        try:mkpayload.build(k,a,'',pas_reservation=True,handoff_fdt_capacity=16384)
        except ValueError:pass
        else:raise AssertionError('preexisting metadata accepted')
        for offset in [0,8,12,16,20,24,152,160,160+262144-1]:
            b=bytearray(raw);b[vo+offset]^=1
            cases.append(('bad-request-'+str(offset),bytes(b),normal[2],'reject'))
        b=bytearray(raw);b[vo-36:vo-4]=b'GauguinHandoffFDT'.ljust(32,b'\0')
        cases.append(('prepublished-input',bytes(b),normal[2],'reject'))
        b=bytearray(raw)
        for tag in [b'LowPASRequest',b'LowPASIOPending']:
            where=b.index(tag,ao);b[where:where+32]=b'OtherMetadata'.ljust(32,b'\0')
        cases.append(('missing-PAS',bytes(b),normal[2],'reject'))
        # Large, valid FDT with an unknown property must reject too-small
        # capture capacity rather than truncate or change original ownership.
        b=cases[0][1]
        be=lambda *v:struct.pack('>'+str(len(v))+'I',*v)
        q=lambda *v:struct.pack('>'+str(len(v))+'Q',*v)
        large=fdt.encode_fdt(fdt.fdt_node('',[
            ('#address-cells',be(2)),('#size-cells',be(2)),('compatible',b'qcom,lagoon\0'),('capture-padding',bytes(20000))],[
            fdt.fdt_node('chosen',[('linux,initrd-start',q(0x90000000)),('linux,initrd-end',q(0x90000000+len(b)))]),
            fdt.fdt_node('memory',[('reg',q(0x80000000,0x80000000,0x180000000,0x100000000))]),
            fdt.fdt_node('reserved-memory',[('#address-cells',be(2)),('#size-cells',be(2)),('ranges',b'')],[
                fdt.fdt_node('unresolved-pool',[('size',q(1048576)),('alloc-ranges',q(0,0xffffffff))])])]))
        cases.append(('oversize-original-FDT',b,large,'reject'))
        for index,(name,payload,dt,mode)in enumerate(cases):
            p=out/(str(index)+'.case');p.write_bytes(struct.pack('<2Q',len(payload),len(dt))+payload+dt)
            if index==1:
                result=subprocess.run([str(executables['old']),str(p),'capture'],capture_output=True,text=True,env=env,timeout=30)
                assert result.returncode==42 and result.stderr=='FAIL actual old loader leaves runtime FDT request unpublished\n',(result.returncode,result.stdout,result.stderr)
                print('Baseline functional RED42: real old loader jumps with unpublished FDT request')
            result=subprocess.run([str(executables['candidate']),str(p),mode],capture_output=True,text=True,env=env,timeout=30)
            assert result.returncode==0,(name,result.returncode,result.stdout,result.stderr)
            print(name+': '+result.stdout.strip())
        print('PASS '+str(len(cases))+' actual-loader cases, source/PAS-tail protection, owner-field/readback and atomic-refusal controls; host only')
if __name__=='__main__':main()
