#!/usr/bin/env python3
"""Prepare bounded CPU-only rejection diagnostics around unchanged GPU submission semantics."""
from pathlib import Path
import difflib,hashlib,json,shutil
MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/submit-reject-327'
BASE=MAIN/'research/tmp/gauguin-perf430-worktree-20261115/research/tmp/perf430-326'
PARENT=BASE/'local-link/build-manifest.json'
CHANGED='iokit/Kernel/arm/GauguinGPU.cpp'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def instrument(raw):
 original=raw;edits=[]
 def edit(old,new):
  nonlocal raw
  assert raw.count(old)==1,old
  raw=raw.replace(old,new);edits.append((old,new))
 marker='struct gpu_queue {uint32_t id,issued,completed;};\n'
 diagnostic='''/* SUBMIT327: CPU metadata only under the existing request/GPU locks.
 * No validator, result, ownership, GPU access or retry changes. Stages1..4
 * are dispatch gates;10..20 identify the original submit refusal branches.
 * At most64 records and one limit marker over the whole boot. */
struct gsub_diag327 {
    uint32_t stage,index,handle,requested,actual,bo_state;
    uint32_t cmd_type,cmd_index,cmd_offset,cmd_bytes;
};
static uint32_t gsub_diag327_count;
static void gsub_diag327_log(const struct gsub_diag327 *d,const struct ggr_submit *r,
    IOReturn result,bool compositor,bool async,uint64_t token,uint32_t pending,
    uint32_t native,uint64_t bytes)
{
    if(result==kIOReturnSuccess||!compositor||!async||gsub_diag327_count>=65)return;
    if(gsub_diag327_count==64){
        ++gsub_diag327_count;
        IOLog("SWEET GPU SUBMIT327: limit=64 coverage=incomplete\\n");return;
    }
    ++gsub_diag327_count;
    IOLog("SWEET GPU SUBMIT327: seq=%u tick=%llu token=%llu rc=%08x stage=%u index=%u handle=%u requested=%08x actual=%08x bo_state=%u cmd_type=%u cmd_index=%u cmd_offset=%u cmd_bytes=%u bos=%u cmds=%u queue=%u flags=%08x fence=%u pending=%u native=%u bytes=%llu\\n",
        gsub_diag327_count,(unsigned long long)mach_absolute_time(),(unsigned long long)token,
        (uint32_t)result,d->stage,d->index,d->handle,d->requested,d->actual,d->bo_state,
        d->cmd_type,d->cmd_index,d->cmd_offset,d->cmd_bytes,r->nr_bos,r->nr_cmds,
        r->queueid,r->flags,r->fence,pending,native,(unsigned long long)bytes);
}
'''
 edit(marker,marker+diagnostic)
 edit('    uint32_t fAllocationStage,fAllocationFailures;','    uint32_t fAllocationStage,fAllocationFailures;\n    struct gsub_diag327 fSubmitDiag327;')
 start=raw.index('IOReturn GauguinGPUUserClient::submit(');end=raw.index('\nIOReturn GauguinGPUUserClient::externalMethod',start)
 method=raw[start:end];before=method
 def change(a,b):
  nonlocal method
  assert method.count(a)==1,a
  method=method.replace(a,b)
 change('''{
    if(fAsync&&fPendingCount){''','''{
    fSubmitDiag327={10,UINT32_MAX,0,0,0,0,0,0,0,0};
    if(fAsync&&fPendingCount){''')
 change('if(settled!=kIOReturnSuccess)return settled;','if(settled!=kIOReturnSuccess){fSubmitDiag327.stage=11;return settled;}')
 change('if(!bos||!cmds){result=kIOReturnNoMemory;goto out;}','if(!bos||!cmds){fSubmitDiag327.stage=12;result=kIOReturnNoMemory;goto out;}')
 change('result=kIOReturnVMError;goto out;','fSubmitDiag327.stage=13;result=kIOReturnVMError;goto out;')
 change('''               (bos[i].presumed&&bos[i].presumed!=b->address))goto out;
            for(uint32_t j=0;j<i;j++)if(bos[j].handle==bos[i].handle)goto out;''','''               (bos[i].presumed&&bos[i].presumed!=b->address)){
                fSubmitDiag327.stage=14;fSubmitDiag327.index=i;
                fSubmitDiag327.handle=bos[i].handle;fSubmitDiag327.requested=bos[i].flags;
                fSubmitDiag327.actual=b?b->flags:0;
                fSubmitDiag327.bo_state=(b?1u:0u)|(b&&b->pending?2u:0u)|
                    (b&&b->closePending?4u:0u)|(b&&b->surface?8u:0u)|
                    (bos[i].presumed?16u:0u)|(b&&bos[i].presumed==b->address?32u:0u);
                goto out;
            }
            for(uint32_t j=0;j<i;j++)if(bos[j].handle==bos[i].handle){
                fSubmitDiag327.stage=15;fSubmitDiag327.index=i;
                fSubmitDiag327.handle=bos[i].handle;fSubmitDiag327.cmd_index=j;goto out;
            }''')
 change('if(cmds[i].submit_idx>=r->nr_bos)goto out;','''if(cmds[i].submit_idx>=r->nr_bos){
                fSubmitDiag327.stage=16;fSubmitDiag327.index=i;
                fSubmitDiag327.cmd_index=cmds[i].submit_idx;goto out;
            }''')
 change('if(!(bos[cmds[i].submit_idx].flags&1)||!ggr_command_range(cmds+i,b->size))goto out;','''if(!(bos[cmds[i].submit_idx].flags&1)||!ggr_command_range(cmds+i,b->size)){
                fSubmitDiag327.stage=17;fSubmitDiag327.index=i;fSubmitDiag327.handle=b->handle;
                fSubmitDiag327.requested=bos[cmds[i].submit_idx].flags;fSubmitDiag327.actual=b->flags;
                fSubmitDiag327.cmd_type=cmds[i].type;fSubmitDiag327.cmd_index=cmds[i].submit_idx;
                fSubmitDiag327.cmd_offset=cmds[i].submit_offset;fSubmitDiag327.cmd_bytes=cmds[i].size;
                goto out;
            }''')
 change('if(!ptr)goto out;','if(!ptr){fSubmitDiag327.stage=18;fSubmitDiag327.index=i;fSubmitDiag327.handle=b->handle;goto out;}')
 change('if(ok&&(!fence||fence<=fNativeFence)){sweet_gpu_runtime_stop();ok=false;}','''if(ok&&(!fence||fence<=fNativeFence)){sweet_gpu_runtime_stop();ok=false;fSubmitDiag327.stage=20;}
        if(!ok&&fSubmitDiag327.stage!=20)fSubmitDiag327.stage=19;''')
 edit(before,method)
 edit('    fAllocationStage=0; /* runtime/client gate, before request validation */','''    fAllocationStage=0; /* runtime/client gate, before request validation */
    if(selector==0x46)fSubmitDiag327={1,UINT32_MAX,0,0,0,0,0,0,0,0};''')
 # The following exact snippets are outside submit(), inside the unchanged dispatch gates.
 edit('''        result=finishPending(true,true);
        if(result!=kIOReturnSuccess)goto out;
    }
    if(!sweet_gpu_runtime_ready()&&!(fAsync&&fPendingCount&&passive)){
        result=kIOReturnNotReady;goto out;
    }''','''        result=finishPending(true,true);
        if(result!=kIOReturnSuccess){if(selector==0x46)fSubmitDiag327.stage=2;goto out;}
    }
    if(!sweet_gpu_runtime_ready()&&!(fAsync&&fPendingCount&&passive)){
        if(selector==0x46)fSubmitDiag327.stage=3;
        result=kIOReturnNotReady;goto out;
    }''')
 edit('''        if(gMetalBootstrapMode&&!fCompositor&&gMetalBootstrap.armed) {
            ggr_bootstrap_fail(&gMetalBootstrap);result=kIOReturnNotPrivileged;break;
        }''','''        if(gMetalBootstrapMode&&!fCompositor&&gMetalBootstrap.armed) {
            fSubmitDiag327.stage=4;
            ggr_bootstrap_fail(&gMetalBootstrap);result=kIOReturnNotPrivileged;break;
        }''')
 edit('''    if(result==kIOReturnSuccess){memcpy(a->structureOutput,&r,size);a->structureOutputSize=(uint32_t)size;}
    gapi_end(profile,result);''','''    if(selector==0x46&&result!=kIOReturnSuccess)
        gsub_diag327_log(&fSubmitDiag327,&r.submit,result,fCompositor,fAsync,profile,
            fPendingCount,fNativeFence,fBytes);
    if(result==kIOReturnSuccess){memcpy(a->structureOutput,&r,size);a->structureOutputSize=(uint32_t)size;}
    gapi_end(profile,result);''')
 undone=raw
 for a,b in reversed(edits):assert undone.count(b)==1;undone=undone.replace(b,a)
 assert undone==original
 return raw

def main():
 assert sha(PARENT)=='936a6d59bdcea541bb7b00c4c8fb41a617555bcf9827e36ab3f10bff2789f610'
 parent=json.loads(PARENT.read_text());budget=json.loads((STATE/'storage-whole-batch-admission.json').read_text())
 assert budget['admitted'] and budget['planned_batch_bytes']==800000000
 src=Path(parent['source_union']['base']);overlay=Path(parent['source_union']['overlay']);out=STATE/'kernel-source';assert not out.exists();out.mkdir()
 pins={str(PARENT):sha(PARENT)}
 for path in sorted(overlay.rglob('*')):
  if not path.is_file():continue
  assert sha(path)==parent['input_pins'][str(path)]['sha256'];dst=out/path.relative_to(overlay);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dst);pins[str(path)]=sha(path)
 raw=(overlay/CHANGED).read_text();new=instrument(raw);(out/CHANGED).write_text(new)
 patch=WORK/'xnu/patches/0241-gauguin-submit-refusal-trace.patch';assert not patch.exists();patch.write_text(''.join(difflib.unified_diff(raw.splitlines(True),new.splitlines(True),fromfile='a/'+CHANGED,tofile='b/'+CHANGED)))
 result=dict(state='prepared-SUBMIT327-source-only',source=str(out),changed_files=[CHANGED],parent_manifest_sha256=sha(PARENT),patch=str(patch),patch_sha256=sha(patch),source_change_reversible=True,diagnostic_limit=64,limit_markers_max=1,record_bytes_max=512,new_GPU_commands=0,new_MMIO_reads=0,new_threads=0,default_results_and_ownership_unchanged=True,input_pins=pins,device_commands=0)
 (STATE/'source-preparation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
