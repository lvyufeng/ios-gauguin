/* Finite launch routing; this grants no GPU access. MIT. */
#ifndef GAUGUIN_METAL_ROUTER_POLICY_H
#define GAUGUIN_METAL_ROUTER_POLICY_H
#include "probe_boot.h"
#include "GauguinMetalDesktopPolicy.h"
#define GAUGUIN_ROUTER_NAME "gauguin-gpu-probe-router"
enum gauguin_router_route { GRR_REJECT=0,GRR_RETAINED=1,GRR_BOOTSTRAP=2 };
static inline enum gauguin_router_route gauguin_router_select(const char *args)
{
    if(gauguin_desktop_boot(args))return GRR_BOOTSTRAP;
    enum gauguin_probe_route old=gauguin_probe_boot_route(args);
    return old==GAUGUIN_PROBE_METAL||old==GAUGUIN_PROBE_GLES?GRR_RETAINED:GRR_REJECT;
}
static inline bool gauguin_router_identity(unsigned long uid,unsigned long euid,
                                           const char *program,const char *version)
{
    return uid==0&&euid==0&&program&&!strcmp(program,GAUGUIN_ROUTER_NAME)&&
           version&&!strcmp(version,"20H392");
}
static inline bool gauguin_router_metadata(const struct stat *st,uint64_t bytes)
{
    return st&&bytes&&bytes<=1048576&&S_ISREG(st->st_mode)&&
           (st->st_mode&07777)==0755&&st->st_uid==0&&st->st_gid==0&&
           st->st_nlink==1&&st->st_size>0&&(uint64_t)st->st_size==bytes;
}
#endif
