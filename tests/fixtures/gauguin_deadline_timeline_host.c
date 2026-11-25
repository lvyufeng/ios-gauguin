#include "gauguin_deadlines419.h"
#include "gauguin_ui_trace.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static struct gut_core frames, timeline419;
static struct gut_event crc_events[3], timeline_events[3];
static uint64_t tick = 100;
static unsigned rows_written, bytes_written;

static uint64_t mach_absolute_time(void) { return tick; }
static uint64_t clock_ticks(void *cookie) { (void)cookie; return tick; }

static void sweet_log_append(const char *line, int bytes)
{
    assert(!strncmp(line, "\nF419E ", 7) && bytes > 0);
    ++rows_written;
    bytes_written += (unsigned)bytes;
}

#include "frame419-timeline.inc"
#include "frame419-drain.inc"

int main(void)
{
    assert(!sweet_frame419_clock());
    assert(gut_init_frames(&frames, crc_events, 2, 100, clock_ticks));
    assert(gut_init_frames(&timeline419, timeline_events, 3, 100, clock_ticks));
    assert(!sweet_frame419_clock());
    assert(gut_report(&frames, tick, tick, 0, 1));
    assert(gut_report(&timeline419, tick, tick, 0, 1));
    tick = 110;
    gut_record(&frames, 49, 0, 0, 0, 0, 0, 0);
    assert(!gut_enabled(&frames) && sweet_frame419_clock() == tick);
    sweet_frame419_record(F419_GPU, 0x20000000f, 5, 4, 108, 109, 0);
    assert(timeline_events[1].kind == F419_GPU && timeline_events[1].tick == tick);
    assert(timeline_events[1].id == 0x20000000f && timeline_events[1].pid == 5);
    ++tick;
    sweet_frame419_record(F419_PROMOTE, 0x20000000f, 5, 4, 2, 6, 150);
    assert(!sweet_frame419_clock());
    sweet_frame419_record(F419_COPY, 7, 15, 4, 2, 150, tick);
    assert(timeline419.reserved == 3);
    frame419_drain();
    assert(rows_written == 3 && bytes_written > 0 && bytes_written < F419_MAX_WIRE_BYTES);
    frame419_drain();
    assert(rows_written == 3);
    puts("native deadline timeline verified");
}
