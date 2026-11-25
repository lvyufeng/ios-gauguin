#include "geni_spi_setup.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Import the frozen transport's ACTUAL configuration predicate. No transfer
 * function is called: a M_CMD/FIFO-data/control write is a model failure.
 */
#include <geni_spi_pio.c>

enum { S_FORCE=0x20, S_OUTPUT=0x24, S_CGC=0x28, S_MCLK=0x48,
       S_MIRQ=0x610, S_MEN=0x614, S_MCLR=0x618,
       S_SIRQ=0x640, S_SEN=0x644, S_SCLR=0x648, S_GSI=0xe18, S_IRQ=0xe1c };
static const struct { uint32_t off, mask; } allowed[] = {
    {0xe1c,15},{0xe18,15},{0x614,UINT32_MAX},{0x644,UINT32_MAX},
    {0x28,0x7f},{0xe30,15},{0x24,0x7f},{0x258,1},{0x7c,7},{0x48,0xfff1},
    {0x260,0xfffff},{0x264,0xfffff},{0x284,0xfffff},{0x288,0xfffff},
    {0x254,UINT32_MAX},{0x268,0x3ff},{0x22c,3},{0x250,15},{0x224,1},
    {0x230,4},{0x24c,15},{0x278,0xfffff},{0x25c,1},{0x80c,63},{0x810,63},{0x814,63},
    {0x26c,0xffffff},{0x270,0xffffff}
};
struct model {
    uint32_t reg[0x1000/4], before[0x1000/4];
    uint32_t wrapper, dfs, cfg, force_flags;
    uint64_t generation, claimed_generation;
    unsigned reads, writes, barriers, claims, releases, forces, clears, dfs_reads;
    unsigned bad_offset, bad_count, revoke_at, revoke_barrier_at, trace_count;
    uint32_t trace[128];
    bool held, quarantine, refuse_claim, changed_dfs, ignore_clear;
};
static int claim(void *cookie,uint64_t *generation)
{
    struct model *m=cookie;m->claims++;
    if(m->refuse_claim || m->held || m->quarantine) return -1;
    m->held=true;m->claimed_generation=++m->generation;*generation=m->generation;
    return 0;
}
static bool owns(void *cookie,uint64_t gen)
{ struct model *m=cookie;return m->held && gen==m->generation; }
static uint32_t read32(void *cookie,uint64_t gen,enum gss_space space,uint32_t off)
{
    struct model *m=cookie;assert(owns(m,gen));m->reads++;
    uint32_t value=0;
    if(space==GSS_WRAPPER) { assert(off==4);value=m->wrapper; }
    else if(space==GSS_GCC) {
        assert(off==0x2115c || off==0x21164);
        if(off==0x2115c) value=m->dfs + (m->changed_dfs && ++m->dfs_reads>1 ? 2 : 0);
        else value=m->cfg;
    } else {
        assert(space==GSS_SE && off<sizeof(m->reg) && !(off&3));
        bool valid=off==0x40 || off==0x64 || off==0x68 || off==0x6c ||
                   off==0xe24 || off==0xe28 || off==0x800 || off==0x804 ||
                   off==S_MIRQ || off==S_SIRQ;
        for(unsigned i=0;i<sizeof(allowed)/sizeof(allowed[0]);i++) valid|=off==allowed[i].off;
        assert(valid); /* No FIFO data, DMA status walk, or unnamed register. */
        value=m->reg[off/4];
    }
    if(m->revoke_at && m->reads==m->revoke_at) { m->generation++;m->held=false; }
    return value;
}
static void write32(void *cookie,uint64_t gen,enum gss_space space,uint32_t off,uint32_t value)
{
    struct model *m=cookie;assert(owns(m,gen));assert(space==GSS_SE);
    assert(m->trace_count<128);m->trace[m->trace_count++]=off;m->writes++;
    if(off==S_FORCE) {
        assert(value==1 && m->reg[S_IRQ/4]==0 && m->reg[S_GSI/4]==0);
        m->forces++;m->reg[S_MIRQ/4]|=m->force_flags;
        return; /* self-clearing action, no restorable latch */
    }
    if(off==S_MCLR || off==S_SCLR) {
        assert(m->reg[S_IRQ/4]==0 && m->reg[S_GSI/4]==0);
        unsigned status=off==S_MCLR?S_MIRQ:S_SIRQ;
        assert(value==m->reg[status/4]); /* only observed status, never blanket ffffffff */
        if (!m->ignore_clear) m->reg[status/4]&=~value;
        m->clears++;
        return;
    }
    bool found=false;
    for(unsigned i=0;i<sizeof(allowed)/sizeof(allowed[0]);i++) if(off==allowed[i].off) {
        found=true;assert(((m->reg[off/4]^value)&~allowed[i].mask)==0);
    }
    assert(found); /* M_CMD, M_CTRL, FIFO-data, GPIO/GCC/PLL writes are forbidden. */
    if(m->bad_count && off==m->bad_offset) { m->bad_count--;value^=1; }
    m->reg[off/4]=value;
}
static void barrier(void *cookie,uint64_t gen)
{
    struct model *m=cookie;assert(owns(m,gen));m->barriers++;
    if (m->revoke_barrier_at && m->barriers==m->revoke_barrier_at) {
        m->generation++;m->held=false;
    }
}
static void release(void *cookie,uint64_t gen,bool quarantine)
{
    struct model *m=cookie;assert(gen==m->claimed_generation);
    m->releases++;m->held=false;m->quarantine=quarantine;
}
static struct gss_owner init(struct model *m)
{
    memset(m,0,sizeof(*m));m->generation=10;
    m->wrapper=0x20070000;m->dfs=0x21;m->cfg=1;
    m->reg[0x68/4]=m->reg[0x6c/4]=0x101;
    m->reg[0xe24/4]=0x201029e4;m->reg[0xe28/4]=0x20104800;
    m->reg[S_MCLK/4]=0x11;
    m->reg[0x260/4]=m->reg[0x284/4]=0x7f807;
    m->reg[0x264/4]=m->reg[0x288/4]=0xffefe;
    m->reg[S_IRQ/4]=15;m->reg[S_MEN/4]=0x33c0007e;m->reg[S_SEN/4]=0x03003e3e;
    m->reg[S_CGC/4]=0x300;m->reg[S_OUTPUT/4]=0x80000000;
    m->reg[0xe30/4]=0x40;m->reg[0x268/4]=0x80000000;
    m->reg[S_MIRQ/4]=8;m->reg[S_SIRQ/4]=4;m->force_flags=1u<<23;
    memcpy(m->before,m->reg,sizeof(m->reg));
    return (struct gss_owner){m,claim,owns,read32,write32,barrier,release};
}
static uint32_t pio_read(void *cookie,uint32_t off)
{ struct model *m=cookie;return read32(m,m->generation,GSS_SE,off); }
static void config_restored(const struct model *m)
{
    for(unsigned i=0;i<sizeof(allowed)/sizeof(allowed[0]);i++)
        assert(m->reg[allowed[i].off/4]==m->before[allowed[i].off/4]);
}
static void normal(void)
{
    struct model m;struct gss_owner o=init(&m);struct gss_session s={0};
    struct gs_pio pio={.io={.cookie=&m,.read32=pio_read}};
    assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
    assert(!m.forces && !m.clears && s.report.divider==20 && s.report.sck_hz==960000);
    assert(configured(&pio)==GS_NOT_CONFIGURED);
    assert(gss_commit_native_defaults(&s)==GSS_OK);
    assert(configured(&pio)==GS_OK); /* actual frozen PIO gate, not a mirrored predicate */
    assert(m.reg[S_MCLK/4]==0x141 && m.reg[0x268/4]==0x80000004);
    assert(m.reg[S_IRQ/4]==0 && m.reg[S_GSI/4]==0);
    assert(s.report.effects==7 && m.forces==1 && m.clears==2);
    assert(s.report.acknowledged_m==(8u|m.force_flags) && s.report.acknowledged_s==4);
    unsigned force_pos=0,clock_pos=0,pack_pos=0;
    for(unsigned i=0;i<m.trace_count;i++) {
        if(m.trace[i]==S_FORCE) force_pos=i;
        if(m.trace[i]==S_MCLK) clock_pos=i;
        if(m.trace[i]==0x260) pack_pos=i;
    }
    assert(force_pos<clock_pos && clock_pos<pack_pos);
    assert(gss_commit_native_defaults(&s)==GSS_ARGUMENT); /* no accidental second force */
    m.reg[0x26c/4]=m.reg[0x270/4]=67; /* Ordinary fields a later PIO call changes. */
    assert(gss_restore(&s,0)==GSS_OK && s.report.config_restored && !m.quarantine);
    config_restored(&m);
    assert(!m.reg[S_MIRQ/4] && !m.reg[S_SIRQ/4]); /* W1C history is NOT restored */
    assert(m.forces==1 && m.clears==2 && m.releases==1);
    assert(m.trace[m.trace_count-1]==S_IRQ && m.trace[m.trace_count-2]==S_GSI);
}
static void preflight(void)
{
    struct model m;struct gss_owner o;struct gss_session s;
    for(unsigned test=0;test<12;test++) {
        o=init(&m);s=(struct gss_session){0};
        if(test==0) m.refuse_claim=true;
        if(test==1) m.wrapper=0x10000000;
        if(test==2) m.reg[0x68/4]=0x201;
        if(test==3) m.reg[0x40/4]=1;
        if(test==4) m.reg[0x800/4]=1;
        if(test==5) m.reg[0x804/4]=1;
        if(test==6) m.reg[0x258/4]=1;
        if(test==7) m.dfs=0x23;
        if(test==8) m.cfg=0x601;
        if(test==9) m.changed_dfs=true;
        if(test==10) m.reg[S_IRQ/4]|=0x100;
        if(test==11) m.reg[0x260/4]|=0x80000000;
        assert(gss_prepare(&s,&o,1000000)<0 && !m.writes && !m.forces && !m.clears);
        if(!test) assert(!m.reads && !m.releases);
        else assert(m.releases==1);
    }
    o=init(&m);s=(struct gss_session){0};
    assert(gss_prepare(&s,&o,1000001)==GSS_ARGUMENT && !m.claims);
    assert(gss_prepare(&s,&o,1000)==GSS_CLOCK && !m.writes); /* divider would exceed4095 */
    o=init(&m);s=(struct gss_session){0};
    assert(gss_prepare(&s,&o,5000)==GSS_PREPARED && s.report.divider==3840);
    assert(gss_restore(&s,0)==GSS_OK && !m.forces && !m.clears);
    config_restored(&m);
}
static void failures(void)
{
    struct model m;struct gss_owner o=init(&m);struct gss_session s={0};
    m.bad_offset=S_OUTPUT;m.bad_count=1;
    assert(gss_prepare(&s,&o,1000000)==GSS_READBACK);
    assert(s.report.config_restored && !m.forces && !m.clears && !m.quarantine);
    config_restored(&m);
    o=init(&m);s=(struct gss_session){0};
    assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
    m.bad_offset=0x260;m.bad_count=1;
    assert(gss_commit_native_defaults(&s)==GSS_UNSAFE_RESTORE);
    assert(s.report.failure==GSS_READBACK && s.report.restore_failure==GSS_UNSAFE_RESTORE);
    assert(m.forces==1 && !m.clears && m.quarantine && !s.report.config_restored);
    assert(m.reg[S_IRQ/4]==0 && m.reg[S_GSI/4]==0);
    o=init(&m);s=(struct gss_session){0};
    assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
    assert(gss_commit_native_defaults(&s)==GSS_OK);
    m.reg[0x40/4]=1;
    assert(gss_restore(&s,0)==GSS_UNSAFE_RESTORE && m.quarantine);
    assert(m.reg[S_MCLK/4]==0x141 && m.reg[S_IRQ/4]==0); /* no live clock rewrite */
    o=init(&m);s=(struct gss_session){0};
    assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
    assert(gss_commit_native_defaults(&s)==GSS_OK);
    m.bad_offset=0x260;m.bad_count=1;
    assert(gss_restore(&s,0)==GSS_RESTORE_FAILED && m.quarantine);
    assert(!m.reg[S_IRQ/4] && !m.reg[S_GSI/4]);
    o=init(&m);s=(struct gss_session){0};
    assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
    assert(gss_commit_native_defaults(&s)==GSS_OK);
    assert(gss_restore(&s,GS_TIMEOUT)==GSS_UNSAFE_RESTORE && m.quarantine);
    assert(s.report.transport_status==GS_TIMEOUT && !m.reg[S_IRQ/4] && !m.reg[S_GSI/4]);
    o=init(&m);s=(struct gss_session){0};
    assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
    m.ignore_clear=true;
    assert(gss_commit_native_defaults(&s)==GSS_UNSAFE_RESTORE && m.quarantine);
    assert(s.report.failure==GSS_READBACK && m.forces==1);
    assert(!m.reg[S_IRQ/4] && !m.reg[S_GSI/4]);
    o=init(&m);s=(struct gss_session){0};m.revoke_at=3;
    assert(gss_prepare(&s,&o,1000000)==GSS_OWNERSHIP);
    assert(m.reads==3 && !m.writes && m.quarantine && s.report.ownership_lost);
}
static void restore_mask_and_late_revoke(void)
{
    struct model m;struct gss_owner o=init(&m);struct gss_session s={0};
    unsigned read_end[3],barrier_end[3];
    assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
    read_end[0]=m.reads;barrier_end[0]=m.barriers;
    assert(gss_commit_native_defaults(&s)==GSS_OK);
    read_end[1]=m.reads;barrier_end[1]=m.barriers;
    assert(gss_restore(&s,0)==GSS_OK);
    read_end[2]=m.reads;barrier_end[2]=m.barriers;
    for(unsigned stage=0;stage<3;stage++) {
        o=init(&m);s=(struct gss_session){0};m.revoke_at=read_end[stage];
        if(stage==0) assert(gss_prepare(&s,&o,1000000)<0);
        else {
            assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
            if(stage==1) assert(gss_commit_native_defaults(&s)<0);
            else {
                assert(gss_commit_native_defaults(&s)==GSS_OK);
                assert(gss_restore(&s,0)<0);
            }
        }
        assert(m.reads==m.revoke_at && s.report.ownership_lost && m.quarantine);
    }
    for(unsigned stage=0;stage<3;stage++) {
        o=init(&m);s=(struct gss_session){0};m.revoke_barrier_at=barrier_end[stage];
        if(stage==0) assert(gss_prepare(&s,&o,1000000)<0);
        else {
            assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
            if(stage==1) assert(gss_commit_native_defaults(&s)<0);
            else {
                assert(gss_commit_native_defaults(&s)==GSS_OK);
                assert(gss_restore(&s,0)<0);
            }
        }
        assert(m.barriers==m.revoke_barrier_at && s.report.ownership_lost && m.quarantine);
    }
    o=init(&m);s=(struct gss_session){0};
    assert(gss_prepare(&s,&o,1000000)==GSS_PREPARED);
    assert(gss_commit_native_defaults(&s)==GSS_OK);
    m.bad_offset=S_IRQ;m.bad_count=1;
    unsigned trace_start=m.trace_count;
    assert(gss_restore(&s,0)==GSS_RESTORE_FAILED && m.quarantine);
    assert(m.reg[S_MCLK/4]==0x141); /* No ordinary config restore after mask failure. */
    bool gsi_attempted=false;
    for(unsigned i=trace_start;i<m.trace_count;i++) {
        assert(m.trace[i]==S_IRQ || m.trace[i]==S_GSI);
        gsi_attempted|=m.trace[i]==S_GSI;
    }
    assert(gsi_attempted && !m.reg[S_IRQ/4] && !m.reg[S_GSI/4]);
}
int main(void)
{
    normal();preflight();failures();restore_mask_and_late_revoke();
    puts("PASS: owned live qualification, actual PIO configuration,960kHz, W1C/force boundary, rollback and quarantine");
    return 0;
}
