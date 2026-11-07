#!/usr/bin/env python3
"""Actual board adapter with typed dependency and raw MMIO/barrier seams."""
from pathlib import Path
import hashlib,os,re,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get('XNU_SOURCE',str(R/'.deps-cache/p0-20261105/source152-v2-codex')))/'bsd/dev'
S=D/'gauguin_gmu_board.c';F=R/'tests/fixtures/gmu-board/board_host.c'
inputs=[S,F,D/'gauguin_gmu_board.h',D/'gauguin_gmu_smmu.h',D/'gauguin_gmu_memory.c',D/'gauguin_gmu_memory.h',D/'gauguin_pas_stage.h',D/'gauguin_gmu_clock.h',D/'gauguin_wdt_lease.h']
inputs += [D/'gauguin_gpu_sqe_asset.h',D/'gauguin_gmu_firmware.h',D/'gauguin_gmu_hfi.h',D/'gauguin_gmu_asset.h']
inputs += [D/(n+s) for n in ['gauguin_gpu_memory','gauguin_gpu_aperture','gauguin_gpu_start','gauguin_gpu_core'] for s in ['.c','.h']]+[D/'gauguin_gpu_smmu.h']
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
for asm,n in [('dmb oshld',4),('dmb oshst',3),('dsb sy',5)]:
    old='__asm__ volatile("'+asm+'" ::: "memory");';assert source.count(old)==n
    source=source.replace(old,'host_dsb();' if asm=='dsb sy' else 'host_barrier();')
assert '__asm__' not in source
# The remaining volatile uint32_t pointer is bounded NC RAM, backed by an
# aligned ordinary host array. Its real copy/zero/verify loops run unchanged.
fixture=F.read_text();assert fixture.count('@SOURCE@')==1
env=os.environ.copy();env.update(ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='gmu-board-') as tmp:
    unit=Path(tmp)/'test.c';binary=Path(tmp)/'test';unit.write_text(fixture.replace('@SOURCE@',source))
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D),str(unit),*[str(D/(n+'.c')) for n in ['gauguin_gmu_memory','gauguin_gpu_memory','gauguin_gpu_aperture','gauguin_gpu_start','gauguin_gpu_core']],'-o',str(binary)],env=env,check=True)
    subprocess.run([str(binary)],env=env,check=True)
assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}
