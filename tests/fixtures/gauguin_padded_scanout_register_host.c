#include <assert.h>
#include <stddef.h>
#include <stdint.h>

#include "gauguin_blank351.h"
#include "gauguin_linear_scanout411.h"
#include "gauguin_page_flip.h"

enum { F344_FRAME_COUNT = 0, F344_LINE_COUNT = 4 };
typedef bool boolean_t;
#define FALSE false

static volatile uint32_t registers[4];
static volatile uint32_t timing[2];
static volatile uint32_t *scan_intf = timing;
static struct {
    uint32_t address[3], requests;
    volatile uint32_t *source, *pitch, *sourceXY, *flush;
    bool padded;
} scan382 = {
    {0xa0000000,0xb0000000,0xb1000000},0,
    &registers[0],&registers[1],&registers[2],&registers[3],true
};

static bool interrupts, routeGood, corruptPostPitch;
static unsigned stage, positionReads;
static uint32_t wantedSource, wantedPitch, wantedXY, endLine, afterLine;

bool sweet_frame382_active(void) { return true; }

bool sweet_frame351_position(struct scan351_position *position)
{
    position->frame = timing[0];
    position->line = positionReads++ ? afterLine : timing[1];
    position->end = endLine;
    return true;
}

static bool scan382_live_route(uint32_t pitch, uint32_t sourceXY)
{
    return routeGood && *scan382.pitch == pitch && *scan382.sourceXY == sourceXY;
}

static boolean_t ml_set_interrupts_enabled(boolean_t enabled)
{
    const bool previous = interrupts;
    interrupts = enabled;
    return previous;
}

static void barrier(unsigned phase)
{
    assert(!interrupts && ++stage == phase);
    assert(*scan382.source == wantedSource && *scan382.pitch == wantedPitch);
    assert(*scan382.sourceXY == wantedXY && *scan382.flush == phase-1);
    if (phase == 2 && corruptPostPitch)
        *scan382.pitch = 4096;
}

#include "frame411_flip_impl.inc"

static void reset(unsigned front, unsigned next, bool padded)
{
    scan382.padded = padded;
    timing[0] = 100;
    timing[1] = 4000;
    endLine = 4878;
    afterLine = 4001;
    routeGood = interrupts = true;
    corruptPostPitch = false;
    scan382.requests = stage = positionReads = 0;
    registers[0] = scan382.address[front];
    registers[1] = f411_pitch(padded,front);
    registers[2] = f411_source_xy(padded,front);
    registers[3] = 0;
    wantedSource = scan382.address[next];
    wantedPitch = f411_pitch(padded,next);
    wantedXY = f411_source_xy(padded,next);
}

static void latch(unsigned target, uint32_t scan)
{
    assert(sweet_frame382_latch(target,scan) == F382_WAIT);
    ++timing[0];
    assert(sweet_frame382_latch(target,scan) == F382_WAIT);
    registers[3] = 0;
    assert(sweet_frame382_latch(target,scan) == F382_CONFIRMED);
}

int main(void)
{
    uint32_t scan = 0;
    reset(F382_FRONT,F382_FIRST,true);
    assert(sweet_frame382_issue(F382_FRONT,F382_FIRST,&scan) == F382_TOUCHED);
    assert(scan == 100 && stage == 2 && interrupts);
    assert(registers[1] == 4608 && registers[2] == 0x00120016);
    latch(F382_FIRST,scan);

    reset(F382_FIRST,F382_SECOND,true);
    assert(sweet_frame382_issue(F382_FIRST,F382_SECOND,&scan) == F382_TOUCHED);
    latch(F382_SECOND,scan);

    reset(F382_SECOND,F382_FRONT,true);
    assert(sweet_frame382_issue(F382_SECOND,F382_FRONT,&scan) == F382_TOUCHED);
    assert(registers[1] == 4320 && registers[2] == 0);
    latch(F382_FRONT,scan);

    reset(F382_FIRST,F382_SECOND,false);
    assert(sweet_frame382_issue(F382_FIRST,F382_SECOND,&scan) == F382_TOUCHED);
    latch(F382_SECOND,scan);

    reset(F382_FRONT,F382_FIRST,true);
    timing[1] = endLine-F382_CUTOFF_GUARD_LINES+1;
    assert(sweet_frame382_issue(F382_FRONT,F382_FIRST,&scan) == F382_WAIT);
    assert(stage == 0 && scan382.requests == 0);

    reset(F382_FRONT,F382_FIRST,true);
    registers[2] = 1;
    assert(sweet_frame382_issue(F382_FRONT,F382_FIRST,&scan) == F382_UNCERTAIN);
    assert(stage == 0 && scan382.requests == 0);

    reset(F382_FRONT,F382_FIRST,true);
    corruptPostPitch = true;
    assert(sweet_frame382_issue(F382_FRONT,F382_FIRST,&scan) == F382_UNCERTAIN);
    assert(stage == 2 && scan382.requests == 1 && interrupts);

    reset(F382_FRONT,F382_FIRST,true);
    assert(sweet_frame382_issue(F382_FRONT,F382_FIRST,&scan) == F382_TOUCHED);
    ++timing[0];
    registers[2] = 0;
    registers[3] = 0;
    assert(sweet_frame382_latch(F382_FIRST,scan) == F382_UNCERTAIN);
}
