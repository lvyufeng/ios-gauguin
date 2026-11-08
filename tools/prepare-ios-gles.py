#!/usr/bin/env python3
"""Prepare a separate, pinned Mesa source tree for gauguin's GLES backend.

No kernel build, device access or installation. Original Mesa/cache inputs are
read-only; output must not exist. This is an A619-specific port, not a generic
Darwin hardware driver. Physical qualification is a separate mandatory step.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,tarfile

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def change(root,rel,old,new):
    p=root/rel;text=p.read_text();assert text.count(old)==1,('source context changed',rel)
    p.write_text(text.replace(old,new))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--upstream-cache',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    repo=Path(__file__).resolve().parent.parent;manifest=repo/'userland/mesa/upstream.json';p=json.loads(manifest.read_text());cache=a.upstream_cache.resolve();out=a.out.resolve()
    assert sha(a.archive)==p['mesa_archive_sha256'],'wrong primary Mesa source archive'
    pins={str(a.archive.resolve()):sha(a.archive),str(manifest):sha(manifest),str(Path(__file__).resolve()):sha(Path(__file__).resolve())}
    for row in p['files']:
        path=cache/row['path'];data=path.read_bytes()
        assert len(data)==row['bytes'] and sha(path)==row['sha256']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['git_blob']
        pins[str(path)]=sha(path)
    out.mkdir(parents=True,exist_ok=False)
    with tarfile.open(a.archive) as t:t.extractall(out,filter='data')
    source=out/('mesa-'+p['mesa_version']);assert (source/'VERSION').read_text().strip()==p['mesa_version']
    for i,name in enumerate(['freedreno-darwin.patch','osmesa-es-profile.patch']):
        patch=cache/'tools/mesa'/name
        with (out/f'upstream-patch-{i}.log').open('x') as f:
            r=subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1','-d',str(source),'-i',str(patch)],stdout=f,stderr=subprocess.STDOUT)
        assert r.returncode==0,('upstream patch failed',name)
    shutil.copytree(cache/'tools/mesa/hakios-drm',source/'src/hakios-drm')
    # Upstream OSMesa's guard predates this Darwin hardware winsys. Keep this
    # port GPU-only: without a real screen, context creation fails explicitly.
    change(source,'meson.build','''  if not with_gallium_swrast
    error('OSMesa gallium requires gallium softpipe or llvmpipe.')''','''  if not with_gallium_swrast and not (host_machine.system() == 'darwin' and with_gallium_freedreno)
    error('OSMesa gallium requires a built software or Darwin freedreno winsys.')''')
    change(source,'src/gallium/targets/osmesa/osmesa_target.c','''   struct sw_winsys *winsys;
   struct pipe_screen *screen;

#ifdef GALLIUM_FREEDRENO
   screen = osmesa_create_gpu_screen();
   if (screen)
      return screen;
#endif''','''#ifdef GALLIUM_FREEDRENO
   return osmesa_create_gpu_screen();
#else
   struct sw_winsys *winsys;
   struct pipe_screen *screen;''')
    change(source,'src/gallium/targets/osmesa/osmesa_target.c','''   return debug_screen_wrap(screen);
}''','''   return debug_screen_wrap(screen);
#endif
}''')
    # Target only the features implemented by our kernel ABI. Version4 keeps
    # softpin/queues; neither robust-reset nor suspend counters are fabricated.
    change(source,'src/hakios-drm/hakios.drm.c','version->version_minor = 7;','version->version_minor = 4; /* gauguin: softpin, no fabricated recovery/suspend API */')
    change(source,'src/hakios-drm/hakios.drm.c','case 0:\n\t\treturn 0;','case 0:\n\t\treturn returned == size ? 0 : EPROTO;')
    change(source,'src/hakios-drm/hakios.drm.c','\t(void)size;\n\t/*','\t/*')
    change(source,'src/hakios-drm/hakios.drm.c','\treturn (void *)(uintptr_t)address;','''\tif (mapped < size || address == 0) {
\t\tif (address) IOConnectUnmapMemory64(connection, handle, mach_task_self(), address);
\t\terrno = EIO;
\t\treturn (void *)-1;
\t}
\treturn (void *)(uintptr_t)address;''')
    # Linux ignores unused relocation fields; our strict wire parser requires
    # zero. fence_fd is -1 for a numeric-fence submission, never fd0 by default.
    change(source,'src/freedreno/drm/msm/msm_ringbuffer_sp.c','      .queueid = msm_pipe->queue_id,','      .queueid = msm_pipe->queue_id,\n      .fence_fd = -1,')
    change(source,'src/freedreno/drm/msm/msm_ringbuffer_sp.c','   struct drm_msm_gem_submit_cmd cmds[nr_cmds];','   struct drm_msm_gem_submit_cmd cmds[nr_cmds];\n   memset(cmds, 0, sizeof(cmds));')
    # DUMP is an advisory Linux capture hint, with no DMA/read/write semantics.
    change(source,'src/freedreno/drm/msm/msm_ringbuffer_sp.c','submit_bos[i].flags = fd_submit->bos[i]->reloc_flags;','submit_bos[i].flags = fd_submit->bos[i]->reloc_flags & ~MSM_SUBMIT_BO_DUMP;')
    change(source,'src/gallium/drivers/freedreno/freedreno_screen.c','caps->native_fence_fd = fd_device_version(screen->dev) >= FD_VERSION_FENCE_FD;','caps->native_fence_fd = false; /* gauguin: real numeric fences only */')
    # This build is intentionally restricted to the hardware whose USER32
    # event profile was exercised in the retained170..174 physical trials.
    change(source,'src/freedreno/drm/msm/msm_pipe.c','   msm_pipe->chip_id = get_param(pipe, MSM_PARAM_CHIP_ID);','''   msm_pipe->chip_id = get_param(pipe, MSM_PARAM_CHIP_ID);
   if (msm_pipe->gpu_id != 619 || msm_pipe->chip_id != 0x06010900 ||
       msm_pipe->gmem != 512 * 1024) {
      ERROR_MSG("gauguin GLES profile requires the actual A619 query identity");
      goto fail;
   }''')
    # Mesa24 profile has already been physically checked; port its source
    # selection, not captured packets, to Mesa25's equivalent template.
    change(source,'src/gallium/drivers/freedreno/a6xx/fd6_emit.h','''   if (CHIP == A6XX) {
      OUT_PKT7(ring, CP_EVENT_WRITE, len);
      OUT_RING(ring, CP_EVENT_WRITE_0_EVENT(info.raw_event) |
               COND(info.needs_seqno, CP_EVENT_WRITE_0_TIMESTAMP));''','''   if (CHIP == A6XX) {
      /* gauguin A619: USER32 writes val; only RB_DONE/ALWAYSON timestamps. */
      if (edst != EV_DST_RAM ||
          !(esrc == EV_WRITE_USER_32B ||
            (esrc == EV_WRITE_ALWAYSON && event == FD_RB_DONE)))
         abort();
      OUT_PKT7(ring, CP_EVENT_WRITE, len);
      OUT_RING(ring, CP_EVENT_WRITE_0_EVENT(info.raw_event) |
               COND(esrc == EV_WRITE_ALWAYSON, CP_EVENT_WRITE_0_TIMESTAMP));''')
    # The native gauguin transport uses queue-local completed fences. Preserve
    # the queue namespace throughout syncobj polling/transfer and never turn a
    # failed wait or an empty job into a fabricated completion receipt.
    local=repo/'userland/mesa/queue-local-fences.patch'
    pins[str(local)]=sha(local)
    with (out/'gauguin-queue-fences.log').open('x') as f:
        r=subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1','-d',str(source),'-i',str(local)],stdout=f,stderr=subprocess.STDOUT)
    assert r.returncode==0,'local queue/fence source patch failed'
    changed={};original={}
    with tarfile.open(a.archive) as t:
        for m in t:
            if not m.isfile():continue
            rel=m.name.removeprefix('mesa-'+p['mesa_version']+'/');old=t.extractfile(m).read();file=source/rel
            if not file.is_file():continue
            if old!=file.read_bytes():original[rel]=hashlib.sha256(old).hexdigest();changed[rel]=sha(file)
    changed['src/hakios-drm/hakios.drm.c']=sha(source/'src/hakios-drm/hakios.drm.c')
    changed['src/hakios-drm/xf86drm.h']=sha(source/'src/hakios-drm/xf86drm.h')
    result={'state':'prepared-pinned-A619-Darwin-GLES-source','source':str(source),'input_pins':pins,'changed_source_pins':changed,'original_source_pins':original,
        'device_commands':0,'kernel_source_modified':False,'physical_qualified':False,'required_kernel_profile':'gauguin179 service, bounded logical queues, configured GMEM parameter6; physical GLES acceptance still required','required_kernel_followup':['multi-client isolation before ordinary UI apps'],
        'scope':'GLES library only. AIR/Metal frontend not included; firmware/power/boot sources untouched.'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if not k.endswith('pins')},indent=2))
if __name__=='__main__':main()
