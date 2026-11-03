/*
 * SWEET FIFO I2C touch bring-up: GT9896 (Goodix) or FT5452/FTS (Focaltech)
 * on a QUPv3 GENI serial engine. Call once after the scheduler is running;
 * all work runs on one thread. Requires ABL-loaded GENI I2C firmware; the
 * touch rail is voted through RPMh (sweet_rpmh.c). No firmware/config upload
 * or direct PMIC writes. Only IC data write: zero to GT9896's event status
 * after reading a report. See touch2/report.md.
 *
 * Board layout (from the live DT / vendor DTS):
 *   sweet   : SE7  0xa84000, TLMM reset gpio8 / irq gpio9, GT9896 @0x5d,
 *             rail PM6150L LDO11C ("ldoc11", 3.2 V), board power gpio90.
 *   gauguin : SE8  0x988000, TLMM reset gpio21 / irq gpio22 (Falling),
 *             Focaltech @0x38, rail PM6350 LDO6A ("ldoa6", 1.8 V), no
 *             board enable (vdd-supply = L6A only), display 1080x2340.
 */
#if defined(ARM64_BOARD_CONFIG_SWEET)
#include <sys/param.h>
#include <sys/systm.h>
#include <sys/errno.h>
#include <kern/clock.h>
#include <kern/thread.h>
#include <kern/sched_prim.h>
#include <kern/clock.h>
#include <kern/thread_call.h>
#include <machine/machine_routines.h>
#include <pexpert/pexpert.h>
#include <IOKit/IOLib.h>

extern vm_offset_t ml_io_map(vm_offset_t, vm_size_t);
/* Mach MIG declaration is not included by BSD's exported thread.h. */
extern kern_return_t thread_terminate(thread_t);
extern kern_return_t kernel_thread_start(thread_continue_t, void *, thread_t *);
extern int sweet_rpmh_vreg_enable(const char *res, unsigned mv);
extern void sweet_hid_touch(int finger, int down, int x, int y);
void sweet_touch_init(void);

#if defined(GAUGUIN)
/*
 * gauguin is SM7225 (lito / lagoon), NOT the SM7125 the port was planned on.
 * The TLMM is at 0x00f100000 (`qcom,lagoon-pinctrl`, 0x30000 - read from the
 * phone's own /sys/firmware/devicetree), not at 0x03900000 as on SM7150.
 * 0x03900000 does not exist on this SoC: mapping it and then reading a GPIO
 * hung the bring-up at "stage D" in every earlier run (NOTES 14:35).
 * The GPIO register layout is the same flat per-pin window, so the rest of
 * the driver (and the TOUCH_GPIO_IO index math) is unchanged.
 */
#define TOUCH_SE_PA      0x00988000u	/* i2c@988000, qcom,i2c-geni */
#define TOUCH_GCC_PA     0x00100000u	/* qcom,lagoon-gcc, 0x1f0000 */
#define TOUCH_NORTH_PA   0x00f100000u	/* qcom,lagoon-pinctrl, 0x30000 */
#define TOUCH_GCC_VOTE   0x5200cu
#define TOUCH_RCG       0x1814cu    /* wrapper1 LOCAL S2 (boot 2) = global SE8 */
#define TOUCH_GPIO_RST   21u
#define TOUCH_GPIO_IRQ   22u
#define TOUCH_RAIL       "ldoa6"
#define TOUCH_RAIL_MV    1800u
#define TOUCH_Y_MAX      2339u      /* focaltech,display-coords 0 0 1080 2340 */
#define TOUCH_FTS_CHIP_ID (0x54u << 8 | 0x54u)  /* FT5452: A3=0x54, A4=0x54 */
#define TOUCH_SDA_PIN    20u
#define TOUCH_SCL_PIN    19u
#else
#define TOUCH_SE_PA      0x00a84000u
#define TOUCH_GCC_PA     0x00100000u
#define TOUCH_NORTH_PA   0x03900000u /* DT TLMM + NORTH (0x500000) */
#define TOUCH_GCC_VOTE   0x5200cu
#define TOUCH_RCG       0x18148u    /* wrapper1 LOCAL S1 = global SE7 */
#define TOUCH_GPIO_RST   8u
#define TOUCH_GPIO_IRQ   9u
#define TOUCH_RAIL       "ldoc11"
#define TOUCH_RAIL_MV    3200u
#define TOUCH_Y_MAX      2399u
#define TOUCH_FTS_CHIP_ID (0x52u << 8 | 0x54u)
#define TOUCH_SDA_PIN    6u
#define TOUCH_SCL_PIN    7u
#endif
#define TOUCH_GPIO_CFG(n) ((uint32_t)(n) * 0x1000u)
#define TOUCH_GPIO_IO(n)  (TOUCH_GPIO_CFG(n) + 4u)
#define TOUCH_MAX        10u
#define FTS_PTR_LEN      4u      /* focaltech: 0x00 00 hi lo in one transaction */
#define TOUCH_GOODIX     1
#define TOUCH_FTS        2
/* GT9896 is Yellowstone in Xiaomi sweet-r-oss, not the Berlin protocol. */
#define GOODIX_PID_REG   0x4022u
#define GOODIX_EVENT_REG 0x4180u
#define GOODIX_HEAD_LEN  8u
#define GOODIX_POINT_LEN 8u

#define SE_STATUS       0x040u
#define SE_MCLK         0x048u
#define SE_FW           0x068u
#define SE_CLK_SEL      0x07cu
#define SE_DMA          0x258u
#define SE_TX_LEN       0x26cu
#define SE_RX_LEN       0x270u
#define SE_SCL          0x278u
#define SE_CMD          0x600u
#define SE_CTRL         0x604u
#define SE_IRQ          0x610u
#define SE_IRQ_EN       0x614u
#define SE_IRQ_CLR      0x618u
#define SE_TX           0x700u
#define SE_RX           0x780u
#define SE_TX_COUNT     0x800u
#define SE_RX_COUNT     0x804u
#define SE_HW_TX        0xe24u
#define SE_HW_RX        0xe28u
#define SE_TX_WM        0x80cu
#define SE_RX_WM_IRQ    (1u << 26)
#define SE_RX_LAST      (1u << 27)
#define SE_TX_WM_IRQ    (1u << 30)
#define SE_DONE         (1u << 0)
#define SE_NACK         (1u << 10)
#define SE_ERRORS       (0x3eu | (1u << 9) | (1u << 10) | (1u << 12) | \
                         (1u << 13) | (3u << 24) | (3u << 28))
#define SE_EVENTS       (SE_DONE | SE_ERRORS | SE_RX_WM_IRQ | SE_RX_LAST | SE_TX_WM_IRQ)
/* geni_se_config_packing(8, 4, true, true, true): start bits 7/15/23/31,
 * MSB-to-LSB, length 8, STOP only on vector 3. FIFO bytes remain LSB first. */
#define SE_PACK0        0x0007f8feu
#define SE_PACK1        0x000ffefeu

static struct {
	vm_offset_t se, gcc, gpio;
	bool started, dead, probing;
	bool thread_started;      /* bring-up thread created (sweet_touch_start_at_init) */
	int kind, irq_hint;
	uint32_t irq_status, irq_last, active;
	unsigned sent, got;
	int x[TOUCH_MAX], y[TOUCH_MAX];
} st;
static char touch_sleep_chan;   /* aligned byte, like the working probe */

static uint32_t
touch_rd(vm_offset_t base, uint32_t off)
{
	uint32_t v = *(volatile uint32_t *)(base + off);
	__asm__ volatile("dmb oshld" ::: "memory");
	return v;
}

static void
touch_wr(vm_offset_t base, uint32_t off, uint32_t val)
{
	__asm__ volatile("dmb oshst" ::: "memory");
	*(volatile uint32_t *)(base + off) = val;
	__asm__ volatile("dsb osh" ::: "memory");
}

static void
touch_wait(unsigned ms)
{
	/*
	 * Busy wait on the hardware counter. Every blocking form tried here
	 * (assert_wait_deadline with THREAD_UNINT and with THREAD_ABORTSAFE) never
	 * returns in this tree (NOTES 22:38), while short spins are cheap and
	 * always work. The longest caller waits 300 ms once, at bring-up.
	 */
	uint64_t until = mach_absolute_time() + (uint64_t)ms * 1000000ull;
	while (mach_absolute_time() < until) {
		;
	}
}

static bool
touch_wait_clear(vm_offset_t base, uint32_t off, uint32_t mask)
{
	for (unsigned i = 0; i < 5000; ++i) {
		if (!(touch_rd(base, off) & mask)) {
			return true;
		}
		delay(1);
	}
	return false;
}

static void
touch_gpio(unsigned pin, unsigned mux, unsigned pull, unsigned drive, bool out, bool high)
{
	uint32_t off = TOUCH_GPIO_CFG(pin);
	uint32_t cfg = touch_rd(st.gpio, off);
	if (out) {
		/* Set the desired latch before enabling output (reset is active low). */
		touch_wr(st.gpio, TOUCH_GPIO_IO(pin),
		    (touch_rd(st.gpio, TOUCH_GPIO_IO(pin)) & ~2u) | (high ? 2u : 0u));
	}
	cfg &= ~0x3ffu;
	cfg |= (mux << 2) | pull | (drive << 6) | (out ? 0x200u : 0u);
	touch_wr(st.gpio, off, cfg);
}

static bool
touch_clocks(void)
{
	/* Vote on only wrapper1 and SE7, preserving other clock users. */
	uint32_t mask = (0x0fu << 18) | (1u << 23);
	touch_wr(st.gcc, TOUCH_GCC_VOTE, touch_rd(st.gcc, TOUCH_GCC_VOTE) | mask);
	uint32_t dfs = touch_rd(st.gcc, TOUCH_RCG + 0x14u);
	uint32_t cfg = touch_rd(st.gcc, TOUCH_RCG + 4u);
	printf("SWEET TOUCH: gcc vote=%#x rcg=%#x cfg=%#x dfs=%#x\n",
	    touch_rd(st.gcc, TOUCH_GCC_VOTE), touch_rd(st.gcc, TOUCH_RCG), cfg, dfs);
	if (dfs & 1u) {
		/* SE CLK_SEL=0 selects DFS performance level 0. Do not alter tables. */
		cfg = touch_rd(st.gcc, TOUCH_RCG + 0x1cu);
		if ((cfg & 0x371fu) != 1u) {
			printf("SWEET TOUCH: DFS level0=%#x is not XO/1; need clock integration\n", cfg);
			return false;
		}
	} else {
		/* XO parent 0, HID divider 1 => 19.2 MHz. No PLL or voltage change. */
		cfg = (cfg & ~(0x371fu | (1u << 20))) | 1u;
		touch_wr(st.gcc, TOUCH_RCG + 4u, cfg);
		touch_wr(st.gcc, TOUCH_RCG, touch_rd(st.gcc, TOUCH_RCG) | 1u);
		if (!touch_wait_clear(st.gcc, TOUCH_RCG, 1u)) {
			printf("SWEET TOUCH: RCG update timeout\n");
			return false;
		}
	}
	const uint32_t branches[] = {0x18004, 0x18008, 0x1800c, 0x18010, 0x18144};
	for (unsigned i = 0; i < sizeof(branches) / sizeof(branches[0]); ++i) {
		if (!touch_wait_clear(st.gcc, branches[i], 1u << 31)) {
			printf("SWEET TOUCH: GCC branch %#x halted (%#x)\n", branches[i],
			    touch_rd(st.gcc, branches[i]));
			return false;
		}
	}
	return true;
}

/* Called only for a transfer started by this driver, including a stretched TX. */
static void
touch_abort(void)
{
	touch_wr(st.se, SE_CTRL, 2); /* abort M command, release held bus */
	bool done = false;
	for (unsigned i = 0; i < 5000; ++i) {
		if (touch_rd(st.se, SE_IRQ) & (1u << 5)) {
			done = true;
			break;
		}
		delay(1);
	}
	if (!done || !touch_wait_clear(st.se, SE_STATUS, 1u)) {
		st.dead = true;
		printf("SWEET TOUCH: abort failed status=%#x irq=%#x; stopping\n",
		    touch_rd(st.se, SE_STATUS), touch_rd(st.se, SE_IRQ));
	}
	/* Bound drain even if the hardware reports an impossible FIFO count. */
	for (unsigned i = 0; i < 64 && (touch_rd(st.se, SE_RX_COUNT) & 0x1ffffffu); ++i) {
		(void)touch_rd(st.se, SE_RX);
	}
	touch_wr(st.se, SE_IRQ_CLR, 0xffffffffu);
	if (touch_rd(st.se, SE_TX_COUNT) & 0xfffffffu) {
		st.dead = true;
		printf("SWEET TOUCH: TX FIFO not empty after abort; stopping\n");
	}
}

/* Keep all observed bits for diagnostics, even if a watermark was cleared. */
static uint32_t
touch_irq(void)
{
	st.irq_last = touch_rd(st.se, SE_IRQ);
	st.irq_status |= st.irq_last;
	return st.irq_last;
}

/* One Linux-style FIFO message. TX is at most 3 bytes; RX at most 90. */
static int
touch_msg_run(uint8_t addr, const uint8_t *tx, unsigned nt, uint8_t *rx,
    unsigned nr, bool stretch)
{
	if (st.dead || nt > MAX(3u, FTS_PTR_LEN) || nr > 90 || (nt && nr) || (!nt && !nr)) {
		return EIO;
	}
	if (!touch_wait_clear(st.se, SE_STATUS, 1u)) {
		st.dead = true; /* no other SE7 owner is supported */
		return EBUSY;
	}
	touch_wr(st.se, SE_IRQ_CLR, 0xffffffffu);
	touch_wr(st.se, SE_TX_WM, nt ? 1u : 0u);
	touch_wr(st.se, nr ? SE_RX_LEN : SE_TX_LEN, nr ? nr : nt);
	touch_wr(st.se, SE_CMD, ((nr ? 2u : 1u) << 27) |
	    ((uint32_t)addr << 9) | (stretch ? 4u : 0u));
	int err = ETIMEDOUT;
	for (unsigned i = 0; i < 20000; ++i) {
		uint32_t irq = touch_irq();
		if (irq & SE_ERRORS) {
			err = (irq & SE_NACK) ? ENXIO : EIO;
			/* A completed NACK is normal during address probing. Aborting an
			 * idle sequencer may never produce ABORT_DONE. Wait for completion
			 * and leave a clean idle engine available for the other IC. */
			for (unsigned j = 0; j < 5000 && !(irq & SE_DONE); ++j) {
				delay(1);
				irq = touch_irq();
			}
			if ((irq & SE_DONE) && !(touch_rd(st.se, SE_STATUS) & 1u) &&
			    !(touch_rd(st.se, SE_TX_COUNT) & 0xfffffffu) &&
			    !(touch_rd(st.se, SE_RX_COUNT) & 0x1ffffffu)) {
				touch_wr(st.se, SE_IRQ_CLR, irq);
				return err;
			}
			break;
		}
		if (nt && !st.sent && (irq & SE_TX_WM_IRQ)) {
			uint32_t word = 0;
			for (unsigned j = 0; j < nt; ++j) {
				word |= (uint32_t)tx[j] << (8u * j);
			}
			touch_wr(st.se, SE_TX, word);
			st.sent = nt;
			touch_wr(st.se, SE_TX_WM, 0);
		}
		uint32_t count = touch_rd(st.se, SE_RX_COUNT) & 0x1ffffffu;
		if (count > 64 || count > (nr - st.got + 3u) / 4u) {
			err = EIO;
			break;
		}
		while (count--) {
			uint32_t word = touch_rd(st.se, SE_RX);
			for (unsigned j = 0; j < 4 && st.got < nr; ++j) {
				rx[st.got++] = (uint8_t)(word >> (8u * j));
			}
		}
		/* DONE is checked after draining RX, so final short words aren't lost. */
		if (irq & SE_DONE) {
			/* Re-sample after the final drain; a late error must beat DONE. */
			irq = touch_irq();
			if (irq & SE_ERRORS) {
				continue;
			}
			touch_wr(st.se, SE_IRQ_CLR, irq);
			if (st.got == nr && st.sent == nt) {
				return 0;
			}
			err = EIO;
			break;
		}
		/* Preserve DONE/errors if they arrive during this iteration. */
		touch_wr(st.se, SE_IRQ_CLR, irq & (SE_RX_WM_IRQ | SE_RX_LAST | SE_TX_WM_IRQ));
		delay(1);
	}
	touch_abort();
	return err;
}

static int
touch_msg(uint8_t addr, const uint8_t *tx, unsigned nt, uint8_t *rx,
    unsigned nr, bool stretch)
{
	st.irq_status = st.irq_last = 0;
	st.sent = st.got = 0;
	int err = touch_msg_run(addr, tx, nt, rx, nr, stretch);
	if (st.probing) {
		printf("SWEET TOUCH: probe xfer addr=%#x %s len=%u stretch=%u err=%d irq=%#x seen=%#x tx=%u rx=%u status=%#x\n",
		    addr, nr ? "read" : "write", nr ? nr : nt, stretch ? 1u : 0u,
		    err, st.irq_last, st.irq_status, st.sent, st.got,
		    touch_rd(st.se, SE_STATUS));
	}
	return err;
}

static int
touch_read(uint8_t addr, uint16_t reg, bool wide, uint8_t *buf, unsigned len)
{
	uint8_t ptr[2] = {(uint8_t)(reg >> 8), (uint8_t)reg};
	int err;
	if (addr == 0x38u) {
		/* Focaltech read: 0x00 <pad> <reg hi> <reg lo>, repeated start, N bytes. */
		const uint8_t fptr[FTS_PTR_LEN] = {0x00, 0x00, (uint8_t)(reg >> 8), (uint8_t)reg};
		err = touch_msg(addr, fptr, FTS_PTR_LEN, NULL, 0, true);
	} else {
		err = touch_msg(addr, wide ? ptr : ptr + 1, wide ? 2u : 1u,
		    NULL, 0, true);
	}
	if (err) {
		return err;
	}
	/* STOP_STRETCH on the pointer write retains the bus for a repeated START. */
	return touch_msg(addr, NULL, 0, buf, len, false);
}

static int
touch_goodix_ack(void)
{
	const uint8_t ack[3] = {GOODIX_EVENT_REG >> 8, GOODIX_EVENT_REG & 0xffu, 0};
	return touch_msg(0x5d, ack, sizeof(ack), NULL, 0, false);
}

/* Raw read only: 0x8240 is the vendor's generic/older VERSION candidate,
 * not a second accepted GT9896 identity. Never try a four-byte Berlin pointer:
 * on this 16-bit IC the extra bytes would be register data writes. */
static int
touch_probe_info(uint16_t reg, uint8_t *buf)
{
	memset(buf, 0xa5, 32);
	int err = touch_read(0x5d, reg, true, buf, 32);
	printf("SWEET TOUCH: probe info reg=%#x len=32 err=%d irq=%#x seen=%#x\n",
	    reg, err, st.irq_last, st.irq_status);
	if (!err) {
		for (unsigned off = 0; off < 32; off += 16) {
			char line[49];
			for (unsigned j = 0; j < 16; ++j) {
				(void)snprintf(line + j * 3u, 4, "%02x ", buf[off + j]);
			}
			printf("SWEET TOUCH: probe raw %#x: %s\n", reg + off, line);
		}
	}
	return err;
}

static unsigned
touch_be16(const uint8_t *p)
{
	return ((unsigned)p[0] << 8) | p[1];
}

static bool
touch_checksum(const uint8_t *buf, unsigned len)
{
	if (len < 2) {
		return false;
	}
	unsigned sum = 0;
	for (unsigned i = 0; i + 2 < len; ++i) {
		sum += buf[i];
	}
	return (sum & 0xffffu) == touch_be16(buf + len - 2);
}

/*
 * Synthetic tap, for bring-up only: boot-arg sweettap=<seconds> followed by
 * sweettapdelay=<seconds>.
 *
 * Why it needs its own timer. The bring-up thread must wait ~45 s before it
 * touches any hardware, because an earlier start puts I2C/RPMh votes on the
 * bus during vfs_mountroot and the boot stops (measured: with
 * sweettouchdelay=12 the system halts at 787 lines and presents=0, against
 * 1586 lines and presents=177 at 45 s). A tap scheduled from that same thread
 * therefore cannot arrive early, and IOSleep in that thread is unreliable once
 * the system is busy. So the tap gets a thread_call of its own, armed at
 * boot-arg time and fired whenever asked - independent of bring-up, and
 * without any waiting primitive in a thread that is already stretched.
 */
static thread_call_t sweet_tap_call;
static unsigned sweet_tap_delay_s = 20;

static void
sweet_tap_fire(__unused thread_call_param_t p0, __unused thread_call_param_t p1)
{
	printf("SWEET TOUCH: synthetic tap (down at %d,%d)\n", 562, 1218);
	sweet_hid_touch(0, 1, 562, 1218);
	sweet_hid_touch(0, 0, 562, 1218);
	printf("SWEET TOUCH: synthetic tap sent\n");
}

void
sweet_tap_arm(void)
{
	int on = 0;

	(void)PE_parse_boot_argn("sweettap", &on, sizeof(on));
	if (!on) {
		return;
	}
	(void)PE_parse_boot_argn("sweettapdelay", &sweet_tap_delay_s,
	    sizeof(sweet_tap_delay_s));
	if (sweet_tap_delay_s < 1 || sweet_tap_delay_s > 600) {
		sweet_tap_delay_s = 20;
	}
	sweet_tap_call = thread_call_allocate(sweet_tap_fire, NULL);
	if (sweet_tap_call == NULL) {
		printf("SWEET TOUCH: no thread_call for the tap\n");
		return;
	}
	printf("SWEET TOUCH: tap armed for %u s\n", sweet_tap_delay_s);
	/*
	 * mach_absolute_time counts absolute ticks, so convert rather than
	 * assuming nanoseconds.
	 */
	uint64_t deadline;
	clock_interval_to_deadline((uint64_t)sweet_tap_delay_s * 1000, NSEC_PER_MSEC,
	    &deadline);
	thread_call_enter_delayed(sweet_tap_call, deadline);
}

static void
touch_report(uint32_t mask, const int *x, const int *y)
{
	for (unsigned id = 0; id < TOUCH_MAX; ++id) {
		uint32_t bit = 1u << id;
		if (mask & bit) {
			if (!(st.active & bit) || x[id] != st.x[id] || y[id] != st.y[id]) {
				sweet_hid_touch((int)id, 1, x[id], y[id]);
			}
			st.x[id] = x[id];
			st.y[id] = y[id];
		} else if (st.active & bit) {
			sweet_hid_touch((int)id, 0, st.x[id], st.y[id]);
		}
	}
	st.active = mask;
}

static int
touch_goodix(void)
{
	uint8_t buf[90];
	int x[TOUCH_MAX] = {0}, y[TOUCH_MAX] = {0};
	uint32_t mask = 0;
	int err = touch_read(0x5d, GOODIX_EVENT_REG, true, buf, GOODIX_HEAD_LEN);
	if (err) {
		return err;
	}
	if (!(buf[0] & 0x80u)) {
		/* Do not acknowledge firmware/config requests that we cannot service. */
		if (buf[0] & 0x40u) {
			return ENOTSUP;
		}
		return 0; /* no new touch frame: retain current contacts */
	}
	if (!touch_checksum(buf, GOODIX_HEAD_LEN)) {
		return EIO; /* header untrusted: no write to the IC */
	}
	unsigned n = buf[2] & 15u;
	if (n > TOUCH_MAX) {
		(void)touch_goodix_ack();
		return EIO;
	}
	if (n) {
		err = touch_read(0x5d, GOODIX_EVENT_REG + GOODIX_HEAD_LEN, true,
		    buf + GOODIX_HEAD_LEN, n * GOODIX_POINT_LEN + 2u);
		if (err) {
			return err;
		}
		if (!touch_checksum(buf + GOODIX_HEAD_LEN, n * GOODIX_POINT_LEN + 2u)) {
			(void)touch_goodix_ack();
			return EIO;
		}
	}
	for (unsigned i = 0; i < n; ++i) {
		const uint8_t *p = buf + GOODIX_HEAD_LEN + i * GOODIX_POINT_LEN;
		unsigned id = p[0] >> 4;
		unsigned px = touch_be16(p + 2), py = touch_be16(p + 4);
		/* Low nibble 1/3 denotes pen data in the vendor parser. */
		if ((p[0] & 15u) == 1u || (p[0] & 15u) == 3u || id >= TOUCH_MAX ||
		    (mask & (1u << id)) || px > 1079 || py > 2399) {
			(void)touch_goodix_ack();
			return EIO;
		}
		mask |= 1u << id;
		x[id] = (int)px;
		y[id] = (int)py;
	}
	err = touch_goodix_ack();
	if (!err) {
		touch_report(mask, x, y);
	}
	return err;
}

/*
 * Focaltech health check, ported from hackios (xnu/files/bsd/dev/redwood_goodix.c):
 * the vendor's fts_wait_tp_to_valid polls the chip-id registers 0xA3/0x9F for up
 * to 1 s at 200 ms steps and expects { 0x56, 0x62 }. A chip that answers nothing
 * here is not running, whatever the I2C layer says, so this has to be checked
 * before any report is read.
 */
#define FTS_CHIP_ID_H   0xa3
#define FTS_CHIP_ID_L   0x9f
#define FTS_ID_H        0x56
#define FTS_ID_L        0x62

static bool
touch_focaltech_valid(void)
{
	for (int attempt = 0; attempt < 5; attempt++) {
		uint8_t h = 0, l = 0;
		if (touch_read(0x38, FTS_CHIP_ID_H, false, &h, 1) == 0 &&
		    touch_read(0x38, FTS_CHIP_ID_L, false, &l, 1) == 0) {
			printf("SWEET TOUCH: focaltech id %02x %02x (attempt %d)\n",
			    h, l, attempt + 1);
			if (h == FTS_ID_H && l == FTS_ID_L) {
				return true;
			}
		} else {
			printf("SWEET TOUCH: focaltech id read failed (attempt %d)\n",
			    attempt + 1);
		}
		touch_wait(200);
	}
	return false;
}

static int
touch_focaltech(void)
{
	uint8_t buf[63];
	int x[TOUCH_MAX] = {0}, y[TOUCH_MAX] = {0};
	uint32_t mask = 0, seen = 0;
	int err = touch_read(0x38, 0, false, buf, sizeof(buf));
	if (err) {
		return err;
	}
	unsigned n = buf[2] & 15u, active = 0;
	if ((buf[0] & 0x70u) || n > TOUCH_MAX) {
		return EIO;
	}
	for (unsigned i = 0; i < TOUCH_MAX; ++i) {
		const uint8_t *p = buf + 3u + 6u * i;
		unsigned id = p[2] >> 4, event = p[0] >> 6;
		if (id >= TOUCH_MAX) {
			break; /* vendor's unused-record sentinel */
		}
		if (seen & (1u << id)) {
			return EIO;
		}
		seen |= 1u << id;
		if (event == 1u) {
			continue; /* UP record */
		}
		if (event == 3u) {
			return EIO;
		}
		unsigned px = ((unsigned)(p[0] & 15u) << 8) | p[1];
		unsigned py = ((unsigned)(p[2] & 15u) << 8) | p[3];
		if (px > 1079 || py > TOUCH_Y_MAX) {
			return EIO;
		}
		mask |= 1u << id;
		x[id] = (int)px;
		y[id] = (int)py;
		++active;
	}
	if (active != n) {
		return EIO;
	}
	touch_report(mask, x, y);
	/*
	 * A report with no contact point is a normal "nothing is touching" frame,
	 * not a touch: report it as EAGAIN so the poller keeps waiting instead of
	 * painting the "touch arrived" colour every cycle (NOTES 21:45).
	 */
	return mask != 0 ? 0 : EAGAIN;
}

static bool
touch_se_init(void)
{
	uint32_t fw = touch_rd(st.se, SE_FW);
	uint32_t tx = touch_rd(st.se, SE_HW_TX), rx = touch_rd(st.se, SE_HW_RX);
	printf("SWEET TOUCH: se7 fw=%#x proto=%u status=%#x tx=%#x rx=%#x ios=%#x\n",
	    fw, (fw >> 8) & 0xffu, touch_rd(st.se, SE_STATUS), tx, rx,
	    touch_rd(st.se, 0x908));
	if (((fw >> 8) & 0xffu) != 3u || (touch_rd(st.se, 0x64) & 1u) ||
	    ((tx >> 24) & 0x3fu) != 32u || ((rx >> 24) & 0x3fu) != 32u ||
	    ((tx >> 16) & 0x3fu) < 2u || ((rx >> 16) & 0x3fu) < 2u) {
		printf("SWEET TOUCH: need ABL-loaded I2C firmware and 32-bit FIFOs; probes skipped\n");
		return false;
	}
	if (touch_rd(st.se, SE_STATUS) & 0x1001u) {
		printf("SWEET TOUCH: SE7 already busy; probes skipped\n");
		return false;
	}
	touch_wr(st.se, 0xe18, 0); /* no GSI events */
	touch_wr(st.se, 0xe1c, 0); /* mask external IRQ routing; poll local status */
	touch_wr(st.se, 0x644, 0);	/* M_CMD_CTRL */
#if defined(GAUGUIN)
	touch_wr(st.se, 0x634, 0);	/* S_CMD_CTRL (SE8 has HW-dependent defaults) */
#endif
	touch_wr(st.se, SE_IRQ_CLR, 0xffffffffu);
	touch_wr(st.se, 0x648, 0xffffffffu);	/* M_CMD_CTRL IRQ clear */
#if defined(GAUGUIN)
	touch_wr(st.se, 0x638, 0xffffffffu);	/* S_CMD_CTRL IRQ clear */
#endif
	touch_wr(st.se, SE_DMA, 0);
	touch_wr(st.se, 0x28, touch_rd(st.se, 0x28) | 0x7fu);
	touch_wr(st.se, 0xe30, touch_rd(st.se, 0xe30) | 0x0fu);
	touch_wr(st.se, 0x24, 0x7f);
	touch_wr(st.se, 0x20, 1);
	touch_wr(st.se, SE_CLK_SEL, 0);
	touch_wr(st.se, SE_MCLK, (7u << 4) | 1u);
	touch_wr(st.se, SE_SCL, (10u << 20) | (11u << 10) | 26u); /* 100 kHz */
	/* Linux 8-bit I2C packing: MSB on the wire, LSB byte first in FIFO. */
	touch_wr(st.se, 0x254, 0);
	touch_wr(st.se, 0x260, SE_PACK0);
	touch_wr(st.se, 0x264, SE_PACK1);
	touch_wr(st.se, 0x284, SE_PACK0);
	touch_wr(st.se, 0x288, SE_PACK1);
	touch_wr(st.se, SE_TX_WM, 0);
	touch_wr(st.se, 0x810, 0);
	touch_wr(st.se, 0x814, ((rx >> 16) & 0x3fu) - 1u);
	touch_wr(st.se, SE_IRQ_EN, SE_EVENTS);
	printf("SWEET TOUCH: packing tx=%#x/%#x rx=%#x/%#x gran=%#x\n",
	    touch_rd(st.se, 0x260), touch_rd(st.se, 0x264),
	    touch_rd(st.se, 0x284), touch_rd(st.se, 0x288), touch_rd(st.se, 0x254));
	if (touch_rd(st.se, 0x260) != SE_PACK0 || touch_rd(st.se, 0x264) != SE_PACK1 ||
	    touch_rd(st.se, 0x284) != SE_PACK0 || touch_rd(st.se, 0x288) != SE_PACK1 ||
	    touch_rd(st.se, 0x254) != 0) {
		printf("SWEET TOUCH: packing readback mismatch; probes skipped\n");
		return false;
	}
	if ((touch_rd(st.se, SE_TX_COUNT) & 0xfffffffu) ||
	    (touch_rd(st.se, SE_RX_COUNT) & 0x1ffffffu)) {
		printf("SWEET TOUCH: inherited FIFO data; probes skipped\n");
		return false;
	}
	return true;
}

/*
 * A bare kernel thread started from userland context arms its deadline but is
 * never woken in this port (NOTES 23:11), while IOTimerEventSource on a workloop
 * fires reliably for the framebuffer at 60 Hz. So the start-up gate is a workloop
 * timer and the bring-up runs from its callback.
 */
void touch_bringup(void);

extern void thread_terminate_self(void);
extern kern_return_t mach_wait_until_trap(void *args);     /* Mach, not exported to BSD */

/* Implemented in C++ (iokit/Kernel/arm/SweetTouchTimer.cpp). */
extern int sweet_touch_timer_arm(unsigned seconds);
extern void sweet_fb_mark(uint32_t colour);
extern void sweet_log_flush_now(void);
extern void sweet_log_mark(const char *text);
#define TOUCH_MARK(t) sweet_log_mark(t)

/*
 * Called from AppleCLCD::vsyncFired (AppleCLCD runs its timer reliably). Waits
 * for the boot-arg delay to expire in frames, then runs the bring-up once.
 */
/*
 * Synchronous, read-only bring-up.
 *
 * Every asynchronous context has failed: a kernel thread parked on a deadline
 * never wakes, and an IOTimerEventSource callback wedges the boot even when it
 * only increments a counter (NOTES 12:20). So this runs directly in the exec
 * hook, takes no lock we do not own, creates nothing, never sleeps, and only
 * *reads* registers - a read cannot hang the way a write to a clock gate can,
 * and the result tells us whether the MMIO windows are even reachable.
 */
void
touch_bringup(void)
{
	/*
	 * Every step is a read, yet the phone reset after the first marker. Paint
	 * before AND after each step so the panel names the exact culprit:
	 *   red -> map GCC -> yellow -> read -> purple -> map TLMM -> cyan -> ...
	 */
	printf("SWEET TOUCH: stage A: map GCC\n");
	sweet_fb_mark(0x00ffff00u);             /* RGB(0,255,255) CYAN: map GCC */
	vm_offset_t gcc = ml_io_map(TOUCH_GCC_PA, 0x60000);
	printf("SWEET TOUCH: gcc=%#lx\n", (unsigned long)gcc);
	if (gcc == 0) {
		printf("SWEET TOUCH: GCC map failed\n");
		sweet_fb_mark(0x0000ffffu);
		return;
	}

	printf("SWEET TOUCH: stage B: read GCC\n");
	sweet_fb_mark(0x00ff00ffu);             /* RGB(255,0,255) MAGENTA: read GCC */
	uint32_t gcc0 = touch_rd(gcc, 0x0);
	printf("SWEET TOUCH: GCC control = %#x\n", gcc0);

	/*
	 * TLMM sits in the NORTH clock domain. Mapping it with no clock running was
	 * where every previous run stopped (NOTES 14:35), so turn the clock on
	 * first, using the GCC window that is already known good.
	 */
	printf("SWEET TOUCH: stage C: clock on\n");
	st.gcc = gcc;
	/*
	 * Everything from 0x18058 to 0x18188 reads back zero while 0x0000-0x0fe8 is
	 * populated (NOTES 15:05), which means that part of the aperture is not
	 * mapped at all rather than having the wrong offset. Walk the 0x60000 window
	 * one page at a time and print only pages that contain a non-zero word, so
	 * the real extent of GCC is visible in one boot.
	 */
	/*
	 * Only walk up to 0x19000: the full 0x60000 walk locks up (NOTES 15:08),
	 * which by itself says some page in the window is not backed. The words at
	 * 0x18058+ read zero, so find the page where reads stop making sense.
	 */
	/*
	 * Sparse walk: 4 reads per page instead of 1024. The dense walk cost 6400
	 * strongly-ordered reads (each with a dmb) and made the boot look dead, so
	 * this samples the page head, +0x800 and the tail - enough to tell a real
	 * register page from an unmapped hole.
	 */
	printf("SWEET TOUCH: sparse GCC walk\n");
	for (uint32_t page = 0; page < 0x19000; page += 0x1000) {
		static const uint32_t sample[3] = { 0x0u, 0x800u, 0xff0u };
		uint32_t a = touch_rd(gcc, page + sample[0]);
		uint32_t b = touch_rd(gcc, page + sample[1]);
		uint32_t c = touch_rd(gcc, page + sample[2]);
		printf("SWEET TOUCH: %#06x: %#010x %#010x %#010x\n",
		    page, a, b, c);
	}
	printf("SWEET TOUCH: GCC page walk done\n");
	sweet_fb_mark(0x00ff8000u);             /* AZURE: walk finished */
	if (!touch_clocks()) {
		printf("SWEET TOUCH: clocks failed; not touching TLMM\n");
		sweet_fb_mark(0x00ffffffu);         /* white: clock failure */
		return;
	}

	printf("SWEET TOUCH: stage D: map TLMM (one page)\n");
	sweet_fb_mark(0x0080ff00u);             /* RGB(0,255,128) SPRING: map TLMM */
	/*
	 * Map the page that holds the pin in use rather than a fixed +0x50000
	 * window: on gauguin/SM7225 the TLMM starts at 0xf100000 and that offset
	 * walked past the end of the window. The per-pin stride (0x1000) is the
	 * same on both SoCs.
	 */
	uint32_t gpio_pa = TOUCH_NORTH_PA + TOUCH_GPIO_CFG(TOUCH_GPIO_RST);
	vm_offset_t gpio = ml_io_map(gpio_pa, 0x1000);
	printf("SWEET TOUCH: gpio map %#x returned %#lx\n", gpio_pa, (unsigned long)gpio);
	if (gpio) {
		uint32_t rst = touch_rd(gpio, TOUCH_GPIO_IO(TOUCH_GPIO_RST) - TOUCH_GPIO_CFG(TOUCH_GPIO_RST));
		printf("SWEET TOUCH: RST cfg=%#x\n", rst);
	}

	printf("SWEET TOUCH: stage E: map SE%u\n",
	    (unsigned)((TOUCH_SE_PA >> 16) - 0x8cu));
	sweet_fb_mark(0x00ff0000u);             /* RGB(0,0,255) BLUE again: map SE */
	vm_offset_t se = ml_io_map(TOUCH_SE_PA, 0x4000);
	if (se) {
		printf("SWEET TOUCH: GENI status=%#x\n", touch_rd(se, 0x20));
	}
	/*
	 * Power the touch rail, then ask the chip who it is - in that order, the
	 * same order hackios uses (RPMh vote, then GPIO, then the IC answers).
	 */
	printf("SWEET TOUCH: stage F: power rail %s\n", TOUCH_RAIL);
	int rail = sweet_rpmh_vreg_enable(TOUCH_RAIL, TOUCH_RAIL_MV);
	printf("SWEET TOUCH: rail %s -> %d\n", TOUCH_RAIL, rail);

	printf("SWEET TOUCH: stage G: release reset, read chip id\n");
	if (gpio) {
		uint32_t off = TOUCH_GPIO_CFG(TOUCH_GPIO_RST) - 0x50000u;
		uint32_t cfg = touch_rd(gpio, off);
		touch_wr(gpio, off, (cfg & ~0x3ffu) | 0x201u);   /* output, func 0 */
		touch_wr(gpio, TOUCH_GPIO_IO(TOUCH_GPIO_RST) - 0x50000u, 2u);
		touch_wait(10);
		printf("SWEET TOUCH: reset released\n");
	}
	bool present = touch_focaltech_valid();
	printf("SWEET TOUCH: focaltech %s\n", present ? "ANSWERS" : "silent");
	/*
	 * Answer on the panel, because the log has not survived six attempts to
	 * read it back (NOTES 21:35). The colour block is the verdict the user can
	 * read straight off the screen:
	 *   RED    rail vote failed      BLUE  no TLMM window
	 *   YELLOW rail ok, chip silent  GREEN chip answered
	 */
	sweet_fb_mark(rail != 0 ? 0x000000ffu : (gpio == 0 ? 0x00ff0000u :
	    (present ? 0x0000ff00u : 0x0000ffffu)));
	{
		char mark[160];
		snprintf(mark, sizeof(mark),
		    "TOUCH rail=%d gpio=%d chip=%s gcc=%#lx se=%#lx",
		    rail, gpio ? 1 : 0, present ? "ANSWERS" : "silent",
		    (unsigned long)gcc, (unsigned long)se);
		sweet_log_mark(mark);       /* survives the ring being overwritten */
	}
	/*
	 * The poll loop is off until it runs on a thread of its own. Putting it
	 * here made it part of the UFS init path, so UFS never finished and iOS
	 * could not read its root - the phone rebooted in a loop (NOTES 21:50).
	 * sweet_touch_poll_start() is where it belongs; this guarded block stays
	 * so the panel test can be reproduced deliberately.
	 */
	int poll_here = 0;
	(void)PE_parse_boot_argn("sweetpollhere", &poll_here, sizeof(poll_here));
	if (present && poll_here) {
		printf("SWEET TOUCH: polling for reports\n");
		bool touching = false;
		for (;;) {
			int err = touch_focaltech();
			if (err == 0 && !touching) {
				touching = true;
				printf("SWEET TOUCH: touch down\n");
				sweet_fb_mark(0x00ff0000u);     /* blue: finger down */
			} else if (err != 0 && touching) {
				touching = false;
				printf("SWEET TOUCH: touch up\n");
				sweet_fb_mark(0x0000ff00u);     /* green: idle */
			}
			/*
			 * Spin a little, then let the scheduler run someone else. There is
			 * no thread_yield() in this tree; IOSleep is the portable way to
			 * give up the CPU from a kernel thread and it does not need the
			 * deadline path that is broken here (only 1 ms, so it is cheap).
			 */
			for (volatile unsigned spin = 0; spin < 20000u; spin++) {
				;
			}
			IOSleep(1);
		}
	}
	/*
	 * Push the result to flash now. The periodic flush runs every
	 * sweetlogms, and userland keeps the disk busy, so this line could sit in
	 * the buffer while the phone is powered off after the check (NOTES 21:12).
	 */
	sweet_log_flush_now();
	TOUCH_MARK(present ? "TOUCH: bringup done, chip answered" : "TOUCH: bringup done, no chip");
	sweet_fb_mark(present ? 0x0000ff00u : 0x000000ffu);

	printf("SWEET TOUCH: read-only probe complete\n");
}


static int
gcc_probe(void)
{
	vm_offset_t gcc = ml_io_map(TOUCH_GCC_PA, 0x60000);
	if (gcc == 0) {
		return -1;
	}
	(void)touch_rd(gcc, 0x0);
	return 0;
}

/*
 * Entry point for the framebuffer driver's start(): a kernel-boot context, not a
 * thread, not a timer callback, not the exec hook.
 */
/*
 * Bring-up thread. Created by sweet_touch_start_at_init() so that the UFS
 * init path - which has to return before BSD can mount the root - never runs
 * the hardware sequence itself.
 */
static void
touch_bringup_thread(__unused void *arg, __unused wait_result_t wr)
{
	static event_t chan;
	/*
	 * Wait before touching any hardware. The working boot shows
	 * "SWEET TOUCH: starting in 45 s" during vfs_mountroot: the bring-up was
	 * deliberately held back so that root mount and launchd start first, and
	 * the touch driver's MMIO/RPMh/I2C work then runs against a settled
	 * system. Starting it immediately (what this thread did until now) puts
	 * GENI, TLMM and an RPMh vote on the buses exactly while the root is being
	 * mounted - the one window where a stall is fatal and hardest to see.
	 */
	int delay_s = 45;
	PE_parse_boot_argn("sweettouchdelay", &delay_s, sizeof(delay_s));
	if (delay_s > 0) {
		printf("SWEET TOUCH: starting in %d s\n", delay_s);
		/*
		 * Plain IOSleep, one second at a time.
		 *
		 * This used assert_wait_deadline + thread_block(THREAD_CONTINUE_NULL)
		 * - the same idiom as sweet_keys.c - but paired with an uninterruptible
		 * wait and a block that supplies no deadline of its own: nothing wakes
		 * &chan, so the delay only ever ended by luck, when some unrelated
		 * wakeup landed on it. With sweettouchdelay=170 the bring-up had still
		 * not started after 540 s of runtime (NOTES (63)). The default 45 worked
		 * by accident.
		 *
		 * IOSleep cannot miss a wakeup because it does not wait for one.
		 */
		for (int i = 0; i < delay_s; i++) {
			IOSleep(1000);
		}
	}
	TOUCH_MARK("TOUCH: bringup enter");
	printf("SWEET TOUCH: bring-up thread running\n");
	touch_bringup();
	printf("SWEET TOUCH: bring-up thread finishing\n");
	thread_terminate_self();
}

void
sweet_touch_start_at_init(void)
{
	int mode = 1;
	(void)PE_parse_boot_argn("sweettouchmode", &mode, sizeof(mode));
	printf("SWEET TOUCH: start_at_init, mode=%d\n", mode);
	/*
	 * Arm the injected tap here, at init, not from the bring-up thread: it
	 * must be able to fire during or after startup without waiting on the
	 * 45 s hardware delay.
	 */
	{
		extern void sweet_tap_arm(void);
		sweet_tap_arm();
	}
	if (mode == 0) {
		printf("SWEET TOUCH: mode 0, nothing to do\n");
		return;
	}
	if (mode == 3) {
		/* Control: prove the ring still refreshes with no touch work at all. */
		printf("SWEET TOUCH: mode 3, print-only control\n");
		return;
	}
	/*
	 * Run the real bring-up, but NOT on this thread.
	 *
	 * This is called from sweet_ufs_rootdev(), i.e. on the thread that has to
	 * finish initialising the root device before BSD can mount the root and
	 * start launchd. The bring-up walks MMIO, votes a rail through RPMh,
	 * reprograms a GENI SE and polls an I2C chip - any of which can block -
	 * and while it runs, iOS has no root and the boot cannot proceed. Touch
	 * is not needed for iOS to boot, so it gets its own thread and the init
	 * path returns immediately (NOTES 2026-11-03).
	 *
	 * The panel carries the progress (the log does not refresh reliably), so
	 * each stage paints a colour.
	 */
	sweet_fb_mark(0x00ff0000u);     /* RGB(0,0,255) BLUE: bring-up starts */
	TOUCH_MARK("TOUCH: bringup queued");
	if (!st.thread_started) {
		thread_t thread;
		st.thread_started = true;
		if (kernel_thread_start((thread_continue_t)touch_bringup_thread, NULL,
		    &thread) == KERN_SUCCESS) {
			thread_deallocate(thread);
			printf("SWEET TOUCH: bring-up on its own thread\n");
			return;
		}
		printf("SWEET TOUCH: kernel_thread_start failed; running inline\n");
	}
	/* Only when the thread could not be created: keep the old behaviour. */
	touch_bringup();
}

void
sweet_touch_init(void)
{
	int enabled = 1;
	if (st.started) {
		return;
	}
	st.started = true;
	(void)PE_parse_boot_argn("sweettouch", &enabled, sizeof(enabled));
	(void)PE_parse_boot_argn("sweettouchirq", &st.irq_hint, sizeof(st.irq_hint));
	if (!enabled) {
		printf("SWEET TOUCH: disabled (sweettouch=0)\n");
		return;
	}
	/*
	 * Queue the bring-up on its own thread, never inline.
	 *
	 * boot-journaled-userland.txt shows the successful sequence printing only
	 * "touch_init" then "touch_init done" with nothing between - that is a
	 * function which starts a thread and returns. Running the hardware
	 * sequence here instead puts it on the UFS init path, which has to return
	 * before BSD can mount the root (NOTES 2026-11-03 (3) and (5)).
	 */
	{
		int mode = 1;
		(void)PE_parse_boot_argn("sweettouchmode", &mode, sizeof(mode));
		if (mode == 0) {
			printf("SWEET TOUCH: mode 0, bring-up skipped\n");
			return;
		}
		if (mode == 2) {
			return;   /* mode 2: init entered, nothing else */
		}
	}
	sweet_touch_start_at_init();
}
#endif /* ARM64_BOARD_CONFIG_SWEET */
