#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "gauguin_gpu_aperture.h"
static unsigned checks;
#define CHECK(x) do {assert(x);++checks;} while(0)
struct fake {struct gpa_context ctx;unsigned step,fail,calls,before,sleeps,mode,bank;bool nested;struct gpa_registers last;};
static bool tick(struct fake *f){return ++f->step!=f->fail;}
static bool guard(void *p,bool initial){struct fake *f=p;CHECK(initial==(f->calls==0));return tick(f);}
static bool before(void *p,unsigned fresh,const struct gpa_registers *r)
{
    struct fake *f=p;if(!tick(f))return false;++f->before;CHECK(fresh==f->before);
    const uint64_t want[]={0x42000c1b,4,0xffff0000u|f->bank,0xffffffff,0xffffffff,0xffffffff,0};
    CHECK(!memcmp(r->x,want,sizeof(want)));return true;
}
static bool delay_ms(void *p,unsigned ms){struct fake *f=p;CHECK(ms==30);if(!tick(f))return false;++f->sleeps;return true;}
static struct gpa_ops ops(struct fake *);
static void invoke(void *p,struct gpa_registers *r)
{
    struct fake *f=p;++f->calls;
    if(f->nested){f->nested=false;struct gpa_ops o=ops(f);struct gpa_receipt out,b;memset(&out,0x63,sizeof(out));b=out;
        CHECK(gpa_program_once(&f->ctx,&o,f->bank,&out)==GPA_ALREADY&&!memcmp(&out,&b,sizeof(out)));}
    bool continued=f->mode==1||f->mode==2||f->mode==7;
    if(continued&&f->calls>1)CHECK(!memcmp(r,&f->last,sizeof(*r)));
    uint64_t ret=0;
    if(f->mode==1)ret=f->calls==1?1:0;
    if(f->mode==2)ret=1;
    if(f->mode==3)ret=f->calls==1?UINT64_C(0xfffffffffffffff4):0;
    if(f->mode==4)ret=UINT64_C(0xfffffffffffffff4);
    if(f->mode==5)ret=UINT64_C(0xfffffffffffffffe);
    if(f->mode==6)ret=2;
    if(f->mode==7)ret=f->calls==1?1:UINT64_C(0x100000001);
    *r=(struct gpa_registers){{ret,0x111,0x222,0x333,0x444,0x555,f->calls}};f->last=*r;
}
static struct gpa_ops ops(struct fake *f){return (struct gpa_ops){f,guard,before,invoke,delay_ms};}
static enum gpa_result run(struct fake *f,struct gpa_receipt *out){struct gpa_ops o=ops(f);return gpa_program_once(&f->ctx,&o,f->bank,out);}
static void stopped(struct fake *f)
{
    unsigned step=f->step;struct gpa_receipt out,b;memset(&out,0x94,sizeof(out));b=out;
    CHECK(run(f,&out)==GPA_ALREADY&&f->step==step&&!memcmp(&out,&b,sizeof(out)));
}
int main(void)
{
    for(unsigned bank=0;bank<8;bank++)for(unsigned mode=0;mode<8;mode++){
        struct fake f={.bank=bank,.mode=mode,.nested=true};struct gpa_receipt out;
        enum gpa_result rc=run(&f,&out);CHECK(rc==(mode==2?GPA_CONTINUATION:mode==4?GPA_BUSY:mode>=5?GPA_TRANSPORT:GPA_OK));
        CHECK(out.bank==bank&&out.calls==f.calls&&out.has_returned==1&&!memcmp(&out.returned,&f.last,sizeof(f.last)));
        CHECK(f.ctx.state==(rc==GPA_OK?2u:3u));CHECK(out.fresh==f.before);
        CHECK(f.calls==(mode==2?9u:mode==4?68u:(mode==1||mode==3||mode==7)?2u:1u));
        CHECK(out.continuations==(mode==2?8u:(mode==1||mode==7)?1u:0u));
        CHECK(f.sleeps==(mode==3?1u:mode==4?67u:0u));unsigned steps=f.step;stopped(&f);
        for(unsigned fail=1;fail<=steps;fail++){
            struct fake g={.bank=bank,.mode=mode,.fail=fail};struct gpa_receipt r;
            CHECK(run(&g,&r)!=GPA_OK&&g.step==fail&&g.ctx.state==3);stopped(&g);
        }
    }
    struct fake f={0};struct gpa_ops o=ops(&f);struct gpa_receipt r,b;memset(&r,0x97,sizeof(r));b=r;
    CHECK(gpa_program_once(&f.ctx,&o,8,&r)==GPA_ARGUMENT&&!f.step&&!f.ctx.state&&!memcmp(&r,&b,sizeof(r)));
    CHECK(gpa_program_once(NULL,&o,0,&r)==GPA_ARGUMENT);CHECK(gpa_program_once(&f.ctx,NULL,0,&r)==GPA_ARGUMENT);
    CHECK(gpa_program_once(&f.ctx,&o,0,NULL)==GPA_ARGUMENT);o.invoke=NULL;CHECK(gpa_program_once(&f.ctx,&o,0,&r)==GPA_ARGUMENT);
    printf("GPU aperture: %u assertions PASS; exact four scalar registers/eight banks, preserved64-bit continuation chain, bounded BUSY, native x1 ignored and all callback failures; no secure-world qualification\n",checks);
}
