#include <array>
#include <cassert>
#include <cstdint>

struct ProcessorSet { int online_processor_count; };
struct Processor {
    ProcessorSet *processor_set;
    Processor *processor_primary;
    unsigned cpu_id;
    bool is_recommended;
    int state;
};
struct Thread { Processor *bound_processor; int sched_pri; uint64_t tid; };
using processor_set_t=ProcessorSet *;
using processor_t=Processor *;
using thread_t=Thread *;
constexpr processor_t PROCESSOR_NULL=nullptr;
constexpr int PROCESSOR_IDLE=2, PROCESSOR_RUNNING=3, BASEPRI_RTQUEUES=96;
static std::array<processor_t,8> processor_array;
static uint64_t gauguin_display_thread_398, gDisplayWriterThread398;
static uint32_t gDisplayIssueCpus398[8], gDisplayOtherWriter398;
static bool sampleActive, gapi_frozen, gDisplayPerformanceCpus398;
static unsigned activeSamples;
static Thread current;
static int current_cpu;
static uint64_t thread_tid(thread_t t) { return t->tid; }
static thread_t current_thread() { return &current; }
static int cpu_number() { return current_cpu; }
static bool sweet_frame344_clock() { ++activeSamples; return sampleActive; }

#include "Frame398Methods.inc"

int main()
{
    ProcessorSet local{8}, other{2};
    Processor cpu0{&local,nullptr,0,true,PROCESSOR_IDLE};
    Processor cpu6{&local,nullptr,6,true,PROCESSOR_IDLE};
    Processor cpu7{&local,nullptr,7,true,PROCESSOR_IDLE};
    cpu0.processor_primary=&cpu0;
    cpu6.processor_primary=&cpu6;
    cpu7.processor_primary=&cpu7;
    processor_array[0]=&cpu0;
    processor_array[6]=&cpu6;
    processor_array[7]=&cpu7;
    Thread worker{nullptr,46,712}, unrelated{nullptr,46,917};
    current=worker;
    current_cpu=3;

    sampleActive=true;
    gDisplayPerformanceCpus398=true;
    observeDisplayIssueCpu398(0);
    assert(!gauguin_display_thread_398 && !gDisplayIssueCpus398[3]);
    assert(!gauguin_display_preferred_cpu(&local,&cpu0,&worker) && !activeSamples);
    observeDisplayIssueCpu398(412);
    assert(gauguin_display_thread_398==712 && gDisplayWriterThread398==712 && gDisplayIssueCpus398[3]==1);
    assert(!gauguin_display_preferred_cpu(&local,&cpu7,&unrelated) && !activeSamples);
    assert(gauguin_display_preferred_cpu(&local,&cpu0,&worker)==&cpu6);
    assert(gauguin_display_preferred_cpu(&local,&cpu7,&worker)==&cpu7);
    cpu6.state=PROCESSOR_RUNNING;
    assert(gauguin_display_preferred_cpu(&local,&cpu6,&worker)==&cpu7);
    cpu7.is_recommended=false;
    assert(!gauguin_display_preferred_cpu(&local,&cpu7,&worker));
    cpu7.is_recommended=true;
    cpu7.processor_set=&other;
    assert(!gauguin_display_preferred_cpu(&local,&cpu7,&worker));
    cpu7.processor_set=&local;
    cpu7.processor_primary=&cpu0;
    assert(!gauguin_display_preferred_cpu(&local,&cpu7,&worker));
    cpu7.processor_primary=&cpu7;
    worker.bound_processor=&cpu0;
    assert(!gauguin_display_preferred_cpu(&local,&cpu7,&worker));
    worker.bound_processor=nullptr;
    worker.sched_pri=BASEPRI_RTQUEUES;
    assert(!gauguin_display_preferred_cpu(&local,&cpu7,&worker));
    worker.sched_pri=46;
    local.online_processor_count=0;
    assert(!gauguin_display_preferred_cpu(&local,&cpu7,&worker));
    local.online_processor_count=8;
    sampleActive=false;
    assert(!gauguin_display_preferred_cpu(&local,&cpu7,&worker));
    current_cpu=7;
    observeDisplayIssueCpu398(400);
    assert(gDisplayIssueCpus398[7]==1);
    current=unrelated;
    observeDisplayIssueCpu398(401);
    assert(gauguin_display_thread_398==712 && gDisplayOtherWriter398==1 && gDisplayIssueCpus398[7]==1);
    gauguin_display_thread_398=0;  // Owner close clears the published identity.
    observeDisplayIssueCpu398(402);
    assert(gauguin_display_thread_398==917 && gDisplayIssueCpus398[7]==2);
    gapi_frozen=true;
    observeDisplayIssueCpu398(403);
    assert(gDisplayIssueCpus398[7]==2);
}
