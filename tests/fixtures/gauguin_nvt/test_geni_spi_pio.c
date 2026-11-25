#include "geni_spi_pio.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum fault {
    NORMAL, STALL, EARLY_DONE, EXTRA_RX, BAD_RX_LAST, BAD_RX_COUNT,
    BAD_TX_COUNT, IRQ_ERROR
};
struct mock {
    uint32_t reg[0x1000 / 4];
    uint32_t tx[16], rx[16];
    unsigned th, tw, rh, rw, max_tw, max_rw;
    unsigned command_count, cancel_count, abort_count, writes, fifo_writes;
    unsigned access_count, advance_every;
    unsigned irq_reads;
    size_t shifted, len;
    uint8_t wire[GS_MAX_WIRE];
    const uint8_t *reply;
    size_t reply_length;
    uint64_t us;
    enum fault fault;
    uint32_t error_irq;
    bool active, tail, ignore_cancel, ignore_abort, frozen_time, slow, concurrent, late_burst;
};
static uint8_t response(uint8_t v) { return (uint8_t)(v ^ 0xa5); }
static void push_rx(struct mock *m, uint32_t word)
{
    assert(m->rw < 16); /* finite hardware RX FIFO, never silently expand */
    m->rx[(m->rh + m->rw) % 16] = word;
    m->rw++;
    if (m->rw > m->max_rw) m->max_rw = m->rw;
}
static void advance(struct mock *m)
{
    if (!m->active) return;
    if (m->fault == STALL) return;
    if (m->fault == IRQ_ERROR) {
        m->reg[GS_M_IRQ_STATUS / 4] |= m->error_irq;
        return;
    }
    if (m->fault == EARLY_DONE) {
        m->active = false;
        m->reg[GS_M_IRQ_STATUS / 4] |= GS_DONE;
        return;
    }
    unsigned available = m->slow ? 1 : 16;
    while (m->tw && available--) {
        uint32_t word = m->tx[m->th], out = 0;
        unsigned n = m->len - m->shifted < 4 ?
            (unsigned)(m->len - m->shifted) : 4;
        assert(n);
        for (unsigned j = 0; j < n; j++) {
            uint8_t b = (uint8_t)(word >> (j * 8));
            size_t pos = m->shifted;
            m->wire[m->shifted++] = b;
            assert(!m->reply || pos < m->reply_length);
            out |= (uint32_t)(m->reply ? m->reply[pos] : response(b)) << (j * 8);
        }
        if (n < 4) assert((word >> (n * 8)) == 0); /* deterministic TX padding */
        m->th = (m->th + 1) % 16;
        m->tw--;
        push_rx(m, out);
        if (m->shifted == m->len) {
            m->tail = true;
            m->active = false;
            /* Intentionally NO RX_LAST IRQ: final drain must use FIFO status. */
            m->reg[GS_M_IRQ_STATUS / 4] |= GS_DONE;
            break;
        }
    }
}
static uint32_t read32(void *cookie, uint32_t reg)
{
    struct mock *m = cookie;
    assert(reg < sizeof(m->reg) && !(reg & 3));
    if (m->concurrent && ++m->access_count % m->advance_every == 0) advance(m);
    switch (reg) {
    case GS_STATUS: return m->active ? GS_CMD_ACTIVE : 0;
    case GS_M_IRQ_STATUS:
        if (m->command_count) m->irq_reads++;
        if (!m->concurrent && !(m->late_burst && m->irq_reads == 2)) advance(m);
        return m->reg[reg / 4];
    case GS_TX_STATUS:
        /* Worst case: queued TX completes just AFTER the RX snapshot. */
        if (m->late_burst && m->irq_reads == 2) advance(m);
        return m->command_count && m->fault == BAD_TX_COUNT ? 17 : m->tw;
    case GS_RX_STATUS:
        if (m->command_count && m->fault == BAD_RX_COUNT) return 17;
        if (m->tail && m->rw) {
            unsigned valid = (unsigned)(m->len % 4);
            if (m->fault == EXTRA_RX) valid = 0;
            if (m->fault == BAD_RX_LAST) valid = 5;
            return m->rw | GS_RX_LAST | ((uint32_t)valid << 28);
        }
        return m->rw;
    case GS_RX_FIFO: {
        assert(m->rw);
        uint32_t value = m->rx[m->rh];
        m->rh = (m->rh + 1) % 16;
        m->rw--;
        return value;
    }
    default: return m->reg[reg / 4];
    }
}
static void write32(void *cookie, uint32_t reg, uint32_t value)
{
    struct mock *m = cookie;
    assert(reg < sizeof(m->reg) && !(reg & 3));
    if (m->concurrent && ++m->access_count % m->advance_every == 0) advance(m);
    m->writes++;
    switch (reg) {
    case GS_M_IRQ_CLEAR: m->reg[GS_M_IRQ_STATUS / 4] &= ~value; return;
    case GS_M_CMD:
        assert(value == GS_FULL_DUPLEX); /* no CS fragmentation/split command */
        assert(!m->active && !m->tw && !m->rw);
        assert(!(m->reg[GS_TRANS_CFG / 4] & 1));
        m->len = m->reg[GS_TX_LEN / 4];
        assert(m->len == m->reg[GS_RX_LEN / 4]);
        assert(m->len && m->len <= GS_MAX_WIRE);
        m->active = true;
        m->tail = false;
        m->command_count++;
        m->irq_reads = 0;
        m->shifted = 0;
        return;
    case GS_TX_FIFO:
        assert(m->active);
        assert(m->tw < 16); /* finite hardware TX FIFO */
        m->tx[(m->th + m->tw) % 16] = value;
        m->tw++;
        m->fifo_writes++;
        if (m->tw > m->max_tw) m->max_tw = m->tw;
        return;
    case GS_M_CTRL:
        if (value == 4) {
            m->cancel_count++;
            if (!m->ignore_cancel) {
                m->active = false;
                m->reg[GS_M_IRQ_STATUS / 4] |= GS_CANCELLED;
            }
        } else {
            assert(value == 2);
            m->abort_count++;
            if (!m->ignore_abort) {
                m->active = false;
                m->reg[GS_M_IRQ_STATUS / 4] |= GS_ABORTED;
            }
        }
        return;
    default:
        /* A transport may not write clocks, GPIO, firmware/reset or DMA. */
        assert(reg == GS_M_IRQ_EN || reg == GS_TX_WM || reg == GS_RX_WM ||
               reg == GS_RX_RFR_WM || reg == GS_TRANS_CFG ||
               reg == GS_TX_LEN || reg == GS_RX_LEN);
        m->reg[reg / 4] = value;
    }
}
static void barrier(void *cookie) { (void)cookie; }
static uint64_t now_us(void *cookie) { return ((struct mock *)cookie)->us; }
static void relax(void *cookie)
{
    struct mock *m = cookie;
    if (!m->frozen_time) m->us += 2;
}
static struct gs_pio setup(struct mock *m)
{
    memset(m, 0, sizeof(*m));
    m->reg[GS_HW_PARAM0 / 4] = m->reg[GS_HW_PARAM1 / 4] = (32u << 24) | (16u << 16);
    m->reg[GS_FW_REVISION / 4] = 1u << 8;
    m->reg[GS_WORD_LEN / 4] = 4;
    m->reg[GS_TX_PACK0 / 4] = m->reg[GS_RX_PACK0 / 4] = GS_PACK0;
    m->reg[GS_TX_PACK1 / 4] = m->reg[GS_RX_PACK1 / 4] = GS_PACK1;
    /* Test that stale completion is cleared and CS_TOGGLE is removed. */
    m->reg[GS_M_IRQ_STATUS / 4] = GS_DONE;
    m->reg[GS_TRANS_CFG / 4] = 0x81;
    return (struct gs_pio) {
        .io = {m, read32, write32, barrier, now_us, relax},
        .timeout_us = 500, .recovery_timeout_us = 20, .max_polls = 1000
    };
}
static void success_cases(void)
{
    const size_t lengths[] = {1, 3, 4, 7, 18, 63, 64, 65, 66, 67, 128, 256};
    for (unsigned slow = 0; slow < 11; slow++) {
        for (unsigned k = 0; k < sizeof(lengths) / sizeof(lengths[0]); k++) {
            size_t len = lengths[k];
            uint8_t *tx = malloc(len), *guard = malloc(len + 2), *rx = guard + 1;
            assert(tx && guard);
            guard[0] = guard[len + 1] = 0x5a;
            for (size_t i = 0; i < len; i++) tx[i] = (uint8_t)(i * 7 + 3);
            struct mock m;
            struct gs_pio s = setup(&m);
            m.slow = slow != 0 && slow != 10;
            m.concurrent = slow >= 2 && slow != 10;
            m.late_burst = slow == 10;
            m.advance_every = slow - 1;
            assert(gs_pio_xfer(&s, tx, rx, len) == GS_OK);
            assert(m.command_count == 1 && m.cancel_count == 0 && m.abort_count == 0);
            assert(m.shifted == len && !memcmp(m.wire, tx, len));
            assert(s.diag.tx_queued == len && s.diag.rx_received == len);
            assert(!s.poisoned && !s.in_flight && !m.active && !m.rw && !m.tw);
            assert(m.fifo_writes == (len + 3) / 4 && m.max_tw <= 15 && m.max_rw <= 16);
            for (size_t i = 0; i < len; i++) assert(rx[i] == response(tx[i]));
            assert(guard[0] == 0x5a && guard[len + 1] == 0x5a);
            assert(m.reg[GS_TRANS_CFG / 4] == 0x80);
            assert(m.reg[GS_M_IRQ_EN / 4] == 0 && m.reg[GS_TX_WM / 4] == 0);
            /* Second call succeeds, without carrying old DONE/RX forward. */
            assert(gs_pio_xfer(&s, tx, NULL, len) == GS_OK);
            assert(m.command_count == 2);
            free(guard);
            free(tx);
        }
    }
}
static void failure_cases(void)
{
    uint8_t tx[67] = {0}, rx[67];
    for (unsigned how = 0; how < 4; how++) {
        struct mock m;
        struct gs_pio s = setup(&m);
        m.fault = STALL;
        m.ignore_cancel = how >= 1;
        m.ignore_abort = how >= 2;
        m.frozen_time = how == 3;
        s.max_polls = how == 3 ? 8 : 1000;
        assert(gs_pio_xfer(&s, tx, rx, 67) == GS_TIMEOUT);
        assert(s.diag.polls == (how == 3 ? 8u : 251u));
        assert(m.cancel_count == 1 && m.abort_count == (how >= 1));
        assert(s.diag.recovery == (how == 0 ? GS_REC_CANCEL :
               how == 1 ? GS_REC_ABORT : GS_REC_STUCK));
        assert(s.poisoned && !s.in_flight);
        unsigned writes = m.writes;
        assert(gs_pio_xfer(&s, tx, rx, 67) == GS_POISONED);
        assert(m.writes == writes); /* no retry after failed exchange */
    }
    {
        struct mock m;
        struct gs_pio s = setup(&m);
        m.us = UINT64_MAX - 10;
        m.fault = STALL;
        s.timeout_us = 20;
        assert(gs_pio_xfer(&s, tx, rx, 67) == GS_TIMEOUT);
        assert(s.diag.polls == 11 && s.diag.recovery == GS_REC_CANCEL);
    }
    const unsigned bits[] = {1, 2, 3, 4, 5, 24, 25, 28, 29};
    for (unsigned k = 0; k < sizeof(bits) / sizeof(bits[0]); k++) {
        struct mock m;
        struct gs_pio s = setup(&m);
        m.fault = IRQ_ERROR;
        m.error_irq = 1u << bits[k];
        assert(gs_pio_xfer(&s, tx, rx, 67) == GS_IO_ERROR);
        assert(s.diag.irq_seen & m.error_irq);
        assert(s.poisoned);
    }
    const enum fault faults[] = {EARLY_DONE, EXTRA_RX, BAD_RX_LAST, BAD_RX_COUNT, BAD_TX_COUNT};
    for (unsigned k = 0; k < sizeof(faults) / sizeof(faults[0]); k++) {
        struct mock m;
        struct gs_pio s = setup(&m);
        m.fault = faults[k];
        assert(gs_pio_xfer(&s, tx, rx, 3) == (faults[k] == EARLY_DONE ? GS_SHORT : GS_IO_ERROR));
        assert(s.poisoned);
    }
}
static void preflight_cases(void)
{
    uint8_t tx[3] = {0xff, 4, 0x5a};
    const unsigned fields[] = {GS_HW_PARAM0, GS_HW_PARAM1, GS_FW_REVISION,
        GS_FIFO_DISABLE, GS_DMA_MODE, GS_IRQ_EN, GS_GSI_EVENT_EN, GS_CPHA,
        GS_CPOL, GS_LOOPBACK, GS_CS_SEL, GS_CS_INV, GS_WORD_LEN, GS_BYTE_GRAN,
        GS_TX_PACK0, GS_TX_PACK1, GS_RX_PACK0, GS_RX_PACK1};
    for (unsigned k = 0; k < sizeof(fields) / sizeof(fields[0]); k++) {
        struct mock m;
        struct gs_pio s = setup(&m);
        m.reg[fields[k] / 4] = ~m.reg[fields[k] / 4];
        assert(gs_pio_xfer(&s, tx, NULL, 3) == GS_NOT_CONFIGURED);
        assert(!m.writes);
    }
    struct mock m;
    struct gs_pio s = setup(&m);
    m.active = true;
    assert(gs_pio_xfer(&s, tx, NULL, 3) == GS_BUSY && !m.writes);
    m.active = false;
    m.tw = 1;
    assert(gs_pio_xfer(&s, tx, NULL, 3) == GS_DIRTY && !m.writes);
    m.tw = 0;
    m.rw = 1;
    assert(gs_pio_xfer(&s, tx, NULL, 3) == GS_DIRTY && !m.writes);
    m.rw = 0;
    s.in_flight = true;
    assert(gs_pio_xfer(&s, tx, NULL, 3) == GS_BUSY && !m.writes);
    s.in_flight = false;
    assert(gs_pio_xfer(&s, tx, NULL, 0) == GS_INVALID && !m.writes);
    assert(gs_pio_xfer(&s, tx, NULL, GS_MAX_WIRE + 1) == GS_INVALID && !m.writes);
}
int main(void)
{
    success_cases();
    failure_cases();
    preflight_cases();
    puts("PASS: finite FIFO, one-CS 67-byte full duplex, final RX, bounds, errors, timeout/cancel/abort");
    return 0;
}
