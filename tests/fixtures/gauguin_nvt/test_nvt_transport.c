/* Composition fixture: actual request encoder + actual PIO + actual decoder.
 * Reuse the finite FIFO hardware model, not a stubbed transport function.
 */
#define main standalone_transport_tests
#include "test_geni_spi_pio.c"
#undef main
#include "nvt_protocol.h"

int main(void)
{
    static const uint8_t fw[18] = {
        0xa5,0x5a,0x10,0xef,18,32,4,0x38,9,0x60,0,0,0,0,0,1,0,0
    };
    static const uint8_t reset[7] = {0x12,0x34,0xa3,1,2,3,4};
    static const uint8_t pid[4] = {0xde,0xad,0x37,0x59};
    static const uint8_t points[67] = {
        [0]=0xab,[1]=0xcd,[2]=0x19,[5]=0x79,[6]=5,[7]=5,[66]=0x71
    };
    const uint8_t *replies[] = {fw,reset,pid,points};
    const size_t sizes[] = {18,7,4,67};
    struct nvt_fw_info info;
    struct nvt_state state;
    struct mock m;
    struct gs_pio s = setup(&m);
    m.concurrent = true;
    m.slow = true;
    m.advance_every = 3;
    for (unsigned kind = 0; kind < 4; kind++) {
        struct nvt_request request;
        uint8_t rx[NVT_MAX_WIRE];
        unsigned count = m.command_count;
        assert(nvt_make_request((enum nvt_read_kind)kind, &request) == NVT_OK);
        assert(request.wire_length == sizes[kind]);
        assert(gs_pio_xfer(&s, request.page, NULL, 3) == GS_OK);
        assert(m.command_count == count + 1 && !memcmp(m.wire, request.page, 3));
        m.reply = replies[kind];
        m.reply_length = sizes[kind];
        assert(gs_pio_xfer(&s, request.tx, rx, request.wire_length) == GS_OK);
        assert(m.command_count == count + 2); /* FWINFO crosses0x80 without split */
        assert(!memcmp(m.wire, request.tx, sizes[kind]));
        assert(!memcmp(rx, replies[kind], sizes[kind]));
        m.reply = NULL;
        assert(gs_pio_xfer(&s, request.restore_page, NULL, 3) == GS_OK);
        assert(m.command_count == count + 3);
        assert(m.wire[0] == 0xff && m.wire[1] == 4 && m.wire[2] == 0x5a);
        if (kind == NVT_READ_FWINFO) {
            assert(nvt_decode_fwinfo(rx, sizes[kind], &info) == NVT_OK);
            assert(info.version == 16 && info.max_x == 1080 && info.max_y == 2400);
            assert(nvt_state_init(&state, &info) == NVT_OK);
        } else if (kind == NVT_READ_RESET) {
            struct nvt_reset_info value;
            assert(nvt_decode_reset(rx, sizes[kind], &value) == NVT_OK);
            assert(nvt_reset_ready(&value, 0xa3));
        } else if (kind == NVT_READ_PID) {
            uint16_t value;
            assert(request.page[2] == 0x5b && request.tx[0] == 0x1a);
            assert(nvt_decode_pid(rx, sizes[kind], &value) == NVT_OK && value == 0x5937);
        } else {
            struct nvt_frame frame;
            assert(nvt_decode_points(&state, rx, sizes[kind], &frame) == NVT_OK);
            assert(frame.active_count == 1 && frame.events[0].id == 3);
            assert(frame.events[0].contact.x == 7 && frame.events[0].contact.y == 9);
            assert(frame.native_tail[4] == 0x71);
        }
    }
    puts("PASS: NVT request/page/read/restore + real PIO + raw-RX decoders (18/7/4/67B)");
    return 0;
}
