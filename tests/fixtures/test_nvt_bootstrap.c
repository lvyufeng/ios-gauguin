/* Deterministic protocol model. Its CRC responses are fixtures, NOT a CRC
 * implementation or evidence that a real chip/transfer/boot has succeeded. */
#include "nvt_bootstrap.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum fault { NONE, BAD_TRIM, DROP_ILM, DROP_DLM, DROP_HEADER, BAD_BANK,
    BAD_CRC_ILM_FLAG, BAD_CRC_DLM_FLAG, LATE_ILM_RESULT, LATE_DLM_RESULT, OBSERVED_DLM_RESULT, LATE_GOLDEN,
    NO_CRC_DONE, NO_RESET_READY, BAD_FW_COMPLEMENT, BAD_FW_GEOMETRY,
    BAD_FW_VERSION, BAD_FW_TYPE, BAD_PID, CLOCK_BACKWARD, CLOCK_TIMEOUT, SHORT_DELAY };
struct model {
    uint8_t ram[0x40000];
    uint32_t page, written, verified;
    uint64_t now, eng_at, high_at, reset_at;
    unsigned calls, resets, software_resets, fast_disables, polls;
    unsigned fail_call, fail_reset, ready_after;
    unsigned first[NBS_READY + 1], last[NBS_READY + 1];
    enum nbs_phase phase;
    enum fault fault;
    bool high, eng, identified, boot, failed, stale_crc_before;
};
static const uint8_t trim_good[6] = {0x0c,0,0,0x72,0x66,3};
static const uint8_t fw_info[16] = {0x10,0xef,0x12,0x20,0x04,0x38,0x09,0x60,0,0,0,0,0,1,0,0};
static void put32(uint8_t *p, uint32_t value)
{ for (unsigned i=0;i<4;++i) p[i]=(uint8_t)(value>>(i*8)); }
static uint32_t get32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static bool sram_range(uint32_t a,size_t n)
{ return (a<0x13608 && n<=0x13608-a)||(a>=0x27040 && a<0x2b4e0 && n<=0x2b4e0-a); }
static int mock_reset(void *cookie,bool high)
{
    struct model *m=cookie;assert(!m->failed);++m->resets;
    if(m->fail_reset==m->resets){m->failed=true;return -52;}
    if(high){assert(m->eng && !m->high && m->now-m->eng_at>=1000);m->high_at=m->now;}
    else assert(!m->eng && !m->high && m->calls==0);
    m->high=high;return 0;
}
static int mock_xfer(void *cookie,const uint8_t *tx,uint8_t *rx,size_t n)
{
    struct model *m=cookie;assert(!m->failed && n && n<=64);++m->calls;
    if(!m->first[m->phase])m->first[m->phase]=m->calls;m->last[m->phase]=m->calls;
    if(m->fail_call==m->calls){m->failed=true;return -71;}
    m->now += n*9;
    if(m->fault==CLOCK_BACKWARD && m->phase==NBS_TRIM)m->now=0;
    if(m->fault==CLOCK_TIMEOUT && m->phase==NBS_UPLOAD)m->now+=120000001;
    if(tx[0]==0xff){
        assert(n==3 && !rx);m->page=((uint32_t)tx[1]<<15)|((uint32_t)tx[2]<<7);
        if(!m->high)assert(m->page==0x7fff80 && m->phase==NBS_ENG_RESET);
        return 0;
    }
    uint32_t address=m->page|(tx[0]&127);
    if(tx[0]&128){
        assert(!rx && n>=2);
        if(address==0x7fff80){assert(!m->high && !m->eng && n==2 && tx[1]==0x5a);m->eng=true;m->eng_at=m->now;return 0;}
        assert(m->high);
        if(address==0x3f0fe){
            assert(n==2 && tx[1]==0x69 && m->software_resets<2);
            if(!m->software_resets)assert(m->now-m->high_at>=10000 && m->phase==NBS_IDENTIFY_RESET);
            else assert(m->identified && m->phase==NBS_LOAD_RESET && !m->written);
            ++m->software_resets;m->reset_at=m->now;return 0;
        }
        if(address==0x3f310){assert(n==2 && !tx[1] && m->now-m->reset_at>=5000);++m->fast_disables;return 0;}
        assert(address+n-1<=sizeof(m->ram));
        if(m->phase==NBS_UPLOAD){
            assert(m->identified && m->software_resets==2 && m->fast_disables==2 && !m->boot);
            assert(sram_range(address,n-1) && (address&127)+n-1<=128);
            bool drop=(m->fault==DROP_ILM && address==0)||(m->fault==DROP_DLM && address==0x27140)||
                (m->fault==DROP_HEADER && address==0x27040);
            if(!drop)memcpy(m->ram+address,tx+1,n-1);
            m->written+=(uint32_t)(n-1);return 0;
        }
        if(m->phase==NBS_CRC_BANKS){
            assert(m->written==96936 && m->verified==96936);
            switch(address){
            case 0x3f128:assert(n==4 && tx[1]==0 && tx[2]==0 && tx[3]==0);break;
            case 0x3f118:assert(n==4 && tx[1]==7 && tx[2]==0x36 && tx[3]==1);break;
            case 0x3f100:assert(n==5 && get32(tx+1)==0x15fe9c6d);break;
            case 0x3f12c:assert(n==4 && tx[1]==0x40 && tx[2]==0x71 && tx[3]==2);break;
            case 0x3f130:assert(n==4 && tx[1]==0x9f && tx[2]==0x43 && tx[3]==0);break;
            case 0x3f104:assert(n==5 && get32(tx+1)==0x90fe20f8);break;
            default:assert(false);
            }
        }else if(address==0x3f30e){assert(m->phase==NBS_CRC_ENABLE && n==2 && tx[1]==0xa3);}
        else if(address==0x22d60){assert(m->phase==NBS_FW_CRC_ENABLE && n==2 && tx[1]==0);}
        else if(address==0x22d50){assert(m->phase==NBS_FW_CRC_ENABLE && n==2 && tx[1]==0xae);}
        else if(address==0x3f10d){
            assert(m->phase==NBS_BOOT_READY && n==2 && tx[1]==1 && !m->boot);
            assert(m->ram[0x3f30e]==0xa3 && m->ram[0x22d50]==0xae && !m->ram[0x22d60]);
            assert(m->verified==96936);m->boot=true;
            /* Test fixture supplies hardware responses; no CRC polynomial is claimed. */
            put32(m->ram+0x3f120,m->fault==LATE_ILM_RESULT?0:0x15fe9c6d);
            put32(m->ram+0x3f124,m->fault==LATE_DLM_RESULT?0:
                m->fault==OBSERVED_DLM_RESULT?0xb0183db6:0x90fe20f8);
            if(m->fault==LATE_GOLDEN){put32(m->ram+0x3f100,0x12345678);put32(m->ram+0x3f104,0x87654321);}
        }else assert(false);
        memcpy(m->ram+address,tx+1,n-1);return 0;
    }
    assert(m->high && rx && n>=3);
    for(size_t i=1;i<n;++i)assert(!tx[i]); /* all read clocks initialized */
    memset(rx,0,n);rx[0]=0x91;rx[1]=0x52; /* not a command echo */
    if(address==0x1f64e){
        assert(m->phase==NBS_TRIM && m->software_resets==1 && m->fast_disables==1 && n==8);
        memcpy(rx+2,trim_good,6);if(m->fault==BAD_TRIM)rx[2]^=1;else m->identified=true;return 0;
    }
    assert(address+n-2<=sizeof(m->ram));
    if(m->phase==NBS_SRAM_READBACK){
        assert(!m->boot && sram_range(address,n-2) && (address&127)+n-2<=128);
        m->verified+=(uint32_t)(n-2);
    }
    memcpy(rx+2,m->ram+address,n-2);
    if(address==0x3f133){
        assert(n==3);
        if(!m->boot){rx[2]=m->stale_crc_before?4:0;assert(m->phase==NBS_CRC_BASELINE);}
        else{
            ++m->polls;rx[2]=(m->polls>m->ready_after)?4:0;
            if(m->fault==NO_CRC_DONE)rx[2]=0;
            if(m->fault==BAD_CRC_ILM_FLAG)rx[2]=5;
            if(m->fault==BAD_CRC_DLM_FLAG)rx[2]=6;
        }
    }else if(address==0x22d60){
        assert(n==7 && m->boot);rx[2]=(m->polls>m->ready_after)?0xa3:0;
        if(m->fault==NO_RESET_READY)rx[2]=0xff;
    }else if(address==0x22d78){
        assert(n==18 && m->boot);memcpy(rx+2,fw_info,16);
        if(m->fault==BAD_FW_COMPLEMENT)rx[3]^=1;
        if(m->fault==BAD_FW_GEOMETRY)rx[6]=0xff;
        if(m->fault==BAD_FW_VERSION){rx[2]=0x11;rx[3]=0xee;}
        if(m->fault==BAD_FW_TYPE)rx[15]=2;
    }else if(address==0x22d9a){assert(n==4 && m->boot);rx[2]=0x37;rx[3]=0x59;if(m->fault==BAD_PID)rx[2]^=1;}
    if(m->fault==BAD_BANK && m->phase==NBS_CRC_BANKS && address==0x3f118)rx[2]^=1;
    return 0;
}
static uint64_t mock_now(void *cookie){return ((struct model *)cookie)->now;}
static void mock_delay(void *cookie,unsigned ms)
{
    struct model *m=cookie;assert(ms==1||ms==5||ms==10);
    m->now+=(uint64_t)ms*(m->fault==SHORT_DELAY?999:1000);
}
static void mock_progress(void *cookie,enum nbs_phase p,uint32_t done,uint32_t total)
{
    struct model *m=cookie;assert(!m->failed && p>=m->phase);m->phase=p;assert(done<=total);
}
static void init(struct model *m,struct nbs_session *s)
{
    memset(m,0,sizeof(*m));memset(s,0,sizeof(*s));m->now=1000;
    m->ready_after=2;m->ram[0x3f30e]=0x23;
}
static int run(struct model *m,struct nbs_session *s,const uint8_t *firmware,size_t bytes)
{
    struct nbs_io io={m,mock_xfer,mock_reset,mock_delay,mock_now,mock_progress};
    return nbs_bootstrap(s,&io,firmware,bytes);
}
static void failed(struct model *m,struct nbs_session *s,const uint8_t *firmware,int expected)
{
    assert(run(m,s,firmware,NBS_FIRMWARE_BYTES)==expected);
    assert(!s->report.ready && s->report.quarantine && s->report.hardware_touched && s->report.result==expected);
    unsigned calls=m->calls,resets=m->resets;
    struct nbs_report before=s->report;
    assert(run(m,s,firmware,NBS_FIRMWARE_BYTES)==NBS_ALREADY_USED && m->calls==calls && m->resets==resets);
    assert(!memcmp(&s->report,&before,sizeof(before)));
}
int main(int argc,char **argv)
{
    assert(argc==2);FILE *file=fopen(argv[1],"rb");assert(file);
    uint8_t *firmware=malloc(NBS_FIRMWARE_BYTES),*bad=malloc(NBS_FIRMWARE_BYTES);assert(firmware&&bad);
    assert(fread(firmware,1,NBS_FIRMWARE_BYTES,file)==NBS_FIRMWARE_BYTES && fgetc(file)==EOF);fclose(file);
    struct model *m=malloc(sizeof(*m));assert(m);struct nbs_session session;
    init(m,&session);assert(run(m,&session,firmware,NBS_FIRMWARE_BYTES)==NBS_OK);
    assert(session.report.ready&&!session.report.quarantine&&session.report.trim_verified);
    assert(session.report.valid==0xfff);
    assert(session.report.bytes_written==96936&&session.report.bytes_verified==96936);
    assert(session.report.event_base==NVT_EVENT_BASE&&session.report.hw_crc==2);
    assert(session.report.ilm_crc==0x15fe9c6d&&session.report.dlm_crc==0x90fe20f8);
    assert(session.report.ilm_golden==0x15fe9c6d&&session.report.dlm_golden==0x90fe20f8);
    assert(session.report.crc_status==4&&session.report.reset_state.state==0xa3&&session.report.pid==0x5937);
    assert(session.report.fwinfo.version==16&&session.report.fwinfo.max_x==1080&&session.report.fwinfo.max_y==2400);
    assert(m->page==NVT_EVENT_BASE && m->high && m->polls==3 && m->resets==2 && m->software_resets==2);
    unsigned first[NBS_READY+1],last[NBS_READY+1];memcpy(first,m->first,sizeof(first));memcpy(last,m->last,sizeof(last));
    printf("model positive: %u exact raw transactions, written=%u, verified=%u; event page restored\n",m->calls,m->written,m->verified);
    unsigned positive_calls=m->calls;
    for(unsigned p=0;p<=NBS_READY;++p){
        unsigned points[2]={first[p],last[p]};
        for(unsigned j=0;j<2;++j)if(points[j]){
            init(m,&session);m->fail_call=points[j];failed(m,&session,firmware,NBS_TRANSPORT);
            assert(m->calls==points[j]&&session.report.callback_error==-71);
            if(p==NBS_TRIM)assert(!(session.report.valid&NBS_VALID_TRIM));
            if(p==NBS_CRC_BASELINE)assert(!(session.report.valid&NBS_VALID_CRC_BEFORE));
            if(p==NBS_READ_FWINFO)assert(!(session.report.valid&NBS_VALID_FWINFO));
            if(p==NBS_READ_PID)assert(!(session.report.valid&NBS_VALID_PID));
        }
    }
    for(unsigned r=1;r<=2;++r){init(m,&session);m->fail_reset=r;failed(m,&session,firmware,NBS_RESET_IO);assert(session.report.callback_error==-52);}
    const struct {enum fault fault;int result;} cases[]={
        {BAD_TRIM,NBS_IDENTITY},{DROP_ILM,NBS_READBACK},{DROP_DLM,NBS_READBACK},{DROP_HEADER,NBS_READBACK},
        {BAD_BANK,NBS_READBACK},{BAD_CRC_ILM_FLAG,NBS_CRC},{BAD_CRC_DLM_FLAG,NBS_CRC},
        {NO_CRC_DONE,NBS_TIMEOUT},{NO_RESET_READY,NBS_TIMEOUT},
        {BAD_FW_COMPLEMENT,NBS_FWINFO},{BAD_FW_GEOMETRY,NBS_FWINFO},{BAD_FW_VERSION,NBS_FWINFO},
        {BAD_FW_TYPE,NBS_FWINFO},{BAD_PID,NBS_IDENTITY},{CLOCK_BACKWARD,NBS_CLOCK},
        {CLOCK_TIMEOUT,NBS_TIMEOUT},{SHORT_DELAY,NBS_CLOCK}
    };
    for(size_t i=0;i<sizeof(cases)/sizeof(cases[0]);++i){
        init(m,&session);m->fault=cases[i].fault;failed(m,&session,firmware,cases[i].result);
        if(cases[i].fault==BAD_TRIM)assert(!m->written&&!session.report.trim_verified&&(session.report.valid&NBS_VALID_TRIM));
        if(cases[i].fault==DROP_ILM||cases[i].fault==DROP_DLM||cases[i].fault==DROP_HEADER)assert(!m->boot);
        if(cases[i].fault==NO_CRC_DONE||cases[i].fault==NO_RESET_READY)assert(m->polls==11);
        if(cases[i].fault==BAD_CRC_ILM_FLAG||cases[i].fault==BAD_CRC_DLM_FLAG)
            assert((session.report.valid&NBS_VALID_CRC_STATUS)&&!(session.report.valid&NBS_VALID_RESET_STATE));
        if(cases[i].fault==BAD_FW_COMPLEMENT||cases[i].fault==BAD_FW_GEOMETRY)assert(!(session.report.valid&NBS_VALID_FWINFO));
        if(cases[i].fault==BAD_FW_VERSION||cases[i].fault==BAD_FW_TYPE)assert(session.report.valid&NBS_VALID_FWINFO);
        if(cases[i].fault==BAD_PID)assert((session.report.valid&NBS_VALID_PID)&&session.report.pid==0x5936);
    }
    /* Post-start registers have no native stability contract. The hardware
     * observation is one case, not a whitelist: other changed results/goldens
     * are recorded while every pre-start integrity/readiness gate still runs. */
    const enum fault observations[]={LATE_ILM_RESULT,LATE_DLM_RESULT,OBSERVED_DLM_RESULT,LATE_GOLDEN};
    for(size_t i=0;i<sizeof(observations)/sizeof(observations[0]);i++){
        init(m,&session);m->fault=observations[i];
        assert(run(m,&session,firmware,NBS_FIRMWARE_BYTES)==NBS_OK);
        assert(session.report.ready&&session.report.valid==0xfff&&session.report.bytes_verified==96936);
        assert(session.report.crc_status==4&&session.report.pid==0x5937&&session.report.fwinfo.version==16);
        if(m->fault==LATE_ILM_RESULT)assert(session.report.ilm_crc==0);
        if(m->fault==LATE_DLM_RESULT)assert(session.report.dlm_crc==0);
        if(m->fault==OBSERVED_DLM_RESULT)assert(session.report.dlm_crc==0xb0183db6);
        if(m->fault==LATE_GOLDEN)assert(session.report.ilm_golden==0x12345678&&session.report.dlm_golden==0x87654321);
    }
    /* No invented clear-on-reset property: stale baseline4 is recorded, but
     * full real-model SRAM readback and CRC status/reset gates remain required. */
    init(m,&session);m->stale_crc_before=true;assert(!run(m,&session,firmware,NBS_FIRMWARE_BYTES));
    assert(session.report.crc_before==4&&session.report.bytes_verified==96936);
    init(m,&session);m->stale_crc_before=true;m->fault=DROP_ILM;failed(m,&session,firmware,NBS_READBACK);assert(!m->boot);
    /* Metadata/size errors perform zero GPIO/SPI and do not request quarantine. */
    init(m,&session);assert(run(m,&session,firmware,NBS_FIRMWARE_BYTES-1)==NBS_FIRMWARE);
    assert(!m->calls&&!m->resets&&!session.report.hardware_touched&&!session.report.quarantine);
    assert(session.report.valid==0);
    memcpy(bad,firmware,NBS_FIRMWARE_BYTES);put32(bad+0x18,0);
    init(m,&session);assert(run(m,&session,bad,NBS_FIRMWARE_BYTES)==NBS_FIRMWARE&& !m->calls&&!m->resets);
    init(m,&session);assert(nbs_bootstrap(&session,NULL,firmware,NBS_FIRMWARE_BYTES)==NBS_ARGUMENT&&!m->calls);
    printf("PASS: actual bootstrap + frozen parser/protocol, %u-transaction model, failures stop without retries/cleanup SPI; no device qualification\n",positive_calls);
    free(m);free(bad);free(firmware);return 0;
}
