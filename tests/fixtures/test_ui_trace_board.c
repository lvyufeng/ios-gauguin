#define GUT_BOARD_HOST_TEST 1
#include GUT_BOARD_SOURCE

int main(int argc,char **argv)
{
 assert(argc==2);
 if(!strcmp(argv[1],"off"))selector=0;
 else if(!strcmp(argv[1],"bad"))selector=17;
 else if(!strcmp(argv[1],"profile")){selector=1;desktop=false;}
 else if(!strcmp(argv[1],"alloc")){selector=1;allocation_fails=true;}
 else selector=2;
 sweet_ui_trace_init();
 if(selector!=2) {
  sweet_ui_trace_record(10,1,1,0,0,0,0);sweet_ui_trace_drain();
  assert(!sweet_ui_trace_clock()&&!gut_enabled(&trace)&&!clocks);
  assert(allocations==(allocation_fails?1u:0u)&&!frees);return 0;
 }
 assert(gut_enabled(&trace)&&allocations==1&&!frees);
 assert(!sweet_ui_trace_report(900000,990000,0,1));
 assert(!sweet_ui_trace_report(900000,990000,0,0));
 assert(!trace.count);
 uint64_t id=sweet_ui_trace_report(900000,990000,0,1);assert(id==1);
 board_ticks+=100;sweet_ui_trace_record(GUT_HID_BEGIN,id,0,1,board_ticks,0,0);
 board_ticks+=50;sweet_ui_trace_record(GUT_HID_END,id,0,1,board_ticks-50,0,0);
 sweet_ui_trace_record(GUT_HID_RETURN,id,0,0,1,0,0);
 board_ticks+=100;sweet_ui_trace_record(GUT_API_BEGIN,9,61,0x46,board_ticks-10,board_ticks,0);
 sweet_ui_trace_record(GUT_SUBMIT_BEGIN,9,61,1,4,1,0);
 board_ticks+=1000;sweet_ui_trace_record(GUT_SURFACE,9,61,2,77,6,1);
 sweet_ui_trace_record(GUT_SUBMIT_END,9,61,0,1,6,6);
 sweet_ui_trace_record(GUT_API_END,9,61,0,board_ticks,0x46,0);
 sweet_ui_trace_record(GUT_SWAP,8,0,0,1,1,0);
 sweet_ui_trace_record(GUT_PRESENT_BEGIN,8,0,0,1,0,0);
 sweet_ui_trace_record(GUT_LAYER,8,0,0,77,1080,2400);
 sweet_ui_trace_record(GUT_READ_LOCK,77,0,0,board_ticks,0,0);
 board_ticks+=300;sweet_ui_trace_record(GUT_READ_END,77,0,0,0,0,0);
 sweet_ui_trace_record(GUT_PRESENT_END,8,0,0,1,0,0);
 if(!strcmp(argv[1],"loss")){trace.busy=1;sweet_ui_trace_record(10,99,1,0,0,0,0);trace.busy=0;}
 board_ticks=trace.end;
 sweet_ui_trace_drain();sweet_ui_trace_drain();sweet_ui_trace_drain();
 assert(footer&&trace.state==GUT_DRAINED&&trace.count==15);
 assert(trace.lost_final==(!strcmp(argv[1],"loss")?1u:0u));
 free(trace.events);return 0;
}
