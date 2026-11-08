/* Compare independent Linux/Mesa UAPI declarations with the actual kernel ABI.
 * Compile and run natively, and also compile for the iOS target. No GPU model.
 */
#include <stddef.h>
#include <stdio.h>
#include <drm-uapi/msm_drm.h>
#include <gauguin_gpu_runtime.h>
#include <xf86drm.h>
#define SIZE(a,b) _Static_assert(sizeof(struct a)==sizeof(struct b),#a " size differs from " #b)
#define FIELD(a,b,f) _Static_assert(offsetof(struct a,f)==offsetof(struct b,f),#a "." #f " differs from " #b)
#define PAIR(a,b,f,g) _Static_assert(offsetof(struct a,f)==offsetof(struct b,g),#a "." #f " differs from " #b "." #g)
SIZE(ggr_timespec,drm_msm_timespec);PAIR(ggr_timespec,drm_msm_timespec,seconds,tv_sec);PAIR(ggr_timespec,drm_msm_timespec,nanoseconds,tv_nsec);
SIZE(ggr_param,drm_msm_param);FIELD(ggr_param,drm_msm_param,pipe);FIELD(ggr_param,drm_msm_param,param);FIELD(ggr_param,drm_msm_param,value);FIELD(ggr_param,drm_msm_param,len);FIELD(ggr_param,drm_msm_param,pad);
SIZE(ggr_new,drm_msm_gem_new);FIELD(ggr_new,drm_msm_gem_new,size);FIELD(ggr_new,drm_msm_gem_new,flags);FIELD(ggr_new,drm_msm_gem_new,handle);
SIZE(ggr_info,drm_msm_gem_info);FIELD(ggr_info,drm_msm_gem_info,handle);FIELD(ggr_info,drm_msm_gem_info,info);FIELD(ggr_info,drm_msm_gem_info,value);FIELD(ggr_info,drm_msm_gem_info,len);FIELD(ggr_info,drm_msm_gem_info,pad);
SIZE(ggr_cpu_prep,drm_msm_gem_cpu_prep);FIELD(ggr_cpu_prep,drm_msm_gem_cpu_prep,handle);FIELD(ggr_cpu_prep,drm_msm_gem_cpu_prep,op);FIELD(ggr_cpu_prep,drm_msm_gem_cpu_prep,timeout);
SIZE(ggr_cpu_fini,drm_msm_gem_cpu_fini);FIELD(ggr_cpu_fini,drm_msm_gem_cpu_fini,handle);
SIZE(ggr_submit_bo,drm_msm_gem_submit_bo);FIELD(ggr_submit_bo,drm_msm_gem_submit_bo,flags);FIELD(ggr_submit_bo,drm_msm_gem_submit_bo,handle);FIELD(ggr_submit_bo,drm_msm_gem_submit_bo,presumed);
SIZE(ggr_submit_cmd,drm_msm_gem_submit_cmd);FIELD(ggr_submit_cmd,drm_msm_gem_submit_cmd,type);FIELD(ggr_submit_cmd,drm_msm_gem_submit_cmd,submit_idx);FIELD(ggr_submit_cmd,drm_msm_gem_submit_cmd,submit_offset);FIELD(ggr_submit_cmd,drm_msm_gem_submit_cmd,size);FIELD(ggr_submit_cmd,drm_msm_gem_submit_cmd,pad);FIELD(ggr_submit_cmd,drm_msm_gem_submit_cmd,nr_relocs);FIELD(ggr_submit_cmd,drm_msm_gem_submit_cmd,relocs);
SIZE(ggr_submit,drm_msm_gem_submit);FIELD(ggr_submit,drm_msm_gem_submit,flags);FIELD(ggr_submit,drm_msm_gem_submit,fence);FIELD(ggr_submit,drm_msm_gem_submit,nr_bos);FIELD(ggr_submit,drm_msm_gem_submit,nr_cmds);FIELD(ggr_submit,drm_msm_gem_submit,bos);FIELD(ggr_submit,drm_msm_gem_submit,cmds);FIELD(ggr_submit,drm_msm_gem_submit,fence_fd);FIELD(ggr_submit,drm_msm_gem_submit,queueid);FIELD(ggr_submit,drm_msm_gem_submit,in_syncobjs);FIELD(ggr_submit,drm_msm_gem_submit,out_syncobjs);FIELD(ggr_submit,drm_msm_gem_submit,nr_in_syncobjs);FIELD(ggr_submit,drm_msm_gem_submit,nr_out_syncobjs);FIELD(ggr_submit,drm_msm_gem_submit,syncobj_stride);FIELD(ggr_submit,drm_msm_gem_submit,pad);
SIZE(ggr_wait,drm_msm_wait_fence);FIELD(ggr_wait,drm_msm_wait_fence,fence);FIELD(ggr_wait,drm_msm_wait_fence,flags);FIELD(ggr_wait,drm_msm_wait_fence,timeout);FIELD(ggr_wait,drm_msm_wait_fence,queueid);
SIZE(ggr_close,drm_gem_close);FIELD(ggr_close,drm_gem_close,handle);FIELD(ggr_close,drm_gem_close,pad);
SIZE(ggr_madvise,drm_msm_gem_madvise);FIELD(ggr_madvise,drm_msm_gem_madvise,handle);FIELD(ggr_madvise,drm_msm_gem_madvise,madv);FIELD(ggr_madvise,drm_msm_gem_madvise,retained);
SIZE(ggr_queue,drm_msm_submitqueue);FIELD(ggr_queue,drm_msm_submitqueue,flags);FIELD(ggr_queue,drm_msm_submitqueue,prio);FIELD(ggr_queue,drm_msm_submitqueue,id);
SIZE(ggr_queue_query,drm_msm_submitqueue_query);FIELD(ggr_queue_query,drm_msm_submitqueue_query,data);FIELD(ggr_queue_query,drm_msm_submitqueue_query,id);FIELD(ggr_queue_query,drm_msm_submitqueue_query,param);FIELD(ggr_queue_query,drm_msm_submitqueue_query,len);FIELD(ggr_queue_query,drm_msm_submitqueue_query,pad);
SIZE(ggr_surface,hakios_drm_surface);FIELD(ggr_surface,hakios_drm_surface,surface);FIELD(ggr_surface,hakios_drm_surface,handle);FIELD(ggr_surface,hakios_drm_surface,size);FIELD(ggr_surface,hakios_drm_surface,offset);PAIR(ggr_surface,hakios_drm_surface,rowBytes,row_bytes);FIELD(ggr_surface,hakios_drm_surface,width);FIELD(ggr_surface,hakios_drm_surface,height);PAIR(ggr_surface,hakios_drm_surface,pixelFormat,pixel_format);FIELD(ggr_surface,hakios_drm_surface,planes);
_Static_assert(MSM_PIPE_3D0==0x10,"actual Linux pipe number");
_Static_assert(MSM_BO_GPU_READONLY==GGR_BO_READONLY && MSM_BO_WC==GGR_BO_WC,"BO flag parity");
_Static_assert(DRM_COMMAND_BASE+DRM_MSM_GET_PARAM==0x40 && DRM_COMMAND_BASE+DRM_MSM_GEM_NEW==0x42 && DRM_COMMAND_BASE+DRM_MSM_GEM_INFO==0x43,"query/BO selector parity");
_Static_assert(DRM_COMMAND_BASE+DRM_MSM_GEM_SUBMIT==0x46 && DRM_COMMAND_BASE+DRM_MSM_WAIT_FENCE==0x47,"submit/fence selector parity");
_Static_assert(DRM_COMMAND_BASE+DRM_MSM_SUBMITQUEUE_NEW==0x4a && DRM_COMMAND_BASE+DRM_MSM_SUBMITQUEUE_CLOSE==0x4b,"queue selector parity");
int main(void){puts("PASS: Mesa25 UAPI + HakiOS surface + actual gauguin ABI sizes, offsets, pipe and request flags/selectors");return 0;}
