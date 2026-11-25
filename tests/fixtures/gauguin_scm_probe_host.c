/* Execute actual production control flow; replace the SMC boundary only. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#define GAUGUIN 1
#define KERN_SUCCESS 0
typedef int kern_return_t;
typedef int wait_result_t;
typedef void *thread_t;
typedef void (*thread_continue_t)(void *, wait_result_t);
struct scmp_registers;
static void fake_smc(struct scmp_registers *);

struct scripted_call { uint64_t input[7], output[7]; };
static struct {
    int enabled, thread_error, bad_context, context_after_delay;
    unsigned starts, deallocations, terminations, sleeps, sleep_ms, retries;
    unsigned markers, flushes, calls, scripted;
    struct scripted_call script[80];
    thread_continue_t worker;
    char marker[224], log[32768]; size_t log_bytes;
} mock;
static int test_printf(const char *format, ...)
{
    char line[256]; va_list args; va_start(args, format);
    int n = vsnprintf(line, sizeof(line), format, args); va_end(args);
    assert(n >= 0 && (size_t)n < sizeof(line));
    assert(mock.log_bytes + (size_t)n + 1 <= sizeof(mock.log));
    memcpy(mock.log + mock.log_bytes, line, (size_t)n + 1); mock.log_bytes += (size_t)n;
    return n;
}
bool PE_parse_boot_argn(const char *key, void *value, size_t bytes)
{ assert(!strcmp(key,"sweetscmprobe") && bytes==sizeof(int)); *(int *)value=mock.enabled; return true; }
kern_return_t kernel_thread_start(thread_continue_t fn, void *arg, thread_t *thread)
{
    assert(!arg); ++mock.starts; if(mock.thread_error) return mock.thread_error;
    mock.worker=fn; *thread=(thread_t)(uintptr_t)1; return 0;
}
void thread_deallocate(thread_t t) { assert(t==(thread_t)(uintptr_t)1); ++mock.deallocations; }
void thread_terminate_self(void) { ++mock.terminations; }
int ml_get_interrupts_enabled(void) { return mock.bad_context!=1; }
int ml_at_interrupt_context(void) { return mock.bad_context==2; }
int get_preemption_level(void) { return mock.bad_context==3; }
void IOSleep(unsigned ms)
{
    if(ms==1000) {
        assert(mock.sleeps<45 && !mock.calls); ++mock.sleeps; mock.sleep_ms+=ms;
        if(mock.sleeps==45) mock.bad_context=mock.context_after_delay;
    } else { assert(ms==30 && mock.sleeps==45); ++mock.retries; }
}
void sweet_log_mark_sync(const char *line)
{
    assert(!mock.bad_context && strlen(line)<sizeof(mock.marker));
    assert(strstr(mock.log,line)); strcpy(mock.marker,line); ++mock.markers;
}
void sweet_log_flush_now(void) { assert(mock.flushes+1==mock.markers); ++mock.flushes; }
#define printf test_printf
@SOURCE@
#undef printf

static void fake_smc(struct scmp_registers *r)
{
    assert(mock.sleeps==45 && mock.sleep_ms==45000 && !mock.bad_context);
    assert(mock.markers==mock.flushes && strstr(mock.marker,"before INFO"));
    assert(mock.calls<mock.scripted);
    const struct scripted_call *s=&mock.script[mock.calls++];
    for(unsigned i=0;i<7;++i) assert(r->x[i]==s->input[i]);
    /* Only approved INFO entry IDs or the exact scripted continuation token.
     * There is no simulated PAS function or firmware success here. */
    assert(r->x[0]==0xc2000601 || r->x[0]==0x82000601 || r->x[0]==0x42000601 ||
           r->x[0]==0x02000601 || r->x[0]==1);
    memcpy(r->x,s->output,sizeof(r->x));
}
static void reset(void) { memset(&mock,0,sizeof(mock)); scmp_started=0; mock.enabled=1; }
static struct scripted_call *append(uint32_t fn,uint32_t arg,int32_t status,uint64_t value)
{
    assert(mock.scripted<80); struct scripted_call *s=&mock.script[mock.scripted++];
    s->input[0]=fn; s->input[1]=1; s->input[2]=arg;
    s->output[0]=(uint64_t)(int64_t)status; s->output[1]=value;
    s->output[2]=UINT64_C(0x123456789abcdef0); s->output[3]=UINT64_C(0xfedcba9876543210);
    return s;
}
static void remaining(bool wide,unsigned from)
{
    const uint32_t ids[4]={0x02000201,0x02000202,0x02000205,0x02000206};
    for(unsigned i=from;i<4;++i) append(wide?0x42000601:0x02000601,ids[i],0,1);
}
static void execute(void)
{
    sweet_scm_probe_init(); sweet_scm_probe_init();
    assert(mock.starts==1 && mock.deallocations==1 && !mock.calls && !mock.markers);
    assert(mock.worker); mock.worker(NULL,0);
    assert(mock.calls==mock.scripted && mock.terminations==1 && mock.markers==mock.flushes);
    sweet_scm_probe_init(); assert(mock.starts==1);
}
static void continuation(unsigned count,bool wide,bool finish)
{
    const uint32_t fn=wide?0xc2000601:0x82000601;
    for(unsigned n=0;n<count;++n) {
        struct scripted_call *s=append(fn,0x82000601,1,UINT64_C(0x1111222233330000)+n);
        if(n) {
            memcpy(s->input,mock.script[mock.scripted-2].output,sizeof(s->input));
            if(!wide) for(unsigned i=0;i<7;++i) s->input[i]=(uint32_t)s->input[i];
        }
        for(unsigned i=2;i<7;++i) s->output[i]=UINT64_C(0x9876543200000000)+(n*10)+i;
        if(!wide) s->output[0]=UINT64_C(0xabcd000000000001);
        if(finish && n+1==count) {s->output[0]=0;s->output[1]=1;}
    }
}
int main(void)
{
    const int disabled[]={0,-1,2,99};
    for(unsigned i=0;i<4;++i) {
        reset();mock.enabled=disabled[i];sweet_scm_probe_init();
        assert(!mock.starts&&!mock.calls&&!mock.markers&&!mock.log_bytes);
    }
    reset();append(0xc2000601,0x82000601,0,1);remaining(true,0);execute();
    assert(mock.calls==5 && !mock.retries && strstr(mock.log,"availability_mask=f"));
    assert(strstr(mock.log,"x2=123456789abcdef0 x3=fedcba9876543210"));
    for(unsigned failed64=0;failed64<2;++failed64) {
        reset();append(0xc2000601,0x82000601,failed64?-1:0,0);
        struct scripted_call *s=append(0x82000601,0x82000601,0,1);
        s->output[0]=UINT64_C(0xabcdef0000000000); s->output[1]=UINT64_C(0x1234567800000001);
        remaining(false,0);execute();assert(strstr(mock.log,"complete width=32"));
    }
    reset();append(0xc2000601,0x82000601,-1,0);append(0x82000601,0x82000601,0,0);execute();
    assert(mock.calls==2 && strstr(mock.log,"no validated ARMv8 ABI"));
    reset();continuation(3,true,true);remaining(true,0);execute();assert(mock.calls==7);
    reset();append(0xc2000601,0x82000601,-1,0);continuation(3,false,true);remaining(false,0);execute();
    assert(mock.calls==8 && strstr(mock.log,"complete width=32"));
    reset();continuation(8,true,false);execute();
    assert(mock.calls==8 && !mock.retries && strstr(mock.log,"stopped control=3"));
    /* ABI detection itself has no fresh busy retry, just native32 fallback. */
    reset();append(0xc2000601,0x82000601,-12,0);append(0x82000601,0x82000601,0,1);
    remaining(false,0);execute();assert(!mock.retries);
    reset();append(0xc2000601,0x82000601,0,1);
    struct scripted_call *busy=append(0x42000601,0x02000201,-12,0xface);
    for(unsigned i=2;i<7;++i) busy->output[i]=0xabcdef00+i;
    remaining(true,0);execute();assert(mock.retries==1 && mock.calls==6);
    reset();append(0xc2000601,0x82000601,0,1);
    for(unsigned i=0;i<4;++i) append(0x42000601,0x02000201,-12,0);
    execute();assert(mock.retries==3 && mock.calls==5 && strstr(mock.log,"stopped control=4"));
    reset();append(0xc2000601,0x82000601,0,1);append(0x42000601,0x02000201,-2,0);
    execute();assert(strstr(mock.log,"INFO query error"));
    reset();append(0xc2000601,0x82000601,0,1);append(0x42000601,0x02000201,0,UINT32_C(0xfffffffc));
    execute();assert(strstr(mock.log,"INFO query error"));
    reset();append(0xc2000601,0x82000601,0,1);append(0x42000601,0x02000201,0,0);
    remaining(true,1);execute();assert(strstr(mock.log,"availability_mask=e"));
    reset();mock.thread_error=7;sweet_scm_probe_init();sweet_scm_probe_init();
    assert(mock.starts==1&&!mock.worker&&!mock.calls&&!mock.markers&&!mock.sleeps&&!mock.deallocations);
    for(int bad=1;bad<=3;++bad) {
        reset();mock.bad_context=bad;execute();assert(!mock.calls&&!mock.sleeps&&!mock.markers);
        reset();mock.context_after_delay=bad;execute();assert(!mock.calls&&mock.sleeps==45&&mock.markers==1);
    }
    reset();struct scmp_registers r={{0}};
    assert(scmp_query(0x42000201,0x02000201,true,true,&r)==SCMP_BAD_REQUEST);
    assert(scmp_query(0x42000107,1,true,true,&r)==SCMP_BAD_REQUEST);
    assert(scmp_query(0x42000601,0x02000c02,true,true,&r)==SCMP_BAD_REQUEST);
    assert(scmp_query(0xc2000601,0x02000201,true,false,&r)==SCMP_BAD_REQUEST);
    assert(scmp_query(0x82000601,0x82000601,true,false,&r)==SCMP_BAD_REQUEST);
    assert(scmp_query(0x42000601,0x02000201,true,true,NULL)==SCMP_BAD_REQUEST);
    assert(!mock.calls&&!mock.markers);
    puts("PASS: actual SCM probe flow; exact INFO-only whitelist, ABI64/32, raw registers, continuation x0..x6,32-bit truncation,busy/resume bounds,off/once/thread/context paths; NO SMC executed");
    return 0;
}
