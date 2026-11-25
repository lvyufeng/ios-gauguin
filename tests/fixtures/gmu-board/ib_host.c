/* Additional actual CP+ZAP+GGU+GGI integration; primitive hardware/owner seams
 * remain explicit. Secure first CPU page stays PROT_NONE after AUTH. */
static bool host_ib_active(void)
{
 return ibf.active&&z.auth_done&&z.flag==4&&sweet_gpu_ib_state()==GMB_RUNNING&&
  ((ggib_context.state==1&&ggib_context.phase>=GGI_SEAL&&ggib_context.phase<=GGI_FINAL)||
   (ggib_context.state==2&&ggib_context.phase==GGI_DONE&&ggib_phase==GGI_FINAL));
}
static void host_ib_budget(void)
{
 if(!ibf.active)return;++ibf.budgets;if(ibf.time_step)h.now+=ibf.time_step;
 if(ibf.budgets==ibf.budget_fail)h.live=false;
 if(!ibf.kind||ibf.fired||ggib_context.state!=1||ggib_context.phase!=ibf.phase)return;
 ibf.fired=1;uint32_t v=1;uint64_t q;
 switch(ibf.kind){
 case 1:h.clock_bad=1;break;case 2:h.irq_bad=1;break;case 3:memcpy(reset_page+0x2000,&v,4);break;
 case 4:memcpy(smmu+0x48,&v,4);break;case 5:v=1u<<9;memcpy(core_page+4*0x201,&v,4);break;
 case 6:memcpy(core_page+4*0x823,&v,4);break;case 7:h.now=ggib_deadline;break;case 8:h.now=ggib_phase_end;break;
 case 9:ibf.owner_bad=1;break;case 10:ggub_work.prefix_checked=14;ggub_context.work=ggub_work;break;
 case 11:gfw_context.dcvs_return=1;break;case 12:core_attr_bad=1;break;case 13:ggc_alias[0]++;break;
 case 14:h.context=1;break;case 15:q=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&q,8);break;
 case 16:v=1u<<24;memcpy(reset_page+0x2648,&v,4);break;case 17:ggc_work.mem_compared=1023;break;
 case 18:h.now=ggib_last_now?ggib_last_now-1:UINT64_MAX;break;
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
 default:CHECK(false);
 }
}
static void host_ib_device(void)
{
 CHECK(ibf.accepted&&!ibf.device_done&&ibf.submits&&ibf.kept);ibf.device_done=1;
 uint32_t direct[4];memcpy(direct,ram+0xa8000+80,sizeof(direct));
 CHECK(direct[0]==0x70bf8003&&direct[1]==0xfc00c000&&!direct[2]&&direct[3]==8&&!(direct[3]&(1u<<20)));
 for(unsigned i=0;i<2;i++){
  uint32_t p[4];memcpy(p,ram+0xac000+16*i,sizeof(p));CHECK(p[0]==0x703d8003);
  uint64_t va=(uint64_t)p[1]|((uint64_t)p[2]<<32);CHECK(va>=0xfc018000&&va<=0xfc018ffc&&!(va&3));
  if(ibf.drop_data!=i+1)memcpy(ram+0xb8000+va-0xfc018000,&p[3],4);++ibf.device_writes;
 }
 if(ibf.corrupt_data){CHECK(ibf.corrupt_data<=1024);ram[0xb8000+4*(ibf.corrupt_data-1)]^=1;}
}
static void host_ib_read(vm_offset_t address,uint32_t *value)
{
 if(!ibf.active)return;CHECK(host_ib_active());++ibf.reads;
 if(address==(uintptr_t)fw_page[0]+0x2c4c){
  *value=ibf.fences++<ibf.drop?3:2;if(!(*value&1)){ibf.accepted=1;if(!ibf.device_done)host_ib_device();}
 }
 if(address==(uintptr_t)fw_page[0]+0x2c30)*value=ggib_context.phase==GGI_WAIT&&ibf.busy_reads++<ibf.busy_delay?0x71800000:0x71000000;
 if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
  unsigned n=ibf.counter_reads++;*value=!ibf.wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
   n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
 }
 bool ring=address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb0000;
 bool scratch=address==(uintptr_t)ram+0xb0000;
 bool data=address>=(uintptr_t)ram+0xb8000&&address<(uintptr_t)ram+0xb9000;
 if(ring||scratch||data){
  ++ibf.memreads;
  if(ggib_context.phase==GGI_WAIT){CHECK(scratch&&ibf.accepted&&ibf.submits&&!ibf.kept&&ibf.device_done);
   if(ibf.shadow_reads++>=ibf.shadow_delay){*value=ibf.bad_shadow?ibf.bad_shadow:27;memcpy(ram+0xb0000,value,4);}}
  bool ib=address>=(uintptr_t)ram+0xac000&&address<(uintptr_t)ram+0xac020;
  unsigned mem=ib?GGI_IB:ring?GGI_RING:scratch?GGI_SCRATCH:GGI_DATA;
  unsigned off=(unsigned)(address-(uintptr_t)ram-(ib?0xac000:ring?0xa8000:scratch?0xb0000:0xb8000));
  if(ggib_context.phase==ibf.corrupt_phase&&mem==ibf.corrupt_mem&&off==ibf.corrupt_off)*value^=1;
 }
}
static bool host_ib_store(vm_offset_t address,uint32_t value)
{
 if(!ibf.active)return false;CHECK(host_ib_active());++ibf.stores;
 if(address>=(uintptr_t)ram&&address<(uintptr_t)ram+sizeof(ram)){
  CHECK(ggib_context.phase==GGI_COMMANDS&&ibf.memstores<15);
  bool indirect=ibf.memstores<8;unsigned n=indirect?ibf.memstores:ibf.memstores-8;
  CHECK(address==(uintptr_t)ram+(indirect?0xac000:0xa8000+80)+4*n&&value==(indirect?ggib_context.command.ib[n]:ggib_context.command.word[n]));
  ++ibf.memstores;if(ibf.memstores!=ibf.drop_write)memcpy((void *)address,&value,4);
 }else{
  uint32_t reg=host_core_reg(address);CHECK(ggib_context.phase==GGI_SUBMIT&&ggi_register_allowed(reg,true)&&ibf.memstores==15&&ggib_context.work.commands_checked==7&&ggib_context.work.ib_checked==8);
  if(reg==0x807){CHECK(value==27&&ibf.kept);++ibf.submits;}else{CHECK(value<=1);ibf.kept=value;}
  memcpy((void *)address,&value,4);
 }
 if(ibf.stores==ibf.stop_store)h.clock_bad=1;if(ibf.stores==ibf.expire_store)h.now=ggib_phase_end;
 return true;
}
static void ib_signed_setup(void)
{
 fixture_gpu_mode=4;cp_setup(0);fixture_gpu_mode=0;
 struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
 CHECK(z.flag==4&&ggb_data_selected==1&&ggb_data_ready==1&&ggb_smmu.layout==GGS_DATA19&&ggb_smmu.gpu_pages==19&&ggb_smmu.translations==171);
 CHECK(ggd_tables_match(&ggb_data_plan,ram+0x9c000,16384));
 for(unsigned i=0xb8000;i<0xbc000;i++)CHECK(ram[i]==0);
 struct gpz_receipt signed_load;CHECK(sweet_gpu_zap_once(&signed_load)==GPZ_OK);cp_active=0;u.active=1;
 CHECK(!mprotect(ram,16384,PROT_NONE));
}
static void ib_setup(void)
{
 ib_signed_setup();unsecure_good();u.active=0;ibf.active=1;
 CHECK(ggub_context.state==2&&ggub_work.rptr==20&&ggib_lifecycle==GMB_IDLE&&ggib_context.state==0);
}
static void ib_untouched(void)
{
 CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60)&&!memcmp(ram+0xa8000+60,ggub_context.command.word,20));
 for(unsigned i=27;i<8192;i++)if(i<4096||i>=4104){uint32_t v;memcpy(&v,ram+0xa8000+4*i,4);CHECK(v==0xaaaaaaaa);}
 for(unsigned i=1;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb0000+4*i,4);CHECK(v==0);}
 for(unsigned i=0xb9000;i<0xbc000;i++)CHECK(ram[i]==0);
}
static void ib_failed(void)
{
 struct ggi_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 CHECK(sweet_gpu_ib_once(&out)!=GGI_OK&&!memcmp(&out,&saved,sizeof(out))&&ibf.partial==1&&!ibf.complete);
 CHECK(sweet_gpu_ib_state()==GMB_QUARANTINED&&sweet_gpu_write_state()==GMB_QUARANTINED&&ggwb_context.state==3&&sweet_gpu_unsecure_state()==GMB_QUARANTINED&&ggub_context.state==3&&
  sweet_gpu_zap_state()==GMB_QUARANTINED&&sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&
  sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&
  z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
 unsigned reads=ibf.reads,stores=ibf.stores,budgets=ibf.budgets;
 CHECK(sweet_gpu_ib_once(&out)==(z.flag==4?GGI_ALREADY:GGI_ARGUMENT)&&!memcmp(&out,&saved,sizeof(out))&&reads==ibf.reads&&stores==ibf.stores&&budgets==ibf.budgets);
 ib_untouched();
}
static void ib_good(void)
{
 struct ggi_receipt out;unsigned maps=h.maps,nc=h.nc_maps,owner_calls=h.owner_calls;
 enum ggi_result rc=sweet_gpu_ib_once(&out);
 if(rc!=GGI_OK)fprintf(stderr,"IB refusal: rc=%u phase=%u reason=%u guard_phase=%u mode=%u/%u sample=%u/%05x expected=%08x actual=%08x stores=%u memstores=%u memreads=%u\n",rc,ggib_context.phase,ggib_diagnostic.reason,ggib_diagnostic.phase,ggb_data_mode,z.flag,ggib_context.diagnostic.memory,ggib_context.diagnostic.reg,ggib_context.diagnostic.expected,ggib_context.diagnostic.actual,ibf.stores,ibf.memstores,ibf.memreads);
 CHECK(rc==GGI_OK&&sweet_gpu_ib_state()==GMB_READY&&ibf.complete==1&&!ibf.partial&&h.live&&!h.quarantine);
 CHECK(out.complete==1&&out.sealed==1&&out.requests_retained==1&&out.prefix_checked==20&&out.clean_checked==7&&out.commands_written==7&&out.commands_checked==7&&out.ib_clean_checked==8&&out.ib_written==8&&out.ib_checked==8&&out.ib_after_checked==8);
 CHECK(out.initial_wptr==20&&out.initial_shadow==20&&out.rptr==27&&out.writes==ibf.drop+3&&out.fence_checks==ibf.drop+1&&ibf.memstores==15&&ibf.submits==ibf.drop+1&&!ibf.kept);
 CHECK(out.data_before_checked==1024&&out.data_after_checked==1024&&out.edge_checked==2&&out.unchanged_checked==1022&&out.ring_after_checked==27);
 CHECK(ggib_samples==15&&!ggib_before_first&&!ggib_before_last&&ggib_after_first==0x47494231&&ggib_after_last==0x47494232&&ggib_diagnostic.reason==IGD_NONE);
 CHECK(ibf.memreads==2134+ibf.shadow_reads&&ibf.device_writes==2&&h.maps==maps&&h.nc_maps==nc&&h.owner_calls==owner_calls);
 for(unsigned i=0;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb8000+4*i,4);CHECK(v==(i==0?0x47494231u:i==1023?0x47494232u:0));}
 ib_untouched();unsigned reads=ibf.reads,stores=ibf.stores,budgets=ibf.budgets;
 CHECK(sweet_gpu_ib_once(&out)==GGI_ALREADY&&reads==ibf.reads&&stores==ibf.stores&&budgets==ibf.budgets);
}
static void gpu_ib_cases(void)
{
 unsigned first=cases;
 for(unsigned scenario=0;scenario<5;scenario++){
  ib_setup();ibf.drop=scenario==1?1:scenario==2?100:scenario==3?199:0;ibf.wrap=scenario==4;
  if(scenario==1)ibf.shadow_delay=ibf.busy_delay=2;ib_good();
 }
 for(unsigned phase=GGI_SEAL;phase<=GGI_FINAL;phase++)for(unsigned kind=1;kind<=34;kind++){
  ib_setup();ibf.phase=phase;ibf.kind=kind;ib_failed();CHECK(ibf.fired);
 }
 for(unsigned n=1;n<=18;n++){
  ib_setup();ibf.stop_store=n;ib_failed();CHECK(ibf.stores==n);
  ib_setup();ibf.expire_store=n;ib_failed();CHECK(ibf.stores==n);
 }
 for(unsigned n=1;n<=15;n++){ib_setup();ibf.drop_write=n;ib_failed();CHECK(!ibf.submits);}
 for(unsigned phase=GGI_CAPTURE;phase<=GGI_VERIFY;phase++)if(phase==GGI_CAPTURE||phase==GGI_COMMANDS||phase==GGI_VERIFY)
  for(unsigned n=0;n<8;n++){ib_setup();ibf.corrupt_phase=phase;ibf.corrupt_mem=GGI_IB;ibf.corrupt_off=4*n;ib_failed();}
 const unsigned offsets[]={0,4,2048,4088,4092};
 for(unsigned phase=GGI_CAPTURE;phase<=GGI_VERIFY;phase++)if(phase==GGI_CAPTURE||phase==GGI_VERIFY)
  for(unsigned n=0;n<5;n++){ib_setup();ibf.corrupt_phase=phase;ibf.corrupt_mem=GGI_DATA;ibf.corrupt_off=offsets[n];ib_failed();}
 for(unsigned n=0;n<5;n++){ib_setup();ibf.corrupt_data=offsets[n]/4+1;ib_failed();}
 for(unsigned n=1;n<=2;n++){ib_setup();ibf.drop_data=n;ib_failed();}
 for(unsigned n=0;n<8;n++)for(unsigned kind=1;kind<=2;kind++){ib_setup();ibf.nc_kind=kind;ibf.nc_page=n;ib_failed();CHECK(!ibf.stores);}
 for(unsigned n=1;n<=8;n++){ib_setup();ibf.phys_bad=n;ib_failed();CHECK(!ibf.stores);}
 /* Every permission/address bit of the DATA PTE is checked through the
  * actual live guard, independently of the pure full-table matcher cases. */
 for(unsigned bit=0;bit<64;bit++){
  ib_setup();ram[0x9c000+0x2000+24*8+bit/8]^=1u<<(bit%8);ib_failed();CHECK(!ibf.stores);
 }
 ib_setup();ibf.drop=200;ib_failed();CHECK(ibf.kept&&ibf.submits==201&&ibf.fences==200);
 ib_setup();ibf.bad_shadow=8192;ib_failed();
 ib_setup();ibf.budget_fail=1;ib_failed();CHECK(ggib_diagnostic.reason==IGD_ENTRY_BUDGET&&!ibf.stores&&!ibf.memreads);
 ib_setup();ibf.time_step=1000000;ib_failed();CHECK(ggib_diagnostic.reason==IGD_TIME);
 /* No public/caller flag may upgrade an already cold18-leaf boot. */
 unsecure_setup();z.flag=4;unsecure_failed();CHECK(!u.stores);
 write_signed_setup();z.flag=4;unsecure_failed();CHECK(!u.stores);
 ib_signed_setup();z.flag=3;unsecure_failed();CHECK(!u.stores);
 ib_signed_setup();ram[0x9c000+0x2000+24*8]^=0x40;unsecure_failed();CHECK(!u.stores);
 for(unsigned mode=0;mode<4;mode++){
  ib_setup();z.flag=(int)mode;struct ggi_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned budgets=h.budgets;
  CHECK(sweet_gpu_ib_once(&out)==GGI_ARGUMENT&&!memcmp(&out,&old,sizeof(out))&&ggib_lifecycle==GMB_IDLE&&budgets==h.budgets&&!ibf.stores);
 }
 ib_setup();
 for(unsigned phase=GGI_IDLE;phase<=GGI_DONE;phase++){
  ggib_context.phase=phase;
  for(unsigned mem=0;mem<=4;mem++)for(unsigned off=0;off<=4096;off+=4)for(unsigned write=0;write<=1;write++){
   bool ring=mem==GGI_RING&&off<108,scratch=mem==GGI_SCRATCH&&!off,data=mem==GGI_DATA&&off<4096,cmd=ring&&off>=80,ib=mem==GGI_IB&&off<32;
   bool allowed=write?(phase==GGI_COMMANDS&&(cmd||ib)):
    ((phase==GGI_CAPTURE&&(ring||scratch||data||ib))||(phase==GGI_COMMANDS&&(cmd||ib))||(phase==GGI_WAIT&&scratch)||(phase==GGI_VERIFY&&(ring||data||ib)));
   CHECK(!!ggib_memory((enum ggi_memory)mem,off,write)==allowed);
  }
 }
 ggib_context.phase=GGI_IDLE;CHECK(!ggib_memory(GGI_DATA,1,false)&&!ggib_memory(GGI_RING,UINT32_MAX,false));
 CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));
 printf("GPU fixed IB live board: %u actual coldDATA19+CP+ZAP+GGU+GGI/PROT_NONE/fault/PTE/NC/private-parent/once cases PASS; source/model only, no hardware IB proof\n",cases-first);
}
