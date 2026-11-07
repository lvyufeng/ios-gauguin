#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include "gauguin_gpu_zap.h"
static struct gpz_context context;
static struct gpz_ops ops;
static struct gpz_plan plan;
static struct gpz_receipt output;
static unsigned cases;
static struct {
    uint64_t now,expected_pa;unsigned now_calls,deadline_calls,guards,owners,copies,barriers,delays,events,quarantines,terminals;
    unsigned fail_guard,fail_now,fail_deadline,fail_owner,fail_copy,bad_copy,fail_barrier,fail_delay,expire_event,rewind_event;
    unsigned tick,owner_state,phase_calls[3],continuations[3],busy[3],bad_return[3],before[3],raw[3];
    unsigned reenter,mutate,trace,interrupted,auth_success,segmented[3];
    struct gpz_registers last;
    enum gpz_phase last_phase;
    char last_event;
} h;
static unsigned id(void)
{assert(context.phase==GPZ_INIT||context.phase==GPZ_MEM||context.phase==GPZ_AUTH);return context.phase==GPZ_INIT?0:context.phase==GPZ_MEM?1:2;}
static uint64_t now(void *p)
{assert(p==&h&&!h.quarantines);++h.now_calls;if(h.now_calls==h.fail_now)return UINT64_MAX;uint64_t n=h.now;h.now+=h.tick;return n;}
static bool deadline(void *p,unsigned seconds,uint64_t *out)
{
    assert(p==&h&&!h.quarantines);assert(seconds==20||seconds==5||seconds==2||seconds==1);
    ++h.deadline_calls;if(h.deadline_calls==h.fail_deadline)return false;
    *out=h.now+(uint64_t)seconds*1000;return true;
}
static bool guard(void *p,enum gpz_phase phase,enum gpz_scope scope,unsigned minimum)
{
    assert(p==&h&&!h.quarantines&&context.state==1&&context.phase==(unsigned)phase);
    assert(minimum==3||minimum==10);assert(h.now<context.total_end&&h.now<context.phase_end);
    if(h.interrupted)assert(scope==GPZ_SECURE);
    if(h.auth_success)assert(scope==GPZ_LATE);
    if(scope==GPZ_LIVE)assert(!h.interrupted&&!h.auth_success);
    ++h.guards;h.last_event='G';return h.guards!=h.fail_guard;
}
static bool owner(void *p,enum gpz_owner_action action,uint64_t pa)
{
    assert(p==&h&&!h.quarantines&&pa==h.expected_pa);++h.owners;
    if(h.owners==h.fail_owner)return false;
    switch(action){
    case GPZO_SEAL:assert(context.phase==GPZ_SEAL&&!h.owner_state);h.owner_state=1;break;
    case GPZO_INIT_ENTER:assert(context.phase==GPZ_INIT&&h.owner_state==1&&!context.work.transaction[0].smc_calls);h.owner_state=2;break;
    case GPZO_INIT_ACCEPT:assert(context.phase==GPZ_INIT&&h.owner_state==2&&context.work.transaction[0].has_returned);h.owner_state=3;break;
    case GPZO_MEM_ACCEPT:assert(context.phase==GPZ_MEM&&h.owner_state==3&&context.work.transaction[1].has_returned);h.owner_state=4;break;
    case GPZO_AUTH_ACCEPT:assert(context.phase==GPZ_AUTH&&h.owner_state==5&&h.auth_success);h.owner_state=6;break;
    }
    if(action==GPZO_SEAL&&h.mutate){plan.owner_pa=1;ops.guard=NULL;}
    return true;
}
static bool copy(void *p,struct gpz_copy *out)
{
    assert(p==&h&&!h.quarantines&&context.phase==GPZ_COPY&&h.owner_state==4&&!h.auth_success);
    assert(!h.copies++);out->written=h.fail_copy?100:1984;out->checked=h.bad_copy?1983:h.fail_copy?0:1984;
    if(h.fail_copy)return false;h.owner_state=5;return true;
}
static bool barrier(void *p)
{assert(p==&h&&!h.quarantines);++h.barriers;h.last_event='B';return h.barriers!=h.fail_barrier;}
static void invoke(void *p,struct gpz_registers *r)
{
    assert(p==&h&&!h.quarantines&&h.last_event=='B');unsigned i=id(),n=h.phase_calls[i]++;
    assert(h.owner_state==(i==0?2:i==1?3:5));
    if(h.interrupted){assert(h.last_phase==context.phase&&!memcmp(r,&h.last,sizeof(*r)));}
    else {
        static const uint64_t fn[]={UINT64_C(0x42000201),UINT64_C(0x42000202),UINT64_C(0x42000205)};
        struct gpz_registers expected={{fn[i],i==0?0x82u:i==1?3u:1u,13,i==2?0:h.expected_pa,i==1?4096u:0u,0,0}};
        assert(!memcmp(r,&expected,sizeof(*r)));
        if(h.trace){for(unsigned j=0;j<7;j++)printf("%s%016" PRIx64,j?" ":"",r->x[j]);puts("");}
    }
    if(h.reenter){struct gpz_receipt other,saved;memset(&other,0xa5,sizeof(other));saved=other;assert(gpz_start_once(&context,&ops,&plan,&other)==GPZ_ALREADY&&!memcmp(&other,&saved,sizeof(other)));}
    for(unsigned j=0;j<7;j++)r->x[j]=UINT64_C(0x123456789abcdef0)+n*16+j;
    if(h.segmented[i]){r->x[0]=(n&1)?UINT64_C(0xfffffffffffffff4):1;h.interrupted=!(n&1);}
    else if(n<h.continuations[i]){r->x[0]=1;h.interrupted=1;}
    else if(n-h.continuations[i]<h.busy[i]){r->x[0]=UINT64_C(0x12345678fffffff4);h.interrupted=0;}
    else {r->x[0]=0;r->x[1]=0;h.interrupted=0;
        if(h.bad_return[i]==1)r->x[0]=UINT64_C(0x100000000);
        if(h.bad_return[i]==2)r->x[1]=UINT64_C(0x100000000);
        if(h.bad_return[i]==3)r->x[0]=UINT64_C(0x100000001);
        if(i==2&&!r->x[0]&&!r->x[1])h.auth_success=1;
    }
    h.last=*r;h.last_phase=(enum gpz_phase)context.phase;h.last_event='I';
}
static bool delay_ms(void *p,unsigned ms)
{
    assert(p==&h&&!h.quarantines&&ms==30&&!h.interrupted&&(int32_t)h.last.x[0]==-12);
    ++h.delays;h.now+=ms;h.last_event='D';return h.delays!=h.fail_delay;
}
static void record(void *p,enum gpz_event e,const struct gpz_receipt *r)
{
    assert(p==&h&&r==&context.work);++h.events;
    if(e==GPZE_TERMINAL){++h.terminals;assert(context.state==(r->result?3u:2u));assert(r->result?h.quarantines==1:!h.quarantines&&h.owner_state==6);return;}
    unsigned i=id();
    if(e==GPZE_BEFORE){assert(!h.quarantines&&!h.interrupted);++h.before[i];}
    else {
        assert(e==GPZE_RAW&&r->transaction[i].has_returned);++h.raw[i];
        uint64_t x0=r->transaction[i].returned.x[0],x1=r->transaction[i].returned.x[1];
        bool failure=(x0&&((int32_t)x0!=-12))||(!x0&&x1)||((int32_t)x0==-12&&r->transaction[i].fresh_attempts==68);
        if(failure)assert(h.quarantines==1&&context.state==3);
        if(h.interrupted)assert(h.quarantines==1);
    }
    if(h.expire_event==(unsigned)e+1)h.now=context.phase_end;
    if(h.rewind_event==(unsigned)e+1)h.now=0;
    h.last_event='R';
}
static void quarantine(void *p)
{assert(p==&h&&context.state==3&&!h.quarantines++);}
static void reset(void)
{
    ++cases;memset(&context,0,sizeof(context));memset(&h,0,sizeof(h));memset(&output,0xa5,sizeof(output));
    h.now=100;h.expected_pa=UINT64_C(0xaa200000);plan=(struct gpz_plan){h.expected_pa};
    ops=(struct gpz_ops){&h,now,deadline,guard,owner,copy,barrier,invoke,delay_ms,record,quarantine};
}
static enum gpz_result start(void)
{return gpz_start_once(&context,&ops,&plan,&output);}
static void failed(enum gpz_result wanted)
{
    struct gpz_receipt saved=output;enum gpz_result r=start();assert(r==wanted&&!memcmp(&saved,&output,sizeof(output)));
    assert(context.state==3&&context.work.result==(unsigned)r&&h.quarantines==1&&h.terminals==1&&!context.work.complete);
    struct gpz_ops valid={&h,now,deadline,guard,owner,copy,barrier,invoke,delay_ms,record,quarantine};
    unsigned events=h.events;assert(gpz_start_once(&context,&valid,&plan,&output)==GPZ_ALREADY&&h.events==events&&!memcmp(&saved,&output,sizeof(output)));
}
static void success(void)
{
    assert(start()==GPZ_OK&&context.state==2&&context.phase==GPZ_DONE&&h.owner_state==6&&!h.quarantines&&h.terminals==1);
    assert(output.complete==1&&output.requests_retained==1&&output.owner_sealed==1&&output.owner_pa==h.expected_pa&&output.copy.written==1984&&output.copy.checked==1984);
    for(unsigned i=0;i<3;i++){const struct gpz_transaction *t=&output.transaction[i];assert(t->has_returned&&t->smc_calls==h.phase_calls[i]&&t->fresh_attempts==h.busy[i]+1&&t->continuations==h.continuations[i]&&!t->returned.x[0]&&!t->returned.x[1]);}
}
int main(int argc,char **argv)
{
    if(argc==2&&!strcmp(argv[1],"--trace")){reset();h.trace=1;success();return 0;}assert(argc==1);
    reset();success();unsigned guards=h.guards,clocks=h.now_calls,deadlines=h.deadline_calls,barriers=h.barriers;
    for(unsigned n=1;n<=guards;n++){reset();h.fail_guard=n;failed(GPZ_GUARD);}
    for(unsigned n=1;n<=clocks;n++){reset();h.fail_now=n;failed(GPZ_DEADLINE);}
    for(unsigned n=1;n<=deadlines;n++){reset();h.fail_deadline=n;failed(GPZ_DEADLINE);}
    for(unsigned n=1;n<=5;n++){reset();h.fail_owner=n;failed(GPZ_OWNER);}
    for(unsigned n=1;n<=barriers;n++){reset();h.fail_barrier=n;failed(GPZ_IO);}
    reset();h.fail_copy=1;failed(GPZ_IO);assert(!h.phase_calls[2]);
    reset();h.bad_copy=1;failed(GPZ_IO);assert(!h.phase_calls[2]);
    for(unsigned i=0;i<3;i++){
        for(unsigned n=1;n<=3;n++){reset();h.bad_return[i]=n;failed(n==2?GPZ_SERVICE:GPZ_TRANSPORT);for(unsigned j=i+1;j<3;j++)assert(!h.phase_calls[j]);}
        reset();h.continuations[i]=9;failed(GPZ_CONTINUATION_LIMIT);assert(context.work.transaction[i].continuations==8&&h.phase_calls[i]==9&&!h.delays);
        reset();h.busy[i]=68;failed(GPZ_BUSY_LIMIT);assert(h.phase_calls[i]==68&&h.delays==67);
        reset();h.busy[i]=1;h.fail_delay=1;failed(GPZ_IO);
        reset();h.segmented[i]=1;failed(GPZ_CONTINUATION_LIMIT);assert(h.phase_calls[i]==17&&h.delays==8&&context.work.transaction[i].fresh_attempts==9&&context.work.transaction[i].continuations==8);
    }
    for(unsigned n=0;n<7;n++){
        reset();for(unsigned i=0;i<3;i++){
            if(n==0)h.continuations[i]=2;
            if(n==1)h.busy[i]=1;
            if(n==2)h.busy[i]=67;
            if(n==3)h.continuations[i]=8;
            if(n==4){h.continuations[i]=2;h.busy[i]=1;}
            if(n==6){h.continuations[i]=8;h.busy[i]=67;}
        }
        if(n==5)h.tick=3;success();
    }
    for(unsigned e=1;e<=2;e++){
        reset();h.expire_event=e;failed(GPZ_DEADLINE);
        reset();h.rewind_event=e;failed(GPZ_DEADLINE);
    }
    reset();h.reenter=1;success();
    reset();h.mutate=1;success();
    reset();plan.owner_pa=h.expected_pa=UINT64_C(0xfff00000);success();
    reset();plan.owner_pa=h.expected_pa=UINT64_C(0x100000);success();
    for(unsigned n=0;n<14;n++){
        reset();switch(n){
        case 0:ops.now=NULL;break;case 1:ops.deadline=NULL;break;case 2:ops.guard=NULL;break;
        case 3:ops.owner=NULL;break;case 4:ops.copy=NULL;break;case 5:ops.barrier=NULL;break;
        case 6:ops.invoke=NULL;break;case 7:ops.delay_ms=NULL;break;case 8:ops.record=NULL;break;
        case 9:ops.quarantine=NULL;break;case 10:plan.owner_pa++;break;
        case 11:plan.owner_pa=0;break;case 12:plan.owner_pa=UINT64_C(0x100000000);break;
        case 13:plan.owner_pa=UINT64_MAX;break;
        }struct gpz_receipt saved=output;assert(start()==GPZ_ARGUMENT&&!context.state&&!h.events&&!h.quarantines&&!memcmp(&output,&saved,sizeof(output)));
    }
    reset();assert(gpz_start_once(NULL,&ops,&plan,&output)==GPZ_ARGUMENT);
    assert(gpz_start_once(&context,NULL,&plan,&output)==GPZ_ARGUMENT);
    assert(gpz_start_once(&context,&ops,NULL,&output)==GPZ_ARGUMENT);
    assert(gpz_start_once(&context,&ops,&plan,NULL)==GPZ_ARGUMENT);
    assert(gpz_start_once(&context,&ops,&plan,&context.work)==GPZ_ARGUMENT);
    assert(gpz_start_once((struct gpz_context *)(UINTPTR_MAX-1),&ops,&plan,&output)==GPZ_ARGUMENT);
    puts("PASS fixed ZAP INIT/MEM/copy/AUTH state machine; host-only, no signed authentication/hardware proof");
    printf("%u cases; every %u live/secure guard, %u clock, %u deadline and %u barrier boundary injected\n",cases,guards,clocks,deadlines,barriers);
}
