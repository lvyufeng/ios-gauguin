#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "console.h"
static jmp_buf boundary;
static int stopped,jumped;
const uint8_t *test_image_start,*test_image_end;
uint64_t last_args;
uint64_t con_fb_base=0xa0000000;
uint32_t con_stride=4320,con_w=1080,con_h=2400;
void con_str(const char *a,const char *b){(void)a;(void)b;}
void con_hex(const char *a,uint64_t b){(void)a;(void)b;}
void con_hex2(const char *a,const char *b,uint32_t c,const char *d,uint32_t e){(void)a;(void)b;(void)c;(void)d;(void)e;}
void test_stop(void) __attribute__((noreturn));
void test_stop(void){stopped++;longjmp(boundary,1);}
void test_jump(uint64_t args) __attribute__((noreturn));
void test_jump(uint64_t args){jumped++;last_args=args;longjmp(boundary,1);}
const char *loader_boot(uintptr_t);
void loader_announce(uintptr_t,const char *,uint32_t);
static uint32_t le32(const uint8_t *p){uint32_t x;memcpy(&x,p,4);return x;}
static uint64_t le64(const uint8_t *p){uint64_t x;memcpy(&x,p,8);return x;}
static void put64(uint8_t *p,uint64_t x){memcpy(p,&x,8);}
static uint32_t be32(const uint8_t *p){return __builtin_bswap32(le32(p));}
static void be64put(uint8_t *p,uint64_t x){x=__builtin_bswap64(x);memcpy(p,&x,8);}
static void patch_initrd(uint8_t *d,uintptr_t start,size_t bytes,int bank) {
    size_t at=be32(d+8),end=at+be32(d+36),strings=be32(d+12);unsigned found=0;
    while(at<end) {
        uint32_t t=be32(d+at);at+=4;
        if(t==1){while(d[at])at++;at=(at+4)&~(size_t)3;}
        else if(t==3){uint32_t n=be32(d+at),s=be32(d+at+4);at+=8;
            if(bank && !strcmp((char*)d+strings+s,"reg")){assert(n==32);be64put(d+at,start & ~(uint64_t)0x3fff);be64put(d+at+8,((start&0x3fff)+bytes+0x3fff)&~(uint64_t)0x3fff);}
            if(!strcmp((char*)d+strings+s,"linux,initrd-start")){assert(n==8);be64put(d+at,start);found++;}
            if(!strcmp((char*)d+strings+s,"linux,initrd-end")){assert(n==8);be64put(d+at,start+bytes);found++;}
            at+=(n+3)&~(size_t)3;
        } else if(t==9)break;else assert(t==2 || t==4);
    }
    assert(found==2);
}
static void boot(uint8_t *fdt,int should_stop) {
    stopped=jumped=0;last_args=0;
    if(!setjmp(boundary)) {loader_boot((uintptr_t)fdt);assert(!"loader returned to fallback");}
    assert(should_stop?stopped==1 && !jumped:jumped==1 && !stopped);
}
int main(int argc,char **argv) {
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);uint8_t h[56];assert(fread(h,1,56,f)==56);
    size_t pn=le64(h+8),fn=le64(h+16);uint8_t *p=malloc(pn),*dt=malloc(fn),*original=malloc(pn);assert(p&&dt&&original);
    assert(fread(p,1,pn,f)==pn && fread(dt,1,fn,f)==fn && fclose(f)==0);
    const size_t span=0x2000000;
    uint8_t *map=mmap(NULL,2*span,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);assert(map!=MAP_FAILED);
    uint8_t *managed=(uint8_t*)(((uintptr_t)map+span-1)&~(uintptr_t)(span-1));
    uint8_t fake_image[256];test_image_start=fake_image;test_image_end=fake_image+sizeof(fake_image);
    put64(p+56,(uintptr_t)managed);put64(p+64,span);
    size_t ao=le64(p+32),az=le64(p+40);unsigned found=0;
    for(size_t i=ao;i+44<ao+az;i++)if(!memcmp(p+i,"dram-base\0",10)){put64(p+i+36,(uintptr_t)managed);found++;}
    assert(found==1);patch_initrd(dt,(uintptr_t)p,pn,1);memcpy(original,p,pn);
    memset(managed,0xa5,span);boot(dt,0);
    uint64_t vb=le64(p+16);uint32_t count=le32(p+12);
    for(uint32_t n=0;n<count;n++) {
        const uint8_t *seg=p+0x2a8+32*n;
        uint64_t dest=le64(seg)-vb,vm=le64(seg+8),source=le64(seg+16),bytes=le64(seg+24);
        assert(dest+vm<=span && source+bytes<=pn);
        assert(!memcmp(managed+dest,p+source,bytes));
        for(uint64_t i=bytes;i<vm;i++)assert(managed[dest+i]==0);
    }
    uint64_t ap=le64(p+48)-vb;assert(!memcmp(managed+ap,p+ao,az));
    uintptr_t bp=((uintptr_t)managed+ap+az+0x3fff)&~(uintptr_t)0x3fff;
    assert(last_args==bp);const uint8_t *ba=(const uint8_t*)bp;
    assert(le32(ba)==0x00020002 && le64(ba+8)==vb && le64(ba+16)==(uintptr_t)managed);
    assert(le64(ba+24)==span && le64(ba+32)==bp+0x4000);
    assert(le64(ba+40)==con_fb_base && le64(ba+56)==con_stride);
    assert(le64(ba+64)==con_w && le64(ba+72)==con_h);
    assert(le64(ba+96)==vb+ap && le32(ba+104)==az);
    assert(!memcmp(ba+108,p+0x48,608) && le64(ba+728)==span);
    uint8_t *announced=malloc(pn);assert(announced);
    loader_announce((uintptr_t)dt,"qa=",0x1234);memcpy(announced,p,pn);
    assert(strstr((char*)p+0x48,"qa=00001234"));
    for(size_t i=0;i<pn;i++)if(i<0x48 || i>=0x2a8)assert(p[i]==original[i]);
    free(announced);
    /* Actual new loader body must not return or start any destination writes. */
    for(unsigned mode=0;mode<5;mode++) {
        memcpy(p,original,pn);
        if(mode==0)memcpy(p,"070701xx",8); /* old no-XNU diagnostic input */
        if(mode==1){uint32_t bad=0xffffffff;memcpy(p+12,&bad,4);}
        if(mode==2)put64(p+32,pn+8);
        if(mode==3)put64(p+0x2a8+16,pn+8);
        if(mode==4){uint32_t bad=2;memcpy(p+8,&bad,4);}
        uint8_t *bad=malloc(pn);assert(bad);memcpy(bad,p,pn);
        loader_announce((uintptr_t)dt,"must-not-write=",1);assert(!memcmp(bad,p,pn));free(bad);
        memset(managed,0xa5,span);boot(dt,1);
        for(size_t i=0;i<span;i++)assert(managed[i]==0xa5);
    }
    memcpy(p,original,pn);
    const uintptr_t invalid[]={0,0x50000000,UINTPTR_MAX-3,(uintptr_t)dt,(uintptr_t)fake_image};
    for(size_t n=0;n<sizeof(invalid)/sizeof(invalid[0]);n++) {
        patch_initrd(dt,invalid[n],pn,0); /* retain genuine synthetic RAM bank */
        loader_announce((uintptr_t)dt,"must-not-access=",1);assert(!memcmp(original,p,pn));
        memset(managed,0xa5,span);boot(dt,1);
        for(size_t i=0;i<span;i++)assert(managed[i]==0xa5);
    }
    free(original);free(p);free(dt);assert(!munmap(map,2*span));
    puts("actual loader: valid default segments/zero fill/ADT/boot_args verified; 10 malformed/non-XNU/non-RAM cases stop before reads/copies/fallback; announce preserves invalid input");return 0;
}
