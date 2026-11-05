#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "pas_reservation.h"
static uint32_t u32(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t u64(const uint8_t *p) {return u32(p)|(uint64_t)u32(p+4)<<32;}
int main(int argc,char **argv)
{
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);
    uint8_t header[56];assert(fread(header,1,sizeof header,f)==sizeof header);
    int32_t expected=(int32_t)u32(header);unsigned protect=u32(header+4);
    size_t pn=(size_t)u64(header+8),fn=(size_t)u64(header+16),page=(size_t)sysconf(_SC_PAGESIZE);
    assert(pn && pn<=0x20000000 && fn && fn<=0x100000);
    size_t size=(pn+page-1)&~(page-1);
    uint8_t *payload=mmap(NULL,size,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
    assert(payload!=MAP_FAILED);uint8_t *fdt=malloc(fn);assert(fdt);
    assert(fread(payload,1,pn,f)==pn && fread(fdt,1,fn,f)==fn);assert(fgetc(f)==EOF);assert(fclose(f)==0);
    size_t prefix=protect?pn-PAS_TAIL_BYTES:pn;
    uint8_t *prior=malloc(prefix);assert(prior);memcpy(prior,payload,prefix);
    /* No virtual tail read/write is possible, even though its advertised
     * logical physical address remains inside the verified initrd extent. */
    if(protect) {assert(!(prefix%page));assert(mprotect(payload+prefix,size-prefix,PROT_NONE)==0);}
    struct pas_context c={payload,fdt,pn,fn,u64(header+24),u64(header+32),u64(header+40),u64(header+48)};
    struct pas_plan p,old;memset(&p,0xa5,sizeof p);memcpy(&old,&p,sizeof p);
    int got=pas_prepare(&c,&p);
    assert(expected<0?got<0:got==expected);
    assert(!memcmp(prior,payload,prefix));
    if(got!=PAS_READY)assert(!memcmp(&p,&old,sizeof p));
    else {
        uint8_t *copy=malloc(p.adt_bytes);assert(copy);memcpy(copy,payload+p.adt_offset,p.adt_bytes);
        assert(pas_commit(copy,p.adt_bytes,&p)==PAS_READY);
        assert(!memcmp(copy+p.request_value,"LPASOWN1",8));
        assert(u64(copy+p.io_value)==p.pa && u64(copy+p.io_value+8)==PAS_REGION_BYTES);
        assert(u32(copy+p.io_value+16)==PAS_WIMG);
        uint8_t *after=malloc(p.adt_bytes);assert(after);memcpy(after,copy,p.adt_bytes);
        assert(pas_commit(copy,p.adt_bytes,&p)<0 && !memcmp(after,copy,p.adt_bytes));
        free(after);free(copy);
    }
    /* Bounded malformed FDT parsing: outputs stay untouched on every error. */
    uint64_t start=0x55,end=0x66;int fs=pas_initrd(fdt,fn,&start,&end);
    if(fs)assert(start==0x55 && end==0x66);
    /* Truncations and one-byte mutations operate on metadata only. */
    for(size_t n=0;n<fn;n+=(n<80?1:37)) {
        start=0x55;end=0x66;assert(pas_initrd(fdt,n,&start,&end)<0);assert(start==0x55 && end==0x66);
    }
    free(prior);free(fdt);assert(munmap(payload,size)==0);return 0;
}
