/* Actual compute provider + complete signed/GGU prerequisites. Typed GPU
 * model only; secure first CPU page remains PROT_NONE after AUTH. */
#define command compute_native_direct
#define indirect compute_native_ib
#define program compute_native_program
#define ibo compute_native_ibo
#include "native_words.h"
#undef command
#undef indirect
#undef program
#undef ibo
/* Additional actual CP+ZAP+GGU+GGK integration; primitive hardware/owner seams
 * remain explicit. Secure first CPU page stays PROT_NONE after AUTH. */
static bool host_compute_active(void)
{
 return kf.active&&z.auth_done&&z.flag==6&&sweet_gpu_compute_state()==GMB_RUNNING&&
  ((ggkb_context.state==1&&ggkb_context.phase>=GGK_SEAL&&ggkb_context.phase<=GGK_FINAL)||
   (ggkb_context.state==2&&ggkb_context.phase==GGK_DONE&&ggkb_phase==GGK_FINAL));
}
static void host_compute_budget(void)
{
 if(!kf.active)return;++kf.budgets;if(kf.time_step)h.now+=kf.time_step;
 if(kf.budgets==kf.budget_fail)h.live=false;
 if(!kf.kind||kf.fired||ggkb_context.state!=1||ggkb_context.phase!=kf.phase)return;
 kf.fired=1;uint32_t v=1;uint64_t q;
 switch(kf.kind){
 case 1:h.clock_bad=1;break;case 2:h.irq_bad=1;break;case 3:memcpy(reset_page+0x2000,&v,4);break;
 case 4:memcpy(smmu+0x48,&v,4);break;case 5:v=1u<<9;memcpy(core_page+4*0x201,&v,4);break;
 case 6:memcpy(core_page+4*0x823,&v,4);break;case 7:h.now=ggkb_deadline;break;case 8:h.now=ggkb_phase_end;break;
 case 9:kf.owner_bad=1;break;case 10:ggub_work.prefix_checked=14;ggub_context.work=ggub_work;break;
 case 11:gfw_context.dcvs_return=1;break;case 12:core_attr_bad=1;break;case 13:ggc_alias[0]++;break;
 case 14:h.context=1;break;case 15:q=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&q,8);break;
 case 16:v=1u<<24;memcpy(reset_page+0x2648,&v,4);break;case 17:ggc_work.mem_compared=1023;break;
 case 18:h.now=ggkb_last_now?ggkb_last_now-1:UINT64_MAX;break;
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
 default:CHECK(false);
 }
}
static void host_compute_device(void)
{
 CHECK(kf.accepted&&!kf.device_done&&kf.submits&&kf.kept);kf.device_done=1;
 CHECK(!memcmp(ram+0xa8000+80,compute_native_direct,sizeof(compute_native_direct)));
 CHECK(!memcmp(ram+0xac000,compute_native_ib,sizeof(compute_native_ib)));
 CHECK(!memcmp(ram+0xad000,compute_native_program,sizeof(compute_native_program)));
 CHECK(!memcmp(ram+0xae000,compute_native_ibo,sizeof(compute_native_ibo)));
 for(unsigned id=0;id<32;id++){
  if(!kf.drop_shader&&kf.drop_data!=id+1)memcpy(ram+0xb8000+4*id,&id,4);++kf.device_writes;
 }
}
static void host_compute_event(void)
{
 CHECK(kf.device_done&&!kf.eop_done&&kf.submits&&!kf.kept);
 CHECK(compute_native_ib[69]==0x70460004&&compute_native_ib[70]==0x16&&compute_native_ib[81]==0x70460004&&compute_native_ib[82]==4);
 uint32_t value=1;memcpy(ram+0xb8000,&value,4);value=kf.bad_eop?kf.bad_eop:2;
 memcpy(ram+0xb8000,&value,4);kf.eop_done=1;kf.device_writes+=2;
 if(kf.corrupt_data){CHECK(kf.corrupt_data<=1024);ram[0xb8000+4*(kf.corrupt_data-1)]^=1;}
}
static void host_compute_read(vm_offset_t address,uint32_t *value)
{
 if(!kf.active)return;CHECK(host_compute_active());++kf.reads;
 if(address==(uintptr_t)fw_page[0]+0x2c4c){
  *value=kf.fences++<kf.drop?3:2;if(!(*value&1)){kf.accepted=1;if(!kf.device_done)host_compute_device();}
 }
 if(address==(uintptr_t)fw_page[0]+0x2c30)*value=ggkb_context.phase==GGK_WAIT&&kf.busy_reads++<kf.busy_delay?0x71800000:0x71000000;
 if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
  unsigned n=kf.counter_reads++;*value=!kf.wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
   n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
 }
 bool ring=address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb0000;
 bool scratch=address==(uintptr_t)ram+0xb0000;
 bool data=address>=(uintptr_t)ram+0xb8000&&address<(uintptr_t)ram+0xb9000;
 if(ring||scratch||data){
  ++kf.memreads;
  if(ggkb_context.phase==GGK_WAIT&&scratch){CHECK(scratch&&kf.accepted&&kf.submits&&!kf.kept&&kf.device_done);
   if(kf.shadow_reads++>=kf.shadow_delay){*value=kf.bad_shadow?kf.bad_shadow:27;memcpy(ram+0xb0000,value,4);}}
  if(ggkb_context.phase==GGK_WAIT&&data){
   CHECK(address==(uintptr_t)ram+0xb8000&&kf.device_done&&!kf.kept&&kf.shadow_reads);
   if(kf.eop_reads++>=kf.eop_delay&&!kf.drop_eop&&!kf.eop_done)host_compute_event();
   memcpy(value,(void *)address,4);
  }
  bool ib=address>=(uintptr_t)ram+0xac000&&address<(uintptr_t)ram+0xac16c;
  bool program=address>=(uintptr_t)ram+0xad000&&address<(uintptr_t)ram+0xad080;
  bool ibo=address>=(uintptr_t)ram+0xae000&&address<(uintptr_t)ram+0xae040;
  unsigned mem=ib?GGK_IB:program?GGK_PROGRAM:ibo?GGK_IBO:ring?GGK_RING:scratch?GGK_SCRATCH:GGK_DATA;
  unsigned off=(unsigned)(address-(uintptr_t)ram-(ib?0xac000:program?0xad000:ibo?0xae000:ring?0xa8000:scratch?0xb0000:0xb8000));
  if(ggkb_context.phase==kf.corrupt_phase&&mem==kf.corrupt_mem&&off==kf.corrupt_off)*value^=1;
 }
}
static bool host_compute_store(vm_offset_t address,uint32_t value)
{
 if(!kf.active)return false;CHECK(host_compute_active());++kf.stores;
 if(address>=(uintptr_t)ram&&address<(uintptr_t)ram+sizeof(ram)){
  CHECK(ggkb_context.phase==GGK_COMMANDS&&kf.memstores<146);
  unsigned total=kf.memstores,n=total<32?total:total<48?total-32:total<139?total-48:total-139;
  unsigned base=total<32?0xad000:total<48?0xae000:total<139?0xac000:0xa8000+80;
  const uint32_t *words=total<32?compute_native_program:total<48?compute_native_ibo:total<139?compute_native_ib:compute_native_direct;
  CHECK(address==(uintptr_t)ram+base+4*n&&value==words[n]);
  ++kf.memstores;if(kf.memstores!=kf.drop_write)memcpy((void *)address,&value,4);
 }else{
  uint32_t reg=host_core_reg(address);CHECK(ggkb_context.phase==GGK_SUBMIT&&ggk_register_allowed(reg,true)&&kf.memstores==146&&ggkb_context.work.commands_checked==7&&ggkb_context.work.ib_checked==91&&ggkb_context.work.program_checked==32&&ggkb_context.work.ibo_checked==16);
  if(reg==0x807){CHECK(value==27&&kf.kept);++kf.submits;}else{CHECK(value<=1);kf.kept=value;}
  memcpy((void *)address,&value,4);
 }
 if(kf.stores==kf.stop_store)h.clock_bad=1;if(kf.stores==kf.expire_store)h.now=ggkb_phase_end;
 return true;
}
static void compute_signed_setup(void)
{
 fixture_gpu_mode=6;cp_setup(0);fixture_gpu_mode=0;
 struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
 CHECK(z.flag==6&&ggb_data_selected==1&&ggb_data_ready==1&&ggb_smmu.layout==GGS_DATA19&&ggb_smmu.gpu_pages==19&&ggb_smmu.translations==171);
 CHECK(ggd_tables_match(&ggb_data_plan,ram+0x9c000,16384));
 for(unsigned i=0xb8000;i<0xbc000;i++)CHECK(ram[i]==0);
 struct gpz_receipt signed_load;CHECK(sweet_gpu_zap_once(&signed_load)==GPZ_OK);cp_active=0;u.active=1;
 CHECK(!mprotect(ram,16384,PROT_NONE));
}
static void compute_setup(void)
{
 compute_signed_setup();unsecure_good();u.active=0;kf.active=1;
 CHECK(ggub_context.state==2&&ggub_work.rptr==20&&ggkb_lifecycle==GMB_IDLE&&ggkb_context.state==0);
}
static void compute_untouched(void)
{
 CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60)&&!memcmp(ram+0xa8000+60,ggub_context.command.word,20));
 for(unsigned i=27;i<8192;i++)if(!(i>=4096&&i<4187)&&!(i>=5120&&i<5152)&&!(i>=6144&&i<6160)){uint32_t v;memcpy(&v,ram+0xa8000+4*i,4);CHECK(v==0xaaaaaaaa);}
 for(unsigned i=1;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb0000+4*i,4);CHECK(v==0);}
 for(unsigned i=0xb9000;i<0xbc000;i++)CHECK(ram[i]==0);
}
static void compute_failed(void)
{
 struct ggk_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 CHECK(sweet_gpu_compute_once(&out)!=GGK_OK&&!memcmp(&out,&saved,sizeof(out))&&kf.partial==1&&!kf.complete);
 CHECK(sweet_gpu_compute_state()==GMB_QUARANTINED&&sweet_gpu_write_state()==GMB_QUARANTINED&&ggwb_context.state==3&&sweet_gpu_ib_state()==GMB_QUARANTINED&&ggib_context.state==3&&sweet_gpu_eop_state()==GMB_QUARANTINED&&ggeb_context.state==3&&sweet_gpu_unsecure_state()==GMB_QUARANTINED&&ggub_context.state==3&&
  sweet_gpu_zap_state()==GMB_QUARANTINED&&sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&
  sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&
  z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
 unsigned reads=kf.reads,stores=kf.stores,budgets=kf.budgets;
 CHECK(sweet_gpu_compute_once(&out)==(z.flag==6?GGK_ALREADY:GGK_ARGUMENT)&&!memcmp(&out,&saved,sizeof(out))&&reads==kf.reads&&stores==kf.stores&&budgets==kf.budgets);
 compute_untouched();
}
static void compute_good(void)
{
 struct ggk_receipt out;unsigned maps=h.maps,nc=h.nc_maps,owner_calls=h.owner_calls;
 enum ggk_result rc=sweet_gpu_compute_once(&out);
 if(rc!=GGK_OK)fprintf(stderr,"IB refusal: rc=%u phase=%u reason=%u guard_phase=%u mode=%u/%u sample=%u/%05x expected=%08x actual=%08x stores=%u memstores=%u memreads=%u\n",rc,ggkb_context.phase,ggkb_diagnostic.reason,ggkb_diagnostic.phase,ggb_data_mode,z.flag,ggkb_context.diagnostic.memory,ggkb_context.diagnostic.reg,ggkb_context.diagnostic.expected,ggkb_context.diagnostic.actual,kf.stores,kf.memstores,kf.memreads);
 CHECK(rc==GGK_OK&&sweet_gpu_compute_state()==GMB_READY&&kf.complete==1&&!kf.partial&&h.live&&!h.quarantine);
 CHECK(out.complete==1&&out.sealed==1&&out.requests_retained==1&&out.prefix_checked==20&&out.clean_checked==7&&out.commands_written==7&&out.commands_checked==7&&out.ib_clean_checked==91&&out.ib_written==91&&out.ib_checked==91&&out.ib_after_checked==91);
 CHECK(out.initial_wptr==20&&out.initial_shadow==20&&out.rptr==27&&out.writes==kf.drop+3&&out.fence_checks==kf.drop+1&&kf.memstores==146&&kf.submits==kf.drop+1&&!kf.kept);
 CHECK(out.data_before_checked==1024&&out.data_after_checked==1024&&out.invocations_checked==31&&out.unchanged_checked==992&&out.eop_checked==1&&out.eop_complete==1&&out.eop_value==2&&out.eop_polls==kf.eop_delay+1&&out.ring_after_checked==27);
 CHECK(out.program_clean_checked==32&&out.program_written==32&&out.program_checked==32&&out.program_after_checked==32);
 CHECK(out.ibo_clean_checked==16&&out.ibo_written==16&&out.ibo_checked==16&&out.ibo_after_checked==16&&out.max_nc_batch_words==64);
 CHECK(ggkb_before_mask==UINT32_MAX&&ggkb_after_mask==UINT32_MAX&&ggkb_tail_mask==3&&!ggkb_before_tail&&!ggkb_after_tail&&ggkb_diagnostic.reason==KGD_NONE);
 for(unsigned i=0;i<32;i++)CHECK(!ggkb_before[i]&&ggkb_after[i]==(i?i:2u));
 CHECK(kf.memreads==2527+kf.shadow_reads+kf.eop_reads&&kf.device_writes==34&&h.maps==maps&&h.nc_maps==nc&&h.owner_calls==owner_calls);
 for(unsigned i=0;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb8000+4*i,4);CHECK(v==(i==0?2u:i<32?i:0));}
 compute_untouched();unsigned reads=kf.reads,stores=kf.stores,budgets=kf.budgets;
 CHECK(sweet_gpu_compute_once(&out)==GGK_ALREADY&&reads==kf.reads&&stores==kf.stores&&budgets==kf.budgets);
}
static void gpu_compute_cases(void)
{
 unsigned first=cases;
 for(unsigned scenario=0;scenario<5;scenario++){
  compute_setup();kf.drop=scenario==1?1:scenario==2?100:scenario==3?199:0;kf.wrap=scenario==4;
  if(scenario==1)kf.shadow_delay=kf.busy_delay=kf.eop_delay=2;compute_good();
 }
 for(unsigned phase=GGK_SEAL;phase<=GGK_FINAL;phase++)for(unsigned kind=1;kind<=44;kind++){
  compute_setup();kf.phase=phase;kf.kind=kind;compute_failed();CHECK(kf.fired);
 }
 for(unsigned n=1;n<=149;n++){
  compute_setup();kf.stop_store=n;compute_failed();CHECK(kf.stores>=n&&kf.stores-n<64&&(n<=146||kf.stores==n));
  compute_setup();kf.expire_store=n;compute_failed();CHECK(kf.stores>=n&&kf.stores-n<64&&(n<=146||kf.stores==n));
 }
 for(unsigned n=1;n<=146;n++){compute_setup();kf.drop_write=n;compute_failed();CHECK(!kf.submits);}
 for(unsigned phase=GGK_CAPTURE;phase<=GGK_VERIFY;phase++)if(phase==GGK_CAPTURE||phase==GGK_COMMANDS||phase==GGK_VERIFY)
  for(unsigned n=0;n<91;n++){compute_setup();kf.corrupt_phase=phase;kf.corrupt_mem=GGK_IB;kf.corrupt_off=4*n;compute_failed();}
 for(unsigned phase=GGK_CAPTURE;phase<=GGK_VERIFY;phase++)if(phase==GGK_CAPTURE||phase==GGK_COMMANDS||phase==GGK_VERIFY)
  for(unsigned mem=GGK_PROGRAM;mem<=GGK_IBO;mem++)for(unsigned n=0;n<(mem==GGK_PROGRAM?32u:16u);n++){
   compute_setup();kf.corrupt_phase=phase;kf.corrupt_mem=mem;kf.corrupt_off=4*n;compute_failed();
  }
 const unsigned offsets[]={0,4,124,2048,4092};
 for(unsigned phase=GGK_CAPTURE;phase<=GGK_VERIFY;phase++)if(phase==GGK_CAPTURE||phase==GGK_VERIFY)
  for(unsigned n=0;n<5;n++){compute_setup();kf.corrupt_phase=phase;kf.corrupt_mem=GGK_DATA;kf.corrupt_off=offsets[n];compute_failed();}
 for(unsigned n=0;n<5;n++){compute_setup();kf.corrupt_data=offsets[n]/4+1;compute_failed();}
 for(unsigned n=2;n<=32;n++){compute_setup();kf.drop_data=n;compute_failed();}
 for(unsigned n=0;n<8;n++)for(unsigned kind=1;kind<=2;kind++){compute_setup();kf.nc_kind=kind;kf.nc_page=n;compute_failed();CHECK(!kf.stores);}
 for(unsigned n=1;n<=8;n++){compute_setup();kf.phys_bad=n;compute_failed();CHECK(!kf.stores);}
 /* Every permission/address bit of the DATA PTE is checked through the
  * actual live guard, independently of the pure full-table matcher cases. */
 for(unsigned bit=0;bit<64;bit++){
  compute_setup();ram[0x9c000+0x2000+24*8+bit/8]^=1u<<(bit%8);compute_failed();CHECK(!kf.stores);
 }
 for(unsigned delay=1;delay<=8;delay*=2){compute_setup();kf.eop_delay=delay;compute_good();}
 compute_setup();kf.drop_eop=1;compute_failed();CHECK(kf.eop_reads==1024&&kf.shadow_reads&&kf.device_writes==32&&!kf.kept);
 compute_setup();kf.bad_eop=1;compute_failed();CHECK(kf.eop_reads==1);
 compute_setup();kf.corrupt_phase=GGK_WAIT;kf.corrupt_mem=GGK_DATA;kf.corrupt_off=0;compute_failed();
 compute_setup();kf.drop=200;compute_failed();CHECK(kf.kept&&kf.submits==201&&kf.fences==200);
 compute_setup();kf.bad_shadow=8192;compute_failed();
 compute_setup();kf.budget_fail=1;compute_failed();CHECK(ggkb_diagnostic.reason==KGD_ENTRY_BUDGET&&!kf.stores&&!kf.memreads);
 compute_setup();kf.time_step=100000000;compute_failed();CHECK(ggkb_diagnostic.reason==KGD_TIME);
 compute_setup();kf.drop_shader=1;compute_failed();CHECK(kf.eop_done&&ggkb_context.work.eop_complete==1);
 /* No public/caller flag may upgrade an already cold18-leaf boot. */
 unsecure_setup();z.flag=4;unsecure_failed();CHECK(!u.stores);
 write_signed_setup();z.flag=6;unsecure_failed();CHECK(!u.stores);
 ib_signed_setup();z.flag=6;unsecure_failed();CHECK(!u.stores);
 eop_signed_setup();z.flag=6;unsecure_failed();CHECK(!u.stores);
 compute_signed_setup();z.flag=5;unsecure_failed();CHECK(!u.stores);
 compute_signed_setup();ram[0x9c000+0x2000+24*8]^=0x40;unsecure_failed();CHECK(!u.stores);
 for(unsigned mode=0;mode<6;mode++){
  compute_setup();z.flag=(int)mode;struct ggk_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned budgets=h.budgets;
  CHECK(sweet_gpu_compute_once(&out)==GGK_ARGUMENT&&!memcmp(&out,&old,sizeof(out))&&ggkb_lifecycle==GMB_IDLE&&budgets==h.budgets&&!kf.stores);
 }
 compute_setup();
 for(unsigned phase=GGK_IDLE;phase<=GGK_DONE;phase++){
  ggkb_context.phase=phase;
  for(unsigned mem=0;mem<=6;mem++)for(unsigned off=0;off<=4096;off+=4)for(unsigned write=0;write<=1;write++){
   bool ring=mem==GGK_RING&&off<108,scratch=mem==GGK_SCRATCH&&!off,data=mem==GGK_DATA&&off<4096,cmd=ring&&off>=80;
   bool artifact=(mem==GGK_IB&&off<364)||(mem==GGK_PROGRAM&&off<128)||(mem==GGK_IBO&&off<64);
   bool allowed=write?(phase==GGK_COMMANDS&&(cmd||artifact)):
    ((phase==GGK_CAPTURE&&(ring||scratch||data||artifact))||(phase==GGK_COMMANDS&&(cmd||artifact))||
     (phase==GGK_WAIT&&(scratch||(data&&off==0)))||(phase==GGK_VERIFY&&(ring||data||artifact)));
   CHECK(!!ggkb_memory((enum ggk_memory)mem,off,write)==allowed);
  }
 }
 ggkb_context.phase=GGK_IDLE;CHECK(!ggkb_memory(GGK_DATA,1,false)&&!ggkb_memory(GGK_RING,UINT32_MAX,false));
 CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));
 printf("GPU native compute live board: %u actual coldDATA19+CP+ZAP+GGU+GGK/PROT_NONE/fault/PTE/NC/private-parent/once cases PASS; source/model only, no hardware shader proof\n",cases-first);
}
