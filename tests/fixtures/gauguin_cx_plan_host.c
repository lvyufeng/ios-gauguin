/* Pure policy boundary: independently encoded binary metadata, real parser.
 * Optional private raw capture is supplied at runtime, never embedded in git. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cmd_db_snapshot.h"
#include "gauguin_cx_rail.h"
static unsigned cases;
static const uint16_t levels[]={0,16,64,128,192,256,384,0};
static void put16(uint8_t *p,uint16_t n){p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);}
static void put32(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i));}
static void rejected(const struct ndb_entry *e)
{
    struct gcr_plan out,prior;memset(&out,0xa5,sizeof(out));prior=out;
    assert(!gcr_plan_build(e,&out));assert(!memcmp(&out,&prior,sizeof(out)));++cases;
}
static void check_good(const struct ndb_entry *e)
{
    struct gcr_plan p;memset(&p,0xa5,sizeof(p));assert(gcr_plan_build(e,&p));
    assert(gcr_plan_valid(&p) && p.address==0x30000 && p.selector==6 && p.level==384 && p.count==7 && p.max_level==65535);
    for(unsigned i=0;i<16;++i)assert(p.levels[i]==(i<7 ? levels[i]:0));++cases;
    for(unsigned i=0;i<21;++i){struct gcr_plan changed=p;
        if(i==0)changed.address=0x30010;if(i==1)changed.selector=2;if(i==2)changed.level=64;
        if(i==3)changed.count=8;if(i==4)changed.max_level=384;if(i>=5)changed.levels[i-5]^=1;
        assert(!gcr_plan_valid(&changed));++cases;
    }
}
int main(int argc,char **argv)
{
    uint8_t blob[512]={0};put32(blob,1);put32(blob+4,0x0c0330db);
    put16(blob+8,3);put16(blob+10,0);put16(blob+12,24);put16(blob+14,1);put16(blob+16,0x1000);
    uint8_t *row=blob+144;memcpy(row,"cx.lvl",6);put32(row+16,0x30000);put16(row+20,32);
    for(unsigned i=0;i<8;++i)put16(blob+168+i*2,levels[i]);
    struct ndb_entry e;assert(ndb_lookup(blob,sizeof(blob),"cx.lvl",6,&e)==NDB_OK);check_good(&e);
    rejected(NULL);assert(!gcr_plan_build(&e,NULL));assert(!gcr_plan_valid(NULL));++cases;
    for(unsigned i=0;i<9;++i){struct ndb_entry changed=e;changed.name[i]^=1;rejected(&changed);}
    const unsigned lengths[]={0,1,2,14,15,16,17,18,30,31,33};
    for(unsigned i=0;i<sizeof(lengths)/sizeof(lengths[0]);++i){struct ndb_entry changed=e;changed.aux_length=(uint16_t)lengths[i];rejected(&changed);}
    const uint32_t addresses[]={0,0x30001,0x30010,0x30050,0x40000,0xffffffff};
    for(unsigned i=0;i<sizeof(addresses)/sizeof(addresses[0]);++i){struct ndb_entry changed=e;changed.address=addresses[i];rejected(&changed);}
    for(unsigned i=0;i<6;++i){struct ndb_entry changed=e;if(i<3)changed.owner_slave=(uint16_t)(i==0 ? 0:i==1 ? 4:5);else changed.bank_version=(uint16_t)(i==3 ? 0:i==4 ? 0x100:0x1001);rejected(&changed);}
    for(unsigned i=0;i<32;++i){struct ndb_entry changed=e;changed.aux[i]^=1;rejected(&changed);}
    /* Valid ARC tables with different supported ranges remain rejected. */
    struct ndb_entry changed=e;put16(changed.aux+12,320);rejected(&changed);
    changed=e;put16(changed.aux+14,416);rejected(&changed);
    changed=e;put16(changed.aux+10,0);rejected(&changed);
    changed=e;put16(changed.aux+2,64);rejected(&changed);
    changed=e;put16(changed.aux+2,0);rejected(&changed);
    if(argc==2){
        FILE *f=fopen(argv[1],"rb");assert(f);uint8_t *raw=malloc(NDB_MAX_BYTES);assert(raw);
        assert(fread(raw,1,NDB_MAX_BYTES,f)==NDB_MAX_BYTES && fgetc(f)==EOF && !ferror(f));assert(!fclose(f));
        assert(ndb_lookup(raw,NDB_MAX_BYTES,"cx.lvl",6,&e)==NDB_OK);check_good(&e);free(raw);
    }else assert(argc==1);
    printf("PASS: %u actual CX legal-domain policy cases; no live floor, voltage or hardware proof\n",cases);return 0;
}
