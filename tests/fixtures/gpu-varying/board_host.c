/* Actual mode10 adapter with real signed/GGU code and hostile typed seams.
 * MODELED device effects only; first secure CPU page remains PROT_NONE. */
#include "gpu-varying/native_words.h"
#include "gpu-varying/pixel_vectors173.h"
static const uint32_t varying_direct[7]={0x70bf8003,0xfc00c000,0,203,0x70620002,0xfc010000,0};
static unsigned varying_offsets[1632],varying_values[3][1632];
static uint32_t varying_pixel(unsigned job,unsigned i)
{return reference_preferred[job][i];}
static bool varying_declared(unsigned job,unsigned i,uint32_t value)
{
 uint32_t lo=reference_lower[job][i],hi=reference_upper[job][i];
 for(unsigned c=0;c<4;c++)if(((value>>(8*c))&255u)<((lo>>(8*c))&255u)||((value>>(8*c))&255u)>((hi>>(8*c))&255u))return false;
 return true;
}
static uint32_t varying_device_pixel(unsigned job,unsigned i)
{
 if(!vf.quantize)return varying_pixel(job,i);
 unsigned choice=(vf.quantize_mode+i+2*job)&7;uint32_t lo=reference_lower[job][i],hi=reference_upper[job][i],v=0;
 for(unsigned c=0;c<4;c++)v|=(((choice&(1u<<c)?hi:lo)>>(8*c))&255u)<<(8*c);
 return v;
}
static uint32_t varying_written(unsigned job,unsigned i)
{uint32_t v=varying_device_pixel(job,i);return vf.job==job&&vf.corrupt_data==i+1?v^1u:v;}
static uint32_t varying_data(unsigned job,unsigned i)
{return i<256?varying_pixel(job,i):i==768?16*job+6:0;}
static bool varying_artifact(unsigned off)
{
 if(off&3)return false;
 for(unsigned id=0;id<27;id++){
  const struct varying173_native_blob *b=&varying173_blobs[0][id];
  if(b->words&&off>=b->iova-0xfc008000u&&off-(b->iova-0xfc008000u)<b->gpu_serialized_extent)return true;
 }
 return false;
}
static void varying_golden(void)
{
 for(unsigned job=0;job<3;job++){
  unsigned n=0;
  for(unsigned id=0;id<27;id++){
   const struct varying173_native_blob *b=&varying173_blobs[job][id];if(!b->words)continue;
   for(unsigned i=0;i<b->gpu_serialized_extent/4;i++){
    CHECK(n<1632);unsigned off=b->iova-0xfc008000u+4*i;
    if(!job)varying_offsets[n]=off;else CHECK(varying_offsets[n]==off);
    varying_values[job][n++]=i<b->words?b->data[i]:0;
   }
  }
  CHECK(n==1632);
 }
}
static bool host_varying_active(void)
{
 return vf.active&&z.auth_done&&z.flag==10&&sweet_gpu_varying_state()==GMB_RUNNING&&
  ((ggvb_context.state==1&&ggvb_context.phase>=GGV_SEAL&&ggvb_context.phase<=GGV_FINAL)||
   (ggvb_context.state==2&&ggvb_context.phase==GGV_DONE&&ggvb_phase==17));
}
static void host_varying_budget(void)
{
 if(!vf.active)return;++vf.budgets;if(vf.time_step)h.now+=vf.time_step;
 if(vf.budgets==vf.budget_fail)h.live=false;
 if(!vf.kind||vf.fired||ggvb_context.state!=1||ggvb_context.job!=vf.job||ggvb_context.phase!=vf.phase)return;
 vf.fired=1;uint32_t v=1;uint64_t q;
 switch(vf.kind){

 case 1:h.clock_bad=1;break;case 2:h.irq_bad=1;break;case 3:memcpy(reset_page+0x2000,&v,4);break;
 case 4:memcpy(smmu+0x48,&v,4);break;case 5:v=1u<<9;memcpy(core_page+4*0x201,&v,4);break;
 case 6:memcpy(core_page+4*0x823,&v,4);break;case 7:h.now=ggvb_deadline;break;case 8:h.now=ggvb_phase_end;break;
 case 9:vf.owner_bad=1;break;case 10:ggub_work.prefix_checked=14;ggub_context.work=ggub_work;break;
 case 11:gfw_context.dcvs_return=1;break;case 12:core_attr_bad=1;break;case 13:ggc_alias[0]++;break;
 case 14:h.context=1;break;case 15:q=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&q,8);break;
 case 16:v=1u<<24;memcpy(reset_page+0x2648,&v,4);break;case 17:ggc_work.mem_compared=1023;break;
 case 18:h.now=ggvb_last_now?ggvb_last_now-1:UINT64_MAX;break;
 case 19:cp_nc_bad=2;cp_nc_page=1;break;case 20:cp_nc_bad=1;cp_nc_page=3;break;case 21:cp_dev_bad=1;break;
 case 22:ggb_data_ready=0;break;
 case 23:ram[0x9c000+0x2000+24*8]^=0x40;break;
 case 24:ram[0x9c000]^=1;break;
 case 25:ggb_data_selected=0;break;
 case 26:ggb_smmu.layout=GGS_BOOTSTRAP18;ggb_context.work=ggb_smmu;break;
 case 27:ggub_work.rptr=19;ggub_context.work=ggub_work;break;
 case 28:ggub_work.counter_before_valid=0;ggub_context.work=ggub_work;break;
 case 29:ggub_context.state=1;break;case 30:z.owner_state=PSZ_COPIED;break;
 case 31:ggb_data_mode=3;break;case 32:z.flag=3;break;
 case 33:ggwb_lifecycle=GMB_READY;break;case 34:ggwb_context.state=2;break;
 case 35:ggib_lifecycle=GMB_READY;break;case 36:ggib_context.state=2;break;
 case 37:ggb_data_mode=4;break;case 38:z.flag=4;break;case 39:ggib_context.phase=GGI_SEAL;break;
 case 40:ggeb_lifecycle=GMB_READY;break;case 41:ggeb_context.state=2;break;
 case 42:ggeb_context.phase=GGE_SEAL;break;case 43:ggb_data_mode=5;break;case 44:z.flag=5;break;
 case 45:ggkb_lifecycle=GMB_READY;break;case 46:ggkb_context.state=2;break;
 case 47:ggkb_context.phase=GGK_SEAL;break;case 48:ggb_data_mode=6;break;case 49:z.flag=6;break;
 case 50:gglb_lifecycle=GMB_READY;break;case 51:gglb_context.state=2;break;
 case 52:gglb_context.phase=GGL_SEAL;break;case 53:ggb_data_mode=7;break;case 54:z.flag=7;break;
 case 55:ggtb_lifecycle=GMB_READY;break;case 56:ggtb_context.state=2;break;
 case 57:ggtb_context.phase=GGT_SEAL;break;case 58:ggb_data_mode=8;break;case 59:z.flag=8;break;
 case 60:ggjb_lifecycle=GMB_READY;break;case 61:ggjb_context.state=2;break;
 case 62:ggjb_context.phase=GGJ_SEAL;break;case 63:ggb_data_mode=9;break;case 64:z.flag=9;break;
 default:CHECK(false);
 }
}
static void host_varying_device(unsigned job)
{
 CHECK(job<3&&vf.j[job].accepted&&!vf.j[job].device_done&&vf.j[job].submits&&vf.j[job].kept);vf.j[job].device_done=1;
 for(unsigned j=0;j<=job;j++)CHECK(!memcmp(ram+0xa8000+4*(20+7*j),varying_direct,sizeof(varying_direct)));
 for(unsigned i=0;i<1632;i++){uint32_t v;memcpy(&v,ram+0xa8000+varying_offsets[i],4);CHECK(v==varying_values[job][i]);}
 CHECK(ggvb_context.work.completed_jobs==job);
 for(unsigned i=0;i<256;i++){
  uint32_t v=varying_device_pixel(job,i);
  if(!vf.j[job].drop_pixels&&vf.j[job].drop_data!=i+1)memcpy(ram+0xb8000+4*i,&v,4);
  ++vf.j[job].device_writes;
 }
}
static void host_varying_event(unsigned job)
{
 CHECK(job<3&&vf.j[job].device_done&&!vf.j[job].eop_done&&vf.j[job].submits&&!vf.j[job].kept);unsigned events=0;
 const uint32_t *ib=varying173_blobs[job][0].data;
 for(unsigned i=0;i+4<203;i++)if(ib[i]==0x70460004){
  CHECK(!(ib[i+1]&0xc0000000u)&&ib[i+2]==0xfc018c00u&&!ib[i+3]&&ib[i+4]==16*job+(++events));
 }
 CHECK(events==6);uint32_t value=vf.j[job].bad_eop?vf.j[job].bad_eop:16*job+6;
 memcpy(ram+0xb8c00,&value,4);vf.j[job].eop_done=1;vf.j[job].device_writes+=6;
 if(vf.corrupt_data&&vf.job==job){CHECK(vf.corrupt_data<=1024);ram[0xb8000+4*(vf.corrupt_data-1)]^=1;}
}
static void host_varying_read(vm_offset_t address,uint32_t *value)
{
 if(!vf.active)return;CHECK(host_varying_active());unsigned job=ggvb_context.job;CHECK(job<3);++vf.reads;
 if(address==(uintptr_t)fw_page[0]+0x2c4c){
  *value=vf.j[job].fences++<vf.j[job].drop?3:2;
  if(!(*value&1)){vf.j[job].accepted=1;if(!vf.j[job].device_done)host_varying_device(job);}
 }
 if(address==(uintptr_t)fw_page[0]+0x2c30)*value=ggvb_context.phase==GGV_WAIT&&vf.j[job].busy_reads++<vf.j[job].busy_delay?0x71800000:0x71000000;
 if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
  unsigned n=vf.j[job].counter_reads++;*value=!vf.j[job].wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
   n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
 }
 bool ring=address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb0000;
 bool scratch=address==(uintptr_t)ram+0xb0000;
 bool data=address>=(uintptr_t)ram+0xb8000&&address<(uintptr_t)ram+0xb9000;
 if(ring||scratch||data){
  ++vf.memreads;
  if(ggvb_context.phase==GGV_WAIT&&scratch){
   CHECK(vf.j[job].accepted&&vf.j[job].submits&&!vf.j[job].kept&&vf.j[job].device_done);
   if(vf.j[job].shadow_reads++>=vf.j[job].shadow_delay){*value=vf.j[job].bad_shadow?vf.j[job].bad_shadow:27+7*job;memcpy(ram+0xb0000,value,4);}
  }
  if(ggvb_context.phase==GGV_WAIT&&data){
   CHECK((address==(uintptr_t)ram+0xb8c00||address==(uintptr_t)ram+0xb8c04)&&vf.j[job].device_done&&!vf.j[job].kept&&vf.j[job].shadow_reads);
   if(address==(uintptr_t)ram+0xb8c00&&ggvb_context.work.job[job].wait_samples==ggvb_context.work.job[job].idle_polls){
    if(vf.j[job].eop_reads++>=vf.j[job].eop_delay&&!vf.j[job].drop_eop&&!vf.j[job].eop_done)host_varying_event(job);
   }
   memcpy(value,(void *)address,4);
  }
  unsigned mem=ring?GGV_RING:scratch?GGV_SCRATCH:GGV_DATA;
  unsigned off=(unsigned)(address-(uintptr_t)ram-(ring?0xa8000:scratch?0xb0000:0xb8000));
  if(job==vf.job&&ggvb_context.phase==vf.corrupt_phase&&mem==vf.corrupt_mem&&off==vf.corrupt_off)*value^=1;
 }
}
static bool host_varying_store(vm_offset_t address,uint32_t value)
{
 if(!vf.active)return false;CHECK(host_varying_active());unsigned job=ggvb_context.job;CHECK(job<3);++vf.stores;
 if(address>=(uintptr_t)ram&&address<(uintptr_t)ram+sizeof(ram)){
  CHECK(ggvb_context.phase==GGV_COMMANDS&&vf.j[job].memstores<1639);unsigned index=vf.j[job].memstores;
  unsigned off=index<1632?varying_offsets[index]:4*(20+7*job+index-1632);
  uint32_t expected=index<1632?varying_values[job][index]:varying_direct[index-1632];
  CHECK(address==(uintptr_t)ram+0xa8000+off&&value==expected);++vf.j[job].memstores;++vf.memstores;
  if(vf.memstores!=vf.drop_write)memcpy((void *)address,&value,4);
  if(vf.trace)printf("N %u %u %u %08x\n",job,GGV_RING,off/4,value);
 }else{
  uint32_t reg=host_core_reg(address);CHECK(ggvb_context.phase==GGV_SUBMIT&&ggv_register_allowed(reg,true)&&vf.j[job].memstores==1639&&ggvb_context.work.job[job].commands_checked==7&&ggvb_context.work.job[job].artifact_checked==1632);
  if(reg==0x807){CHECK(value==27+7*job&&vf.j[job].kept);++vf.j[job].submits;}else{CHECK(value<=1);vf.j[job].kept=value;}
  memcpy((void *)address,&value,4);if(vf.trace)printf("W %u %05x %08x\n",job,reg,value);
 }
 if(vf.stores==vf.stop_store)h.clock_bad=1;if(vf.stores==vf.expire_store)h.now=ggvb_phase_end;
 return true;
}
static void varying_signed_setup(void)
{
 fixture_gpu_mode=10;cp_setup(0);fixture_gpu_mode=0;
 struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
 CHECK(z.flag==10&&ggb_data_selected==1&&ggb_data_ready==1&&ggb_smmu.layout==GGS_DATA19&&ggb_smmu.gpu_pages==19&&ggb_smmu.translations==171);
 CHECK(ggd_tables_match(&ggb_data_plan,ram+0x9c000,16384));
 for(unsigned i=0xb8000;i<0xbc000;i++)CHECK(ram[i]==0);
 struct gpz_receipt signed_load;CHECK(sweet_gpu_zap_once(&signed_load)==GPZ_OK);cp_active=0;u.active=1;
 CHECK(!mprotect(ram,16384,PROT_NONE));
}
static void varying_setup(void)
{varying_signed_setup();unsecure_good();u.active=0;vf.active=1;}
static void varying_untouched(void)
{
 CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60)&&!memcmp(ram+0xa8000+60,ggub_context.command.word,20));
 for(unsigned i=41;i<8192;i++)if(!varying_artifact(4*i)){uint32_t v;memcpy(&v,ram+0xa8000+4*i,4);CHECK(v==0xaaaaaaaa);}
 for(unsigned i=1;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb0000+4*i,4);CHECK(!v);}
 for(unsigned i=0xb9000;i<0xbc000;i++)CHECK(!ram[i]);
}
static void varying_failed(void)
{
 struct ggv_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 CHECK(sweet_gpu_varying_once(&out)!=GGV_OK&&!memcmp(&out,&saved,sizeof(out))&&vf.partial==1&&!vf.complete);
 CHECK(sweet_gpu_varying_state()==GMB_QUARANTINED&&sweet_gpu_sequence_state()==GMB_QUARANTINED&&ggjb_context.state==3&&sweet_gpu_draw_state()==GMB_QUARANTINED&&ggtb_context.state==3&&sweet_gpu_clear_state()==GMB_QUARANTINED&&gglb_context.state==3&&sweet_gpu_write_state()==GMB_QUARANTINED&&ggwb_context.state==3&&sweet_gpu_ib_state()==GMB_QUARANTINED&&ggib_context.state==3&&sweet_gpu_compute_state()==GMB_QUARANTINED&&ggkb_context.state==3&&sweet_gpu_eop_state()==GMB_QUARANTINED&&ggeb_context.state==3&&sweet_gpu_unsecure_state()==GMB_QUARANTINED&&ggub_context.state==3&&sweet_gpu_zap_state()==GMB_QUARANTINED&&sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
 unsigned reads=vf.reads,stores=vf.stores,budgets=vf.budgets;
 CHECK(sweet_gpu_varying_once(&out)==(z.flag==10?GGV_ALREADY:GGV_ARGUMENT)&&!memcmp(&out,&saved,sizeof(out))&&reads==vf.reads&&stores==vf.stores&&budgets==vf.budgets);varying_untouched();
}
static void varying_good(void)
{
 struct ggv_receipt out;unsigned maps=h.maps,nc=h.nc_maps,owner_calls=h.owner_calls;
 enum ggv_result rc=sweet_gpu_varying_once(&out);
 if(rc!=GGV_OK)fprintf(stderr,"Sequence refusal rc=%u job=%u phase=%u reason=%u step=%u mode=%u/%u sample=%u/%05x expected=%08x actual=%08x stores=%u memstores=%u memreads=%u\n",rc,ggvb_context.job,ggvb_context.phase,ggvb_diagnostic.reason,ggvb_phase,ggb_data_mode,z.flag,ggvb_context.diagnostic.memory,ggvb_context.diagnostic.reg,ggvb_context.diagnostic.expected,ggvb_context.diagnostic.actual,vf.stores,vf.memstores,vf.memreads);
 CHECK(rc==GGV_OK&&sweet_gpu_varying_state()==GMB_READY&&vf.complete==1&&!vf.partial&&h.live&&!h.quarantine);
 CHECK(out.complete==1&&out.sealed==1&&out.requests_retained==1&&out.completed_jobs==3&&vf.memstores==4917&&ggvb_phase==17&&ggvb_diagnostic.reason==VGD_NONE);
 unsigned extra=0;
 for(unsigned job=0;job<3;job++){
  const struct ggv_job_receipt *r=&out.job[job];
  CHECK(r->complete==1&&r->prefix_checked==20+7*job&&r->clean_checked==7&&r->commands_written==7&&r->commands_checked==7);
  CHECK(r->artifact_before_checked==1632&&r->artifact_written==1632&&r->artifact_checked==1632&&r->artifact_after_checked==1632);
  CHECK(r->initial_wptr==20+7*job&&r->initial_shadow==20+7*job&&r->rptr==27+7*job&&r->writes==vf.j[job].drop+3&&r->fence_checks==vf.j[job].drop+1&&vf.j[job].memstores==1639&&vf.j[job].submits==vf.j[job].drop+1&&!vf.j[job].kept);
  CHECK(r->data_before_checked==1024&&r->data_after_checked==1024&&r->pixels_checked==256&&r->foreground_checked==256&&r->background_checked==0&&r->unchanged_checked==767&&r->eop_checked==1&&r->eop_complete==1&&r->eop_value==16*job+6&&r->eop_polls==vf.j[job].eop_delay+1&&r->ring_after_checked==27+7*job&&r->max_nc_batch_words==64);
  CHECK(ggvb_aux_mask[job]==63&&ggvb_before_control[job]==(job?16*(job-1)+6:0)&&ggvb_after_control[job]==16*job+6&&!ggvb_before_hi[job]&&!ggvb_before_tail[job]&&!ggvb_after_hi[job]&&!ggvb_after_tail[job]);
  for(unsigned i=0;i<8;i++)CHECK(ggvb_before_mask[job][i]==UINT32_MAX&&ggvb_after_mask[job][i]==UINT32_MAX);
  for(unsigned i=0;i<256;i++)CHECK(ggvb_before[job][i]==(job?varying_written(job-1,i):0)&&ggvb_after[job][i]==varying_written(job,i));
  CHECK(r->wait_samples==r->idle_polls&&r->wait_samples==vf.j[job].shadow_reads&&!r->wait_control_hi&&vf.j[job].device_writes==262);
  extra+=3*vf.j[job].shadow_reads+vf.j[job].eop_reads;
 }
 CHECK(vf.memreads==21060+extra&&h.maps==maps&&h.nc_maps==nc&&h.owner_calls==owner_calls);
 for(unsigned i=0;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb8000+4*i,4);CHECK(v==(i<256?varying_written(2,i):varying_data(2,i)));}
 varying_untouched();unsigned reads=vf.reads,stores=vf.stores,budgets=vf.budgets;
 CHECK(sweet_gpu_varying_once(&out)==GGV_ALREADY&&reads==vf.reads&&stores==vf.stores&&budgets==vf.budgets);
}
static void varying_scenario(unsigned scenario,bool trace)
{
 varying_setup();vf.trace=trace;
 for(unsigned j=0;j<3;j++){
  vf.j[j].drop=scenario==1?1:scenario==2?100:scenario==3?199:0;vf.j[j].wrap=scenario==4;
  if(scenario==1)vf.j[j].shadow_delay=vf.j[j].busy_delay=vf.j[j].eop_delay=2;
 }
 varying_good();
}
static void gpu_varying_cases(void)
{
 unsigned first=cases;varying_golden();
 for(unsigned mode=0;mode<8;mode++){varying_setup();vf.quantize=1;vf.quantize_mode=mode;varying_good();}
 for(unsigned s=0;s<5;s++)varying_scenario(s,false);
 for(unsigned job=0;job<3;job++)for(unsigned phase=GGV_SEAL;phase<=GGV_FINAL;phase++){
  if((phase==GGV_SEAL&&job)||(phase==GGV_FINAL&&job!=2))continue;
  for(unsigned kind=1;kind<=64;kind++){varying_setup();vf.job=job;vf.phase=phase;vf.kind=kind;varying_failed();CHECK(vf.fired);}
 }
 /* Probe every guarded copy batch edge and all per-submit MMIO boundaries.
  * The portable core separately injects every callback and all4917 writes. */
 unsigned edges[1643]={0};unsigned n=0;
 for(unsigned id=0;id<27;id++){
  unsigned words=varying173_blobs[0][id].gpu_serialized_extent/4;
  for(unsigned base=0;base<words;base+=64){unsigned end=base+64;if(end>words)end=words;edges[n+base+1]=1;edges[n+end]=1;}
  n+=words;
 }
 CHECK(n==1632);for(unsigned i=1633;i<=1642;i++)edges[i]=1;
 for(unsigned job=0;job<3;job++)for(unsigned edge=1;edge<=1642;edge++)if(edges[edge]){
  varying_setup();vf.stop_store=job*1642+edge;varying_failed();CHECK(vf.stores>=vf.stop_store&&vf.stores-vf.stop_store<64);
  varying_setup();vf.expire_store=job*1642+edge;varying_failed();CHECK(vf.stores>=vf.expire_store&&vf.stores-vf.expire_store<64);
 }
 for(unsigned job=0;job<3;job++){
  for(unsigned phase=GGV_CAPTURE;phase<=GGV_VERIFY;phase++)if(phase==GGV_CAPTURE||phase==GGV_COMMANDS||phase==GGV_VERIFY){
   for(unsigned id=0;id<27;id++){
    const struct varying173_native_blob *b=&varying173_blobs[job][id];if(!b->words)continue;
    unsigned selected[]={0,b->words-1,b->gpu_serialized_extent/4-1};
    for(unsigned k=0;k<3;k++){varying_setup();vf.job=job;vf.corrupt_phase=phase;vf.corrupt_mem=GGV_RING;vf.corrupt_off=b->iova-0xfc008000u+4*selected[k];varying_failed();}
   }
  }
  const unsigned offsets[]={0,4,1020,2048,3072,3076,4092};
  for(unsigned phase=GGV_CAPTURE;phase<=GGV_VERIFY;phase++)if(phase==GGV_CAPTURE||phase==GGV_VERIFY)
   for(unsigned k=0;k<7;k++){varying_setup();vf.job=job;vf.corrupt_phase=phase;vf.corrupt_mem=GGV_DATA;vf.corrupt_off=offsets[k];varying_failed();}
  for(unsigned k=0;k<7;k++){varying_setup();vf.job=job;vf.corrupt_data=offsets[k]/4+1;if(offsets[k]<1024&&varying_declared(job,offsets[k]/4,varying_pixel(job,offsets[k]/4)^1u))varying_good();else varying_failed();}
  const unsigned pixels[]={0,3,4,63,64,68,143,244,255};
  for(unsigned k=0;k<9;k++){varying_setup();vf.j[job].drop_data=pixels[k]+1;if(job&&varying_declared(job,pixels[k],varying_pixel(job-1,pixels[k])))varying_good();else varying_failed();}
  varying_setup();vf.j[job].drop_pixels=1;varying_failed();CHECK(vf.j[job].eop_done&&ggvb_context.work.job[job].eop_complete==1);
  varying_setup();vf.j[job].drop_eop=1;varying_failed();CHECK(vf.j[job].eop_reads==1024&&vf.j[job].device_writes==256&&!vf.j[job].kept);
  varying_setup();vf.j[job].bad_eop=16*job+7;varying_failed();
  varying_setup();vf.j[job].drop=200;varying_failed();CHECK(vf.j[job].kept&&vf.j[job].submits==201&&vf.j[job].fences==200);
  varying_setup();vf.j[job].bad_shadow=8192;varying_failed();
  for(unsigned off=3072;off<=3076;off+=4){varying_setup();vf.job=job;vf.corrupt_phase=GGV_WAIT;vf.corrupt_mem=GGV_DATA;vf.corrupt_off=off;varying_failed();}
 }
 for(unsigned n=0;n<8;n++)for(unsigned kind=1;kind<=2;kind++){varying_setup();vf.nc_kind=kind;vf.nc_page=n;varying_failed();CHECK(!vf.stores);}
 for(unsigned n=1;n<=8;n++){varying_setup();vf.phys_bad=n;varying_failed();CHECK(!vf.stores);}
 for(unsigned bit=0;bit<64;bit++){varying_setup();ram[0x9c000+0x2000+24*8+bit/8]^=1u<<(bit%8);varying_failed();CHECK(!vf.stores);}
 varying_setup();vf.budget_fail=1;varying_failed();CHECK(ggvb_diagnostic.reason==VGD_ENTRY_BUDGET&&!vf.stores&&!vf.memreads);
 varying_setup();vf.time_step=100000000;varying_failed();CHECK(ggvb_diagnostic.reason==VGD_TIME);
 for(unsigned mode=0;mode<=11;mode++)if(mode!=10){
  varying_setup();z.flag=(int)mode;struct ggv_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned budgets=h.budgets;
  CHECK(sweet_gpu_varying_once(&out)==GGV_ARGUMENT&&!memcmp(&out,&old,sizeof(out))&&ggvb_lifecycle==GMB_IDLE&&budgets==h.budgets&&!vf.stores);
 }
 for(unsigned mode=2;mode<=9;mode++){
  fixture_gpu_mode=mode;cp_setup(0);fixture_gpu_mode=0;struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
  struct gpz_receipt zap;CHECK(sweet_gpu_zap_once(&zap)==GPZ_OK);cp_active=0;u.active=1;CHECK(!mprotect(ram,16384,PROT_NONE));
  z.flag=10;unsecure_failed();CHECK(!u.stores);
 }
 for(unsigned job=0;job<3;job++)for(unsigned id=0;id<27;id++)for(unsigned field=0;field<4;field++){
  varying_setup();varying_good();ggvb_lifecycle=GMB_RUNNING;
  uint32_t *counts[]={ggvb_work.job[job].blob_before_checked,ggvb_work.job[job].blob_written,ggvb_work.job[job].blob_checked,ggvb_work.job[job].blob_after_checked};
  counts[field][id]^=1;ggvb_context.work=ggvb_work;CHECK(!ggvb_guard(NULL,2,GGV_FINAL)&&ggvb_diagnostic.reason==VGD_ENGINE);
 }
 for(unsigned job=0;job<3;job++)for(unsigned i=0;i<256;i+=17){
  varying_setup();varying_good();ggvb_lifecycle=GMB_RUNNING;ggvb_after[job][i]^=1;CHECK(!ggvb_guard(NULL,2,GGV_FINAL)&&ggvb_diagnostic.reason==VGD_ENGINE);
 }
 varying_setup();
 for(unsigned job=0;job<3;job++)for(unsigned phase=GGV_IDLE;phase<=GGV_DONE;phase++){
  ggvb_context.job=job;ggvb_context.phase=phase;
  for(unsigned mem=0;mem<=3;mem++)for(unsigned off=0;off<=32768;off+=4)for(unsigned write=0;write<=1;write++){
   bool ring=mem==GGV_RING&&off<4*(27+7*job),scratch=mem==GGV_SCRATCH&&!off,data=mem==GGV_DATA&&off<4096,cmd=ring&&off>=4*(20+7*job);
   bool artifact=mem==GGV_RING&&varying_artifact(off);
   bool allowed=write?(phase==GGV_COMMANDS&&(cmd||artifact)):
    ((phase==GGV_CAPTURE&&(ring||scratch||data||artifact))||(phase==GGV_COMMANDS&&(cmd||artifact))||
     (phase==GGV_WAIT&&(scratch||(data&&(off==3072||off==3076))))||(phase==GGV_VERIFY&&(ring||data||artifact)));
   CHECK(!!ggvb_memory((enum ggv_memory)mem,off,write)==allowed);
  }
 }
 ggvb_context.phase=GGV_IDLE;CHECK(!ggvb_memory(GGV_DATA,1,false)&&!ggvb_memory(GGV_RING,UINT32_MAX,false));
 ggvb_context.job=3;CHECK(!ggvb_memory(GGV_RING,80,true));ggvb_context.job=UINT32_MAX;CHECK(!ggvb_memory(GGV_DATA,0,false));
 CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));
 printf("GPU native varying live board: %u actual coldDATA19+CP+ZAP+GGU+GGV/three-job/PROT_NONE/owner/PTE/NC/phase/WDT/once cases PASS; MODEL only, no physical varying or Metal proof\n",cases-first);
}
