#!/usr/bin/env python3
"""Actual board adapter with typed dependency and raw MMIO/barrier seams."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source173-codex')))/'bsd/dev'
C=Path(os.environ.get('GMU_BOARD_SOURCE_DIR',str(D)))
S=C/'gauguin_gmu_board.c';F=R/'tests/fixtures/gmu-board/board_host.c'
G=R/'tests/fixtures/gmu-board/write_host.c'
I=R/'tests/fixtures/gmu-board/ib_host.c'
E=R/'tests/fixtures/gmu-board/eop_host.c'
K=R/'tests/fixtures/gmu-board/compute_host.c'
L=R/'tests/fixtures/gmu-board/clear_host.c'
T=R/'tests/fixtures/gmu-board/draw_host.c'
TV=R/'tests/fixtures/gpu-draw/native_words.h'
J=R/'tests/fixtures/gmu-board/sequence_host.c'
JV=R/'tests/fixtures/gpu-sequence/native_words.h'
VV=R/'tests/fixtures/gpu-varying/native_words.h'
VF=R/'tests/fixtures/gpu-varying/board_host.c'
VP=R/'tests/fixtures/gpu-varying/pixel_vectors173.h'
LV=R/'tests/fixtures/gpu-clear/source_profile_words.h'
V=R/'tests/fixtures/gpu-compute/native_words.h'
inputs=[S,F,G,I,E,K,L,T,TV,J,JV,VV,VF,VP,V,LV,C/'gauguin_gmu_board.h',D/'gauguin_gmu_smmu.h',D/'gauguin_gmu_memory.c',D/'gauguin_gmu_memory.h',D/'gauguin_pas_stage.h',D/'gauguin_gmu_clock.h',D/'gauguin_wdt_lease.h']
inputs += [D/'gauguin_gpu_sqe_asset.h',D/'gauguin_gmu_firmware.h',D/'gauguin_gmu_hfi.h',D/'gauguin_gmu_asset.h']
inputs += [D/(n+s) for n in ['gauguin_gpu_memory','gauguin_gpu_aperture','gauguin_gpu_start','gauguin_gpu_core','gauguin_gpu_cp','gauguin_gpu_zap','gauguin_gpu_unsecure','gauguin_gpu_data','gauguin_gpu_write','gauguin_gpu_ib'] for s in ['.c','.h']]+[D/'gauguin_gpu_smmu.h']
inputs += [D/'gauguin_gpu_eop.c',D/'gauguin_gpu_eop.h',C/'gauguin_gpu_compute.c',C/'gauguin_gpu_compute.h',C/'gauguin_gpu_clear.c',C/'gauguin_gpu_clear.h',C/'gauguin_gpu_draw.c',C/'gauguin_gpu_draw.h',C/'gauguin_gpu_draw_native.h',C/'gauguin_gpu_sequence.c',C/'gauguin_gpu_sequence.h',C/'gauguin_gpu_sequence_native.h',C/'gauguin_gpu_varying.c',C/'gauguin_gpu_varying.h',C/'gauguin_gpu_varying_native.h']
pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
source=re.sub(r'^#include .*\n','',S.read_text(),flags=re.M)
# Only the physical SMC instruction/register binding is replaced. The real
# fixed transaction engine is linked below and tested independently too.
pattern=r'static void ggb_invoke\(void \*cookie,struct gpa_registers \*r\)\n\{.*?\n\}'
smc=re.findall(pattern,source,flags=re.S);assert len(smc)==1 and '"smc #0"' in smc[0] and smc[0].count('"+r"')==7
source=re.sub(pattern,'static void ggb_invoke(void *cookie,struct gpa_registers *r)\n{host_gpu_smc(cookie,r);}',source,flags=re.S)
seams={
    'uint32_t reset=*(volatile uint32_t *)(gmb_reset+0x2000);':'uint32_t reset=mmio_read32(gmb_reset+0x2000);',
    '*v=*(volatile uint32_t *)(gmb_smmu+off);':'*v=mmio_read32(gmb_smmu+off);',
    '*(volatile uint32_t *)(gmb_smmu+off)=v;':'mmio_write32(gmb_smmu+off,v);',
    '*v=*(volatile uint64_t *)(gmb_smmu+off);':'*v=mmio_read64(gmb_smmu+off);',
    '*(volatile uint64_t *)(gmb_smmu+off)=v;':'mmio_write64(gmb_smmu+off,v);',
    'uint32_t value=*(volatile uint32_t *)address;':'uint32_t value=fw_read32(address);',
    '*(volatile uint32_t *)address=value;':'fw_write32(address,value);'}
for old,new in seams.items():assert source.count(old)==1;source=source.replace(old,new)
for asm,n in [('dmb oshld',5),('dmb oshst',3),('dsb sy',5)]:
    old='__asm__ volatile("'+asm+'" ::: "memory");';assert source.count(old)==n
    source=source.replace(old,'host_dsb();' if asm=='dsb sy' else 'host_barrier();')
assert '__asm__' not in source
# The remaining volatile uint32_t pointer is bounded NC RAM, backed by an
# aligned ordinary host array. Its real copy/zero/verify loops run unchanged.
fixture=F.read_text();assert fixture.count('@SOURCE@')==1 and fixture.count('@WRITE_FIXTURE@')==1
fixture=fixture.replace('@WRITE_FIXTURE@',G.read_text())
assert fixture.count('@IB_FIXTURE@')==1;fixture=fixture.replace('@IB_FIXTURE@',I.read_text())
assert fixture.count('@EOP_FIXTURE@')==1;fixture=fixture.replace('@EOP_FIXTURE@',E.read_text())
assert fixture.count('@COMPUTE_FIXTURE@')==1;fixture=fixture.replace('@COMPUTE_FIXTURE@',K.read_text())
assert fixture.count('@CLEAR_FIXTURE@')==1;fixture=fixture.replace('@CLEAR_FIXTURE@',L.read_text())
assert fixture.count('@TRIANGLE_FIXTURE@')==1;fixture=fixture.replace('@TRIANGLE_FIXTURE@',T.read_text())
assert fixture.count('@SEQUENCE_FIXTURE@')==1;fixture=fixture.replace('@SEQUENCE_FIXTURE@',J.read_text())
assert fixture.count('@VARYING_FIXTURE@')==1;fixture=fixture.replace('@VARYING_FIXTURE@',VF.read_text())
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gmu-board-') as tmp:
    unit=Path(tmp)/'test.c';binary=Path(tmp)/'test';unit.write_text(fixture.replace('@SOURCE@',source))
    if os.environ.get('GMU_BOARD_UNIT_COPY'):
        with Path(os.environ['GMU_BOARD_UNIT_COPY']).open('x') as f:f.write(unit.read_text())
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(C),'-I'+str(D),'-I'+str(V.parent),'-I'+str(R/'tests/fixtures'),str(unit),*[str(D/(n+'.c')) for n in ['gauguin_gmu_memory','gauguin_gpu_memory','gauguin_gpu_aperture','gauguin_gpu_start','gauguin_gpu_core','gauguin_gpu_cp','gauguin_gpu_zap','gauguin_gpu_unsecure','gauguin_gpu_data','gauguin_gpu_write','gauguin_gpu_ib']],str(D/'gauguin_gpu_eop.c'),str(C/'gauguin_gpu_compute.c'),str(C/'gauguin_gpu_clear.c'),str(C/'gauguin_gpu_draw.c'),str(C/'gauguin_gpu_sequence.c'),str(C/'gauguin_gpu_varying.c'),'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
    if os.environ.get('GPU_VARYING_BOARD_TRACE_DIR'):
        out=Path(os.environ['GPU_VARYING_BOARD_TRACE_DIR']);out.mkdir(exist_ok=False)
        for i in range(5):
            with (out/('scenario'+str(i)+'.log')).open('x') as f:subprocess.run([str(binary),'--varying',str(i)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    if os.environ.get('GPU_SEQUENCE_BOARD_TRACE_DIR'):
        out=Path(os.environ['GPU_SEQUENCE_BOARD_TRACE_DIR']);out.mkdir(exist_ok=False)
        for i in range(5):
            with (out/('scenario'+str(i)+'.log')).open('x') as f:subprocess.run([str(binary),str(i)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
