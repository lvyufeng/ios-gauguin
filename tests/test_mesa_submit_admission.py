#!/usr/bin/env python3
"""Compile actual Mesa flush/transport and native submit, with typed host seams.

Old source must reproduce readonly admission refusal; new source must pass
without removing native BO permissions, range checks or failure propagation.
The ring/IO/object storage are fake. No physical GPU acceptance is possible.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--old-source',type=Path,required=True);ap.add_argument('--kernel-source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    R=Path(__file__).resolve().parents[1];a.out.mkdir(parents=True,exist_ok=False)
    cfixture=R/'tests/fixtures/mesa_submit_admission.c';nativefixture=R/'tests/fixtures/mesa_submit_native.cpp';native=a.kernel_source/'iokit/Kernel/arm/GauguinGPU.cpp';runtime=a.kernel_source/'bsd/dev/gauguin_gpu_runtime.c';header=a.kernel_source/'bsd/dev/gauguin_gpu_runtime.h'
    native_text=native.read_text();start=native_text.index('IOReturn GauguinGPUUserClient::submit(');end=native_text.index('\nIOReturn GauguinGPUUserClient::externalMethod',start);body=native_text[start:end]
    assert '((bos[i].flags&2)&&(b->flags&GGR_BO_READONLY))' in body and 'ggr_command_range' in body
    paths=[Path(__file__),cfixture,nativefixture,native,runtime,header]
    for source in [a.old_source,a.source]:paths += [source/'src/freedreno/drm/msm/msm_ringbuffer_sp.c',source/'src/hakios-drm/hakios.drm.c',source/'src/hakios-drm/xf86drm.h',source/'src/freedreno/drm/freedreno_drmif.h',source/'src/freedreno/drm/freedreno_priv.h',*list((source/'include/drm-uapi').glob('*.h'))]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pins={str(p.resolve()):sha(p) for p in paths}
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip();cc=subprocess.check_output(['xcrun','--sdk','macosx','--find','clang'],text=True).strip();cxx=subprocess.check_output(['xcrun','--sdk','macosx','--find','clang++'],text=True).strip()
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    common=['-isysroot',sdk,'-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer'];runs=[]
    result={'state':'running-actual-Mesa-native-admission-RED-GREEN','device_commands':0,'physical_qualified':False,'input_pins':pins,'runs':runs,'native_submit_body_sha256':hashlib.sha256(body.encode()).hexdigest(),'scope':'Full production Mesa flush+libdrm transport and full original native submit body. Object/list storage, IO and hardware ring execution are mocked.'}
    def save():(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(name,argv,expected=0):
        p=subprocess.run(argv,env=env,capture_output=True);(a.out/(name+'.stdout')).write_bytes(p.stdout);(a.out/(name+'.stderr')).write_bytes(p.stderr);runs.append({'name':name,'exit':p.returncode,'argv':argv});save();assert p.returncode==expected,(name,p.returncode,p.stderr.decode(errors='replace'));return p
    unit=a.out/'native.cpp';unit.write_text(nativefixture.read_text().replace('@KERNEL_HEADER@',json.dumps(str(header.resolve()))).replace('@NATIVE_SUBMIT_FUNCTION@',body))
    run('native-compile',[cxx,*common,'-std=c++17','-c',str(unit),'-o',str(a.out/'native.o')])
    run('runtime-compile',[cc,*common,'-std=c11','-I'+str(header.parent),'-c',str(runtime),'-o',str(a.out/'runtime.o')])
    for mode,source in [('old',a.old_source.resolve()),('new',a.source.resolve())]:
        flags=(source/'src/freedreno/drm/freedreno_drmif.h').read_text();definition=re.search(r'^#define FD_BO_GPUREADONLY[^\n]+',flags,re.M).group();assert definition.split()[-1]=='BITSET_BIT(1)'
        assert '#define RING_FLAGS (FD_BO_GPUREADONLY |' in (source/'src/freedreno/drm/freedreno_priv.h').read_text()
        flush=(source/'src/freedreno/drm/msm/msm_ringbuffer_sp.c').read_text();start=flush.index('static int\nflush_submit_list(');end=flush.index('\nstruct fd_submit *\nmsm_submit_sp_new',start);function=flush[start:end]
        text=cfixture.read_text().replace('@TRANSPORT_SOURCE@','#include '+json.dumps(str(source/'src/hakios-drm/hakios.drm.c'))).replace('@FD_FLAGS@','#define BITSET_BIT(b) (1U<<(b))\n'+definition).replace('@KERNEL_HEADER@',json.dumps(str(header.resolve()))).replace('@FLUSH_FUNCTION@',function)
        assert not re.search(r'@[A-Z_]+@',text);unit=a.out/(mode+'.c');unit.write_text(text)
        run(mode+'-compile',[cc,*common,'-std=c11','-I'+str(source/'include'),'-c',str(unit),'-o',str(a.out/(mode+'.o'))])
        run(mode+'-link',[cxx,*common,str(a.out/(mode+'.o')),str(a.out/'native.o'),str(a.out/'runtime.o'),'-framework','IOKit','-framework','CoreFoundation','-o',str(a.out/mode)])
        p=run(mode+'-run',[str(a.out/mode),mode],17 if mode=='old' else 0)
        assert not p.stderr,p.stderr
        if mode=='old':assert b'rc=-22 jobs=0 readonly_flags=3 writable_flags=3' in p.stdout and b'RED: actual old flush rejected' in p.stdout
        else:assert b'rc=0 jobs=1 readonly_flags=1 writable_flags=3' in p.stdout and b'GREEN:' in p.stdout and b'8scenarios' in p.stdout
    assert pins=={str(p.resolve()):sha(p) for p in paths}
    result.update(state='passed-actual-Mesa-native-submit-admission-RED-GREEN',inputs_unchanged=True,scenarios=8,native_readonly_validation_unchanged=True,native_range_validation_unchanged=True);save();print(json.dumps({k:v for k,v in result.items() if k not in ['input_pins','runs']},indent=2))
if __name__=='__main__':main()
