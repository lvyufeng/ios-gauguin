/* Actual mode8 provider with real signed/GGU/model prerequisites.
 * Explicit hostile hardware MODEL, never GPU/IR3 execution evidence.
 * The first secure CPU page remains PROT_NONE after original AUTH path. */
#include "gpu-draw/native_words.h"
static const uint32_t triangle_native_direct[7]={0x70bf8003,0xfc00c000,0,203,0x70620002,0xfc010000,0};
static unsigned triangle_offsets[1632],triangle_values[1632];
static const struct draw171_native_blob *triangle_blob(unsigned id)
{return id<24?&draw171_rings[id]:id<27?&draw171_programs[id-24]:NULL;}
static bool triangle_artifact(unsigned off)
{
 if(off&3)return false;
 for(unsigned id=0;id<27;id++){
  const struct draw171_native_blob *b=triangle_blob(id);
  if(b->words&&off>=b->iova-DRAW171_RING_BASE&&off-(b->iova-DRAW171_RING_BASE)<b->gpu_serialized_extent)return true;
 }
 return false;
}
static void triangle_golden(void)
{
 unsigned n=0;
 for(unsigned id=0;id<27;id++){
  const struct draw171_native_blob *b=triangle_blob(id);if(!b->words)continue;
  for(unsigned i=0;i<b->gpu_serialized_extent/4;i++){
   CHECK(n<1632);triangle_offsets[n]=b->iova-DRAW171_RING_BASE+4*i;
   triangle_values[n++]=i<b->words?b->data[i]:0;
  }
 }
 CHECK(n==1632);
}
/* Additional actual CP+ZAP+GGU+GGT integration; primitive hardware/owner seams
 * remain explicit. Secure first CPU page stays PROT_NONE after AUTH. */
static bool host_triangle_active(void)
{
 return tf.active&&z.auth_done&&z.flag==8&&sweet_gpu_draw_state()==GMB_RUNNING&&
  ((ggtb_context.state==1&&ggtb_context.phase>=GGT_SEAL&&ggtb_context.phase<=GGT_FINAL)||
   (ggtb_context.state==2&&ggtb_context.phase==GGT_DONE&&ggtb_phase==GGT_FINAL));
}
static void host_triangle_budget(void)
{
 if(!tf.active)return;++tf.budgets;if(tf.time_step)h.now+=tf.time_step;
 if(tf.budgets==tf.budget_fail)h.live=false;
 if(!tf.kind||tf.fired||ggtb_context.state!=1||ggtb_context.phase!=tf.phase)return;
 tf.fired=1;uint32_t v=1;uint64_t q;
 switch(tf.kind){
 case 1:h.clock_bad=1;break;case 2:h.irq_bad=1;break;case 3:memcpy(reset_page+0x2000,&v,4);break;
 case 4:memcpy(smmu+0x48,&v,4);break;case 5:v=1u<<9;memcpy(core_page+4*0x201,&v,4);break;
 case 6:memcpy(core_page+4*0x823,&v,4);break;case 7:h.now=ggtb_deadline;break;case 8:h.now=ggtb_phase_end;break;
 case 9:tf.owner_bad=1;break;case 10:ggub_work.prefix_checked=14;ggub_context.work=ggub_work;break;
 case 11:gfw_context.dcvs_return=1;break;case 12:core_attr_bad=1;break;case 13:ggc_alias[0]++;break;
 case 14:h.context=1;break;case 15:q=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&q,8);break;
 case 16:v=1u<<24;memcpy(reset_page+0x2648,&v,4);break;case 17:ggc_work.mem_compared=1023;break;
 case 18:h.now=ggtb_last_now?ggtb_last_now-1:UINT64_MAX;break;
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
 default:CHECK(false);
 }
}
static void host_triangle_device(void)
{
 CHECK(tf.accepted&&!tf.device_done&&tf.submits&&tf.kept);tf.device_done=1;
 CHECK(!memcmp(ram+0xa8000+80,triangle_native_direct,sizeof(triangle_native_direct)));
 for(unsigned i=0;i<1632;i++){
  uint32_t word;memcpy(&word,ram+0xa8000+triangle_offsets[i],4);CHECK(word==triangle_values[i]);
 }
 for(unsigned i=0;i<256;i++){
  uint32_t word=0xff00ff00u;if(!tf.drop_pixels&&tf.drop_data!=i+1)memcpy(ram+0xb8000+4*i,&word,4);++tf.device_writes;
 }
}
static void host_triangle_event(void)
{
 CHECK(tf.device_done&&!tf.eop_done&&tf.submits&&!tf.kept);unsigned events=0;
 for(unsigned i=0;i+4<203;i++)if(draw171_ring_00[i]==0x70460004){
  CHECK(!(draw171_ring_00[i+1]&0xc0000000u)&&draw171_ring_00[i+2]==0xfc018c00u&&!draw171_ring_00[i+3]&&draw171_ring_00[i+4]==++events);
 }
 CHECK(events==6);uint32_t value=tf.bad_eop?tf.bad_eop:6;
 memcpy(ram+0xb8c00,&value,4);tf.eop_done=1;tf.device_writes+=6;
 if(tf.corrupt_data){CHECK(tf.corrupt_data<=1024);ram[0xb8000+4*(tf.corrupt_data-1)]^=1;}
}
static void host_triangle_read(vm_offset_t address,uint32_t *value)
{
 if(!tf.active)return;CHECK(host_triangle_active());++tf.reads;
 if(address==(uintptr_t)fw_page[0]+0x2c4c){
  *value=tf.fences++<tf.drop?3:2;if(!(*value&1)){tf.accepted=1;if(!tf.device_done)host_triangle_device();}
 }
 if(address==(uintptr_t)fw_page[0]+0x2c30)*value=ggtb_context.phase==GGT_WAIT&&tf.busy_reads++<tf.busy_delay?0x71800000:0x71000000;
 if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
  unsigned n=tf.counter_reads++;*value=!tf.wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
   n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
 }
 bool ring=address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb0000;
 bool scratch=address==(uintptr_t)ram+0xb0000;
 bool data=address>=(uintptr_t)ram+0xb8000&&address<(uintptr_t)ram+0xb9000;
 if(ring||scratch||data){
  ++tf.memreads;
  if(ggtb_context.phase==GGT_WAIT&&scratch){CHECK(scratch&&tf.accepted&&tf.submits&&!tf.kept&&tf.device_done);
   if(tf.shadow_reads++>=tf.shadow_delay){*value=tf.bad_shadow?tf.bad_shadow:27;memcpy(ram+0xb0000,value,4);}}
  if(ggtb_context.phase==GGT_WAIT&&data){
   CHECK((address==(uintptr_t)ram+0xb8c00||address==(uintptr_t)ram+0xb8c04)&&tf.device_done&&!tf.kept&&tf.shadow_reads);
   if(address==(uintptr_t)ram+0xb8c00&&ggtb_context.work.wait_samples==ggtb_context.work.idle_polls){
    if(tf.eop_reads++>=tf.eop_delay&&!tf.drop_eop&&!tf.eop_done)host_triangle_event();
   }
   memcpy(value,(void *)address,4);
  }
  unsigned mem=ring?GGT_RING:scratch?GGT_SCRATCH:GGT_DATA;
  unsigned off=(unsigned)(address-(uintptr_t)ram-(ring?0xa8000:scratch?0xb0000:0xb8000));
  if(ggtb_context.phase==tf.corrupt_phase&&mem==tf.corrupt_mem&&off==tf.corrupt_off)*value^=1;
 }
}
static bool host_triangle_store(vm_offset_t address,uint32_t value)
{
 if(!tf.active)return false;CHECK(host_triangle_active());++tf.stores;
 if(address>=(uintptr_t)ram&&address<(uintptr_t)ram+sizeof(ram)){
  CHECK(ggtb_context.phase==GGT_COMMANDS&&tf.memstores<1639);unsigned index=tf.memstores;
  unsigned off=index<1632?triangle_offsets[index]:80+4*(index-1632);
  uint32_t expected=index<1632?triangle_values[index]:triangle_native_direct[index-1632];
  CHECK(address==(uintptr_t)ram+0xa8000+off&&value==expected);
  ++tf.memstores;if(tf.memstores!=tf.drop_write)memcpy((void *)address,&value,4);
 }else{
  uint32_t reg=host_core_reg(address);CHECK(ggtb_context.phase==GGT_SUBMIT&&ggt_register_allowed(reg,true)&&tf.memstores==1639&&ggtb_context.work.commands_checked==7&&ggtb_context.work.artifact_checked==1632);
  if(reg==0x807){CHECK(value==27&&tf.kept);++tf.submits;}else{CHECK(value<=1);tf.kept=value;}
  memcpy((void *)address,&value,4);
 }
 if(tf.stores==tf.stop_store)h.clock_bad=1;if(tf.stores==tf.expire_store)h.now=ggtb_phase_end;
 return true;
}
static void triangle_signed_setup(void)
{
 fixture_gpu_mode=8;cp_setup(0);fixture_gpu_mode=0;
 struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
 CHECK(z.flag==8&&ggb_data_selected==1&&ggb_data_ready==1&&ggb_smmu.layout==GGS_DATA19&&ggb_smmu.gpu_pages==19&&ggb_smmu.translations==171);
 CHECK(ggd_tables_match(&ggb_data_plan,ram+0x9c000,16384));
 for(unsigned i=0xb8000;i<0xbc000;i++)CHECK(ram[i]==0);
 struct gpz_receipt signed_load;CHECK(sweet_gpu_zap_once(&signed_load)==GPZ_OK);cp_active=0;u.active=1;
 CHECK(!mprotect(ram,16384,PROT_NONE));
}
static void triangle_setup(void)
{
 triangle_signed_setup();unsecure_good();u.active=0;tf.active=1;
 CHECK(ggub_context.state==2&&ggub_work.rptr==20&&ggtb_lifecycle==GMB_IDLE&&ggtb_context.state==0);
}
static void triangle_untouched(void)
{
 CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60)&&!memcmp(ram+0xa8000+60,ggub_context.command.word,20));
 for(unsigned i=27;i<8192;i++)if(!triangle_artifact(4*i)){uint32_t value;memcpy(&value,ram+0xa8000+4*i,4);CHECK(value==0xaaaaaaaa);}
 for(unsigned i=1;i<1024;i++){uint32_t value;memcpy(&value,ram+0xb0000+4*i,4);CHECK(!value);}
 for(unsigned i=0xb9000;i<0xbc000;i++)CHECK(!ram[i]);
}
static void triangle_failed(void)
{
 struct ggt_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 CHECK(sweet_gpu_draw_once(&out)!=GGT_OK&&!memcmp(&out,&saved,sizeof(out))&&tf.partial==1&&!tf.complete);
 CHECK(sweet_gpu_draw_state()==GMB_QUARANTINED&&sweet_gpu_clear_state()==GMB_QUARANTINED&&gglb_context.state==3&&sweet_gpu_write_state()==GMB_QUARANTINED&&ggwb_context.state==3&&sweet_gpu_ib_state()==GMB_QUARANTINED&&ggib_context.state==3&&sweet_gpu_compute_state()==GMB_QUARANTINED&&ggkb_context.state==3&&sweet_gpu_eop_state()==GMB_QUARANTINED&&ggeb_context.state==3&&sweet_gpu_unsecure_state()==GMB_QUARANTINED&&ggub_context.state==3&&
  sweet_gpu_zap_state()==GMB_QUARANTINED&&sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&
  sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&
  z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
 unsigned reads=tf.reads,stores=tf.stores,budgets=tf.budgets;
 CHECK(sweet_gpu_draw_once(&out)==(z.flag==8?GGT_ALREADY:GGT_ARGUMENT)&&!memcmp(&out,&saved,sizeof(out))&&reads==tf.reads&&stores==tf.stores&&budgets==tf.budgets);
 triangle_untouched();
}
static void triangle_good(void)
{
 struct ggt_receipt out;unsigned maps=h.maps,nc=h.nc_maps,owner_calls=h.owner_calls;
 enum ggt_result rc=sweet_gpu_draw_once(&out);
 if(rc!=GGT_OK)fprintf(stderr,"Triangle refusal rc=%u phase=%u reason=%u guard_phase=%u mode=%u/%u sample=%u/%05x expected=%08x actual=%08x stores=%u memstores=%u memreads=%u\n",rc,ggtb_context.phase,ggtb_diagnostic.reason,ggtb_diagnostic.phase,ggb_data_mode,z.flag,ggtb_context.diagnostic.memory,ggtb_context.diagnostic.reg,ggtb_context.diagnostic.expected,ggtb_context.diagnostic.actual,tf.stores,tf.memstores,tf.memreads);
 CHECK(rc==GGT_OK&&sweet_gpu_draw_state()==GMB_READY&&tf.complete==1&&!tf.partial&&h.live&&!h.quarantine);
 CHECK(out.complete==1&&out.sealed==1&&out.requests_retained==1&&out.prefix_checked==20&&out.clean_checked==7&&out.commands_written==7&&out.commands_checked==7);
 CHECK(out.artifact_clean_checked==1632&&out.artifact_written==1632&&out.artifact_checked==1632&&out.artifact_after_checked==1632);
 for(unsigned id=0;id<27;id++){
  unsigned words=triangle_blob(id)->gpu_serialized_extent/4;
  CHECK(out.blob_clean_checked[id]==words&&out.blob_written[id]==words&&out.blob_checked[id]==words&&out.blob_after_checked[id]==words);
 }
 CHECK(out.initial_wptr==20&&out.initial_shadow==20&&out.rptr==27&&out.writes==tf.drop+3&&out.fence_checks==tf.drop+1&&tf.memstores==1639&&tf.submits==tf.drop+1&&!tf.kept);
 CHECK(out.data_before_checked==1024&&out.data_after_checked==1024&&out.pixels_checked==256&&out.foreground_checked==256&&!out.background_checked&&out.unchanged_checked==767&&out.eop_checked==1&&out.eop_complete==1&&out.eop_value==6&&out.eop_polls==tf.eop_delay+1&&out.ring_after_checked==27&&out.max_nc_batch_words==64);
 CHECK(ggtb_aux_mask==63&&!ggtb_before_control&&!ggtb_before_hi&&!ggtb_before_tail&&ggtb_after_control==6&&!ggtb_after_hi&&!ggtb_after_tail&&ggtb_diagnostic.reason==TGD_NONE);
 for(unsigned i=0;i<8;i++)CHECK(ggtb_before_mask[i]==UINT32_MAX&&ggtb_after_mask[i]==UINT32_MAX);
 for(unsigned i=0;i<256;i++)CHECK(!ggtb_before[i]&&ggtb_after[i]==0xff00ff00u);
 CHECK(out.wait_samples==out.idle_polls&&out.wait_samples==tf.shadow_reads&&!out.wait_control_hi);
 CHECK(tf.memreads==7006+3*tf.shadow_reads+tf.eop_reads&&tf.device_writes==262&&h.maps==maps&&h.nc_maps==nc&&h.owner_calls==owner_calls);
 for(unsigned i=0;i<1024;i++){uint32_t value;memcpy(&value,ram+0xb8000+4*i,4);CHECK(value==(i<256?0xff00ff00u:i==768?6u:0u));}
 triangle_untouched();unsigned reads=tf.reads,stores=tf.stores,budgets=tf.budgets;
 CHECK(sweet_gpu_draw_once(&out)==GGT_ALREADY&&reads==tf.reads&&stores==tf.stores&&budgets==tf.budgets);
}
static void gpu_triangle_cases(void)
{
 unsigned first=cases;triangle_golden();
 for(unsigned scenario=0;scenario<5;scenario++){
  triangle_setup();tf.drop=scenario==1?1:scenario==2?100:scenario==3?199:0;tf.wrap=scenario==4;
  if(scenario==1)tf.shadow_delay=tf.busy_delay=tf.eop_delay=2;triangle_good();
 }
 for(unsigned phase=GGT_SEAL;phase<=GGT_FINAL;phase++)for(unsigned kind=1;kind<=54;kind++){
  triangle_setup();tf.phase=phase;tf.kind=kind;triangle_failed();CHECK(tf.fired);
 }
 for(unsigned n=1;n<=1642;n++){
  triangle_setup();tf.stop_store=n;triangle_failed();CHECK(tf.stores>=n&&tf.stores-n<64&&(n<=1639||tf.stores==n));
  triangle_setup();tf.expire_store=n;triangle_failed();CHECK(tf.stores>=n&&tf.stores-n<64&&(n<=1639||tf.stores==n));
 }
 for(unsigned n=1;n<=1639;n++){triangle_setup();tf.drop_write=n;triangle_failed();CHECK(!tf.submits);}
 for(unsigned phase=GGT_CAPTURE;phase<=GGT_VERIFY;phase++)if(phase==GGT_CAPTURE||phase==GGT_COMMANDS||phase==GGT_VERIFY)
  for(unsigned n=0;n<1632;n++){triangle_setup();tf.corrupt_phase=phase;tf.corrupt_mem=GGT_RING;tf.corrupt_off=triangle_offsets[n];triangle_failed();}
 const unsigned offsets[]={0,4,1020,2048,3072,3076,4092};
 for(unsigned phase=GGT_CAPTURE;phase<=GGT_VERIFY;phase++)if(phase==GGT_CAPTURE||phase==GGT_VERIFY)
  for(unsigned n=0;n<7;n++){triangle_setup();tf.corrupt_phase=phase;tf.corrupt_mem=GGT_DATA;tf.corrupt_off=offsets[n];triangle_failed();}
 for(unsigned n=0;n<7;n++){triangle_setup();tf.corrupt_data=offsets[n]/4+1;triangle_failed();}
 for(unsigned n=1;n<=256;n++){triangle_setup();tf.drop_data=n;triangle_failed();}
 for(unsigned n=0;n<8;n++)for(unsigned kind=1;kind<=2;kind++){triangle_setup();tf.nc_kind=kind;tf.nc_page=n;triangle_failed();CHECK(!tf.stores);}
 for(unsigned n=1;n<=8;n++){triangle_setup();tf.phys_bad=n;triangle_failed();CHECK(!tf.stores);}
 for(unsigned bit=0;bit<64;bit++){
  triangle_setup();ram[0x9c000+0x2000+24*8+bit/8]^=1u<<(bit%8);triangle_failed();CHECK(!tf.stores);
 }
 for(unsigned delay=1;delay<=8;delay*=2){triangle_setup();tf.eop_delay=delay;triangle_good();}
 triangle_setup();tf.drop_eop=1;triangle_failed();CHECK(tf.eop_reads==1024&&tf.shadow_reads&&tf.device_writes==256&&!tf.kept);
 const unsigned wrong[]={1,5,7,0x0cf49802u,UINT32_MAX};
 for(unsigned i=0;i<5;i++){triangle_setup();tf.bad_eop=wrong[i];triangle_failed();CHECK(tf.eop_reads==1);}
 for(unsigned off=3072;off<=3076;off+=4){triangle_setup();tf.corrupt_phase=GGT_WAIT;tf.corrupt_mem=GGT_DATA;tf.corrupt_off=off;triangle_failed();}
 triangle_setup();tf.drop=200;triangle_failed();CHECK(tf.kept&&tf.submits==201&&tf.fences==200);
 triangle_setup();tf.bad_shadow=8192;triangle_failed();
 triangle_setup();tf.budget_fail=1;triangle_failed();CHECK(ggtb_diagnostic.reason==TGD_ENTRY_BUDGET&&!tf.stores&&!tf.memreads);
 triangle_setup();tf.time_step=100000000;triangle_failed();CHECK(ggtb_diagnostic.reason==TGD_TIME);
 triangle_setup();tf.drop_pixels=1;triangle_failed();CHECK(tf.eop_done&&ggtb_context.work.eop_complete==1);
 /* No late caller mode switch may upgrade any earlier cold mode. */
 unsecure_setup();z.flag=8;unsecure_failed();CHECK(!u.stores);
 write_signed_setup();z.flag=8;unsecure_failed();CHECK(!u.stores);
 ib_signed_setup();z.flag=8;unsecure_failed();CHECK(!u.stores);
 eop_signed_setup();z.flag=8;unsecure_failed();CHECK(!u.stores);
 compute_signed_setup();z.flag=8;unsecure_failed();CHECK(!u.stores);
 clear_signed_setup();z.flag=8;unsecure_failed();CHECK(!u.stores);
 triangle_signed_setup();z.flag=7;unsecure_failed();CHECK(!u.stores);
 triangle_signed_setup();ram[0x9c000+0x2000+24*8]^=0x40;unsecure_failed();CHECK(!u.stores);
 for(unsigned mode=0;mode<=9;mode++)if(mode!=8){
  triangle_setup();z.flag=(int)mode;struct ggt_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned budgets=h.budgets;
  CHECK(sweet_gpu_draw_once(&out)==GGT_ARGUMENT&&!memcmp(&out,&old,sizeof(out))&&ggtb_lifecycle==GMB_IDLE&&budgets==h.budgets&&!tf.stores);
 }
 /* Corrupt both copies of a final per-blob receipt to bypass the memcmp;
  * source-derived native expected counts must still reject the forgery. */
 for(unsigned id=0;id<27;id++)for(unsigned field=0;field<4;field++){
  triangle_setup();triangle_good();ggtb_lifecycle=GMB_RUNNING;
  uint32_t *counts[]={ggtb_work.blob_clean_checked,ggtb_work.blob_written,ggtb_work.blob_checked,ggtb_work.blob_after_checked};
  counts[field][id]^=1;ggtb_context.work=ggtb_work;
  CHECK(!ggtb_guard(NULL,GGT_FINAL)&&ggtb_diagnostic.reason==TGD_ENGINE);
 }
 triangle_setup();
 for(unsigned phase=GGT_IDLE;phase<=GGT_DONE;phase++){
  ggtb_context.phase=phase;
  for(unsigned mem=0;mem<=3;mem++)for(unsigned off=0;off<=32768;off+=4)for(unsigned write=0;write<=1;write++){
   bool ring=mem==GGT_RING&&off<108,scratch=mem==GGT_SCRATCH&&!off,data=mem==GGT_DATA&&off<4096,cmd=ring&&off>=80;
   bool artifact=mem==GGT_RING&&triangle_artifact(off);
   bool allowed=write?(phase==GGT_COMMANDS&&(cmd||artifact)):
    ((phase==GGT_CAPTURE&&(ring||scratch||data||artifact))||(phase==GGT_COMMANDS&&(cmd||artifact))||
     (phase==GGT_WAIT&&(scratch||(data&&(off==3072||off==3076))))||(phase==GGT_VERIFY&&(ring||data||artifact)));
   CHECK(!!ggtb_memory((enum ggt_memory)mem,off,write)==allowed);
  }
 }
 ggtb_context.phase=GGT_IDLE;CHECK(!ggtb_memory(GGT_DATA,1,false)&&!ggtb_memory(GGT_RING,UINT32_MAX,false));
 CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));
 printf("GPU native triangle live board: %u actual coldDATA19+CP+ZAP+GGU+GGT/PROT_NONE/fault/PTE/NC/private-parent/once cases PASS; source/model only, no physical triangle/Metal proof\n",cases-first);
}
