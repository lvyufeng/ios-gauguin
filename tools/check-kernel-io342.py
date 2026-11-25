#!/usr/bin/env python3
"""Run actual337/342 IOUserClient against paired typed seams, no device IO."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/io-path-342'
P=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337/kernel-preparation-v2/kernel-source')
GPU='iokit/Kernel/arm/GauguinGPU.cpp'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);out=ap.parse_args().out.resolve();assert out.is_relative_to(B) and not out.exists()
    C=B/'kernel-prepared-v8/kernel-source';sys.path.insert(0,str(W/'tools'));import kernel_io342_patch as patch
    manifest=json.loads((P.parent.parent/'local-link/build-manifest.json').read_text());base=Path(manifest['source_union']['base'])
    effective=lambda name:C/name if (C/name).is_file() else base/name
    sources={};paths=[Path(__file__),W/'tools/kernel_io342_patch.py',W/'tests/fixtures/gpu-user/iokit_host.cpp']
    for name in (GPU,):
        original=P/name
        if not original.exists():
            manifest=json.loads((P.parent/'local-link/build-manifest.json').read_text());original=Path(manifest['source_union']['base'])/name
        changed,edits=patch.patch(original.read_text());patch.reverse(original.read_text(),changed,edits);assert changed==(C/name).read_text();paths.extend([original,C/name]);sources[name]=changed
    paths.extend(p for p in C.rglob('*') if p.is_file());paths.append(effective('iokit/Kernel/arm/SweetSurface.cpp'));pins={str(p.resolve()):sha(p) for p in paths}
    fixture=(W/'tests/fixtures/gpu-user/iokit_host.cpp').read_text().replace('    void retain(){++refs;}','    unsigned getRetainCount() const{return refs;}\n    void retain(){++refs;}')
    old='extern "C" void sweet_ui_trace_record(uint32_t,uint64_t,uint32_t,uint32_t,uint64_t,uint64_t,uint64_t){}'
    assert fixture.count(old)==1
    fixture=fixture.replace(old,'''struct Trace333{uint32_t phase,pid;uint64_t token,a,b,c;};
static std::vector<Trace333> trace333;
extern "C" void sweet_ui_trace_record(uint32_t kind,uint64_t token,uint32_t pid,uint32_t phase,uint64_t a,uint64_t b,uint64_t c){
    if(kind==GUT_BO_ALLOC333)trace333.push_back({phase,pid,token,a,b,c});
}
[[maybe_unused]] static uint64_t current_thread(){return 1234;}
[[maybe_unused]] static uint64_t thread_tid(uint64_t value){assert(value==1234);return value;}
extern "C" bool sweet_gpu_runtime_pending_metadata(uint32_t){return false;}
extern "C" void sweet_log_append(const char*,int bytes){assert(bytes>0&&bytes<=2048);}
''')
    old='    IOReturn result=c->externalMethod(selector,&a,nullptr,nullptr,nullptr);'
    assert fixture.count(old)==1
    fixture=fixture.replace(old,'''    const size_t traceStart=trace333.size();
#ifdef IO342_CANDIDATE
    const unsigned before342=io342::count;
#endif
    IOReturn result=c->externalMethod(selector,&a,nullptr,nullptr,nullptr);
#ifdef IO342_CANDIDATE
    if(io342::count!=before342){
        assert(io342::count==before342+1);const auto& row342=io342::rows[before342];
        assert(row342.pid==57&&row342.tid==1234&&row342.selector==selector&&row342.result==uint32_t(result));
        assert(!row342.phases.flags&&row342.token&&row342.phases.last>=row342.phases.first);
        uint64_t body342=row342.phases.queryWall;
        for(unsigned i342=0;i342<12;i342++)body342+=row342.phases.end[i342]-row342.phases.begin[i342];
        assert(body342==row342.phases.last-row342.phases.first);
    }
#endif
#ifdef TEST_BO333
    if(trace333.size()!=traceStart){
        assert(selector==0x42&&trace333.size()-traceStart<=6);
        const auto &first=trace333[traceStart],&last=trace333.back();
        assert(first.phase==1&&last.phase==6&&first.c==1234&&last.a==uint32_t(result));
        uint32_t prior=0;
        for(size_t i=traceStart;i<trace333.size();i++){
            assert(trace333[i].phase>prior&&trace333[i].token==first.token&&trace333[i].pid==57);
            prior=trace333[i].phase;
        }
        if(result==0){
            assert(trace333.size()-traceStart==6&&last.c==0&&last.b);
            assert(trace333[traceStart+2].a==1&&trace333[traceStart+4].b==last.b);
        }
    }
#else
    assert(trace333.size()==traceStart);
#endif
    printf("OBS selector=%x shape=%d result=%d sync=%u submit=%u maps=%u\\n",selector,shape,result,sync_calls,submit_calls,map_calls);''')
    fixture=fixture.replace('int main(int argc,char **argv)','int inheritedMain(int argc,char **argv)')
    opening=fixture.index('{',fixture.index('int inheritedMain('));ending=patch.matching(fixture,opening,'{','}')
    fixture=fixture[:ending]+'    return 0;\n'+fixture[ending:]
    fixture+='\nint main(int argc,char **argv){int rc=inheritedMain(argc,argv);\n#ifdef IO342_CANDIDATE\n if(!strcmp(argv[1],\"pilot\"))assert(io342::count>0);\n assert(!io342::invalid&&io342::active==nullptr);\n printf(\"IO342HOST records=%u\\n\",io342::count);\n#endif\n return rc;}\n'
    strip=lambda p:re.sub(r'^#include .*\n','',p.read_text(),flags=re.M)
    fixture=fixture.replace('static uint64_t ticks;return ++ticks;','static uint64_t ticks=210000000000ull;return ++ticks;')
    fixture=fixture.replace('@SURFACE_HEADER@',strip(C/'iokit/Kernel/arm/SweetSurface.h'))
    matches=re.findall(r'uintptr_t\nSweetSurface::kernelAddress\(\)\n\{[\s\S]*?\n\}',effective('iokit/Kernel/arm/SweetSurface.cpp').read_text());assert len(matches)==1
    fixture=fixture.replace('@SURFACE_KERNEL_ADDRESS@',matches[0])
    extra=strip(C/'iokit/Kernel/arm/SweetMetalBootstrap.h')+'\n[[maybe_unused]] static bool PE_parse_boot_argn(const char *,void *,int){return false;}\n[[maybe_unused]] static bool sweet_metal_desktop_enabled(){return false;}\n'
    out.mkdir();env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    flags=['-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(C/'bsd/dev')];steps=[]
    def run(args,label):
        with (out/(label+'.log')).open('x') as f:p=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        steps.append(dict(label=label,exit=p.returncode));assert p.returncode==0,(label,p.returncode)
    run(['clang','-std=c11',*flags,'-c',str(C/'bsd/dev/gauguin_gpu_runtime.c'),'-o',str(out/'runtime.o')],'compile-runtime')
    names=['submit','sync','queues','readonly','readonly-fault','slots','pilot','readonly-unmap']
    observations={}
    for variant,root in [('baseline',P),('candidate',C)]:
        src=fixture.replace('@SOURCE@',extra+(('[[maybe_unused]] static uint64_t thread_get_runtime_self(){return mach_absolute_time();}\n#include \"'+str(C/'iokit/Kernel/arm/Kernel342.hpp')+'\"\n') if variant=='candidate' else '')+strip(root/GPU)).replace('__asm__ volatile("dsb sy" ::: "memory")','__atomic_thread_fence(__ATOMIC_SEQ_CST)')
        unit=out/(variant+'.cpp');unit.write_text(src)
        run(['clang++','-std=c++17',*flags,'-DGAUGUIN_GPU_REQUEST_LOCKS=2','-DGAUGUIN_GPU_PILOT_HOST=1','-DTEST_BO333=1',*(['-DIO342_CANDIDATE=1'] if variant=='candidate' else []),str(unit),str(out/'runtime.o'),'-o',str(out/variant)],variant+'-compile')
        observations[variant]={}
        for name in names:
            label=variant+'-'+name;run([str(out/variant),name],label)
            observations[variant][name]=[line for line in (out/(label+'.log')).read_text().splitlines() if line.startswith('OBS ')]
    assert observations['baseline']==observations['candidate']
    count=sum(map(len,observations['candidate'].values()));assert count>1000
    assert all(sha(p)==d for p,d in pins.items())
    result=dict(state='0342-real-driver-root-request-equivalence-and-phase-contract-passed',scenarios=names,paired_request_observations=count,parent_candidate_observations_identical=True,source_transform_reversible=True,allocation_phases_monotonic=True,maximum_records_per_allocation=6,legacy_BO333_nonallocation_requests_uninstrumented=True,actual_IO342_records_and_phase_partition_checked=True,return_values_sync_submit_map_calls_unchanged=True,sanitizers='ASan+UBSan',root_cache_disabled=True,input_pins=pins,inputs_unchanged=True,steps=steps,device_commands=0)
    with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))
if __name__=='__main__':main()
