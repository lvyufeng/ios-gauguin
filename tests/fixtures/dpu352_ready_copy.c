#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "gauguin_blank352.h"

static void check_ready(void)
{
    struct scan351_slot slot = {0};
    struct scan351_position pos = {.tick=1000, .frame=82, .line=2480, .end=4878};
    assert(scan352_can_take(&slot,&pos,false));
    assert(!scan352_can_take(&slot,&pos,true));
    scan351_take(&slot,&pos);
    assert(!scan352_can_take(&slot,&pos,false));
    assert(scan352_delay_lines(&slot,&pos)==4910);
    pos.line=3044;
    assert(scan352_can_take(&slot,&pos,true));
    pos.line++;
    assert(!scan352_can_take(&slot,&pos,true));
    pos.line=3044;
    scan351_take(&slot,&pos);
    assert(!scan352_can_take(&slot,&pos,true));
    pos.frame++;
    pos.line=2500;
    assert(!scan352_can_take(&slot,&pos,true));
    assert(scan352_can_take(&slot,&pos,false));
    scan351_take(&slot,&pos);
    slot.done=true;
    assert(!scan352_can_take(&slot,&pos,true));

    uint64_t ticket=scan352_ticket(7,19);
    assert(ticket==((UINT64_C(7)<<32)|19));
    assert(!scan352_ticket(0,19) && !scan352_ticket(7,0) && !scan352_ticket(UINT64_C(1)<<32,19));
    assert(scan352_matches(ticket,ticket,88,88,19));
    assert(!scan352_matches(ticket,0,88,88,19));
    assert(!scan352_matches(ticket,scan352_ticket(8,19),88,88,19));
    assert(!scan352_matches(ticket,ticket,88,89,19));
    assert(!scan352_matches(ticket,ticket,88,88,20));
}

static void check_full_copy(void)
{
    const size_t source_bytes=SCAN352_SOURCE_STRIDE*SCAN352_HEIGHT;
    const size_t panel_bytes=SCAN352_PANEL_STRIDE*SCAN352_HEIGHT;
    uint8_t *source_storage=malloc(source_bytes+32);
    uint8_t *panel_storage=malloc(panel_bytes+32);
    assert(source_storage && panel_storage);
    uint8_t *source=source_storage+8;
    uint8_t *panel=panel_storage+16;
    memset(panel_storage,0xed,panel_bytes+32);
    for (size_t i=0;i<source_bytes;i++)
        source[i]=(uint8_t)((i^(i>>6)^(i>>14))*127);
    assert(scan352_copy_supported((uintptr_t)panel,(uintptr_t)source,1080,2400,4320,4608));
    assert(!scan352_copy_supported((uintptr_t)panel+8,(uintptr_t)source,1080,2400,4320,4608));
    assert(!scan352_copy_supported((uintptr_t)panel,(uintptr_t)source+4,1080,2400,4320,4608));
    assert(!scan352_copy_supported((uintptr_t)panel,(uintptr_t)source,1079,2400,4320,4608));
    assert(!scan352_copy_supported((uintptr_t)panel,(uintptr_t)source,1080,2400,4320,4320));
    assert(!scan352_copy_supported((uintptr_t)panel,(uintptr_t)panel+8,1080,2400,4320,4608));
    for (size_t y=0;y<SCAN352_HEIGHT;y++) {
        scan352_copy_row(panel+y*SCAN352_PANEL_STRIDE,source+y*SCAN352_SOURCE_STRIDE);
        assert(!memcmp(panel+y*SCAN352_PANEL_STRIDE,source+y*SCAN352_SOURCE_STRIDE,SCAN352_PANEL_STRIDE));
    }
    for (size_t byte=0;byte<16;byte++) {
        assert(panel_storage[byte]==0xed);
        assert(panel[panel_bytes+byte]==0xed);
    }
    free(panel_storage);
    free(source_storage);
}

int main(void)
{
    check_ready();
    check_full_copy();
    return 0;
}
