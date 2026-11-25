/* Additional actual CP+ZAP+GGU+GGE integration; primitive hardware/owner seams
 * remain explicit. Secure first CPU page stays PROT_NONE after AUTH. */
static bool host_eop_active(void)
{
 return eopf.active&&z.auth_done&&z.flag==5&&sweet_gpu_eop_state()==GMB_RUNNING&&
  ((ggeb_context.state==1&&ggeb_context.phase>=GGE_SEAL&&ggeb_context.phase<=GGE_FINAL)||
   (ggeb_context.state==2&&ggeb_context.phase==GGE_DONE&&ggeb_phase==GGE_FINAL));
}
static void host_eop_budget(void)
{
 if(!eopf.active)return;++eopf.budgets;if(eopf.time_step)h.now+=eopf.time_step;
 if(eopf.budgets==eopf.budget_fail)h.live=false;
 if(!eopf.kind||eopf.fired||ggeb_context.state!=1||ggeb_context.phase!=eopf.phase)return;
 eopf.fired=1;uint32_t v=1;uint64_t q;
 switch(eopf.kind){
 case 1:h.clock_bad=1;break;case 2:h.irq_bad=1;break;case 3:memcpy(reset_page+0x2000,&v,4);break;
 case 4:memcpy(smmu+0x48,&v,4);break;case 5:v=1u<<9;memcpy(core_page+4*0x201,&v,4);break;
 case 6:memcpy(core_page+4*0x823,&v,4);break;case 7:h.now=ggeb_deadline;break;case 8:h.now=ggeb_phase_end;break;
 case 9:eopf.owner_bad=1;break;case 10:ggub_work.prefix_checked=14;ggub_context.work=ggub_work;break;
 case 11:gfw_context.dcvs_return=1;break;case 12:core_attr_bad=1;break;case 13:ggc_alias[0]++;break;
 case 14:h.context=1;break;case 15:q=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&q,8);break;
 case 16:v=1u<<24;memcpy(reset_page+0x2648,&v,4);break;case 17:ggc_work.mem_compared=1023;break;
 case 18:h.now=ggeb_last_now?ggeb_last_now-1:UINT64_MAX;break;
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
 default:CHECK(false);
 }
}
static void host_eop_device(void)
{
 CHECK(eopf.accepted&&!eopf.device_done&&eopf.submits&&eopf.kept);eopf.device_done=1;
 uint32_t direct[4];memcpy(direct,ram+0xa8000+80,sizeof(direct));
 CHECK(direct[0]==0x70bf8003&&direct[1]==0xfc00c000&&!direct[2]&&direct[3]==8&&!(direct[3]&(1u<<20)));
 for(unsigned i=0;i<2;i++){
  uint32_t p[4];memcpy(p,ram+0xac000+16*i,sizeof(p));CHECK(p[0]==0x703d8003);
  uint64_t va=(uint64_t)p[1]|((uint64_t)p[2]<<32);CHECK(va>=0xfc018000&&va<=0xfc018ffc&&!(va&3));
  if(eopf.drop_data!=i+1)memcpy(ram+0xb8000+va-0xfc018000,&p[3],4);++eopf.device_writes;
 }

}
static void host_eop_event(void)
{
 CHECK(eopf.device_done&&!eopf.eop_done&&eopf.submits&&!eopf.kept);
 uint32_t p[5];memcpy(p,ram+0xa8000+96,sizeof(p));CHECK(p[0]==0x70460004&&p[1]==4&&!(p[1]&(1u<<31))&&p[2]==0xfc018004&&!p[3]&&p[4]==0x47455031);
 uint32_t value=eopf.bad_eop?eopf.bad_eop:p[4];memcpy(ram+0xb8004,&value,4);eopf.eop_done=1;++eopf.device_writes;
 if(eopf.corrupt_data){CHECK(eopf.corrupt_data<=1024);ram[0xb8000+4*(eopf.corrupt_data-1)]^=1;}
}
static void host_eop_read(vm_offset_t address,uint32_t *value)
{
 if(!eopf.active)return;CHECK(host_eop_active());++eopf.reads;
 if(address==(uintptr_t)fw_page[0]+0x2c4c){
  *value=eopf.fences++<eopf.drop?3:2;if(!(*value&1)){eopf.accepted=1;if(!eopf.device_done)host_eop_device();}
 }
 if(address==(uintptr_t)fw_page[0]+0x2c30)*value=ggeb_context.phase==GGE_WAIT&&eopf.busy_reads++<eopf.busy_delay?0x71800000:0x71000000;
 if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
  unsigned n=eopf.counter_reads++;*value=!eopf.wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
   n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
 }
 bool ring=address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb0000;
 bool scratch=address==(uintptr_t)ram+0xb0000;
 bool data=address>=(uintptr_t)ram+0xb8000&&address<(uintptr_t)ram+0xb9000;
 if(ring||scratch||data){
  ++eopf.memreads;
  if(ggeb_context.phase==GGE_WAIT&&scratch){CHECK(scratch&&eopf.accepted&&eopf.submits&&!eopf.kept&&eopf.device_done);
   if(eopf.shadow_reads++>=eopf.shadow_delay){*value=eopf.bad_shadow?eopf.bad_shadow:32;memcpy(ram+0xb0000,value,4);}}
  if(ggeb_context.phase==GGE_WAIT&&data){
   CHECK(address==(uintptr_t)ram+0xb8004&&eopf.device_done&&!eopf.kept&&eopf.shadow_reads);
   if(eopf.eop_reads++>=eopf.eop_delay&&!eopf.drop_eop&&!eopf.eop_done)host_eop_event();
   memcpy(value,(void *)address,4);
  }
  bool ib=address>=(uintptr_t)ram+0xac000&&address<(uintptr_t)ram+0xac020;
  unsigned mem=ib?GGE_IB:ring?GGE_RING:scratch?GGE_SCRATCH:GGE_DATA;
  unsigned off=(unsigned)(address-(uintptr_t)ram-(ib?0xac000:ring?0xa8000:scratch?0xb0000:0xb8000));
  if(ggeb_context.phase==eopf.corrupt_phase&&mem==eopf.corrupt_mem&&off==eopf.corrupt_off)*value^=1;
 }
}
static bool host_eop_store(vm_offset_t address,uint32_t value)
{
 if(!eopf.active)return false;CHECK(host_eop_active());++eopf.stores;
 if(address>=(uintptr_t)ram&&address<(uintptr_t)ram+sizeof(ram)){
  CHECK(ggeb_context.phase==GGE_COMMANDS&&eopf.memstores<20);
  bool indirect=eopf.memstores<8;unsigned n=indirect?eopf.memstores:eopf.memstores-8;
  CHECK(address==(uintptr_t)ram+(indirect?0xac000:0xa8000+80)+4*n&&value==(indirect?ggeb_context.command.ib[n]:ggeb_context.command.word[n]));
  ++eopf.memstores;if(eopf.memstores!=eopf.drop_write)memcpy((void *)address,&value,4);
 }else{
  uint32_t reg=host_core_reg(address);CHECK(ggeb_context.phase==GGE_SUBMIT&&gge_register_allowed(reg,true)&&eopf.memstores==20&&ggeb_context.work.commands_checked==12&&ggeb_context.work.ib_checked==8);
  if(reg==0x807){CHECK(value==32&&eopf.kept);++eopf.submits;}else{CHECK(value<=1);eopf.kept=value;}
  memcpy((void *)address,&value,4);
 }
 if(eopf.stores==eopf.stop_store)h.clock_bad=1;if(eopf.stores==eopf.expire_store)h.now=ggeb_phase_end;
 return true;
}
static void eop_signed_setup(void)
{
 fixture_gpu_mode=5;cp_setup(0);fixture_gpu_mode=0;
 struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;
 CHECK(z.flag==5&&ggb_data_selected==1&&ggb_data_ready==1&&ggb_smmu.layout==GGS_DATA19&&ggb_smmu.gpu_pages==19&&ggb_smmu.translations==171);
 CHECK(ggd_tables_match(&ggb_data_plan,ram+0x9c000,16384));
 for(unsigned i=0xb8000;i<0xbc000;i++)CHECK(ram[i]==0);
 struct gpz_receipt signed_load;CHECK(sweet_gpu_zap_once(&signed_load)==GPZ_OK);cp_active=0;u.active=1;
 CHECK(!mprotect(ram,16384,PROT_NONE));
}
static void eop_setup(void)
{
 eop_signed_setup();unsecure_good();u.active=0;eopf.active=1;
 CHECK(ggub_context.state==2&&ggub_work.rptr==20&&ggeb_lifecycle==GMB_IDLE&&ggeb_context.state==0);
}
static void eop_untouched(void)
{
 CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60)&&!memcmp(ram+0xa8000+60,ggub_context.command.word,20));
 for(unsigned i=32;i<8192;i++)if(i<4096||i>=4104){uint32_t v;memcpy(&v,ram+0xa8000+4*i,4);CHECK(v==0xaaaaaaaa);}
 for(unsigned i=1;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb0000+4*i,4);CHECK(v==0);}
 for(unsigned i=0xb9000;i<0xbc000;i++)CHECK(ram[i]==0);
}
static void eop_failed(void)
{
 struct gge_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 CHECK(sweet_gpu_eop_once(&out)!=GGE_OK&&!memcmp(&out,&saved,sizeof(out))&&eopf.partial==1&&!eopf.complete);
 CHECK(sweet_gpu_eop_state()==GMB_QUARANTINED&&sweet_gpu_write_state()==GMB_QUARANTINED&&ggwb_context.state==3&&sweet_gpu_ib_state()==GMB_QUARANTINED&&ggib_context.state==3&&sweet_gpu_unsecure_state()==GMB_QUARANTINED&&ggub_context.state==3&&
  sweet_gpu_zap_state()==GMB_QUARANTINED&&sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&
  sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&
  z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
 unsigned reads=eopf.reads,stores=eopf.stores,budgets=eopf.budgets;
 CHECK(sweet_gpu_eop_once(&out)==(z.flag==5?GGE_ALREADY:GGE_ARGUMENT)&&!memcmp(&out,&saved,sizeof(out))&&reads==eopf.reads&&stores==eopf.stores&&budgets==eopf.budgets);
 eop_untouched();
}
static void eop_good(void)
{
 struct gge_receipt out;unsigned maps=h.maps,nc=h.nc_maps,owner_calls=h.owner_calls;
 enum gge_result rc=sweet_gpu_eop_once(&out);
 if(rc!=GGE_OK)fprintf(stderr,"IB refusal: rc=%u phase=%u reason=%u guard_phase=%u mode=%u/%u sample=%u/%05x expected=%08x actual=%08x stores=%u memstores=%u memreads=%u\n",rc,ggeb_context.phase,ggeb_diagnostic.reason,ggeb_diagnostic.phase,ggb_data_mode,z.flag,ggeb_context.diagnostic.memory,ggeb_context.diagnostic.reg,ggeb_context.diagnostic.expected,ggeb_context.diagnostic.actual,eopf.stores,eopf.memstores,eopf.memreads);
 CHECK(rc==GGE_OK&&sweet_gpu_eop_state()==GMB_READY&&eopf.complete==1&&!eopf.partial&&h.live&&!h.quarantine);
 CHECK(out.complete==1&&out.sealed==1&&out.requests_retained==1&&out.prefix_checked==20&&out.clean_checked==12&&out.commands_written==12&&out.commands_checked==12&&out.ib_clean_checked==8&&out.ib_written==8&&out.ib_checked==8&&out.ib_after_checked==8);
 CHECK(out.initial_wptr==20&&out.initial_shadow==20&&out.rptr==32&&out.writes==eopf.drop+3&&out.fence_checks==eopf.drop+1&&eopf.memstores==20&&eopf.submits==eopf.drop+1&&!eopf.kept);
 CHECK(out.data_before_checked==1024&&out.data_after_checked==1024&&out.edge_checked==2&&out.unchanged_checked==1021&&out.eop_checked==1&&out.eop_complete==1&&out.eop_value==0x47455031&&out.eop_polls==eopf.eop_delay+1&&out.ring_after_checked==32);
 CHECK(ggeb_samples==63&&!ggeb_before_first&&!ggeb_before_last&&!ggeb_before_eop&&ggeb_after_eop==0x47455031&&ggeb_after_first==0x47455032&&ggeb_after_last==0x47455033&&ggeb_diagnostic.reason==EGD_NONE);
 CHECK(eopf.memreads==2149+eopf.shadow_reads+eopf.eop_reads&&eopf.device_writes==3&&h.maps==maps&&h.nc_maps==nc&&h.owner_calls==owner_calls);
 for(unsigned i=0;i<1024;i++){uint32_t v;memcpy(&v,ram+0xb8000+4*i,4);CHECK(v==(i==0?0x47455032u:i==1023?0x47455033u:i==1?0x47455031u:0));}
 eop_untouched();unsigned reads=eopf.reads,stores=eopf.stores,budgets=eopf.budgets;
 CHECK(sweet_gpu_eop_once(&out)==GGE_ALREADY&&reads==eopf.reads&&stores==eopf.stores&&budgets==eopf.budgets);
}
static void gpu_eop_cases(void)
{
 unsigned first=cases;
 for(unsigned scenario=0;scenario<5;scenario++){
  eop_setup();eopf.drop=scenario==1?1:scenario==2?100:scenario==3?199:0;eopf.wrap=scenario==4;
  if(scenario==1)eopf.shadow_delay=eopf.busy_delay=eopf.eop_delay=2;eop_good();
 }
 for(unsigned phase=GGE_SEAL;phase<=GGE_FINAL;phase++)for(unsigned kind=1;kind<=39;kind++){
  eop_setup();eopf.phase=phase;eopf.kind=kind;eop_failed();CHECK(eopf.fired);
 }
 for(unsigned n=1;n<=23;n++){
  eop_setup();eopf.stop_store=n;eop_failed();CHECK(eopf.stores==n);
  eop_setup();eopf.expire_store=n;eop_failed();CHECK(eopf.stores==n);
 }
 for(unsigned n=1;n<=20;n++){eop_setup();eopf.drop_write=n;eop_failed();CHECK(!eopf.submits);}
 for(unsigned phase=GGE_CAPTURE;phase<=GGE_VERIFY;phase++)if(phase==GGE_CAPTURE||phase==GGE_COMMANDS||phase==GGE_VERIFY)
  for(unsigned n=0;n<8;n++){eop_setup();eopf.corrupt_phase=phase;eopf.corrupt_mem=GGE_IB;eopf.corrupt_off=4*n;eop_failed();}
 const unsigned offsets[]={0,4,2048,4088,4092};
 for(unsigned phase=GGE_CAPTURE;phase<=GGE_VERIFY;phase++)if(phase==GGE_CAPTURE||phase==GGE_VERIFY)
  for(unsigned n=0;n<5;n++){eop_setup();eopf.corrupt_phase=phase;eopf.corrupt_mem=GGE_DATA;eopf.corrupt_off=offsets[n];eop_failed();}
 for(unsigned n=0;n<5;n++){eop_setup();eopf.corrupt_data=offsets[n]/4+1;eop_failed();}
 for(unsigned n=1;n<=2;n++){eop_setup();eopf.drop_data=n;eop_failed();}
 for(unsigned n=0;n<8;n++)for(unsigned kind=1;kind<=2;kind++){eop_setup();eopf.nc_kind=kind;eopf.nc_page=n;eop_failed();CHECK(!eopf.stores);}
 for(unsigned n=1;n<=8;n++){eop_setup();eopf.phys_bad=n;eop_failed();CHECK(!eopf.stores);}
 /* Every permission/address bit of the DATA PTE is checked through the
  * actual live guard, independently of the pure full-table matcher cases. */
 for(unsigned bit=0;bit<64;bit++){
  eop_setup();ram[0x9c000+0x2000+24*8+bit/8]^=1u<<(bit%8);eop_failed();CHECK(!eopf.stores);
 }
 for(unsigned delay=1;delay<=8;delay*=2){eop_setup();eopf.eop_delay=delay;eop_good();}
 eop_setup();eopf.drop_eop=1;eop_failed();CHECK(eopf.eop_reads==1024&&eopf.shadow_reads&&eopf.device_writes==2&&!eopf.kept);
 eop_setup();eopf.bad_eop=1;eop_failed();CHECK(eopf.eop_reads==1);
 eop_setup();eopf.corrupt_phase=GGE_WAIT;eopf.corrupt_mem=GGE_DATA;eopf.corrupt_off=4;eop_failed();
 eop_setup();eopf.drop=200;eop_failed();CHECK(eopf.kept&&eopf.submits==201&&eopf.fences==200);
 eop_setup();eopf.bad_shadow=8192;eop_failed();
 eop_setup();eopf.budget_fail=1;eop_failed();CHECK(ggeb_diagnostic.reason==EGD_ENTRY_BUDGET&&!eopf.stores&&!eopf.memreads);
 eop_setup();eopf.time_step=1000000;eop_failed();CHECK(ggeb_diagnostic.reason==EGD_TIME);
 /* No public/caller flag may upgrade an already cold18-leaf boot. */
 unsecure_setup();z.flag=4;unsecure_failed();CHECK(!u.stores);
 write_signed_setup();z.flag=5;unsecure_failed();CHECK(!u.stores);
 ib_signed_setup();z.flag=5;unsecure_failed();CHECK(!u.stores);
 eop_signed_setup();z.flag=4;unsecure_failed();CHECK(!u.stores);
 eop_signed_setup();ram[0x9c000+0x2000+24*8]^=0x40;unsecure_failed();CHECK(!u.stores);
 for(unsigned mode=0;mode<5;mode++){
  eop_setup();z.flag=(int)mode;struct gge_receipt out,old;memset(&out,0xa5,sizeof(out));old=out;unsigned budgets=h.budgets;
  CHECK(sweet_gpu_eop_once(&out)==GGE_ARGUMENT&&!memcmp(&out,&old,sizeof(out))&&ggeb_lifecycle==GMB_IDLE&&budgets==h.budgets&&!eopf.stores);
 }
 eop_setup();
 for(unsigned phase=GGE_IDLE;phase<=GGE_DONE;phase++){
  ggeb_context.phase=phase;
  for(unsigned mem=0;mem<=4;mem++)for(unsigned off=0;off<=4096;off+=4)for(unsigned write=0;write<=1;write++){
   bool ring=mem==GGE_RING&&off<128,scratch=mem==GGE_SCRATCH&&!off,data=mem==GGE_DATA&&off<4096,cmd=ring&&off>=80,ib=mem==GGE_IB&&off<32;
   bool allowed=write?(phase==GGE_COMMANDS&&(cmd||ib)):
    ((phase==GGE_CAPTURE&&(ring||scratch||data||ib))||(phase==GGE_COMMANDS&&(cmd||ib))||(phase==GGE_WAIT&&(scratch||(data&&off==4)))||(phase==GGE_VERIFY&&(ring||data||ib)));
   CHECK(!!ggeb_memory((enum gge_memory)mem,off,write)==allowed);
  }
 }
 ggeb_context.phase=GGE_IDLE;CHECK(!ggeb_memory(GGE_DATA,1,false)&&!ggeb_memory(GGE_RING,UINT32_MAX,false));
 CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));
 printf("GPU native EOP live board: %u actual coldDATA19+CP+ZAP+GGU+GGE/PROT_NONE/fault/PTE/NC/private-parent/once cases PASS; source/model only, no hardware EOP proof\n",cases-first);
}
