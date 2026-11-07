/* Actual164 cached record functions, immutable fixture; no hardware model. */
static void baseline_gmb_record(const char *line)
{printf("%s\n",line);if(gmb_thread()){sweet_log_mark_sync(line);sweet_log_flush_now();}}

static void baseline_ggb_records(bool complete)
{
    if(!ggb_started)return;char line[224];const struct ggs_receipt *s=complete?&ggb_smmu:&ggb_context.work;
    if(!complete&&ggb_result==GSM_ARGUMENT){
        const struct gsm_receipt *m=&gmb_work.smmu;
        snprintf(line,sizeof(line),"SWEET GPU INPUT: reason=%u groups=%u banks=%u s2banks=%u ias=%u oas=%u match=%u mapped=%u atos=%u; cached only",ggb_argument,m->groups,m->banks,m->s2banks,m->ias,m->oas,m->stream_match,m->mapped_pages,m->translations);baseline_gmb_record(line);
        for(unsigned n=0;n<2;n++){
            snprintf(line,sizeof(line),"SWEET GPU INPUT: stream%u slot=%u bank=%u asid=%u smr=%08x s2cr=%08x sctlr=%08x actlr=%08x; cached only",4+n,m->slot[n],m->bank[n],m->asid[n],m->smr_after[n],m->s2cr_after[n],m->sctlr[n],m->actlr[n]);baseline_gmb_record(line);
        }
    }
    snprintf(line,sizeof(line),"SWEET GPU SMMU: %s phase=%u rc=%u slot=%u bank=%u asid=%u gpu_pages=%u gmu_pages=%u atos=%u writes=%u polls=%u",complete?"complete":"partial",ggb_context.phase,ggb_result,s->slot,s->bank,s->asid,s->gpu_pages,s->gmu_pages,s->translations,s->writes,s->polls);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU SMMU: ttbr0=%016llx ttbr1=%016llx sctlr=%08x smr=%08x s2cr=%08x micro=%08x/%08x; context only, no GPU commands",s->ttbr0,s->ttbr1,s->sctlr,s->smr,s->s2cr,s->micro_before,s->micro_after);baseline_gmb_record(line);
    if(ggb_data_selected){
        const struct ggp_region *m=&ggb_data_plan.data;
        snprintf(line,sizeof(line),"SWEET GPU DATA MAP: layout=%u ready=%u off=%05x reserved=%u mapped=%u iova=%08x pages=%u atos=%u table_bytes=16384; userRW NC NX",s->layout,ggb_data_ready,m->offset,m->reserved,m->mapped,m->iova,s->gpu_pages,s->translations);baseline_gmb_record(line);
    }
    const struct gsm_diagnostics *d=&ggb_context.diagnostic;
    if(!complete&&d->check){snprintf(line,sizeof(line),"SWEET GPU SMMU FAIL: phase=%u check=%u off=%05x mask=%016llx expected=%016llx actual=%016llx",ggb_context.phase,d->check,d->offset,d->mask,d->expected,d->actual);baseline_gmb_record(line);}
    const struct gsm_atos_sample *a=&ggb_context.translation;
    if(!complete&&a->valid){snprintf(line,sizeof(line),"SWEET GPU ATOS FAIL: sid=%u bank=%u iova=%08x expected=%016llx par=%016llx level=%u",a->stream,a->bank,a->iova,a->expected,a->par,a->level);baseline_gmb_record(line);}
    const struct gpa_registers *r=&ggb_secure.returned;
    snprintf(line,sizeof(line),"SWEET GPU APERTURE: %s rc=%u returned=%u calls=%u fresh=%u continuations=%u x0=%016llx x1=%016llx x2=%016llx x3=%016llx",complete?"complete":"partial",ggb_secure_result,ggb_secure.has_returned,ggb_secure.calls,ggb_secure.fresh,ggb_secure.continuations,r->x[0],r->x[1],r->x[2],r->x[3]);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU APERTURE: x4=%016llx x5=%016llx x6=%016llx; native transport only, no GPU execution",r->x[4],r->x[5],r->x[6]);baseline_gmb_record(line);
}

static void baseline_ggx_records(bool complete)
{
    const struct ggx_receipt *r=complete?&ggx_work:&ggx_context.work;char line[192];
    snprintf(line,sizeof(line),"SWEET GPU START: %s phase=%u rc=%u bank=%u asid=%u writes=%u/%u polls=%u/%u; HOST GPU request retained=%u",complete?"complete":"partial",ggx_context.phase,ggx_result,r->bank,r->asid,r->writes32,r->writes64,r->tlb_polls,r->oob_polls,r->request_retained);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU START MMU: hum=%08x dora=%08x ttbr0=%016llx contextidr=%08x tlb=%08x; native writes, HUM/DORA equality unqualified",r->hum,r->dora,r->ttbr0,r->contextidr,r->tlb_status);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU START OOB: before=%08x ack=%08x cleared=%08x request=%u accepted=%u clear=%u; legacy set16/ACK24, no HOST release",r->oob_before,r->oob_ack,r->oob_cleared,r->request_attempted,r->ack_valid,r->ack_clear_attempted);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU START CORE: mapped=%u status=%08x status3=%08x; raw reads only, no GPU commands/Metal",r->core_opened,r->status,r->status3);baseline_gmb_record(line);
    if(!complete&&ggx_context.diagnostic.valid){
        const struct ggx_diagnostic *d=&ggx_context.diagnostic;
        snprintf(line,sizeof(line),"SWEET GPU START SAMPLE: phase=%u window=%u off=%05x expected=%016llx actual=%016llx; last cached sample",ggx_context.phase,d->window,d->offset,d->expected,d->actual);baseline_gmb_record(line);
    }
}

static void baseline_ggc_records(bool complete)
{
    const struct ggc_receipt *r=complete?&ggc_work:&ggc_context.work;char line[320];
    snprintf(line,sizeof(line),"SWEET GPU CORE: %s phase=%u rc=%u reads=%u writes=%u memory=%u/%u hwcg_skip=%u configured=%u retained=%u",complete?"complete":"partial",ggc_context.phase,ggc_result,r->reads,r->writes,r->mem_written,r->mem_compared,r->hwcg_skipped,r->configured,r->requests_retained);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CORE PAGES: ready=%u required=10 map_attempts=%u reused=%u; private Device aliases retained",ggc_maps_ready,ggc_created,ggc_maps_ready?4u:0u);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CORE RESTORE: iova=%08x pa=%016llx values=66 length=%u offset=%u bytes=544; live registers, no CP/SQE execution",ggb_plan.region[GGP_REGLIST].iova,gmb_stage.pa+ggb_plan.region[GGP_REGLIST].offset,r->list_length,r->list_offset);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CORE MEMORY: zero_checked=%u batch_words=64; private NC scan progress",ggc_context.zero_checked);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CORE GUARD: reason=%u phase=%u now=%016llx entry=%016llx phase_entry=%016llx total_end=%016llx phase_end=%016llx; cached ticks",ggc_guard_diagnostic.reason,ggc_guard_diagnostic.phase,ggc_guard_diagnostic.now,ggc_entry,ggc_phase_entry,ggc_deadline,ggc_phase_deadline);baseline_gmb_record(line);
    if(complete)for(unsigned i=0;i<GGC_REGLIST_VALUES;i++){
        snprintf(line,sizeof(line),"SWEET GPU CORE RGL: index=%u reg=%05x value=%08x",i,ggc_context.reglist[4+2*i],ggc_context.reglist[5+2*i]);baseline_gmb_record(line);
    }
    else if(ggc_context.diagnostic.valid){
        snprintf(line,sizeof(line),"SWEET GPU CORE SAMPLE: phase=%u reg=%05x value=%08x; last cached sample",ggc_context.phase,ggc_context.diagnostic.reg,ggc_context.diagnostic.value);baseline_gmb_record(line);
    }
}

static void baseline_ggq_records(bool complete)
{
    const struct ggq_receipt *r=complete?&ggq_work:&ggq_context.work;char line[256];
    snprintf(line,sizeof(line),"SWEET GPU CP: %s phase=%u rc=%u reads=%u writes=%u commands=%u/%u sqe=%u submit=%u complete=%u retained=%u",complete?"complete":"partial",ggq_context.phase,ggq_result,r->reads,r->writes,r->commands_written,r->commands_checked,r->sqe_start_attempted,r->submit_attempted,r->complete,r->requests_retained);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CP MEMORY: ring=%u/%u scratch=%u/%u batch_words=64; private NC, no CPU shadow store after SQE start",r->ring_written,r->ring_checked,r->scratch_written,r->scratch_checked);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CP INITIAL: rptr=%08x wptr=%08x sqe=%08x; raw before private ring preparation",r->initial_rptr,r->initial_wptr,r->initial_sqe);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CP FENCE: checks=%u status=%08x slow=%u counters=%u/%u before=%016llx after=%016llx keepalive=%u/%u",r->fence_checks,r->fence_status,r->fence_slow,r->counter_before_valid,r->counter_after_valid,r->counter_before,r->counter_after,r->keepalive_set_attempted,r->keepalive_clear_attempted);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CP IDLE: polls=%u rptr=%08x busy=%08x rbbm=%08x cp=%08x; native shadow equality and AO busy bit23",r->idle_polls,r->rptr,r->busy,r->rbbm_status,r->cp_status);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CP GUARD: reason=%u phase=%u now=%016llx entry=%016llx phase_entry=%016llx total_end=%016llx phase_end=%016llx; cached ticks",ggq_guard_diagnostic.reason,ggq_guard_diagnostic.phase,ggq_guard_diagnostic.now,ggq_entry,ggq_phase_entry,ggq_deadline,ggq_phase_deadline);baseline_gmb_record(line);
    snprintf(line,sizeof(line),"SWEET GPU CP FAULT: rbbm=%08x cp=%08x; cached live guard samples",ggq_guard_diagnostic.rbbm,ggq_guard_diagnostic.cp);baseline_gmb_record(line);
    if(complete)for(unsigned i=0;i<GGQ_COMMAND_WORDS;i++){
        snprintf(line,sizeof(line),"SWEET GPU CP WORD: index=%u value=%08x",i,ggq_context.command.word[i]);baseline_gmb_record(line);
    }else if(ggq_context.diagnostic.valid){
        const struct ggq_diagnostic *d=&ggq_context.diagnostic;
        snprintf(line,sizeof(line),"SWEET GPU CP SAMPLE: phase=%u memory=%u off=%05x expected=%08x actual=%08x; last cached sample",ggq_context.phase,d->memory,d->reg,d->expected,d->actual);baseline_gmb_record(line);
    }
}
