/* SPDX-License-Identifier: MIT
 * Read-only recovery helper. Scan the first 16 GiB of the fixed userdata device;
 * emit per-MiB SHA-256 plus the complete prefix SHA-256. No block write syscall.
 * Linux arm64 numbers/BLKGETSIZE64: Linux v4.19 asm-generic/unistd.h, linux/fs.h.
 * Native execution requires the CPU SHA2 extension, checked before deployment.
 */
#include <stdint.h>
#include <stddef.h>
#include <arm_neon.h>
#define CHUNK 1048576u
#define VOLUME UINT64_C(17179869184)
#define PARTITION UINT64_C(114919714816)
static uint8_t input[CHUNK], manifest[32+16384*32+32];
static const uint32_t constants[64]={
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
struct sha { uint32_t h[8]; uint64_t bytes; size_t used; uint8_t block[64]; };
static void copy_bytes(void *to,const void *from,size_t n)
{uint8_t*d=to;const uint8_t*s=from;while(n--)*d++=*s++;}
static void compress(struct sha *s,const uint8_t *p)
{
    uint32x4_t a=vld1q_u32(s->h),b=vld1q_u32(s->h+4),old_a=a,old_b=b,w[4];
    for(unsigned i=0;i<4;i++)w[i]=vreinterpretq_u32_u8(vrev32q_u8(vld1q_u8(p+16*i)));
    for(unsigned i=0;i<16;i++){
        unsigned j=i&3;uint32x4_t k=vaddq_u32(w[j],vld1q_u32(constants+4*i)),save=a;
        a=vsha256hq_u32(a,b,k);b=vsha256h2q_u32(b,save,k);
        if(i<12)w[j]=vsha256su1q_u32(vsha256su0q_u32(w[j],w[(j+1)&3]),w[(j+2)&3],w[(j+3)&3]);
    }
    vst1q_u32(s->h,vaddq_u32(a,old_a));vst1q_u32(s->h+4,vaddq_u32(b,old_b));
}
static void sha_init(struct sha *s)
{
    static const uint32_t initial[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    copy_bytes(s->h,initial,sizeof(initial));s->used=0;s->bytes=0;
}
static void sha_update(struct sha *s,const uint8_t *p,size_t n)
{
    s->bytes+=n;
    if(s->used){size_t take=64-s->used;if(take>n)take=n;copy_bytes(s->block+s->used,p,take);s->used+=take;p+=take;n-=take;
        if(s->used==64){compress(s,s->block);s->used=0;}}
    while(n>=64){compress(s,p);p+=64;n-=64;}
    if(n){copy_bytes(s->block,p,n);s->used=n;}
}
static void sha_final(struct sha *s,uint8_t *out)
{
    uint64_t bits=s->bytes*8;uint8_t padding[128],length[8];
    for(unsigned i=0;i<128;i++)padding[i]=0;padding[0]=128;
    for(unsigned i=0;i<8;i++)length[7-i]=(uint8_t)(bits>>(8*i));
    size_t n=s->used<56?56-s->used:120-s->used;
    sha_update(s,padding,n);sha_update(s,length,8);
    for(unsigned i=0;i<8;i++)for(unsigned j=0;j<4;j++)out[i*4+j]=(uint8_t)(s->h[i]>>(24-8*j));
}
static void le64(uint8_t *p,uint64_t n){for(unsigned i=0;i<8;i++)p[i]=(uint8_t)(n>>(8*i));}

#ifdef ROOT_SCAN_NATIVE
static long call4(long number,long a,long b,long c,long d)
{
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x8 __asm__("x8")=number;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x8):"memory","cc");return x0;
}
static long read_at(long fd,void *p,size_t n,uint64_t at){return call4(67,fd,(long)p,(long)n,(long)at);}
static int send_bytes(const void *p,size_t n)
{
    const uint8_t *s=p;
    while(n){long k=call4(64,1,(long)s,(long)n,0);if(k==-4)continue;if(k<=0||(uint64_t)k>n)return 1;s+=k;n-=(size_t)k;}
    return 0;
}
static int equal(const char *a,const char *b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
#else
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
static long read_at(long fd,void *p,size_t n,uint64_t at){return (long)pread((int)fd,p,n,(off_t)at);}
static int send_bytes(const void *p,size_t n){return fwrite(p,1,n,stdout)==n?0:1;}
#endif

static int scan(long fd,uint64_t volume,uint64_t partition)
{
    if(!volume||volume>VOLUME||volume%CHUNK||partition<volume)return 2;
    struct sha full,part;sha_init(&full);size_t count=(size_t)(volume/CHUNK);
    for(size_t i=0;i<count;i++){
        size_t at=0;
        while(at<CHUNK){long n=read_at(fd,input+at,CHUNK-at,(uint64_t)i*CHUNK+at);
#ifdef ROOT_SCAN_NATIVE
            if(n==-4)continue;
#endif
            if(n<=0||(uint64_t)n>CHUNK-at)return 3;at+=(size_t)n;}
        sha_update(&full,input,CHUNK);sha_init(&part);sha_update(&part,input,CHUNK);
        sha_final(&part,manifest+32+i*32);
    }
    copy_bytes(manifest,"GGSCAN1\0",8);le64(manifest+8,volume);le64(manifest+16,CHUNK);le64(manifest+24,partition);
    sha_final(&full,manifest+32+count*32);return send_bytes(manifest,64+count*32)?4:0;
}

#ifdef ROOT_SCAN_NATIVE
__attribute__((noreturn,used)) void root_entry(uint64_t *stack)
{
    uint64_t argc=stack[0];char **argv=(char **)(stack+1);uint64_t volume=VOLUME;int result=2;
    if(argc==2&&equal(argv[1],"--selftest"))volume=8u*CHUNK;
    else if(argc!=1)goto done;
    long fd=call4(56,-100,(long)"/dev/block/by-name/userdata",0,0);
    if(fd<3)goto done;
    uint64_t bytes=0;
    if(call4(29,fd,0x80081272,(long)&bytes,0)==0&&bytes==PARTITION)result=scan(fd,volume,bytes);
    if(call4(57,fd,0,0,0)!=0)result=5;
done:
    call4(93,result,0,0,0);for(;;){}
}
__asm__(".text\n.balign 4\n.global _start\n_start:\nmov x0, sp\nbl root_entry\n1: b 1b\n");
void *memcpy(void *to,const void *from,size_t n){copy_bytes(to,from,n);return to;}
void *memset(void *to,int value,size_t n){uint8_t*p=to;while(n--)*p++=(uint8_t)value;return to;}
#else
int main(int argc,char **argv)
{
    if(argc!=4)return 2;
    int fd=open(argv[2],O_RDONLY);if(fd<0)return 2;
    if(!strcmp(argv[1],"--hash")){
        size_t piece=(size_t)strtoull(argv[3],NULL,10);if(!piece||piece>CHUNK)return 2;
        struct sha s;sha_init(&s);uint64_t offset=0;
        for(;;){long n=read_at(fd,input,piece,offset);if(n<0)return 3;if(!n)break;sha_update(&s,input,(size_t)n);offset+=(uint64_t)n;}
        uint8_t out[32];sha_final(&s,out);for(unsigned i=0;i<32;i++)printf("%02x",out[i]);puts("");close(fd);return 0;
    }
    struct stat st;if(fstat(fd,&st))return 2;
    uint64_t volume=strtoull(argv[3],NULL,10);int result=scan(fd,volume,(uint64_t)st.st_size);
    close(fd);return result;
}
#endif
