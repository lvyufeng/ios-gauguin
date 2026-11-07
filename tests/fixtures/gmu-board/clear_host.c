/* Actual clear provider + complete signed/GGU prerequisites. Typed GPU
 * model only; secure first CPU page remains PROT_NONE after AUTH. */
#define command clear_native_direct
#define indirect clear_native_ib
#define restore clear_native_restore
#define preamble clear_native_preamble
#define expected_page clear_expected_page
#include "gpu-clear/native_words.h"
#undef expected_page
#undef command
#undef indirect
#undef restore
#undef preamble
/* Additional actual CP+ZAP+GGU+GGL integration; primitive hardware/owner seams
 * remain explicit. Secure first CPU page stays PROT_NONE after AUTH. */
static bool host_clear_active(void)
{
 return lf.active&&z.auth_done&&z.flag==7&&sweet_gpu_clear_state()==GMB_RUNNING&&
  ((gglb_context.state==1&&gglb_context.phase>=GGL_SEAL&&gglb_context.phase<=GGL_FINAL)||
   (gglb_context.state==2&&gglb_context.phase==GGL_DONE&&gglb_phase==GGL_FINAL));
}
static void host_clear_budget(void)
{
 if(!lf.active)return;++lf.budgets;if(lf.time_step)h.now+=lf.time_step;
 if(lf.budgets==lf.budget_fail)h.live=false;
 if(!lf.kind||lf.fired||gglb_context.state!=1||gglb_context.phase!=lf.phase)return;
 lf.fired=1;uint32_t v=1;uint64_t q;
 switch(lf.kind){
 case 1:h.clock_bad=1;break;case 2:h.irq_bad=1;break;case 3:memcpy(reset_page+0x2000,&v,4);break;
 case 4:memcpy(smmu+0x48,&v,4);break;case 5:v=1u<<9;memcpy(core_page+4*0x201,&v,4);break;
 case 6:memcpy(core_page+4*0x823,&v,4);break;case 7:h.now=gglb_deadline;break;case 8:h.now=gglb_phase_end;break;
 case 9:lf.owner_bad=1;break;case 10:ggub_work.prefix_checked=14;ggub_context.work=ggub_work;break;
 case 11:gfw_context.dcvs_return=1;break;case 12:core_attr_bad=1;break;case 13:ggc_alias[0]++;break;
 case 14:h.context=1;break;case 15:q=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&q,8);break;
 case 16:v=1u<<24;memcpy(reset_page+0x2648,&v,4);break;case 17:ggc_work.mem_compared=1023;break;
 case 18:h.now=gglb_last_now?gglb_last_now-1:UINT64_MAX;break;
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
 default:CHECK(false);
 }
}
static void host_clear_device(void)
{
 CHECK(lf.accepted&&!lf.device_done&&lf.submits&&lf.kept);lf.device_done=1;
 CHECK(!memcmp(ram+0xa8000+80,clear_native_direct,sizeof(clear_native_direct)));
 CHECK(!memcmp(ram+0xac000,clear_native_ib,sizeof(clear_native_ib)));
 CHECK(!memcmp(ram+0xad000,clear_native_restore,sizeof(clear_native_restore)));
 CHECK(!memcmp(ram+0xae000,clear_native_preamble,sizeof(clear_native_preamble)));
 for(unsigned id=0;id<256;id++){
  if(!lf.drop_pixels&&lf.drop_data!=id+1)memcpy(ram+0xb8000+4*id,&clear_expected_page[id],4);++lf.device_writes;
 }
}
static void host_clear_event(void)
{
 CHECK(lf.device_done&&!lf.eop_done&&lf.submits&&!lf.kept);
 unsigned events=0;
 for(unsigned i=0;i+4<149;i++)if(clear_native_ib[i]==0x70460004){
  CHECK((clear_native_ib[i+1]&0xc0000000u)==0x40000000u&&clear_native_ib[i+2]==0xfc018c00u&&clear_native_ib[i+3]==0&&clear_native_ib[i+4]==++events);
 }
 CHECK(events==7);uint32_t value=lf.bad_eop?lf.bad_eop:7;
 memcpy(ram+0xb8c00,&value,4);lf.eop_done=1;lf.device_writes+=7;
 if(lf.corrupt_data){CHECK(lf.corrupt_data<=1024);ram[0xb8000+4*(lf.corrupt_data-1)]^=1;}
}
static void host_clear_read(vm_offset_t address,uint32_t *value)
{
 if(!lf.active)return;CHECK(host_clear_active());++lf.reads;
 if(address==(uintptr_t)fw_page[0]+0x2c4c){
  *value=lf.fences++<lf.drop?3:2;if(!(*value&1)){lf.accepted=1;if(!lf.device_done)host_clear_device();}
 }
 if(address==(uintptr_t)fw_page[0]+0x2c30)*value=gglb_context.phase==GGL_WAIT&&lf.busy_reads++<lf.busy_delay?0x71800000:0x71000000;
 if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
  unsigned n=lf.counter_reads++;*value=!lf.wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
   n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
 }
 bool ring=address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb0000;
 bool scratch=address==(uintptr_t)ram+0xb0000;
 bool data=address>=(uintptr_t)ram+0xb8000&&address<(uintptr_t)ram+0xb9000;
 if(ring||scratch||data){
  ++lf.memreads;
  if(gglb_context.phase==GGL_WAIT&&scratch){CHECK(scratch&&lf.accepted&&lf.submits&&!lf.kept&&lf.device_done);
   if(lf.shadow_reads++>=lf.shadow_delay){*value=lf.bad_shadow?lf.bad_shadow:27;memcpy(ram+0xb0000,value,4);}}
  if(gglb_context.phase==GGL_WAIT&&data){
   CHECK((address==(uintptr_t)ram+0xb8c00||address==(uintptr_t)ram+0xb8c04)&&lf.device_done&&!lf.kept&&lf.shadow_reads);
   if(address==(uintptr_t)ram+0xb8c00&&gglb_context.work.wait_samples==gglb_context.work.idle_polls){
    if(lf.eop_reads++>=lf.eop_delay&&!lf.drop_eop&&!lf.eop_done)host_clear_event();
   }
   memcpy(value,(void *)address,4);
  }
  bool ib=address>=(uintptr_t)ram+0xac000&&address<(uintptr_t)ram+0xac254;
  bool restore=address>=(uintptr_t)ram+0xad000&&address<(uintptr_t)ram+0xad308;
  bool preamble=address>=(uintptr_t)ram+0xae000&&address<(uintptr_t)ram+0xae334;
  unsigned mem=ib?GGL_IB:restore?GGL_RESTORE:preamble?GGL_PREAMBLE:ring?GGL_RING:scratch?GGL_SCRATCH:GGL_DATA;
  unsigned off=(unsigned)(address-(uintptr_t)ram-(ib?0xac000:restore?0xad000:preamble?0xae000:ring?0xa8000:scratch?0xb0000:0xb8000));
  if(gglb_context.phase==lf.corrupt_phase&&mem==lf.corrupt_mem&&off==lf.corrupt_off&&
     (gglb_context.phase!=GGL_WAIT||gglb_context.work.wait_samples==gglb_context.work.idle_polls))*value^=1;
 }
}
static bool host_clear_store(vm_offset_t address,uint32_t value)
{
 if(!lf.active)return false;CHECK(host_clear_active());++lf.stores;
 if(address>=(uintptr_t)ram&&address<(uintptr_t)ram+sizeof(ram)){
  CHECK(gglb_context.phase==GGL_COMMANDS&&lf.memstores<555);
  unsigned total=lf.memstores,n=total<194?total:total<399?total-194:total<548?total-399:total-548;
  unsigned base=total<194?0xad000:total<399?0xae000:total<548?0xac000:0xa8000+80;
  const uint32_t *words=total<194?clear_native_restore:total<399?clear_native_preamble:total<548?clear_native_ib:clear_native_direct;
  CHECK(address==(uintptr_t)ram+base+4*n&&value==words[n]);
  ++lf.memstores;if(lf.memstores!=lf.drop_write)memcpy((void *)address,&value,4);
 }else{
  uint32_t reg=host_core_reg(address);CHECK(gglb_context.phase==GGL_SUBMIT&&ggl_register_allowed(reg,true)&&lf.memstores==555&&gglb_context.work.commands_checked==7&&gglb_context.work.ib_checked==149&&gglb_context.work.restore_checked==194&&gglb_context.work.preamble_checked==205);
  if(reg==0x807){CHECK(value==27&&lf.kept);++lf.submits;}else{CHECK(value<=1);lf.kept=value;}
  memcpy((void *)address,&value,4);
 }
 if(lf.stores==lf.stop_store)h.clock_bad=1;if(lf.stores==lf.expire_store)h.now=gglb_phase_end;
 return true;
}
static void clear_signed_setup(void)
{
 fixture_gpu_mode=7;cp_setup(0);fixture_gpu_mode=0;
 struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
 CHECK(z.flag==7&&ggb_data_selected==1&&ggb_data_ready==1&&ggb_smmu.layout==GGS_DATA19&&ggb_smmu.gpu_pages==19&&ggb_smmu.translations==171);
 CHECK(ggd_tables_match(&ggb_data_plan,ram+0x9c000,16384));
 for(unsigned i=0xb8000;i<0xbc000;i++)CHECK(ram[i]==0);
 struct gpz_receipt signed_load;CHECK(sweet_gpu_zap_once(&signed_load)==GPZ_OK);cp_active=0;u.active=1;
 CHECK(!mprotect(ram,16384,PROT_NONE));
}
static void clear_setup(void)
{
 clear_signed_setup();unsecure_good();u.active=0;lf.active=1;
 CHECK(ggub_context.state==2&&ggub_work.rptr==20&&gglb_lifecycle==GMB_IDLE&&gglb_context.state==0);
}
static void clear_untouched(void)
{
 CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60)&&!memcmp(ram+0xa8000+60,ggub_context.command.word,20));
 for(unsigned i=27;i<8192;i++)if(!(i>=4096&&i<4245)&&!(i>=5120&&i<5314)&&!(i>=6144&&i<6349)){uint32_t v;memcpy(&v,ram+0xa8000+4*i,4);CHECK(v==0xaaaaaaaa);}
 for(unsigned i=1;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb0000+4*i,4);CHECK(v==0);}
 for(unsigned i=0xb9000;i<0xbc000;i++)CHECK(ram[i]==0);
}
static void clear_failed(void)
{
 struct ggl_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 CHECK(sweet_gpu_clear_once(&out)!=GGL_OK&&!memcmp(&out,&saved,sizeof(out))&&lf.partial==1&&!lf.complete);
 CHECK(sweet_gpu_clear_state()==GMB_QUARANTINED&&sweet_gpu_write_state()==GMB_QUARANTINED&&ggwb_context.state==3&&sweet_gpu_ib_state()==GMB_QUARANTINED&&ggib_context.state==3&&sweet_gpu_compute_state()==GMB_QUARANTINED&&ggkb_context.state==3&&sweet_gpu_eop_state()==GMB_QUARANTINED&&ggeb_context.state==3&&sweet_gpu_unsecure_state()==GMB_QUARANTINED&&ggub_context.state==3&&
  sweet_gpu_zap_state()==GMB_QUARANTINED&&sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&
  sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&
  z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
 unsigned reads=lf.reads,stores=lf.stores,budgets=lf.budgets;
 CHECK(sweet_gpu_clear_once(&out)==(z.flag==7?GGL_ALREADY:GGL_ARGUMENT)&&!memcmp(&out,&saved,sizeof(out))&&reads==lf.reads&&stores==lf.stores&&budgets==lf.budgets);
 clear_untouched();
}
static void clear_good(void)
{
 struct ggl_receipt out;unsigned maps=h.maps,nc=h.nc_maps,owner_calls=h.owner_calls;
 enum ggl_result rc=sweet_gpu_clear_once(&out);
 if(rc!=GGL_OK)fprintf(stderr,"IB refusal: rc=%u phase=%u reason=%u guard_phase=%u mode=%u/%u sample=%u/%05x expected=%08x actual=%08x stores=%u memstores=%u memreads=%u\n",rc,gglb_context.phase,gglb_diagnostic.reason,gglb_diagnostic.phase,ggb_data_mode,z.flag,gglb_context.diagnostic.memory,gglb_context.diagnostic.reg,gglb_context.diagnostic.expected,gglb_context.diagnostic.actual,lf.stores,lf.memstores,lf.memreads);
 CHECK(rc==GGL_OK&&sweet_gpu_clear_state()==GMB_READY&&lf.complete==1&&!lf.partial&&h.live&&!h.quarantine);
 CHECK(out.complete==1&&out.sealed==1&&out.requests_retained==1&&out.prefix_checked==20&&out.clean_checked==7&&out.commands_written==7&&out.commands_checked==7&&out.ib_clean_checked==149&&out.ib_written==149&&out.ib_checked==149&&out.ib_after_checked==149);
 CHECK(out.initial_wptr==20&&out.initial_shadow==20&&out.rptr==27&&out.writes==lf.drop+3&&out.fence_checks==lf.drop+1&&lf.memstores==555&&lf.submits==lf.drop+1&&!lf.kept);
 CHECK(out.data_before_checked==1024&&out.data_after_checked==1024&&out.pixels_checked==256&&out.foreground_checked==64&&out.background_checked==192&&out.unchanged_checked==767&&out.eop_checked==1&&out.eop_complete==1&&out.eop_value==7&&out.eop_polls==lf.eop_delay+1&&out.ring_after_checked==27);
 CHECK(out.restore_clean_checked==194&&out.restore_written==194&&out.restore_checked==194&&out.restore_after_checked==194);
 CHECK(out.preamble_clean_checked==205&&out.preamble_written==205&&out.preamble_checked==205&&out.preamble_after_checked==205&&out.max_nc_batch_words==64);
 CHECK(gglb_aux_mask==63&&!gglb_before_control&&!gglb_before_hi&&!gglb_before_tail&&gglb_after_control==7&&!gglb_after_hi&&!gglb_after_tail&&gglb_diagnostic.reason==LGD_NONE);
 for(unsigned i=0;i<8;i++)CHECK(gglb_before_mask[i]==UINT32_MAX&&gglb_after_mask[i]==UINT32_MAX);
 for(unsigned i=0;i<256;i++)CHECK(!gglb_before[i]&&gglb_after[i]==clear_expected_page[i]);
 CHECK(out.wait_samples==out.idle_polls&&out.wait_samples==lf.shadow_reads&&out.wait_control_hi==0);
 CHECK(lf.memreads==3754+3*lf.shadow_reads+lf.eop_reads&&lf.device_writes==263&&h.maps==maps&&h.nc_maps==nc&&h.owner_calls==owner_calls);
 for(unsigned i=0;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb8000+4*i,4);CHECK(v==clear_expected_page[i]);}
 clear_untouched();unsigned reads=lf.reads,stores=lf.stores,budgets=lf.budgets;
 CHECK(sweet_gpu_clear_once(&out)==GGL_ALREADY&&reads==lf.reads&&stores==lf.stores&&budgets==lf.budgets);
}
static void gpu_clear_cases(void)
{
 unsigned first=cases;
 for(unsigned scenario=0;scenario<5;scenario++){
  clear_setup();lf.drop=scenario==1?1:scenario==2?100:scenario==3?199:0;lf.wrap=scenario==4;
  if(scenario==1)lf.shadow_delay=lf.busy_delay=lf.eop_delay=2;clear_good();
 }
 for(unsigned phase=GGL_SEAL;phase<=GGL_FINAL;phase++)for(unsigned kind=1;kind<=49;kind++){
  clear_setup();lf.phase=phase;lf.kind=kind;clear_failed();CHECK(lf.fired);
 }
 for(unsigned n=1;n<=558;n++){
  clear_setup();lf.stop_store=n;clear_failed();CHECK(lf.stores>=n&&lf.stores-n<64&&(n<=555||lf.stores==n));
  clear_setup();lf.expire_store=n;clear_failed();CHECK(lf.stores>=n&&lf.stores-n<64&&(n<=555||lf.stores==n));
 }
 for(unsigned n=1;n<=555;n++){clear_setup();lf.drop_write=n;clear_failed();CHECK(!lf.submits);}
 for(unsigned phase=GGL_CAPTURE;phase<=GGL_VERIFY;phase++)if(phase==GGL_CAPTURE||phase==GGL_COMMANDS||phase==GGL_VERIFY)
  for(unsigned n=0;n<149;n++){clear_setup();lf.corrupt_phase=phase;lf.corrupt_mem=GGL_IB;lf.corrupt_off=4*n;clear_failed();}
 for(unsigned phase=GGL_CAPTURE;phase<=GGL_VERIFY;phase++)if(phase==GGL_CAPTURE||phase==GGL_COMMANDS||phase==GGL_VERIFY)
  for(unsigned mem=GGL_RESTORE;mem<=GGL_PREAMBLE;mem++)for(unsigned n=0;n<(mem==GGL_RESTORE?194u:205u);n++){
   clear_setup();lf.corrupt_phase=phase;lf.corrupt_mem=mem;lf.corrupt_off=4*n;clear_failed();
  }
 const unsigned offsets[]={0,4,1020,2048,3072,3076,4092};
 for(unsigned phase=GGL_CAPTURE;phase<=GGL_VERIFY;phase++)if(phase==GGL_CAPTURE||phase==GGL_VERIFY)
  for(unsigned n=0;n<7;n++){clear_setup();lf.corrupt_phase=phase;lf.corrupt_mem=GGL_DATA;lf.corrupt_off=offsets[n];clear_failed();}
 for(unsigned n=0;n<7;n++){clear_setup();lf.corrupt_data=offsets[n]/4+1;clear_failed();}
 for(unsigned n=1;n<=256;n++){clear_setup();lf.drop_data=n;clear_failed();}
 for(unsigned n=0;n<8;n++)for(unsigned kind=1;kind<=2;kind++){clear_setup();lf.nc_kind=kind;lf.nc_page=n;clear_failed();CHECK(!lf.stores);}
 for(unsigned n=1;n<=8;n++){clear_setup();lf.phys_bad=n;clear_failed();CHECK(!lf.stores);}
 /* Every permission/address bit of the DATA PTE is checked through the
  * actual live guard, independently of the pure full-table matcher cases. */
 for(unsigned bit=0;bit<64;bit++){
  clear_setup();ram[0x9c000+0x2000+24*8+bit/8]^=1u<<(bit%8);clear_failed();CHECK(!lf.stores);
 }
 for(unsigned delay=1;delay<=8;delay*=2){clear_setup();lf.eop_delay=delay;clear_good();}
 clear_setup();lf.drop_eop=1;clear_failed();CHECK(lf.eop_reads==1024&&lf.shadow_reads&&lf.device_writes==256&&!lf.kept);
 clear_setup();lf.bad_eop=1;clear_failed();CHECK(lf.eop_reads==1);
 clear_setup();lf.corrupt_phase=GGL_WAIT;lf.corrupt_mem=GGL_DATA;lf.corrupt_off=3072;clear_failed();
 clear_setup();lf.drop=200;clear_failed();CHECK(lf.kept&&lf.submits==201&&lf.fences==200);
 clear_setup();lf.bad_shadow=8192;clear_failed();
 clear_setup();lf.budget_fail=1;clear_failed();CHECK(gglb_diagnostic.reason==LGD_ENTRY_BUDGET&&!lf.stores&&!lf.memreads);
 clear_setup();lf.time_step=100000000;clear_failed();CHECK(gglb_diagnostic.reason==LGD_TIME);
 clear_setup();lf.drop_pixels=1;clear_failed();CHECK(lf.eop_done&&gglb_context.work.eop_complete==1);
 /* No public/caller flag may upgrade an already cold18-leaf boot. */
 unsecure_setup();z.flag=7;unsecure_failed();CHECK(!u.stores);
 write_signed_setup();z.flag=7;unsecure_failed();CHECK(!u.stores);
 ib_signed_setup();z.flag=7;unsecure_failed();CHECK(!u.stores);
 eop_signed_setup();z.flag=7;unsecure_failed();CHECK(!u.stores);
 compute_signed_setup();z.flag=7;unsecure_failed();CHECK(!u.stores);
 clear_signed_setup();z.flag=6;unsecure_failed();CHECK(!u.stores);
 clear_signed_setup();ram[0x9c000+0x2000+24*8]^=0x40;unsecure_failed();CHECK(!u.stores);
 for(unsigned mode=0;mode<7;mode++){
  clear_setup();z.flag=(int)mode;struct ggl_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned budgets=h.budgets;
  CHECK(sweet_gpu_clear_once(&out)==GGL_ARGUMENT&&!memcmp(&out,&old,sizeof(out))&&gglb_lifecycle==GMB_IDLE&&budgets==h.budgets&&!lf.stores);
 }
 clear_setup();
 for(unsigned phase=GGL_IDLE;phase<=GGL_DONE;phase++){
  gglb_context.phase=phase;
  for(unsigned mem=0;mem<=6;mem++)for(unsigned off=0;off<=4096;off+=4)for(unsigned write=0;write<=1;write++){
   bool ring=mem==GGL_RING&&off<108,scratch=mem==GGL_SCRATCH&&!off,data=mem==GGL_DATA&&off<4096,cmd=ring&&off>=80;
   bool artifact=(mem==GGL_IB&&off<596)||(mem==GGL_RESTORE&&off<776)||(mem==GGL_PREAMBLE&&off<820);
   bool allowed=write?(phase==GGL_COMMANDS&&(cmd||artifact)):
    ((phase==GGL_CAPTURE&&(ring||scratch||data||artifact))||(phase==GGL_COMMANDS&&(cmd||artifact))||
     (phase==GGL_WAIT&&(scratch||(data&&(off==3072||off==3076))))||(phase==GGL_VERIFY&&(ring||data||artifact)));
   CHECK(!!gglb_memory((enum ggl_memory)mem,off,write)==allowed);
  }
 }
 gglb_context.phase=GGL_IDLE;CHECK(!gglb_memory(GGL_DATA,1,false)&&!gglb_memory(GGL_RING,UINT32_MAX,false));
 CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));
 printf("GPU native clear live board: %u actual coldDATA19+CP+ZAP+GGU+GGL/PROT_NONE/fault/PTE/NC/private-parent/once cases PASS; source/model only, no physical clear/rendering/Metal proof\n",cases-first);
}
