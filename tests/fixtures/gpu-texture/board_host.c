/* Actual mode11 adapter with real signed/GGU code and hostile typed seams.
 * MODELED device effects only; first secure CPU page remains PROT_NONE. */
#include "gpu-texture/native_words.h"
#include "texture_vectors_board174.h"
static const uint32_t texture_direct[7]={0x70bf8003,0xfc00c000,0,203,0x70620002,0xfc010000,0};
static unsigned texture_offsets[2752],texture_values[3][2752];
static uint32_t texture_pixel(unsigned job,unsigned i)
{return texture_reference_preferred[job][i];}
static bool texture_declared(unsigned job,unsigned i,uint32_t value)
{return value==texture_pixel(job,i);}
static uint32_t texture_device_pixel(unsigned job,unsigned i)
{return texture_pixel(job,i);}
static uint32_t texture_written(unsigned job,unsigned i)
{uint32_t v=texture_device_pixel(job,i);return ff.job==job&&ff.corrupt_data==i+1?v^1u:v;}
static uint32_t texture_data(unsigned job,unsigned i)
{return i<256?texture_pixel(job,i):i==768?16*job+6:0;}
static bool texture_artifact(unsigned off)
{
 if(off&3)return false;
 for(unsigned id=0;id<31;id++){
  const struct texture174_native_blob *b=&texture174_blobs[0][id];
  if(b->words&&off>=b->iova-0xfc008000u&&off-(b->iova-0xfc008000u)<b->gpu_serialized_extent)return true;
 }
 return false;
}
static void texture_golden(void)
{
 for(unsigned job=0;job<3;job++){
  unsigned n=0;
  for(unsigned id=0;id<31;id++){
   const struct texture174_native_blob *b=&texture174_blobs[job][id];if(!b->words)continue;
   for(unsigned i=0;i<b->gpu_serialized_extent/4;i++){
    CHECK(n<2752);unsigned off=b->iova-0xfc008000u+4*i;
    if(!job)texture_offsets[n]=off;else CHECK(texture_offsets[n]==off);
    texture_values[job][n++]=i<b->words?b->data[i]:0;
   }
  }
  CHECK(n==2752);
 }
}
static bool host_texture_active(void)
{
 return ff.active&&z.auth_done&&z.flag==11&&sweet_gpu_texture_state()==GMB_RUNNING&&
  ((ggfb_context.state==1&&ggfb_context.phase>=GGF_SEAL&&ggfb_context.phase<=GGF_FINAL)||
   (ggfb_context.state==2&&ggfb_context.phase==GGF_DONE&&ggfb_phase==17));
}
static void host_texture_budget(void)
{
 if(!ff.active)return;++ff.budgets;if(ff.time_step)h.now+=ff.time_step;
 if(ff.budgets==ff.budget_fail)h.live=false;
 if(!ff.kind||ff.fired||ggfb_context.state!=1||ggfb_context.job!=ff.job||ggfb_context.phase!=ff.phase)return;
 ff.fired=1;uint32_t v=1;uint64_t q;
 switch(ff.kind){

 case 1:h.clock_bad=1;break;case 2:h.irq_bad=1;break;case 3:memcpy(reset_page+0x2000,&v,4);break;
 case 4:memcpy(smmu+0x48,&v,4);break;case 5:v=1u<<9;memcpy(core_page+4*0x201,&v,4);break;
 case 6:memcpy(core_page+4*0x823,&v,4);break;case 7:h.now=ggfb_deadline;break;case 8:h.now=ggfb_phase_end;break;
 case 9:ff.owner_bad=1;break;case 10:ggub_work.prefix_checked=14;ggub_context.work=ggub_work;break;
 case 11:gfw_context.dcvs_return=1;break;case 12:core_attr_bad=1;break;case 13:ggc_alias[0]++;break;
 case 14:h.context=1;break;case 15:q=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&q,8);break;
 case 16:v=1u<<24;memcpy(reset_page+0x2648,&v,4);break;case 17:ggc_work.mem_compared=1023;break;
 case 18:h.now=ggfb_last_now?ggfb_last_now-1:UINT64_MAX;break;
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
 case 65:ggvb_lifecycle=GMB_READY;break;case 66:ggvb_context.state=2;break;
 case 67:ggvb_context.phase=GGV_SEAL;break;case 68:ggb_data_mode=10;break;case 69:z.flag=10;break;
 default:CHECK(false);
 }
}
static void host_texture_device(unsigned job)
{
 CHECK(job<3&&ff.j[job].accepted&&!ff.j[job].device_done&&ff.j[job].submits&&ff.j[job].kept);ff.j[job].device_done=1;
 for(unsigned j=0;j<=job;j++)CHECK(!memcmp(ram+0xa8000+4*(20+7*j),texture_direct,sizeof(texture_direct)));
 for(unsigned i=0;i<2752;i++){uint32_t v;memcpy(&v,ram+0xa8000+texture_offsets[i],4);CHECK(v==texture_values[job][i]);}
 CHECK(ggfb_context.work.completed_jobs==job);
 for(unsigned i=0;i<256;i++){
  uint32_t v=texture_device_pixel(job,i);
  if(!ff.j[job].drop_pixels&&ff.j[job].drop_data!=i+1)memcpy(ram+0xb8000+4*i,&v,4);
  ++ff.j[job].device_writes;
 }
}
static void host_texture_event(unsigned job)
{
 CHECK(job<3&&ff.j[job].device_done&&!ff.j[job].eop_done&&ff.j[job].submits&&!ff.j[job].kept);unsigned events=0;
 const uint32_t *ib=texture174_blobs[job][0].data;
 for(unsigned i=0;i+4<203;i++)if(ib[i]==0x70460004){
  CHECK(!(ib[i+1]&0xc0000000u)&&ib[i+2]==0xfc018c00u&&!ib[i+3]&&ib[i+4]==16*job+(++events));
 }
 CHECK(events==6);uint32_t value=ff.j[job].bad_eop?ff.j[job].bad_eop:16*job+6;
 memcpy(ram+0xb8c00,&value,4);ff.j[job].eop_done=1;ff.j[job].device_writes+=6;
 if(ff.corrupt_data&&ff.job==job){CHECK(ff.corrupt_data<=1024);ram[0xb8000+4*(ff.corrupt_data-1)]^=1;}
}
static void host_texture_read(vm_offset_t address,uint32_t *value)
{
 if(!ff.active)return;CHECK(host_texture_active());unsigned job=ggfb_context.job;CHECK(job<3);++ff.reads;
 if(address==(uintptr_t)fw_page[0]+0x2c4c){
  *value=ff.j[job].fences++<ff.j[job].drop?3:2;
  if(!(*value&1)){ff.j[job].accepted=1;if(!ff.j[job].device_done)host_texture_device(job);}
 }
 if(address==(uintptr_t)fw_page[0]+0x2c30)*value=ggfb_context.phase==GGF_WAIT&&ff.j[job].busy_reads++<ff.j[job].busy_delay?0x71800000:0x71000000;
 if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
  unsigned n=ff.j[job].counter_reads++;*value=!ff.j[job].wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
   n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
 }
 bool ring=address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb0000;
 bool scratch=address==(uintptr_t)ram+0xb0000;
 bool data=address>=(uintptr_t)ram+0xb8000&&address<(uintptr_t)ram+0xb9000;
 if(ring||scratch||data){
  ++ff.memreads;
  if(ggfb_context.phase==GGF_WAIT&&scratch){
   CHECK(ff.j[job].accepted&&ff.j[job].submits&&!ff.j[job].kept&&ff.j[job].device_done);
   if(ff.j[job].shadow_reads++>=ff.j[job].shadow_delay){*value=ff.j[job].bad_shadow?ff.j[job].bad_shadow:27+7*job;memcpy(ram+0xb0000,value,4);}
  }
  if(ggfb_context.phase==GGF_WAIT&&data){
   CHECK((address==(uintptr_t)ram+0xb8c00||address==(uintptr_t)ram+0xb8c04)&&ff.j[job].device_done&&!ff.j[job].kept&&ff.j[job].shadow_reads);
   if(address==(uintptr_t)ram+0xb8c00&&ggfb_context.work.job[job].wait_samples==ggfb_context.work.job[job].idle_polls){
    if(ff.j[job].eop_reads++>=ff.j[job].eop_delay&&!ff.j[job].drop_eop&&!ff.j[job].eop_done)host_texture_event(job);
   }
   memcpy(value,(void *)address,4);
  }
  unsigned mem=ring?GGF_RING:scratch?GGF_SCRATCH:GGF_DATA;
  unsigned off=(unsigned)(address-(uintptr_t)ram-(ring?0xa8000:scratch?0xb0000:0xb8000));
  if(job==ff.job&&ggfb_context.phase==ff.corrupt_phase&&mem==ff.corrupt_mem&&off==ff.corrupt_off)*value^=1;
 }
}
static bool host_texture_store(vm_offset_t address,uint32_t value)
{
 if(!ff.active)return false;CHECK(host_texture_active());unsigned job=ggfb_context.job;CHECK(job<3);++ff.stores;
 if(address>=(uintptr_t)ram&&address<(uintptr_t)ram+sizeof(ram)){
  CHECK(ggfb_context.phase==GGF_COMMANDS&&ff.j[job].memstores<2759);unsigned index=ff.j[job].memstores;
  unsigned off=index<2752?texture_offsets[index]:4*(20+7*job+index-2752);
  uint32_t expected=index<2752?texture_values[job][index]:texture_direct[index-2752];
  CHECK(address==(uintptr_t)ram+0xa8000+off&&value==expected);++ff.j[job].memstores;++ff.memstores;
  if(ff.memstores!=ff.drop_write)memcpy((void *)address,&value,4);
  if(ff.trace)printf("N %u %u %u %08x\n",job,GGF_RING,off/4,value);
 }else{
  uint32_t reg=host_core_reg(address);CHECK(ggfb_context.phase==GGF_SUBMIT&&ggf_register_allowed(reg,true)&&ff.j[job].memstores==2759&&ggfb_context.work.job[job].commands_checked==7&&ggfb_context.work.job[job].artifact_checked==2752);
  if(reg==0x807){CHECK(value==27+7*job&&ff.j[job].kept);++ff.j[job].submits;}else{CHECK(value<=1);ff.j[job].kept=value;}
  memcpy((void *)address,&value,4);if(ff.trace)printf("W %u %05x %08x\n",job,reg,value);
 }
 if(ff.stores==ff.stop_store)h.clock_bad=1;if(ff.stores==ff.expire_store)h.now=ggfb_phase_end;
 return true;
}
static void texture_signed_setup(void)
{
 fixture_gpu_mode=11;cp_setup(0);fixture_gpu_mode=0;
 struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
 CHECK(z.flag==11&&ggb_data_selected==1&&ggb_data_ready==1&&ggb_smmu.layout==GGS_DATA19&&ggb_smmu.gpu_pages==19&&ggb_smmu.translations==171);
 CHECK(ggd_tables_match(&ggb_data_plan,ram+0x9c000,16384));
 for(unsigned i=0xb8000;i<0xbc000;i++)CHECK(ram[i]==0);
 struct gpz_receipt signed_load;CHECK(sweet_gpu_zap_once(&signed_load)==GPZ_OK);cp_active=0;u.active=1;
 CHECK(!mprotect(ram,16384,PROT_NONE));
}
static void texture_setup(void)
{texture_signed_setup();unsecure_good();u.active=0;ff.active=1;}
static void texture_untouched(void)
{
 CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60)&&!memcmp(ram+0xa8000+60,ggub_context.command.word,20));
 for(unsigned i=41;i<8192;i++)if(!texture_artifact(4*i)){uint32_t v;memcpy(&v,ram+0xa8000+4*i,4);CHECK(v==0xaaaaaaaa);}
 for(unsigned i=1;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb0000+4*i,4);CHECK(!v);}
 for(unsigned i=0xb9000;i<0xbc000;i++)CHECK(!ram[i]);
}
static void texture_failed(void)
{
 struct ggf_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 CHECK(sweet_gpu_texture_once(&out)!=GGF_OK&&!memcmp(&out,&saved,sizeof(out))&&ff.partial==1&&!ff.complete);
 CHECK(sweet_gpu_texture_state()==GMB_QUARANTINED&&sweet_gpu_varying_state()==GMB_QUARANTINED&&ggvb_context.state==3&&sweet_gpu_sequence_state()==GMB_QUARANTINED&&ggjb_context.state==3&&sweet_gpu_draw_state()==GMB_QUARANTINED&&ggtb_context.state==3&&sweet_gpu_clear_state()==GMB_QUARANTINED&&gglb_context.state==3&&sweet_gpu_write_state()==GMB_QUARANTINED&&ggwb_context.state==3&&sweet_gpu_ib_state()==GMB_QUARANTINED&&ggib_context.state==3&&sweet_gpu_compute_state()==GMB_QUARANTINED&&ggkb_context.state==3&&sweet_gpu_eop_state()==GMB_QUARANTINED&&ggeb_context.state==3&&sweet_gpu_unsecure_state()==GMB_QUARANTINED&&ggub_context.state==3&&sweet_gpu_zap_state()==GMB_QUARANTINED&&sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
 unsigned reads=ff.reads,stores=ff.stores,budgets=ff.budgets;
 CHECK(sweet_gpu_texture_once(&out)==(z.flag==11?GGF_ALREADY:GGF_ARGUMENT)&&!memcmp(&out,&saved,sizeof(out))&&reads==ff.reads&&stores==ff.stores&&budgets==ff.budgets);texture_untouched();
}
static void texture_good(void)
{
 struct ggf_receipt out;unsigned maps=h.maps,nc=h.nc_maps,owner_calls=h.owner_calls;
 enum ggf_result rc=sweet_gpu_texture_once(&out);
 if(rc!=GGF_OK)fprintf(stderr,"Sequence refusal rc=%u job=%u phase=%u reason=%u step=%u mode=%u/%u sample=%u/%05x expected=%08x actual=%08x stores=%u memstores=%u memreads=%u\n",rc,ggfb_context.job,ggfb_context.phase,ggfb_diagnostic.reason,ggfb_phase,ggb_data_mode,z.flag,ggfb_context.diagnostic.memory,ggfb_context.diagnostic.reg,ggfb_context.diagnostic.expected,ggfb_context.diagnostic.actual,ff.stores,ff.memstores,ff.memreads);
 CHECK(rc==GGF_OK&&sweet_gpu_texture_state()==GMB_READY&&ff.complete==1&&!ff.partial&&h.live&&!h.quarantine);
 CHECK(out.complete==1&&out.sealed==1&&out.requests_retained==1&&out.completed_jobs==3&&ff.memstores==8277&&ggfb_phase==17&&ggfb_diagnostic.reason==FGD_NONE);
 unsigned extra=0;
 for(unsigned job=0;job<3;job++){
  const struct ggf_job_receipt *r=&out.job[job];
  CHECK(r->complete==1&&r->prefix_checked==20+7*job&&r->clean_checked==7&&r->commands_written==7&&r->commands_checked==7);
  CHECK(r->artifact_before_checked==2752&&r->artifact_written==2752&&r->artifact_checked==2752&&r->artifact_after_checked==2752);
  CHECK(r->initial_wptr==20+7*job&&r->initial_shadow==20+7*job&&r->rptr==27+7*job&&r->writes==ff.j[job].drop+3&&r->fence_checks==ff.j[job].drop+1&&ff.j[job].memstores==2759&&ff.j[job].submits==ff.j[job].drop+1&&!ff.j[job].kept);
  CHECK(r->data_before_checked==1024&&r->data_after_checked==1024&&r->pixels_checked==256&&r->foreground_checked==256&&r->background_checked==0&&r->unchanged_checked==767&&r->eop_checked==1&&r->eop_complete==1&&r->eop_value==16*job+6&&r->eop_polls==ff.j[job].eop_delay+1&&r->ring_after_checked==27+7*job&&r->max_nc_batch_words==64);
  CHECK(ggfb_aux_mask[job]==63&&ggfb_before_control[job]==(job?16*(job-1)+6:0)&&ggfb_after_control[job]==16*job+6&&!ggfb_before_hi[job]&&!ggfb_before_tail[job]&&!ggfb_after_hi[job]&&!ggfb_after_tail[job]);
  for(unsigned i=0;i<8;i++)CHECK(ggfb_before_mask[job][i]==UINT32_MAX&&ggfb_after_mask[job][i]==UINT32_MAX);
  for(unsigned i=0;i<256;i++)CHECK(ggfb_before[job][i]==(job?texture_written(job-1,i):0)&&ggfb_after[job][i]==texture_written(job,i));
  CHECK(r->wait_samples==r->idle_polls&&r->wait_samples==ff.j[job].shadow_reads&&!r->wait_control_hi&&ff.j[job].device_writes==262);
  extra+=3*ff.j[job].shadow_reads+ff.j[job].eop_reads;
 }
 CHECK(ff.memreads==31140+extra&&h.maps==maps&&h.nc_maps==nc&&h.owner_calls==owner_calls);
 for(unsigned i=0;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb8000+4*i,4);CHECK(v==(i<256?texture_written(2,i):texture_data(2,i)));}
 texture_untouched();unsigned reads=ff.reads,stores=ff.stores,budgets=ff.budgets;
 CHECK(sweet_gpu_texture_once(&out)==GGF_ALREADY&&reads==ff.reads&&stores==ff.stores&&budgets==ff.budgets);
}
static void texture_scenario(unsigned scenario,bool trace)
{
 texture_setup();ff.trace=trace;
 for(unsigned j=0;j<3;j++){
  ff.j[j].drop=scenario==1?1:scenario==2?100:scenario==3?199:0;ff.j[j].wrap=scenario==4;
  if(scenario==1)ff.j[j].shadow_delay=ff.j[j].busy_delay=ff.j[j].eop_delay=2;
 }
 texture_good();
}
static void gpu_texture_cases(void)
{
 unsigned first=cases;texture_golden();
 for(unsigned s=0;s<5;s++)texture_scenario(s,false);
 for(unsigned job=0;job<3;job++)for(unsigned phase=GGF_SEAL;phase<=GGF_FINAL;phase++){
  if((phase==GGF_SEAL&&job)||(phase==GGF_FINAL&&job!=2))continue;
  for(unsigned kind=1;kind<=69;kind++){texture_setup();ff.job=job;ff.phase=phase;ff.kind=kind;texture_failed();CHECK(ff.fired);}
 }
 /* Probe every guarded copy batch edge and all per-submit MMIO boundaries.
  * The portable core separately injects every callback and all8277 writes. */
 unsigned edges[2763]={0};unsigned n=0;
 for(unsigned id=0;id<31;id++){
  unsigned words=texture174_blobs[0][id].gpu_serialized_extent/4;
  for(unsigned base=0;base<words;base+=64){unsigned end=base+64;if(end>words)end=words;edges[n+base+1]=1;edges[n+end]=1;}
  n+=words;
 }
 CHECK(n==2752);for(unsigned i=1633;i<=2762;i++)edges[i]=1;
 for(unsigned job=0;job<3;job++)for(unsigned edge=1;edge<=2762;edge++)if(edges[edge]){
  texture_setup();ff.stop_store=job*2762+edge;texture_failed();CHECK(ff.stores>=ff.stop_store&&ff.stores-ff.stop_store<64);
  texture_setup();ff.expire_store=job*2762+edge;texture_failed();CHECK(ff.stores>=ff.expire_store&&ff.stores-ff.expire_store<64);
 }
 for(unsigned job=0;job<3;job++){
  for(unsigned phase=GGF_CAPTURE;phase<=GGF_VERIFY;phase++)if(phase==GGF_CAPTURE||phase==GGF_COMMANDS||phase==GGF_VERIFY){
   for(unsigned id=0;id<31;id++){
    const struct texture174_native_blob *b=&texture174_blobs[job][id];if(!b->words)continue;
    unsigned selected[]={0,b->words-1,b->gpu_serialized_extent/4-1};
    for(unsigned k=0;k<3;k++){texture_setup();ff.job=job;ff.corrupt_phase=phase;ff.corrupt_mem=GGF_RING;ff.corrupt_off=b->iova-0xfc008000u+4*selected[k];texture_failed();}
   }
  }
  const unsigned offsets[]={0,4,1020,2048,3072,3076,4092};
  for(unsigned phase=GGF_CAPTURE;phase<=GGF_VERIFY;phase++)if(phase==GGF_CAPTURE||phase==GGF_VERIFY)
   for(unsigned k=0;k<7;k++){texture_setup();ff.job=job;ff.corrupt_phase=phase;ff.corrupt_mem=GGF_DATA;ff.corrupt_off=offsets[k];texture_failed();}
  for(unsigned k=0;k<7;k++){texture_setup();ff.job=job;ff.corrupt_data=offsets[k]/4+1;if(offsets[k]<1024&&texture_declared(job,offsets[k]/4,texture_pixel(job,offsets[k]/4)^1u))texture_good();else texture_failed();}
  const unsigned pixels[]={0,3,4,63,64,68,143,244,255};
  for(unsigned k=0;k<9;k++){texture_setup();ff.j[job].drop_data=pixels[k]+1;if(texture_declared(job,pixels[k],job?texture_pixel(job-1,pixels[k]):0))texture_good();else texture_failed();}
  texture_setup();ff.j[job].drop_pixels=1;texture_failed();CHECK(ff.j[job].eop_done&&ggfb_context.work.job[job].eop_complete==1);
  texture_setup();ff.j[job].drop_eop=1;texture_failed();CHECK(ff.j[job].eop_reads==1024&&ff.j[job].device_writes==256&&!ff.j[job].kept);
  texture_setup();ff.j[job].bad_eop=16*job+7;texture_failed();
  texture_setup();ff.j[job].drop=200;texture_failed();CHECK(ff.j[job].kept&&ff.j[job].submits==201&&ff.j[job].fences==200);
  texture_setup();ff.j[job].bad_shadow=8192;texture_failed();
  for(unsigned off=3072;off<=3076;off+=4){texture_setup();ff.job=job;ff.corrupt_phase=GGF_WAIT;ff.corrupt_mem=GGF_DATA;ff.corrupt_off=off;texture_failed();}
 }
 for(unsigned n=0;n<8;n++)for(unsigned kind=1;kind<=2;kind++){texture_setup();ff.nc_kind=kind;ff.nc_page=n;texture_failed();CHECK(!ff.stores);}
 for(unsigned n=1;n<=8;n++){texture_setup();ff.phys_bad=n;texture_failed();CHECK(!ff.stores);}
 for(unsigned bit=0;bit<64;bit++){texture_setup();ram[0x9c000+0x2000+24*8+bit/8]^=1u<<(bit%8);texture_failed();CHECK(!ff.stores);}
 texture_setup();ff.budget_fail=1;texture_failed();CHECK(ggfb_diagnostic.reason==FGD_ENTRY_BUDGET&&!ff.stores&&!ff.memreads);
 texture_setup();ff.time_step=100000000;texture_failed();CHECK(ggfb_diagnostic.reason==FGD_TIME);
 for(unsigned mode=0;mode<=12;mode++)if(mode!=11){
  texture_setup();z.flag=(int)mode;struct ggf_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned budgets=h.budgets;
  CHECK(sweet_gpu_texture_once(&out)==GGF_ARGUMENT&&!memcmp(&out,&old,sizeof(out))&&ggfb_lifecycle==GMB_IDLE&&budgets==h.budgets&&!ff.stores);
 }
 for(unsigned mode=2;mode<=10;mode++){
  fixture_gpu_mode=mode;cp_setup(0);fixture_gpu_mode=0;struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
  struct gpz_receipt zap;CHECK(sweet_gpu_zap_once(&zap)==GPZ_OK);cp_active=0;u.active=1;CHECK(!mprotect(ram,16384,PROT_NONE));
  z.flag=11;unsecure_failed();CHECK(!u.stores);
 }
 for(unsigned job=0;job<3;job++)for(unsigned id=0;id<31;id++)for(unsigned field=0;field<4;field++){
  texture_setup();texture_good();ggfb_lifecycle=GMB_RUNNING;
  uint32_t *counts[]={ggfb_work.job[job].blob_before_checked,ggfb_work.job[job].blob_written,ggfb_work.job[job].blob_checked,ggfb_work.job[job].blob_after_checked};
  counts[field][id]^=1;ggfb_context.work=ggfb_work;CHECK(!ggfb_guard(NULL,2,GGF_FINAL)&&ggfb_diagnostic.reason==FGD_ENGINE);
 }
 for(unsigned job=0;job<3;job++)for(unsigned i=0;i<256;i+=17){
  texture_setup();texture_good();ggfb_lifecycle=GMB_RUNNING;ggfb_after[job][i]^=1;CHECK(!ggfb_guard(NULL,2,GGF_FINAL)&&ggfb_diagnostic.reason==FGD_ENGINE);
 }
 texture_setup();
 for(unsigned job=0;job<3;job++)for(unsigned phase=GGF_IDLE;phase<=GGF_DONE;phase++){
  ggfb_context.job=job;ggfb_context.phase=phase;
  for(unsigned mem=0;mem<=3;mem++)for(unsigned off=0;off<=32768;off+=4)for(unsigned write=0;write<=1;write++){
   bool ring=mem==GGF_RING&&off<4*(27+7*job),scratch=mem==GGF_SCRATCH&&!off,data=mem==GGF_DATA&&off<4096,cmd=ring&&off>=4*(20+7*job);
   bool artifact=mem==GGF_RING&&texture_artifact(off);
   bool allowed=write?(phase==GGF_COMMANDS&&(cmd||artifact)):
    ((phase==GGF_CAPTURE&&(ring||scratch||data||artifact))||(phase==GGF_COMMANDS&&(cmd||artifact))||
     (phase==GGF_WAIT&&(scratch||(data&&(off==3072||off==3076))))||(phase==GGF_VERIFY&&(ring||data||artifact)));
   CHECK(!!ggfb_memory((enum ggf_memory)mem,off,write)==allowed);
  }
 }
 ggfb_context.phase=GGF_IDLE;CHECK(!ggfb_memory(GGF_DATA,1,false)&&!ggfb_memory(GGF_RING,UINT32_MAX,false));
 ggfb_context.job=3;CHECK(!ggfb_memory(GGF_RING,80,true));ggfb_context.job=UINT32_MAX;CHECK(!ggfb_memory(GGF_DATA,0,false));
 CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));
 printf("GPU native texture live board: %u actual coldDATA19+CP+ZAP+GGU+GGF/three-job/PROT_NONE/owner/PTE/NC/phase/WDT/once cases PASS; MODEL only, no physical texture or Metal proof\n",cases-first);
}
