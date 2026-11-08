/* Include the ACTUAL prepared libdrm transport. Only its IOKit call boundary
 * is mocked; no GPU, device service or root volume is used by this test. */
#include <assert.h>
#include <IOKit/IOKitLib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static kern_return_t fixture_call(io_connect_t,uint32_t,const void *,size_t,void *,size_t *);
#define IOConnectCallStructMethod fixture_call
@SOURCE@
#undef IOConnectCallStructMethod
static unsigned checks,submits,waits,zero_queue_waits;
static bool defer_completion,submit_fails;
static struct {uint32_t submitted,completed;bool closed;} model_queues[3];
#define CHECK(x) do{++checks;assert(x);}while(0)
static kern_return_t fixture_call(io_connect_t c,uint32_t selector,const void *input,size_t bytes,void *output,size_t *returned)
{
    (void)c;assert(input==output&&*returned==bytes);
    if(selector==DRM_COMMAND_BASE+DRM_MSM_GEM_SUBMIT) {
        assert(bytes==sizeof(struct drm_msm_gem_submit));
        struct drm_msm_gem_submit *s=output;
        assert(s->queueid>0&&s->queueid<3&&!model_queues[s->queueid].closed);
        assert(s->nr_cmds&&!s->in_syncobjs&&!s->out_syncobjs&&!s->nr_in_syncobjs&&!s->nr_out_syncobjs);
        ++submits;
        if(submit_fails)return kIOReturnTimeout;
        s->fence=++model_queues[s->queueid].submitted;
        if(!defer_completion)model_queues[s->queueid].completed=s->fence;
        return 0;
    }
    assert(selector==DRM_COMMAND_BASE+DRM_MSM_WAIT_FENCE&&bytes==sizeof(struct drm_msm_wait_fence));
    struct drm_msm_wait_fence *w=output;++waits;
    if(!w->queueid){++zero_queue_waits;return kIOReturnBadArgument;}
    assert(w->queueid<3);
    return !model_queues[w->queueid].closed&&w->fence&&w->fence<=model_queues[w->queueid].completed?0:kIOReturnTimeout;
}
static uint32_t make(void)
{uint32_t h=0;CHECK(drmSyncobjCreate(0,0,&h)==0&&h);return h;}
static int send(uint32_t queue,uint32_t handle,uint64_t point,uint32_t *fence)
{
    struct drm_msm_gem_submit_syncobj out={.handle=handle,.point=point};
    struct drm_msm_gem_submit s={.flags=0x10|MSM_SUBMIT_SYNCOBJ_OUT,.nr_cmds=1,.fence_fd=-1,
        .queueid=queue,.out_syncobjs=(uintptr_t)&out,.nr_out_syncobjs=1,.syncobj_stride=sizeof(out)};
    int error=drmCommandWriteRead(0,DRM_MSM_GEM_SUBMIT,&s,sizeof(s));
    if(fence)*fence=s.fence;
    return error;
}
static int poll(uint32_t h,uint64_t point)
{return drmSyncobjTimelineWait(0,&h,&point,1,0,DRM_SYNCOBJ_WAIT_FLAGS_WAIT_ALL,NULL);}
int main(int argc,char **argv)
{
    uint32_t a=make(),b=make(),fa=0,fb=0;
    CHECK(send(1,a,1,&fa)==0&&fa==1);
    CHECK(send(2,b,1,&fb)==0&&fb==1);
    CHECK(poll(a,1)==0); /* old code asks queue0 and functionally fails here */
    CHECK(poll(b,1)==0&&waits&&!zero_queue_waits);
    if(argc>1&&!strcmp(argv[1],"common"))return 0;
    /* A completion on q2 must not complete the same number on q1. */
    uint32_t pending=make();defer_completion=true;
    CHECK(send(1,pending,7,&fa)==0&&fa==2);
    defer_completion=false;CHECK(send(2,b,2,&fb)==0&&fb==2);
    CHECK(poll(pending,7)==-ETIME&&poll(b,2)==0);
    /* Timeline transfer must carry the entire queue/fence pair. */
    uint32_t destination=make();
    CHECK(drmSyncobjTransfer(0,destination,11,pending,7,0)==0);
    model_queues[1].completed=2;
    CHECK(poll(destination,11)==0&&poll(pending,7)==0&&!zero_queue_waits);
    /* Cache only an actually verified completed receipt before queue close. */
    CHECK(send(2,b,3,&fb)==0&&fb==3);
    model_queues[2].closed=true;unsigned previous_waits=waits;
    CHECK(poll(b,3)==0&&waits==previous_waits);
    model_queues[2].closed=false;
    uint32_t empty=make();unsigned previous_submits=submits;
    struct drm_msm_gem_submit_syncobj out={.handle=empty,.point=1};
    struct drm_msm_gem_submit s={.flags=0x10|MSM_SUBMIT_SYNCOBJ_OUT,.queueid=1,
        .out_syncobjs=(uintptr_t)&out,.nr_out_syncobjs=1,.syncobj_stride=sizeof(out),.fence_fd=-1};
    CHECK(drmCommandWriteRead(0,DRM_MSM_GEM_SUBMIT,&s,sizeof(s))==-EINVAL&&submits==previous_submits);
    CHECK(poll(empty,1)==-EINVAL);
    submit_fails=true;CHECK(send(1,empty,1,NULL)==-ETIMEDOUT);submit_fails=false;
    CHECK(poll(empty,1)==-EINVAL);
    /* Saturated pending storage and a failed old wait must preserve reached0,
     * all16pending receipts and the caller-visible failure of the17th. */
    uint32_t full=make();defer_completion=true;
    for(uint64_t point=1;point<=16;point++)CHECK(send(1,full,point,NULL)==0);
    CHECK(send(1,full,17,NULL)==-ETIME);
    CHECK(syncobj_of(full)->pending==16&&syncobj_of(full)->reached==0);
    CHECK(poll(full,1)==-ETIME&&!zero_queue_waits);
    printf("PASS: %u actual Mesa libdrm queue/fence assertions; host-only typed IOKit boundary\n",checks);
}
