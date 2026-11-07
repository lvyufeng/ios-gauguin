/* Additional actual CP+ZAP+GGU+GGW integration; primitive hardware/owner seams
 * remain explicit. Secure first CPU page stays PROT_NONE after AUTH. */
static bool host_write_active(void)
{
 return w.active&&z.auth_done&&z.flag==3&&sweet_gpu_write_state()==GMB_RUNNING&&
  ((ggwb_context.state==1&&ggwb_context.phase>=GGW_SEAL&&ggwb_context.phase<=GGW_FINAL)||
   (ggwb_context.state==2&&ggwb_context.phase==GGW_DONE&&ggwb_phase==GGW_FINAL));
}
static void host_write_budget(void)
{
 if(!w.active)return;++w.budgets;if(w.time_step)h.now+=w.time_step;
 if(w.budgets==w.budget_fail)h.live=false;
 if(!w.kind||w.fired||ggwb_context.state!=1||ggwb_context.phase!=w.phase)return;
 w.fired=1;uint32_t v=1;uint64_t q;
 switch(w.kind){
 case 1:h.clock_bad=1;break;case 2:h.irq_bad=1;break;case 3:memcpy(reset_page+0x2000,&v,4);break;
 case 4:memcpy(smmu+0x48,&v,4);break;case 5:v=1u<<9;memcpy(core_page+4*0x201,&v,4);break;
 case 6:memcpy(core_page+4*0x823,&v,4);break;case 7:h.now=ggwb_deadline;break;case 8:h.now=ggwb_phase_end;break;
 case 9:w.owner_bad=1;break;case 10:ggub_work.prefix_checked=14;ggub_context.work=ggub_work;break;
 case 11:gfw_context.dcvs_return=1;break;case 12:core_attr_bad=1;break;case 13:ggc_alias[0]++;break;
 case 14:h.context=1;break;case 15:q=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&q,8);break;
 case 16:v=1u<<24;memcpy(reset_page+0x2648,&v,4);break;case 17:ggc_work.mem_compared=1023;break;
 case 18:h.now=ggwb_last_now?ggwb_last_now-1:UINT64_MAX;break;
 case 19:cp_nc_bad=2;cp_nc_page=1;break;case 20:cp_nc_bad=1;cp_nc_page=3;break;case 21:cp_dev_bad=1;break;
 case 22:ggb_data_ready=0;break;
 case 23:ram[0x9c000+0x2000+24*8]^=0x40;break;
 case 24:ram[0x9c000]^=1;break;
 case 25:ggb_data_selected=0;break;
 case 26:ggb_smmu.layout=GGS_BOOTSTRAP18;ggb_context.work=ggb_smmu;break;
 case 27:ggub_work.rptr=19;ggub_context.work=ggub_work;break;
 case 28:ggub_work.counter_before_valid=0;ggub_context.work=ggub_work;break;
 case 29:ggub_context.state=1;break;case 30:z.owner_state=PSZ_COPIED;break;
 default:CHECK(false);
 }
}
static void host_write_device(void)
{
 CHECK(w.accepted&&!w.device_done&&w.submits&&w.kept);w.device_done=1;
 for(unsigned i=0;i<2;i++){
  uint32_t p[4];memcpy(p,ram+0xa8000+80+16*i,sizeof(p));CHECK(p[0]==0x703d8003);
  uint64_t va=(uint64_t)p[1]|((uint64_t)p[2]<<32);CHECK(va>=0xfc018000&&va<=0xfc018ffc&&!(va&3));
  if(w.drop_data!=i+1)memcpy(ram+0xb8000+va-0xfc018000,&p[3],4);++w.device_writes;
 }
 if(w.corrupt_data){CHECK(w.corrupt_data<=1024);ram[0xb8000+4*(w.corrupt_data-1)]^=1;}
}
static void host_write_read(vm_offset_t address,uint32_t *value)
{
 if(!w.active)return;CHECK(host_write_active());++w.reads;
 if(address==(uintptr_t)fw_page[0]+0x2c4c){
  *value=w.fences++<w.drop?3:2;if(!(*value&1)){w.accepted=1;if(!w.device_done)host_write_device();}
 }
 if(address==(uintptr_t)fw_page[0]+0x2c30)*value=ggwb_context.phase==GGW_WAIT&&w.busy_reads++<w.busy_delay?0x71800000:0x71000000;
 if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
  unsigned n=w.counter_reads++;*value=!w.wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
   n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
 }
 bool ring=address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb0000;
 bool scratch=address==(uintptr_t)ram+0xb0000;
 bool data=address>=(uintptr_t)ram+0xb8000&&address<(uintptr_t)ram+0xb9000;
 if(ring||scratch||data){
  ++w.memreads;
  if(ggwb_context.phase==GGW_WAIT){CHECK(scratch&&w.accepted&&w.submits&&!w.kept&&w.device_done);
   if(w.shadow_reads++>=w.shadow_delay){*value=w.bad_shadow?w.bad_shadow:31;memcpy(ram+0xb0000,value,4);}}
  unsigned mem=ring?GGW_RING:scratch?GGW_SCRATCH:GGW_DATA;
  unsigned off=(unsigned)(address-(uintptr_t)ram-(ring?0xa8000:scratch?0xb0000:0xb8000));
  if(ggwb_context.phase==w.corrupt_phase&&mem==w.corrupt_mem&&off==w.corrupt_off)*value^=1;
 }
}
static bool host_write_store(vm_offset_t address,uint32_t value)
{
 if(!w.active)return false;CHECK(host_write_active());++w.stores;
 if(address>=(uintptr_t)ram&&address<(uintptr_t)ram+sizeof(ram)){
  CHECK(ggwb_context.phase==GGW_COMMANDS&&w.memstores<11&&address==(uintptr_t)ram+0xa8000+80+4*w.memstores&&value==ggwb_context.command.word[w.memstores]);
  ++w.memstores;if(w.memstores!=w.drop_write)memcpy((void *)address,&value,4);
 }else{
  uint32_t reg=host_core_reg(address);CHECK(ggwb_context.phase==GGW_SUBMIT&&ggw_register_allowed(reg,true)&&w.memstores==11&&ggwb_context.work.commands_checked==11);
  if(reg==0x807){CHECK(value==31&&w.kept);++w.submits;}else{CHECK(value<=1);w.kept=value;}
  memcpy((void *)address,&value,4);
 }
 if(w.stores==w.stop_store)h.clock_bad=1;if(w.stores==w.expire_store)h.now=ggwb_phase_end;
 return true;
}
static void write_signed_setup(void)
{
 fixture_gpu_mode=3;cp_setup(0);fixture_gpu_mode=0;
 struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
 CHECK(z.flag==3&&ggb_data_selected==1&&ggb_data_ready==1&&ggb_smmu.layout==GGS_DATA19&&ggb_smmu.gpu_pages==19&&ggb_smmu.translations==171);
 CHECK(ggd_tables_match(&ggb_data_plan,ram+0x9c000,16384));
 for(unsigned i=0xb8000;i<0xbc000;i++)CHECK(ram[i]==0);
 struct gpz_receipt signed_load;CHECK(sweet_gpu_zap_once(&signed_load)==GPZ_OK);cp_active=0;u.active=1;
 CHECK(!mprotect(ram,16384,PROT_NONE));
}
static void write_setup(void)
{
 write_signed_setup();unsecure_good();u.active=0;w.active=1;
 CHECK(ggub_context.state==2&&ggub_work.rptr==20&&ggwb_lifecycle==GMB_IDLE&&ggwb_context.state==0);
}
static void write_untouched(void)
{
 CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60)&&!memcmp(ram+0xa8000+60,ggub_context.command.word,20));
 for(unsigned i=31;i<8192;i++){uint32_t v;memcpy(&v,ram+0xa8000+4*i,4);CHECK(v==0xaaaaaaaa);}
 for(unsigned i=1;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb0000+4*i,4);CHECK(v==0);}
 for(unsigned i=0xb9000;i<0xbc000;i++)CHECK(ram[i]==0);
}
static void write_failed(void)
{
 struct ggw_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 CHECK(sweet_gpu_write_once(&out)!=GGW_OK&&!memcmp(&out,&saved,sizeof(out))&&w.partial==1&&!w.complete);
 CHECK(sweet_gpu_write_state()==GMB_QUARANTINED&&sweet_gpu_unsecure_state()==GMB_QUARANTINED&&ggub_context.state==3&&
  sweet_gpu_zap_state()==GMB_QUARANTINED&&sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&
  sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&
  z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
 unsigned reads=w.reads,stores=w.stores,budgets=w.budgets;
 CHECK(sweet_gpu_write_once(&out)==GGW_ALREADY&&!memcmp(&out,&saved,sizeof(out))&&reads==w.reads&&stores==w.stores&&budgets==w.budgets);
 write_untouched();
}
static void write_good(void)
{
 struct ggw_receipt out;unsigned maps=h.maps,nc=h.nc_maps,owner_calls=h.owner_calls;
 CHECK(sweet_gpu_write_once(&out)==GGW_OK&&sweet_gpu_write_state()==GMB_READY&&w.complete==1&&!w.partial&&h.live&&!h.quarantine);
 CHECK(out.complete==1&&out.sealed==1&&out.requests_retained==1&&out.prefix_checked==20&&out.clean_checked==11&&out.commands_written==11&&out.commands_checked==11);
 CHECK(out.initial_wptr==20&&out.initial_shadow==20&&out.rptr==31&&out.writes==w.drop+3&&out.fence_checks==w.drop+1&&w.memstores==11&&w.submits==w.drop+1&&!w.kept);
 CHECK(out.data_before_checked==1024&&out.data_after_checked==1024&&out.edge_checked==2&&out.unchanged_checked==1022&&out.ring_after_checked==31);
 CHECK(ggwb_samples==15&&!ggwb_before_first&&!ggwb_before_last&&ggwb_after_first==0x47504431&&ggwb_after_last==0x47504432&&ggwb_diagnostic.reason==WGD_NONE);
 CHECK(w.memreads==2122+w.shadow_reads&&w.device_writes==2&&h.maps==maps&&h.nc_maps==nc&&h.owner_calls==owner_calls);
 for(unsigned i=0;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb8000+4*i,4);CHECK(v==(i==0?0x47504431u:i==1023?0x47504432u:0));}
 write_untouched();unsigned reads=w.reads,stores=w.stores,budgets=w.budgets;
 CHECK(sweet_gpu_write_once(&out)==GGW_ALREADY&&reads==w.reads&&stores==w.stores&&budgets==w.budgets);
}
static void gpu_write_cases(void)
{
 unsigned first=cases;
 for(unsigned scenario=0;scenario<5;scenario++){
  write_setup();w.drop=scenario==1?1:scenario==2?100:scenario==3?199:0;w.wrap=scenario==4;
  if(scenario==1)w.shadow_delay=w.busy_delay=2;write_good();
 }
 for(unsigned phase=GGW_SEAL;phase<=GGW_FINAL;phase++)for(unsigned kind=1;kind<=30;kind++){
  write_setup();w.phase=phase;w.kind=kind;write_failed();CHECK(w.fired);
 }
 for(unsigned n=1;n<=14;n++){
  write_setup();w.stop_store=n;write_failed();CHECK(w.stores==n);
  write_setup();w.expire_store=n;write_failed();CHECK(w.stores==n);
 }
 for(unsigned n=1;n<=11;n++){write_setup();w.drop_write=n;write_failed();CHECK(!w.submits);}
 const unsigned offsets[]={0,4,2048,4088,4092};
 for(unsigned phase=GGW_CAPTURE;phase<=GGW_VERIFY;phase++)if(phase==GGW_CAPTURE||phase==GGW_VERIFY)
  for(unsigned n=0;n<5;n++){write_setup();w.corrupt_phase=phase;w.corrupt_mem=GGW_DATA;w.corrupt_off=offsets[n];write_failed();}
 for(unsigned n=0;n<5;n++){write_setup();w.corrupt_data=offsets[n]/4+1;write_failed();}
 for(unsigned n=1;n<=2;n++){write_setup();w.drop_data=n;write_failed();}
 for(unsigned n=0;n<8;n++)for(unsigned kind=1;kind<=2;kind++){write_setup();w.nc_kind=kind;w.nc_page=n;write_failed();CHECK(!w.stores);}
 for(unsigned n=1;n<=8;n++){write_setup();w.phys_bad=n;write_failed();CHECK(!w.stores);}
 /* Every permission/address bit of the DATA PTE is checked through the
  * actual live guard, independently of the pure full-table matcher cases. */
 for(unsigned bit=0;bit<64;bit++){
  write_setup();ram[0x9c000+0x2000+24*8+bit/8]^=1u<<(bit%8);write_failed();CHECK(!w.stores);
 }
 write_setup();w.drop=200;write_failed();CHECK(w.kept&&w.submits==201&&w.fences==200);
 write_setup();w.bad_shadow=8192;write_failed();
 write_setup();w.budget_fail=1;write_failed();CHECK(ggwb_diagnostic.reason==WGD_ENTRY_BUDGET&&!w.stores&&!w.memreads);
 write_setup();w.time_step=1000000;write_failed();CHECK(ggwb_diagnostic.reason==WGD_TIME);
 /* No public/caller flag may upgrade an already cold18-leaf boot. */
 unsecure_setup();z.flag=3;unsecure_failed();CHECK(!u.stores);
 write_signed_setup();ram[0x9c000+0x2000+24*8]^=0x40;unsecure_failed();CHECK(!u.stores);
 for(unsigned mode=0;mode<3;mode++){
  write_setup();z.flag=(int)mode;struct ggw_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned budgets=h.budgets;
  CHECK(sweet_gpu_write_once(&out)==GGW_ARGUMENT&&!memcmp(&out,&old,sizeof(out))&&ggwb_lifecycle==GMB_IDLE&&budgets==h.budgets&&!w.stores);
 }
 write_setup();
 for(unsigned phase=GGW_IDLE;phase<=GGW_DONE;phase++){
  ggwb_context.phase=phase;
  for(unsigned mem=0;mem<=3;mem++)for(unsigned off=0;off<=4096;off+=4)for(unsigned write=0;write<=1;write++){
   bool ring=mem==GGW_RING&&off<124,scratch=mem==GGW_SCRATCH&&!off,data=mem==GGW_DATA&&off<4096,cmd=ring&&off>=80;
   bool allowed=write?(phase==GGW_COMMANDS&&cmd):
    ((phase==GGW_CAPTURE&&(ring||scratch||data))||(phase==GGW_COMMANDS&&cmd)||(phase==GGW_WAIT&&scratch)||(phase==GGW_VERIFY&&(ring||data)));
   CHECK(!!ggwb_memory((enum ggw_memory)mem,off,write)==allowed);
  }
 }
 ggwb_context.phase=GGW_IDLE;CHECK(!ggwb_memory(GGW_DATA,1,false)&&!ggwb_memory(GGW_RING,UINT32_MAX,false));
 CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));
 printf("GPU ordinary write live board: %u actual coldDATA19+CP+ZAP+GGU+GGW/PROT_NONE/fault/PTE/NC/private-parent/once cases PASS; source/model only, no hardware data-write proof\n",cases-first);
}
