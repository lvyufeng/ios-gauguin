/* Actual Mesa flush + actual libdrm transport. Only IOKit/object/list storage
 * is provided by this host fixture; the native admission body is compiled too. */
#include <assert.h>
#include <IOKit/IOKitLib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static kern_return_t fixture_call(io_connect_t,uint32_t,const void *,size_t,void *,size_t *);
#define IOConnectCallStructMethod fixture_call
@TRANSPORT_SOURCE@
#undef IOConnectCallStructMethod
@FD_FLAGS@
#include @KERNEL_HEADER@
_Static_assert(sizeof(struct ggr_submit)==sizeof(struct drm_msm_gem_submit),"actual independent native submit size");
_Static_assert(sizeof(struct ggr_submit_bo)==sizeof(struct drm_msm_gem_submit_bo),"actual independent native BO size");
_Static_assert(sizeof(struct ggr_submit_cmd)==sizeof(struct drm_msm_gem_submit_cmd),"actual independent native command size");
_Static_assert(GGR_BO_READONLY==FD_BO_GPUREADONLY,"actual readonly allocation bit");
extern void native_reset(void);
extern void native_add(unsigned,unsigned long long,unsigned);
extern unsigned native_submit(struct drm_msm_gem_submit *);
extern unsigned native_jobs(void);
extern unsigned native_wait(unsigned,unsigned);
extern void native_timeout(int);
struct fd_bo { uint32_t handle,reloc_flags,alloc_flags; };
struct fd_device { int fd; };
struct fd_pipe { struct fd_device *dev; bool no_implicit_sync; };
struct msm_pipe { struct fd_pipe base; uint32_t pipe,queue_id; };
struct fd_fence { bool use_fence_fd; uint32_t kfence; int fence_fd; };
struct fd_ringbuffer { int unused; };
struct fd_ringbuffer_sp { struct fd_ringbuffer base; uint32_t offset; struct {unsigned nr_cmds;struct {struct fd_bo *ring_bo;uint32_t size;} cmds[1];} u; };
struct fd_submit { struct fd_pipe *pipe;struct fd_ringbuffer *primary;struct{int x;}node; };
struct fd_submit_sp { struct fd_submit base;unsigned nr_bos;struct fd_bo *bos[16];int in_fence_fd;struct fd_fence *out_fence; };
struct list_head { struct fd_submit *only; };
static struct fd_submit_sp *to_fd_submit_sp(struct fd_submit*p){return (void*)p;}
static struct msm_pipe *to_msm_pipe(struct fd_pipe*p){return (void*)p;}
static struct fd_ringbuffer_sp *to_fd_ringbuffer_sp(struct fd_ringbuffer*p){return (void*)p;}
static struct fd_submit *last_submit(struct list_head*p){return p->only;}
static unsigned submit_offset(struct fd_bo *bo,unsigned off){(void)bo;return off;}
static unsigned fd_submit_append_bo(struct fd_submit_sp*s,struct fd_bo*b){for(unsigned i=0;i<s->nr_bos;i++)if(s->bos[i]==b)return i;assert(s->nr_bos<16);s->bos[s->nr_bos]=b;return s->nr_bos++;}
static void list_del(void *node){(void)node;assert(!"single-entry fixture cannot delete a deferred item");}
static void fd_submit_del(struct fd_submit*s){(void)s;assert(!"single-entry fixture cannot delete a deferred item");}
static void msm_dump_submit(const struct drm_msm_gem_submit*s){(void)s;}
static void msm_dump_rd(struct fd_pipe*p,const struct drm_msm_gem_submit*s){(void)p;(void)s;}
#define foreach_submit(item,list) for(struct fd_submit *item=(list)->only;item;item=NULL)
#define foreach_submit_safe(item,list) foreach_submit(item,list)
#define MESA_TRACE_FUNC() ((void)0)
#define VOID2U64(p) ((uint64_t)(uintptr_t)(p))
#define DEBUG_MSG(...) ((void)0)
#define ERROR_MSG(...) ((void)0)
@FLUSH_FUNCTION@
static unsigned calls,checked,seen_readonly,seen_writable;
#define CHECK(x) do{checked++;assert(x);}while(0)
static kern_return_t fixture_call(io_connect_t c,uint32_t selector,const void *input,size_t size,void *output,size_t *returned)
{
    (void)c;CHECK(input==output&&*returned==size);
    if(selector==DRM_COMMAND_BASE+DRM_MSM_GEM_SUBMIT){
        CHECK(size==sizeof(struct drm_msm_gem_submit));struct drm_msm_gem_submit*s=output;calls++;
        struct drm_msm_gem_submit_bo*b=(void*)(uintptr_t)s->bos;
        for(unsigned i=0;i<s->nr_bos;i++){if(b[i].handle==10)seen_readonly=b[i].flags;if(b[i].handle==3)seen_writable=b[i].flags;}
        return native_submit(s);
    }
    CHECK(selector==DRM_COMMAND_BASE+DRM_MSM_WAIT_FENCE&&size==sizeof(struct drm_msm_wait_fence));
    struct drm_msm_wait_fence*w=output;return native_wait(w->queueid,w->fence);
}
static int send(unsigned readonly,unsigned reloc_flags,unsigned offset,unsigned bytes,struct fd_fence *fence)
{
    static const uint32_t handles[13]={3,12,16,21,22,23,24,25,10,14,15,17,7};
    struct fd_bo bos[13];struct fd_submit_sp submit={0};struct fd_device dev={0};struct msm_pipe pipe={.base={.dev=&dev},.pipe=0x10,.queue_id=1};
    for(unsigned i=0;i<13;i++){
        bos[i]=(struct fd_bo){.handle=handles[i],.reloc_flags=3,.alloc_flags=(i==8&&readonly)?FD_BO_GPUREADONLY:0};
        native_add(handles[i],262144,(i==8&&readonly)?2:0);submit.bos[i]=&bos[i];
    }
    bos[8].reloc_flags=reloc_flags;submit.nr_bos=13;
    struct fd_ringbuffer_sp ring={.offset=offset,.u={.nr_cmds=1,.cmds={{.ring_bo=&bos[8],.size=bytes}}}};
    submit.base=(struct fd_submit){.pipe=&pipe.base,.primary=&ring.base};submit.out_fence=fence;submit.in_fence_fd=-1;struct list_head list={.only=&submit.base};
    return flush_submit_list(&list);
}
int main(int argc,char**argv)
{
    bool old=argc>1&&!strcmp(argv[1],"old");native_reset();struct fd_fence f={.kfence=99,.fence_fd=-1};
    int rc=send(1,3,32768,656,&f);
    printf("captured13BO readonly-command request rc=%d jobs=%u readonly_flags=%u writable_flags=%u\n",rc,native_jobs(),seen_readonly,seen_writable);fflush(stdout);
    if(old){CHECK(rc==-EINVAL&&native_jobs()==0&&seen_readonly==3&&f.kfence==99);puts("RED: actual old flush rejected by actual native readonly admission");return 17;}
    CHECK(rc==0&&native_jobs()==1&&seen_readonly==1&&seen_writable==3&&f.kfence==1);
    native_reset();CHECK(send(0,3,32768,656,&f)==0&&native_jobs()==1&&seen_readonly==3);
    native_reset();CHECK(send(1,MSM_SUBMIT_BO_READ|MSM_SUBMIT_BO_DUMP,32768,656,&f)==0&&native_jobs()==1&&seen_readonly==1);
    native_reset();CHECK(send(1,MSM_SUBMIT_BO_WRITE,32768,656,&f)==-EINVAL&&native_jobs()==0&&seen_readonly==0);
    native_reset();CHECK(send(1,MSM_SUBMIT_BO_READ|0x40,32768,656,&f)==-EINVAL&&native_jobs()==0&&seen_readonly==0x41);
    native_reset();CHECK(send(1,3,262144,656,&f)==-EINVAL&&native_jobs()==0);
    native_reset();native_timeout(1);f.kfence=99;CHECK(send(1,3,32768,656,&f)==-ETIMEDOUT&&native_jobs()==1&&f.kfence==99);native_timeout(0);
    /* Exercise the actual transport's private syncobj consumption against the
     * actual kernel rule that no array count, pointer OR stride reaches it. */
    native_reset();native_add(10,262144,2);uint32_t handle=0;CHECK(drmSyncobjCreate(0,0,&handle)==0&&handle);
    struct drm_msm_gem_submit_bo bo={.flags=1,.handle=10};struct drm_msm_gem_submit_cmd cmd={.type=1,.submit_offset=32768,.size=656};
    struct drm_msm_gem_submit_syncobj out={.handle=handle,.point=7};
    struct drm_msm_gem_submit s={.flags=0x10|MSM_SUBMIT_SYNCOBJ_OUT,.nr_bos=1,.nr_cmds=1,.bos=(uintptr_t)&bo,.cmds=(uintptr_t)&cmd,.fence_fd=-1,.queueid=1,.out_syncobjs=(uintptr_t)&out,.nr_out_syncobjs=1,.syncobj_stride=sizeof(out)};
    CHECK(drmCommandWriteRead(0,DRM_MSM_GEM_SUBMIT,&s,sizeof(s))==0&&s.fence==1&&s.syncobj_stride==0&&!s.out_syncobjs&&!s.nr_out_syncobjs);
    uint64_t point=7;CHECK(drmSyncobjTimelineWait(0,&handle,&point,1,0,DRM_SYNCOBJ_WAIT_FLAGS_WAIT_ALL,NULL)==0);
    CHECK(calls==8);printf("GREEN: %u checks; actual flush/transport/native admission;8scenarios;no device GPU execution\n",checked);return 0;
}
