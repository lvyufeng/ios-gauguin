/* Actual loader/helpers; logical input-PA resolution, EL1 entry/stop are host seams. */
#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "console.h"
#include "pas_reservation.h"
static unsigned checks;
static void check(int ok){checks++;assert(ok);}
static jmp_buf boundary;
static unsigned stopped,jumped;
static uint64_t args_pa;
const uint8_t *test_image_start,*test_image_end;
static uint8_t *input;
uint64_t con_fb_base=0xa0000000;
uint32_t con_stride=4320,con_w=1080,con_h=2400;
void con_str(const char *a,const char *b){(void)a;(void)b;}
void con_hex(const char *a,uint64_t b){(void)a;(void)b;}
void con_hex2(const char *a,const char *b,uint32_t c,const char *d,uint32_t e){(void)a;(void)b;(void)c;(void)d;(void)e;}
void test_stop(void) __attribute__((noreturn));
void test_stop(void){stopped++;longjmp(boundary,1);}
void test_jump(uint64_t p) __attribute__((noreturn));
void test_jump(uint64_t p){jumped++;args_pa=p;longjmp(boundary,1);}
const void *test_payload_from_pa(uint64_t pa){check(pa==0x90000000);return input;}
const char *loader_boot(uintptr_t);
void loader_announce(uintptr_t,const char *,uint32_t);
static uint32_t u32(const void *p){uint32_t v;memcpy(&v,p,4);return v;}
static uint64_t u64(const void *p){uint64_t v;memcpy(&v,p,8);return v;}
static void put64(void *p,uint64_t v){memcpy(p,&v,8);}
static void beput64(void *p,uint64_t v){v=__builtin_bswap64(v);memcpy(p,&v,8);}
static size_t find(const uint8_t *p,size_t bytes,const char *tag){
    for(size_t i=0;i+strlen(tag)<=bytes;i++)if(!memcmp(p+i,tag,strlen(tag)))return i;
    assert(!"fixture marker missing");return 0;
}
int main(int argc,char **argv){
    check(argc==3);
    FILE *f=fopen(argv[1],"rb");check(f!=NULL);uint64_t lengths[2];
    check(fread(lengths,1,16,f)==16);size_t pn=lengths[0],fn=lengths[1];
    check(pn<=0x1000000&&fn<=0x100000);
    size_t allocation=(pn+0x3fff)&~(size_t)0x3fff;
    input=mmap(NULL,allocation,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
    check(input!=MAP_FAILED);uint8_t *dt=malloc(fn);check(dt!=NULL);
    check(fread(input,1,pn,f)==pn&&fread(dt,1,fn,f)==fn&&fclose(f)==0);
    const size_t span=0x2000000;
    uint8_t *map=mmap(NULL,2*span,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
    check(map!=MAP_FAILED);
    uint8_t *managed=(uint8_t*)(((uintptr_t)map+span-1)&~(uintptr_t)(span-1));
    uint8_t image[256];test_image_start=image;test_image_end=image+sizeof image;
    put64(input+56,(uintptr_t)managed);put64(input+64,span);
    size_t ao=u64(input+32),az=u64(input+40);
    size_t base=find(input+ao,az,"dram-base");
    put64(input+ao+base+36,(uintptr_t)managed);
    const uint8_t high_bank[]={0,0,0,1,0x80,0,0,0,0,0,0,1,0,0,0,0};
    unsigned replaced=0;
    for(size_t i=0;i+16<=fn;i++)if(!memcmp(dt+i,high_bank,16)){
        beput64(dt+i,(uintptr_t)managed);beput64(dt+i+8,span);replaced++;
    }
    check(replaced==1);
    size_t ro=find(input+ao,az,"LPASREQ1")+ao;
    size_t tail=u64(input+ro+16);check(tail+PAS_TAIL_BYTES==pn);
    uint8_t *prior=malloc(tail);check(prior!=NULL);memcpy(prior,input,tail);
    check(!mprotect(input+tail,allocation-tail,PROT_NONE));
    memset(managed,0xa5,span);
    if(!setjmp(boundary)){loader_boot((uintptr_t)dt);check(0);}
    int reject=!strcmp(argv[2],"reject");
    if(reject){
        check(stopped==1&&!jumped);
        for(size_t i=0;i<span;i++)check(managed[i]==0xa5);
        loader_announce((uintptr_t)dt,"must-not-change=",1);
        check(!memcmp(prior,input,tail));
        printf("PASS rejected before destination writes; source/announce unchanged checks=%u\n",checks);
        return 0;
    }
    check(jumped==1&&!stopped);
    uint64_t vb=u64(input+16),ap=u64(input+48)-vb;
    uint8_t *copy=managed+ap;
    size_t vo=find(prior+ao,az,"GHFDREQ1");
    uint8_t *value=copy+vo;
    if(memcmp(value,"GHFDOWN1",8)){
        fputs("FAIL actual old loader leaves runtime FDT request unpublished\n",stderr);return 42;
    }
    check(!memcmp(value-36,"GauguinHandoffFDT",17));
    check(u32(value+8)==1&&u32(value+12)==1&&u32(value+16)==fn);
    uint32_t cap=u32(value+20);check(fn<=cap);
    check(!memcmp(value+160,dt,fn));
    for(size_t i=fn;i<cap;i++)check(value[160+i]==0);
    check(u64(value+24)==(uintptr_t)dt&&u64(value+32)==0x90000000&&u64(value+40)==pn);
    check(u64(value+48)==(uintptr_t)image&&u64(value+56)==sizeof image);
    check(u64(value+64)==(uintptr_t)managed&&u64(value+72)==span);
    check(u64(value+80)==(uintptr_t)copy&&u64(value+88)==az);
    uintptr_t bp=((uintptr_t)copy+az+0x3fff)&~(uintptr_t)0x3fff;
    check(u64(value+96)==bp&&u64(value+104)==bp+0x4000&&args_pa==bp);
    uint64_t pas=(0x90000000+tail+0xfffff)&~UINT64_C(0xfffff);
    check(u64(value+112)==pas&&u64(value+120)==0x100000);
    check(u64(value+128)==con_fb_base&&u64(value+136)==(uint64_t)con_stride*con_h);
    check(u64(value+144)==(uintptr_t)copy&&u64(value+152)==0);
    check(!memcmp(copy+ro-ao,"LPASOWN1",8)&&!memcmp(prior,input,tail));
    check(!memcmp((const uint8_t*)bp+108,input+0x48,608));
    /* Direct real commit rejection: original pending copy, real physical
     * destination in the modeled managed range; no request-tail access. */
    struct pas_context context={input,dt,pn,fn,0x90000000,(uintptr_t)dt,
        (uintptr_t)image,sizeof image};
    struct pas_handoff_plan plan;
    check(pas_handoff_prepare(&context,con_fb_base,(uint64_t)con_stride*con_h,&plan)==PAS_READY);
    uint8_t *saved=malloc(az);check(saved!=NULL);
    for(size_t byte=0;byte<sizeof(plan);byte++){
        memcpy(copy,input+ao,az);memcpy(saved,copy,az);
        struct pas_handoff_plan bad=plan;((uint8_t*)&bad)[byte]^=1;
        check(pas_handoff_commit(&context,copy,az,con_fb_base,(uint64_t)con_stride*con_h,&bad)<0);
        check(!memcmp(copy,saved,az));
    }
    const size_t corrupt[]={0,8,12,16,20,24,152,160,160+cap-1};
    for(size_t i=0;i<sizeof corrupt/sizeof corrupt[0];i++){
        memcpy(copy,input+ao,az);copy[vo+corrupt[i]]^=1;memcpy(saved,copy,az);
        check(pas_handoff_commit(&context,copy,az,con_fb_base,(uint64_t)con_stride*con_h,&plan)<0);
        check(!memcmp(copy,saved,az));
    }
    memcpy(copy,input+ao,az);
    check(pas_handoff_commit(&context,copy,az,con_fb_base,(uint64_t)con_stride*con_h,&plan)==PAS_READY);
    memcpy(saved,copy,az);
    check(pas_handoff_commit(&context,copy,az,con_fb_base,(uint64_t)con_stride*con_h,&plan)<0);
    check(!memcmp(saved,copy,az));
    check(!memcmp(prior,input,tail));
    printf("PASS full original FDT,17 owner fields,zero unused capacity,plan/destination errors,repeat refusal; PAS tail PROT_NONE checks=%u\n",checks);
    free(saved);free(prior);free(dt);
    check(!munmap(input,allocation));check(!munmap(map,2*span));return 0;
}
