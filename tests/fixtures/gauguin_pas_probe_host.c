/* Actual kernel consumer + actual shim ownership publication; mocked pmap/DT. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include "pas_reservation.h"
#define GAUGUIN 1
#define PAGE_SHIFT 14
#define KERN_SUCCESS 0
#define kSuccess 0
#define kBootArgsVersion2 2
typedef int boolean_t;
typedef uint32_t ppnum_t;
typedef int kern_return_t;
typedef int wait_result_t;
typedef void *thread_t;
typedef void (*thread_continue_t)(void *, wait_result_t);
typedef unsigned DTEntry;
typedef struct { unsigned Version; uint64_t physBase, memSize; } boot_args;
static boot_args args;
static struct { boot_args *bootArgs; } PE_state = { &args };
unsigned long gPhysBase, real_phys_size;
static uint8_t owner[128], tuple[24];
static uint64_t selected;
static struct {
    int enabled, thread_error, bad_context, after_delay, missing, pending;
    unsigned starts, deallocations, terminations, sleeps, properties;
    unsigned valid_calls, attr_calls, managed_page, wrong_attr_page, markers, flushes;
    thread_continue_t worker;
    char log[8192]; size_t used;
} mock;
static int test_printf(const char *format, ...)
{
    va_list ap; va_start(ap, format);
    int n = vsnprintf(mock.log + mock.used, sizeof(mock.log) - mock.used, format, ap);
    va_end(ap); assert(n >= 0 && (size_t)n < sizeof(mock.log) - mock.used);
    mock.used += (size_t)n; return n;
}
bool PE_parse_boot_argn(const char *name, void *out, size_t bytes)
{ assert(!strcmp(name,"sweetpasprobe") && bytes==sizeof(int)); *(int *)out=mock.enabled; return true; }
kern_return_t kernel_thread_start(thread_continue_t fn, void *arg, thread_t *thread)
{
    assert(!arg); ++mock.starts; if(mock.thread_error)return mock.thread_error;
    mock.worker=fn; *thread=(thread_t)(uintptr_t)1; return 0;
}
void thread_deallocate(thread_t t) { assert(t==(thread_t)(uintptr_t)1); ++mock.deallocations; }
void thread_terminate_self(void) { ++mock.terminations; }
int ml_get_interrupts_enabled(void) { return mock.bad_context!=1; }
int ml_at_interrupt_context(void) { return mock.bad_context==2; }
int get_preemption_level(void) { return mock.bad_context==3; }
void IOSleep(unsigned ms)
{ assert(ms==1000 && !mock.properties); if(++mock.sleeps==45)mock.bad_context=mock.after_delay; }
int SecureDTLookupEntry(void *parent, const char *name, DTEntry *entry)
{
    assert(!parent && !mock.bad_context && mock.sleeps==45);
    unsigned which=!strcmp(name,"/chosen")?1:2; assert(which==1 || !strcmp(name,"/defaults"));
    if(mock.missing==(int)which+2)return -1; *entry=which; return 0;
}
int SecureDTGetProperty(DTEntry node, const char *name, const void **out, unsigned *bytes)
{
    ++mock.properties; assert(!mock.bad_context);
    if(node==1 && !strcmp(name,"LowPASReservation")) {
        if(mock.missing==1)return -1; *out=owner; *bytes=sizeof(owner); return 0;
    }
    if(node==2 && !strcmp(name,"pmap-io-ranges")) {
        if(mock.missing==2)return -1; *out=tuple; *bytes=sizeof(tuple); return 0;
    }
    assert((node==1 && !strcmp(name,"LowPASRequest")) || (node==2 && !strcmp(name,"LowPASIOPending")));
    if(mock.pending==(int)node) { *out=owner; *bytes=24; return 0; } return -1;
}
boolean_t pmap_valid_page(ppnum_t pn)
{
    assert(!mock.bad_context && mock.sleeps==45 && mock.valid_calls==mock.attr_calls);
    assert(((uint64_t)pn<<14)==selected+mock.valid_calls*0x4000);
    return ++mock.valid_calls==mock.managed_page;
}
unsigned pmap_cache_attributes(ppnum_t pn)
{
    assert(((uint64_t)pn<<14)==selected+mock.attr_calls*0x4000);
    assert(mock.valid_calls==mock.attr_calls+1);
    return ++mock.attr_calls==mock.wrong_attr_page?7:0xd0000006;
}
void sweet_log_mark_sync(const char *line)
{ assert(!mock.bad_context && strstr(mock.log,line)); ++mock.markers; }
void sweet_log_flush_now(void) { assert(mock.flushes+1==mock.markers); ++mock.flushes; }
#define printf test_printf
@SOURCE@
#undef printf
static void reset(void)
{ memset(&mock,0,sizeof(mock)); psr_started=0; args=(boot_args){2,gPhysBase,real_phys_size}; }
static void execute(void)
{ sweet_pas_probe_init(); assert(mock.worker); mock.worker(NULL,0); assert(mock.terminations==1); }
static void u64put(uint8_t *p,uint64_t v) { for(unsigned i=0;i<8;i++)p[i]=(uint8_t)(v>>(8*i)); }
int main(int argc,char **argv)
{
    assert(argc==2); FILE *f=fopen(argv[1],"rb"); assert(f); uint8_t h[56]; assert(fread(h,1,56,f)==56);
    size_t pn=psr_u64(h+8),fn=psr_u64(h+16); uint8_t *p=malloc(pn),*dt=malloc(fn); assert(p&&dt);
    assert(fread(p,1,pn,f)==pn && fread(dt,1,fn,f)==fn && fclose(f)==0);
    struct pas_context c={p,dt,pn,fn,psr_u64(h+24),psr_u64(h+32),psr_u64(h+40),psr_u64(h+48)};
    struct pas_plan plan; assert(pas_prepare(&c,&plan)==PAS_READY);
    uint8_t *adt=malloc(plan.adt_bytes); assert(adt); memcpy(adt,p+plan.adt_offset,plan.adt_bytes);
    assert(pas_commit(adt,plan.adt_bytes,&plan)==PAS_READY);
    memcpy(owner,adt+plan.request_value,128); memcpy(tuple,adt+plan.io_value,24);
    gPhysBase=(unsigned long)plan.managed_pa; real_phys_size=(unsigned long)plan.managed_bytes; selected=plan.pa;
    uint8_t valid_owner[128],valid_tuple[24]; memcpy(valid_owner,owner,128); memcpy(valid_tuple,tuple,24);
    reset(); sweet_pas_probe_init(); assert(!mock.starts && !mock.properties);
    reset(); mock.enabled=2; sweet_pas_probe_init(); assert(!mock.starts);
    reset(); mock.enabled=1; execute(); assert(mock.attr_calls==64 && mock.valid_calls==64);
    assert(strstr(mock.log,"complete unmanaged_pages=64") && mock.markers==mock.flushes);
    sweet_pas_probe_init(); assert(mock.starts==1);
    reset(); mock.enabled=1; mock.thread_error=3; sweet_pas_probe_init(); assert(!mock.worker && !mock.properties);
    for(int i=1;i<=3;i++) for(int late=0;late<2;late++) {
        reset();mock.enabled=1;if(late)mock.after_delay=i;else mock.bad_context=i;
        execute();assert(!mock.properties && !mock.attr_calls);
    }
    for(int i=1;i<=4;i++) { reset();mock.enabled=1;mock.missing=i;execute();assert(!mock.attr_calls); }
    for(int i=1;i<=2;i++) { reset();mock.enabled=1;mock.pending=i;execute();assert(!mock.attr_calls); }
    const unsigned offsets[]={0,8,12,16,24,32,40,48,56,64,72,80,88};
    for(unsigned n=0;n<sizeof(offsets)/sizeof(offsets[0]);n++) {
        memcpy(owner,valid_owner,128);owner[offsets[n]]^=1;reset();mock.enabled=1;execute();assert(!mock.attr_calls);
    }
    memcpy(owner,valid_owner,128);
    for(unsigned n=0;n<24;n++) { memcpy(tuple,valid_tuple,24);tuple[n]^=1;reset();mock.enabled=1;execute();assert(!mock.attr_calls); }
    memcpy(tuple,valid_tuple,24);
    for(unsigned n=0;n<6;n++) {
        memcpy(owner,valid_owner,128);
        if(n==0)u64put(owner+80,UINT64_MAX-0x1000);
        if(n==1)u64put(owner+96,selected);
        if(n==2)u64put(owner+112,selected);
        if(n==3){u64put(owner+64,0xfff00000);u64put(tuple,0xfff00000);}
        if(n==4)u64put(owner+104,0);
        if(n==5)u64put(owner+120,0);
        reset();mock.enabled=1;execute();assert(!mock.attr_calls);
    }
    memcpy(owner,valid_owner,128);memcpy(tuple,valid_tuple,24);
    for(unsigned n=1;n<=64;n++) for(int mode=0;mode<2;mode++) {
        reset();mock.enabled=1;if(mode)mock.managed_page=n;else mock.wrong_attr_page=n;
        execute();assert(mock.attr_calls==n && !strstr(mock.log,"complete unmanaged_pages"));
    }
    reset();mock.enabled=1;args.memSize=real_phys_size+0x4000;execute();assert(!mock.attr_calls);
    struct psr_owner out,prior;memset(&out,0xa5,sizeof(out));memcpy(&prior,&out,sizeof(out));
    assert(!psr_validate(owner,127,tuple,24,(struct psr_range){gPhysBase,real_phys_size},&out));
    assert(!memcmp(&out,&prior,sizeof(out)));
    free(adt);free(p);free(dt);puts("PAS consumer: real shim publication, 64-page pmap inspection and fail-closed paths pass");return 0;
}
