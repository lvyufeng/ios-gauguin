/*
 * SWEET internal UFS root device.
 *
 * The Qualcomm UFS host (UFSHCI 2.1) is left enabled with the link up by the
 * bootloader, which loaded our boot image from it. This driver reuses that
 * state: it points the transfer request list at its own memory (verifying the
 * host took it before ringing any doorbell) and issues polled SCSI commands,
 * one at a time, to LUN 0. It finds one GPT partition by name (boot-arg
 * ufsroot=, default "userdata") and exposes it as the BSD disk ufsroot0
 * (rufsroot0), with 512-byte logical sectors over the device's 4 KiB blocks.
 * Root on it with rd=ufsroot0.
 *
 * All DMA goes through one physically contiguous allocation (descriptors and
 * a 1 MiB bounce buffer); the host is not cache coherent, so caches are
 * cleaned/invalidated around each command.
 *
 * Writes are refused unless boot-arg ufsrw=1 is set. Every write is checked
 * against the partition bounds again right before it is issued, so nothing
 * outside the named partition can be written.
 */
#if defined(ARM64_BOARD_CONFIG_SWEET)
#include <sys/param.h>
#include <sys/systm.h>
#include <sys/buf.h>
#include <sys/conf.h>
#include <sys/disk.h>
#include <sys/errno.h>
#include <sys/proc.h>
#include <sys/proc_internal.h>
#include <sys/uio.h>
#include <miscfs/devfs/devfs.h>
/* Kept identical to xnu/sweet_init_watchdog.h in the repo (deps/sync-watchdog.sh). */
#include "sweet_init_watchdog.h"
#include <kern/locks.h>
#include <kern/clock.h>
#include <kern/sched_prim.h>
#include <machine/machine_routines.h>
#include <arm/caches_internal.h>
#include <vm/pmap.h>
#include <vm/vm_kern.h>
#include <pexpert/pexpert.h>
#include <pexpert/device_tree.h>
#include <libkern/libkern.h>
#include <machine/atomic.h>

extern ppnum_t pmap_find_phys(pmap_t pmap, addr64_t va);
/* osfmk/arm/machine_routines.h, not exported to the BSD layer */
extern vm_offset_t ml_io_map(vm_offset_t phys_addr, vm_size_t size);
/* osfmk/arm/cpu_data.h, not exported to the BSD layer */
extern int get_preemption_level(void);
extern kern_return_t kernel_thread_start(thread_continue_t, void *, thread_t *);
extern void thread_deallocate(thread_t);
extern int hz;
static void sweet_log_start(void);
static void sweet_log_sync(void);
static void sweet_reboot_start(void);
extern void sweet_sample_start(void);
extern void sweet_keys_init(void);
extern void sweet_touch_init(void);
extern void sweet_touch_start_at_init(void);
extern void sweet_log_mark(const char *text);
extern void sweet_log_mark_sync(const char *text);
extern void sweet_usb_probe(void);

#define REG_CAP         0x00
#define REG_IS          0x20
#define REG_IE          0x24
#define REG_HCS         0x30
#define REG_HCE         0x34
#define REG_UTRLBA      0x50
#define REG_UTRLBAU     0x54
#define REG_UTRLDBR     0x58
#define REG_UTRLCLR     0x5c
#define REG_UTRLRSR     0x60

#define HCS_DP          (1u << 0)
#define HCS_UTRLRDY     (1u << 1)
#define CAP_64AS        (1u << 24)              /* 64-bit DMA addressing */

#define UFS_BLOCK       4096u
#define BOUNCE_SIZE     (1u << 20)
#define PRDT_CHUNK      (256u << 10)            /* PRDT byte count field: 18 bits */
#define PRDT_MAX        (BOUNCE_SIZE / PRDT_CHUNK)
#define CMD_TIMEOUT_NS  (5ull * NSEC_PER_SEC)
#define CMD_SPIN_NS     (50ull * NSEC_PER_USEC)
#define CMD_SLEEP_NS    (200ull * NSEC_PER_USEC)

struct utrd {
	uint32_t dw0, dw1, dw2, dw3;
	uint32_t ucdba, ucdbau;
	uint32_t resp;          /* [31:16] response UPIU offset, [15:0] length, DWORDs */
	uint32_t prdt;          /* [31:16] PRDT offset (DWORDs), [15:0] entries */
};

struct ucd {
	uint8_t cmd[512];
	uint8_t resp[512];
	struct {
		uint32_t addr_lo, addr_hi, rsvd, dbc;
	} prdt[PRDT_MAX];
};

/* Layout of the contiguous DMA allocation. */
#define DMA_UTRL        0x0000                  /* 1 KiB aligned */
#define DMA_UCD         0x1000                  /* 128 byte aligned */
#define DMA_BOUNCE      0x4000
#define DMA_STAGE       (DMA_BOUNCE + BOUNCE_SIZE)      /* stage block, see sweet_stage() */
/*
 * The persistent log gets its own request slot and its own data buffer.
 *
 * Until now every command - the root device's, the file system's and the log
 * thread's - used UTRL slot 0 and DMA_BOUNCE. Two of them at once is a
 * deadlock, not a race that sorts itself out: ufs_scsi_pa() overwrites the
 * shared UTRD, rings the doorbell and then polls UTRLDBR bit 0, which the
 * hardware may already have cleared for the *other* command, so the second
 * caller waits on a completion it will never see. The log thread is started
 * from the init path and its first flush runs while init is still inside
 * sweet_ufs_rootdev(), which is where the boot stopped (NOTES 2026-11-03).
 *
 * Slot 1 + DMA_UCD_LOG + DMA_BOUNCE_LOG let the log write while any one other
 * command is in flight, without taking the other caller's slot.
 */
#define DMA_UCD_LOG     0x2000
#define DMA_UCD_MARK    0x3000
#define DMA_MARK        (DMA_STAGE + 4096)      /* one 4 KiB block for sweet_log_mark() */
#define DMA_BOUNCE_LOG  (DMA_MARK + 4096)
#define DMA_SIZE        (DMA_BOUNCE_LOG + BOUNCE_SIZE)

#define UFS_SLOT_MAIN   0u
#define UFS_SLOT_LOG    1u
#define UFS_SLOT_MARK   2u

static struct {
	vm_offset_t regs;
	vm_offset_t dma;                        /* kernel VA of the DMA allocation */
	uint64_t dma_pa;
	uint8_t lun;
	uint8_t tag;				/* atomic: command tag, see ufs_scsi_slot() */
	uint64_t first_block, nblocks;          /* partition, in 4 KiB device blocks */
	uint32_t secsize;                       /* logical sector size for the BSD layer */
	bool writable;                          /* boot-arg ufsrw=1 */
	bool cache;                             /* boot-arg ufscache=1 */
	bool wait;                              /* boot-arg ufswait=1 */
	int bmajor, cmajor;
	dev_t bdev;
	bool ready;
} su;

static LCK_GRP_DECLARE(sweet_ufs_grp, "sweet_ufs");
static LCK_MTX_DECLARE(sweet_ufs_lock, &sweet_ufs_grp);
/*
 * One lock per request slot. sweet_ufs_lock still serialises everything that
 * uses slot 0 and DMA_BOUNCE (root device, file system, partition scan); the
 * persistent log takes sweet_log_lock and slot 1, so the two never wait on
 * each other's completion. See the DMA_SLOT comment for why sharing was a
 * deadlock.
 */
static LCK_MTX_DECLARE(sweet_log_lock, &sweet_ufs_grp);
static LCK_MTX_DECLARE(sweet_mark_lock, &sweet_ufs_grp);

/*
 * Init-tail progress, readable from the log thread. sweet_init_step names the
 * step currently being entered so the watchdog above can print something
 * useful when the step itself never returns.
 */
static uint32_t _Atomic sweet_init_done;
static const char *_Atomic sweet_init_step = "not started";
static struct sweet_wd_state sweet_init_wd;    /* see xnu/sweet_init_watchdog.h */

static inline uint32_t
ufs_rd(uint32_t off)
{
	return *(volatile uint32_t *)(su.regs + off);
}

static inline void
ufs_wr(uint32_t off, uint32_t v)
{
	*(volatile uint32_t *)(su.regs + off) = v;
}

static void
dma_sync(uint32_t off, uint32_t len)
{
	flush_dcache64((addr64_t)(su.dma_pa + off), len, TRUE);
}

static void
dma_clean(uint32_t off, uint32_t len)
{
	clean_dcache64((addr64_t)(su.dma_pa + off), len, TRUE);
}

/*
 * One SCSI command in `slot`, data (if any) to/from that slot's bounce buffer
 * (to the device when write is set). Returns 0 or an errno.
 */
static int ufs_write_abs(uint64_t lba, uint32_t count, uintptr_t pa);
static int ufs_scsi_slot(const uint8_t *cdb, unsigned cdb_len, uint32_t len, bool write,
    uintptr_t data_pa, unsigned slot);

static int
ufs_scsi(const uint8_t *cdb, unsigned cdb_len, uint32_t len, bool write)
{
	return ufs_scsi_slot(cdb, cdb_len, len, write, su.dma_pa + DMA_BOUNCE, UFS_SLOT_MAIN);
}

/* Same command with its data at an arbitrary physical address (stage block). */
static int
ufs_scsi_slot(const uint8_t *cdb, unsigned cdb_len, uint32_t len, bool write,
    uintptr_t data_pa, unsigned slot)
{
	struct utrd *utrd = (struct utrd *)(su.dma + DMA_UTRL + slot * sizeof(struct utrd));
	uint32_t ucd_off = slot == UFS_SLOT_LOG ? DMA_UCD_LOG : (slot == UFS_SLOT_MARK ? DMA_UCD_MARK : DMA_UCD);
	struct ucd *ucd = (struct ucd *)(su.dma + ucd_off);
	uint64_t ucd_pa = su.dma_pa + ucd_off, bounce_pa = data_pa;
	uint32_t bit = 1u << slot;
	uint32_t bounce_off = slot == UFS_SLOT_LOG ? DMA_BOUNCE_LOG :
	    (slot == UFS_SLOT_MARK ? DMA_MARK : DMA_BOUNCE);

	assert(len <= BOUNCE_SIZE);
	bzero(utrd, sizeof(*utrd));
	bzero(ucd, sizeof(*ucd));

	ucd->cmd[0] = 0x01;                     /* COMMAND UPIU */
	ucd->cmd[1] = len ? (write ? 0x20 : 0x40) : 0x00;      /* W: data out, R: data in */
	ucd->cmd[2] = su.lun;
	/*
	 * The tag must be unique among commands the controller is running at the
	 * same time, and since the request slots were split the callers really can
	 * be concurrent. Plain ++ is a read-modify-write with no atomicity, so two
	 * slots could stamp the same tag and a completion could be attributed to
	 * the wrong command. Atomic fetch-add, 1..31 (0 is reserved/not used here).
	 */
	ucd->cmd[3] = (uint8_t)((os_atomic_inc_orig(&su.tag, relaxed) & 0x1f) + 1);
	ucd->cmd[12] = (uint8_t)(len >> 24);
	ucd->cmd[13] = (uint8_t)(len >> 16);
	ucd->cmd[14] = (uint8_t)(len >> 8);
	ucd->cmd[15] = (uint8_t)len;
	memcpy(&ucd->cmd[16], cdb, cdb_len);

	/* DD: 1 = memory to device, 2 = device to memory. */
	utrd->dw0 = (1u << 28) | ((len ? (write ? 1u : 2u) : 0u) << 25) | (1u << 24);
	utrd->dw2 = 0x0f;                       /* OCS invalid until updated */
	utrd->ucdba = (uint32_t)ucd_pa;
	utrd->ucdbau = (uint32_t)(ucd_pa >> 32);
	utrd->resp = (512u / 4) << 16 | (512u / 4);
	if (len) {
		uint32_t n = 0;
		for (uint32_t done = 0; done < len; done += PRDT_CHUNK, n++) {
			uint32_t chunk = MIN(PRDT_CHUNK, len - done);
			ucd->prdt[n].addr_lo = (uint32_t)(bounce_pa + done);
			ucd->prdt[n].addr_hi = (uint32_t)((bounce_pa + done) >> 32);
			ucd->prdt[n].dbc = chunk - 1;
		}
		utrd->prdt = (1024u / 4) << 16 | n;
	}

	if (su.cache) {
		dma_clean(DMA_UTRL + slot * sizeof(struct utrd), sizeof(*utrd));
		dma_clean(ucd_off, 16 + cdb_len);
		dma_sync(ucd_off + offsetof(struct ucd, resp), sizeof(ucd->resp));
		if (len) {
			dma_clean(ucd_off + offsetof(struct ucd, prdt),
			    (utrd->prdt & 0xffff) * sizeof(ucd->prdt[0]));
		}
	} else {
		dma_sync(DMA_UTRL + slot * sizeof(struct utrd), sizeof(*utrd));
		dma_sync(ucd_off, sizeof(*ucd));
	}
	if (len) {
		if (su.cache && write) {
			dma_clean(bounce_off, len);
		} else {
			dma_sync(bounce_off, len);
		}
	}
	__builtin_arm_dsb(0xf);

	/*
	 * Per-command lines only for the first commands: userland issues tens of
	 * thousands of them and they were 97% of the ring, pushing the boot-time
	 * touch lines out (NOTES 20:10). sweetufslog=N raises the budget.
	 */
	static int ufs_budget = -1;
	if (ufs_budget < 0) {
		ufs_budget = 64;
		PE_parse_boot_argn("sweetufslog", &ufs_budget, sizeof(ufs_budget));
	}
	if (ufs_budget > 0) {
		ufs_budget--;
		printf("SWEET UFS: scsi cdb 0x%02x len %u, slot %u, ringing\n",
		    cdb[0], len, slot);
	}
	ufs_wr(REG_UTRLDBR, bit);
	uint64_t deadline;
	nanoseconds_to_absolutetime(CMD_TIMEOUT_NS, &deadline);
	deadline += mach_absolute_time();
	bool sleepable = su.wait && su.ready && ml_get_interrupts_enabled() &&
	    !ml_at_interrupt_context() && get_preemption_level() == 0;
	uint64_t spin_until = 0, sleep_interval = 0;
	if (sleepable) {
		nanoseconds_to_absolutetime(CMD_SPIN_NS, &spin_until);
		spin_until += mach_absolute_time();
		nanoseconds_to_absolutetime(CMD_SLEEP_NS, &sleep_interval);
	}
	unsigned spins = 0;
	while (ufs_rd(REG_UTRLDBR) & bit) {
		uint64_t now = mach_absolute_time();
		if (++spins == 1000 || (spins & 0xfffff) == 0) {
			printf("SWEET UFS: still busy after %u spins (now %llu, deadline %llu, db 0x%x)\n",
			    spins, (unsigned long long)now, (unsigned long long)deadline,
			    ufs_rd(REG_UTRLDBR));
		}
		if (now > deadline) {
			ufs_wr(REG_UTRLCLR, ~bit);
			printf("SWEET UFS: command 0x%02x timed out\n", cdb[0]);
			return ETIMEDOUT;
		}
		if (sleepable && now >= spin_until) {
			uint64_t wake = now + MIN(sleep_interval, deadline - now);
			/* Keep the mutex: our slot and bounce buffer are still owned. */
			if (assert_wait_deadline_with_leeway((event_t)&su.wait, THREAD_UNINT,
			    TIMEOUT_URGENCY_SYS_CRITICAL, wake, 0) == THREAD_WAITING) {
				thread_block(THREAD_CONTINUE_NULL);
			}
		} else {
			delay(1);
		}
	}
	__builtin_arm_dsb(0xf);
	/*
	 * Per-command completion lines are on by default because they are the
	 * cheapest way to see the storage layer move, but they swamp everything
	 * else: 14,257 of 16,910 log lines in one boot (84%) are this one
	 * printf, and they are what pushed the synthetic-tap experiment's output
	 * off the end of the ring five times (NOTES (61)). sweetufsquiet=1
	 * silences them so an experiment later in the boot has somewhere to land.
	 */
	{
		static int quiet = -1;
		if (quiet < 0) {
			quiet = 0;
			PE_parse_boot_argn("sweetufsquiet", &quiet, sizeof(quiet));
		}
		if (!quiet) {
			printf("SWEET UFS: scsi 0x%02x completed after %u spins\n", cdb[0], spins);
		}
	}
	ufs_wr(REG_IS, ufs_rd(REG_IS));         /* acknowledge completion status */

	dma_sync(DMA_UTRL + slot * sizeof(struct utrd), sizeof(*utrd));
	if (su.cache) {
		dma_sync(ucd_off + offsetof(struct ucd, resp), sizeof(ucd->resp));
	} else {
		dma_sync(ucd_off, sizeof(*ucd));
	}
	if (len && !(su.cache && write)) {
		dma_sync(bounce_off, len);
	}

	uint32_t ocs = utrd->dw2 & 0xff;
	if (ocs || ucd->resp[0] != 0x21 || ucd->resp[6] || ucd->resp[7]) {
		printf("SWEET UFS: command 0x%02x failed: ocs 0x%x upiu 0x%x response 0x%x status 0x%x\n",
		    cdb[0], ocs, ucd->resp[0], ucd->resp[6], ucd->resp[7]);
		return EIO;
	}
	return 0;
}

/* READ(10) of count device blocks at lba into the bounce buffer. */
static int
ufs_read_blocks(uint64_t lba, uint32_t count)
{
	if (lba > UINT32_MAX || count > BOUNCE_SIZE / UFS_BLOCK) {
		return EINVAL;
	}
	uint8_t cdb[10] = {
		0x28, 0,
		(uint8_t)(lba >> 24), (uint8_t)(lba >> 16), (uint8_t)(lba >> 8), (uint8_t)lba,
		0, (uint8_t)(count >> 8), (uint8_t)count, 0
	};
	return ufs_scsi(cdb, sizeof(cdb), count * UFS_BLOCK, false);
}

/*
 * WRITE(10) of count device blocks from the bounce buffer to lba. The range
 * must lie inside the partition: this is the only place data goes out.
 */
static int
ufs_write_blocks(uint64_t lba, uint32_t count)
{
	if (!su.writable || !su.nblocks || count == 0 || count > BOUNCE_SIZE / UFS_BLOCK ||
	    lba < su.first_block || lba - su.first_block >= su.nblocks ||
	    count > su.nblocks - (lba - su.first_block) || lba + count - 1 > UINT32_MAX) {
		printf("SWEET UFS: refusing write of %u blocks at 0x%llx\n", count, lba);
		return EPERM;
	}
	uint8_t cdb[10] = {
		0x2a, 0,
		(uint8_t)(lba >> 24), (uint8_t)(lba >> 16), (uint8_t)(lba >> 8), (uint8_t)lba,
		0, (uint8_t)(count >> 8), (uint8_t)count, 0
	};
	return ufs_scsi(cdb, sizeof(cdb), count * UFS_BLOCK, true);
}

/*
 * The same two writes for the persistent log: slot 1 and DMA_BOUNCE_LOG, so a
 * flush does not disturb - and is not disturbed by - the root device's I/O.
 * Callers already hold sweet_log_lock.
 */
static int
sweet_log_write_blocks(uint64_t lba, uint32_t count)
{
	if (!su.writable || !su.nblocks || count == 0 || count > BOUNCE_SIZE / UFS_BLOCK ||
	    lba < su.first_block || lba - su.first_block >= su.nblocks ||
	    count > su.nblocks - (lba - su.first_block) || lba + count - 1 > UINT32_MAX) {
		printf("SWEET LOG: refusing write of %u blocks at 0x%llx\n", count, lba);
		return EPERM;
	}
	uint8_t cdb[10] = {
		0x2a, 0,
		(uint8_t)(lba >> 24), (uint8_t)(lba >> 16), (uint8_t)(lba >> 8), (uint8_t)lba,
		0, (uint8_t)(count >> 8), (uint8_t)count, 0
	};
	return ufs_scsi_slot(cdb, sizeof(cdb), count * UFS_BLOCK, true,
	    su.dma_pa + DMA_BOUNCE_LOG, UFS_SLOT_LOG);
}

static int
sweet_log_write_abs(uint64_t lba, uint32_t count, uintptr_t pa)
{
	if (lba + count - 1 > UINT32_MAX) {
		return EPERM;
	}
	uint8_t cdb[10] = {
		0x2a, 0,
		(uint8_t)(lba >> 24), (uint8_t)(lba >> 16), (uint8_t)(lba >> 8), (uint8_t)lba,
		0, (uint8_t)(count >> 8), (uint8_t)count, 0
	};
	return ufs_scsi_slot(cdb, sizeof(cdb), count * UFS_BLOCK, true, pa, UFS_SLOT_LOG);
}

static int
sweet_log_sync_cache(void)
{
	static const uint8_t cdb[10] = { 0x35 };
	int rc = ufs_scsi_slot(cdb, sizeof(cdb), 0, false, 0, UFS_SLOT_LOG);
	/*
	 * SYNC CACHE is a durability hint, not a precondition: the data is
	 * already in the controller's cache after the WRITE, and the point of the
	 * log is to be readable by TWRP after a reset, which does not need the
	 * media flushed. It started failing with OCS 0xf once HFS+ owned the
	 * partition (NOTES 2026-11-03 (39)), which used to abort the whole flush
	 * and silence the ring for the rest of the boot - exactly when the boot
	 * was most interesting.
	 */
	if (rc != 0) {
		static bool warned;
		if (!warned) {
			warned = true;
			printf("SWEET LOG: sync cache failed (%d), continuing unflushed\n", rc);
		}
	}
	return 0;
}

/* WRITE(10) of count blocks straight from a physical address; no partition
 * bounds (the stage block may sit outside the named partition). Polled like
 * every command here, so it is safe from panic(). */
static int
ufs_write_abs(uint64_t lba, uint32_t count, uintptr_t pa)
{
	if (lba + count - 1 > UINT32_MAX) {
		return EPERM;
	}
	uint8_t cdb[10] = {
		0x2a, 0,
		(uint8_t)(lba >> 24), (uint8_t)(lba >> 16), (uint8_t)(lba >> 8), (uint8_t)lba,
		0, (uint8_t)(count >> 8), (uint8_t)count, 0
	};
	return ufs_scsi_slot(cdb, sizeof(cdb), count * UFS_BLOCK, true, pa, UFS_SLOT_MAIN);
}

static int
ufs_sync_cache(void)
{
	static const uint8_t cdb[10] = { 0x35 };       /* SYNCHRONIZE CACHE(10), whole LUN */
	return ufs_scsi(cdb, sizeof(cdb), 0, false);
}

static int
ufs_find_partition(const char *want)
{
	const uint8_t *b = (const uint8_t *)(su.dma + DMA_BOUNCE);
	int error = ufs_read_blocks(1, 1);
	if (error) {
		return error;
	}
	printf("SWEET UFS: gpt header read, sig %.8s\n", (const char *)b);
	if (memcmp(b, "EFI PART", 8) != 0) {
		printf("SWEET UFS: LUN %u has no GPT\n", su.lun);
		return ENXIO;
	}
	uint64_t entry_lba;
	uint32_t nent, esz;
	memcpy(&entry_lba, b + 72, 8);
	memcpy(&nent, b + 80, 4);
	memcpy(&esz, b + 84, 4);
	printf("SWEET UFS: entries at lba %llu, %u x %u\n",
	    (unsigned long long)entry_lba, nent, esz);
	if (esz != 128 || nent == 0 || nent * esz > BOUNCE_SIZE) {
		printf("SWEET UFS: unsupported GPT entries %u x %u\n", nent, esz);
		return ENXIO;
	}
	error = ufs_read_blocks(entry_lba, (nent * esz + UFS_BLOCK - 1) / UFS_BLOCK);
	printf("SWEET UFS: entries read rc=%d\n", error);
	if (error) {
		return error;
	}
	for (uint32_t i = 0; i < nent; i++) {
		const uint8_t *e = b + i * esz;
		char name[37];
		unsigned c;
		for (c = 0; c < 36; c++) {
			uint16_t ch = (uint16_t)(e[56 + 2 * c] | e[57 + 2 * c] << 8);
			if (ch == 0 || ch > 0x7f) {
				break;
			}
			name[c] = (char)ch;
		}
		name[c] = 0;
		if (strcmp(name, want) != 0) {
			continue;
		}
		uint64_t first, last;
		memcpy(&first, e + 32, 8);
		memcpy(&last, e + 40, 8);
		if (last < first) {
			return ENXIO;
		}
		su.first_block = first;
		su.nblocks = last - first + 1;
		return 0;
	}
	printf("SWEET UFS: no GPT partition named \"%s\"\n", want);
	return ENOENT;
}

static int
ufs_take_over_host(void)
{
	uint32_t hce = ufs_rd(REG_HCE), hcs = ufs_rd(REG_HCS);
	if (!(hce & 1) || !(hcs & HCS_DP) || !(hcs & HCS_UTRLRDY)) {
		printf("SWEET UFS: host not ready (hce 0x%x hcs 0x%x)\n", hce, hcs);
		return ENXIO;
	}
	if (ufs_rd(REG_UTRLDBR)) {
		printf("SWEET UFS: requests outstanding from the bootloader\n");
		return EBUSY;
	}
	/* With RAM above 4 GiB (mkadt.py --highmem) the DMA memory can be there too. */
	if (((su.dma_pa + DMA_SIZE - 1) >> 32) && !(ufs_rd(REG_CAP) & CAP_64AS)) {
		printf("SWEET UFS: DMA memory at 0x%llx but the host has no 64-bit addressing\n",
		    su.dma_pa);
		return ENXIO;
	}
	ufs_wr(REG_IE, 0);                      /* polled operation */
	ufs_wr(REG_IS, ufs_rd(REG_IS));
	ufs_wr(REG_UTRLRSR, 0);
	uint64_t list = su.dma_pa + DMA_UTRL;
	ufs_wr(REG_UTRLBA, (uint32_t)list);
	ufs_wr(REG_UTRLBAU, (uint32_t)(list >> 32));
	ufs_wr(REG_UTRLRSR, 1);
	/* Never ring a doorbell unless the host uses our list. */
	if (ufs_rd(REG_UTRLBA) != (uint32_t)list || ufs_rd(REG_UTRLBAU) != (uint32_t)(list >> 32) ||
	    !(ufs_rd(REG_UTRLRSR) & 1)) {
		printf("SWEET UFS: host did not take our request list\n");
		return EIO;
	}
	return 0;
}

static int
sweet_ufs_open(__unused dev_t dev, int flags, __unused int devtype, __unused struct proc *p)
{
	if (!su.ready) {
		return ENXIO;
	}
	return ((flags & FWRITE) && !su.writable) ? EROFS : 0;
}

static int
sweet_ufs_close(__unused dev_t dev, __unused int flags, __unused int devtype, __unused struct proc *p)
{
	return 0;
}

static void
sweet_ufs_strategy(buf_t bp)
{
	int error = 0;
	caddr_t vaddr = NULL;
	uint64_t off = (uint64_t)buf_blkno(bp) * su.secsize;
	uint32_t count = buf_count(bp);
	uint64_t part_bytes = su.nblocks * UFS_BLOCK;

	bool rd = buf_flags(bp) & B_READ;

	buf_setresid(bp, count);
	if (!rd && !su.writable) {
		error = EROFS;
		goto done;
	}
	if (off > part_bytes || count > part_bytes - off) {
		error = EINVAL;
		goto done;
	}
	if (count == 0) {
		goto done;
	}
	if (buf_map(bp, &vaddr)) {
		error = EIO;
		goto done;
	}

	lck_mtx_lock(&sweet_ufs_lock);
	for (uint32_t done = 0; done < count;) {
		uint64_t pos = off + done;
		uint64_t lba = pos / UFS_BLOCK;
		uint32_t skip = (uint32_t)(pos % UFS_BLOCK);
		uint32_t want = MIN(count - done, BOUNCE_SIZE - skip);
		uint32_t blocks = (skip + want + UFS_BLOCK - 1) / UFS_BLOCK;
		void *bounce = (void *)(su.dma + DMA_BOUNCE);
		if (rd) {
			error = ufs_read_blocks(su.first_block + lba, blocks);
			if (!error) {
				memcpy(vaddr + done, (const char *)bounce + skip, want);
			}
		} else {
			/* Partial device blocks at either end: read, merge, write back. */
			if (skip || (want % UFS_BLOCK)) {
				error = ufs_read_blocks(su.first_block + lba, blocks);
			}
			if (!error) {
				memcpy((char *)bounce + skip, vaddr + done, want);
				error = ufs_write_blocks(su.first_block + lba, blocks);
			}
		}
		if (error) {
			break;
		}
		done += want;
		buf_setresid(bp, count - done);
	}
	lck_mtx_unlock(&sweet_ufs_lock);
	buf_unmap(bp);

done:
	if (error) {
		buf_seterror(bp, error);
	}
	buf_biodone(bp);
}

static int
sweet_ufs_ioctl(__unused dev_t dev, u_long cmd, caddr_t data, __unused int flag,
    __unused struct proc *p, int is_char)
{
	uint32_t *f = (uint32_t *)data;
	uint64_t *o = (uint64_t *)data;

	switch (cmd) {
	case DKIOCGETBLOCKSIZE:
		*f = su.secsize;
		return 0;
	case DKIOCSETBLOCKSIZE:
		if (is_char) {
			return ENODEV;
		}
		if (*f < DEV_BSIZE || *f > UFS_BLOCK || (*f & (*f - 1))) {
			return EINVAL;
		}
		su.secsize = *f;
		return 0;
	case DKIOCGETPHYSICALBLOCKSIZE:
		*f = UFS_BLOCK;
		return 0;
	case DKIOCGETBLOCKCOUNT:
		*o = su.nblocks * UFS_BLOCK / su.secsize;
		return 0;
	case DKIOCISWRITABLE:
		*f = su.writable;
		return 0;
	case DKIOCSYNCHRONIZE:
	case DKIOCSYNCHRONIZECACHE: {
		if (!su.writable) {
			return 0;
		}
		lck_mtx_lock(&sweet_ufs_lock);
		int error = ufs_sync_cache();
		lck_mtx_unlock(&sweet_ufs_lock);
		return error;
	}
	case DKIOCGETMAXBLOCKCOUNTREAD:
		*o = BOUNCE_SIZE / su.secsize;
		return 0;
	case DKIOCGETMAXBLOCKCOUNTWRITE:
		*o = su.writable ? BOUNCE_SIZE / su.secsize : 0;
		return 0;
	case DKIOCGETMAXSEGMENTCOUNTREAD:
	case DKIOCGETMAXSEGMENTCOUNTWRITE:
		*o = 1;
		return 0;
	default:
		return ENOTTY;
	}
}

static int
sweet_ufs_bioctl(dev_t dev, u_long cmd, caddr_t data, int flag, struct proc *p)
{
	return sweet_ufs_ioctl(dev, cmd, data, flag, p, 0);
}

static int
sweet_ufs_cioctl(dev_t dev, u_long cmd, caddr_t data, int flag, struct proc *p)
{
	return sweet_ufs_ioctl(dev, cmd, data, flag, p, 1);
}

static int
sweet_ufs_psize(__unused dev_t dev)
{
	return su.ready ? (int)MIN(su.nblocks * UFS_BLOCK / su.secsize, INT_MAX) : -1;
}

static int
sweet_ufs_read(dev_t dev, struct uio *uio, __unused int ioflag)
{
	return physio(sweet_ufs_strategy, NULL, dev, B_READ, minphys, uio, (int)su.secsize);
}

static int
sweet_ufs_write(dev_t dev, struct uio *uio, __unused int ioflag)
{
	if (!su.writable) {
		return EROFS;
	}
	return physio(sweet_ufs_strategy, NULL, dev, B_WRITE, minphys, uio, (int)su.secsize);
}

static const struct bdevsw sweet_ufs_bdevsw = {
	.d_open     = sweet_ufs_open,
	.d_close    = sweet_ufs_close,
	.d_strategy = sweet_ufs_strategy,
	.d_ioctl    = sweet_ufs_bioctl,
	.d_dump     = eno_dump,
	.d_psize    = sweet_ufs_psize,
	.d_type     = D_DISK,
};

static const struct cdevsw sweet_ufs_cdevsw = {
	.d_open       = sweet_ufs_open,
	.d_close      = sweet_ufs_close,
	.d_read       = sweet_ufs_read,
	.d_write      = sweet_ufs_write,
	.d_ioctl      = sweet_ufs_cioctl,
	.d_stop       = eno_stop,
	.d_reset      = eno_reset,
	.d_ttys       = NULL,
	.d_select     = eno_select,
	.d_mmap       = eno_mmap,
	.d_strategy   = eno_strat,
	.d_reserved_1 = eno_getc,
	.d_reserved_2 = eno_putc,
	.d_type       = D_DISK,
};

/*
 * Crash-proof stage record ("sweetstage=<MiB>", default off).
 *
 * A stuck kernel cannot be diagnosed from the console log: the flush thread is
 * often the one that stopped, and a panic that never prints says nothing. So
 * the kernel reports marks here and this writes them, one 4 KiB block, at
 * partition MiB <n> (64 or later: past the HFS image at the start, before the
 * 4 MiB log ring at the end). Device lba = su.first_block + n * 256.
 *
 *   0:      'S','W','E','E','T','S','T','G' | u32 tick_lo | u32 count
 *           | { u64 tick, u32 code, u32 arg }[50]
 *   2048:   'S','W','E','E','T','P','A','N' | u32 code | u32 arg | u32 pid
 *           | u64 thread | u64 pc | u64 tick | u64 sp | u8 saved_state[272]
 *   2336:   u8 kernel stack[1024]
 *
 * It goes out with polling SCSI from its own DMA block (never the bounce
 * buffer), so panic() and a wedged thread can both use it.
 */
#define SWEET_STAGE_MAX          50
#define STG_PANIC_OFF            2048
#define STG_STACK_OFF            2336
#define STG_STACK_SIZE           1024

static bool sweet_stage_on;
static uint64_t sweet_stage_lba;
static uint32_t sweet_stage_count;

#define STG_BLK ((uint8_t *)(su.dma + DMA_STAGE))

static void
sweet_stage_header(void)
{
	static const char magic[8] = { 'S', 'W', 'E', 'E', 'T', 'S', 'T', 'G' };
	if (sweet_stage_on && memcmp(STG_BLK, magic, 8) != 0) {
		bzero(STG_BLK, UFS_BLOCK);
		memcpy(STG_BLK, magic, 8);
		sweet_stage_count = 0;
	}
}

static void
sweet_stage_commit(void)
{
	uint32_t tick = (uint32_t)mach_absolute_time();
	memcpy(STG_BLK + 8, &tick, 4);
	clean_dcache64((addr64_t)(su.dma_pa + DMA_STAGE), UFS_BLOCK, TRUE);
	(void)ufs_write_abs(sweet_stage_lba, 1, (uintptr_t)STG_BLK);
}

/* Record one stage. Safe from any thread context; not from an interrupt. */
void
sweet_stage(uint32_t code, uint32_t arg)
{
	if (!sweet_stage_on) {
		return;
	}
	sweet_stage_header();
	if (sweet_stage_count < SWEET_STAGE_MAX) {
		uint32_t i = sweet_stage_count++;
		uint64_t tick = mach_absolute_time();
		memcpy(STG_BLK + 12, &sweet_stage_count, 4);
		memcpy(STG_BLK + 16 + i * 16, &tick, 8);
		memcpy(STG_BLK + 24 + i * 16, &code, 4);
		memcpy(STG_BLK + 28 + i * 16, &arg, 4);
	}
	sweet_stage_commit();
}

/* Called from panic() (osfmk/kern/debug.c, weak): where and why it died. */
void sweet_stage_panic(uint32_t code, uint32_t arg, uint64_t thread_id,
    uint64_t pc, void *saved_state);

void
sweet_stage_panic(uint32_t code, uint32_t arg, uint64_t thread_id,
    uint64_t pc, void *saved_state)
{
	if (!sweet_stage_on) {
		return;
	}
	sweet_stage_header();
	uint8_t *p = STG_BLK + STG_PANIC_OFF;
	uint32_t pid = (uint32_t)proc_selfpid();
	uint64_t tick = mach_absolute_time();
	uintptr_t sp;
	__asm__ volatile ("mov %0, sp" : "=r"(sp));
	memcpy(p, "SWEETPAN", 8);
	memcpy(p + 8, &code, 4);
	memcpy(p + 12, &arg, 4);
	memcpy(p + 16, &pid, 4);
	memcpy(p + 24, &thread_id, 8);
	memcpy(p + 32, &pc, 8);
	memcpy(p + 40, &tick, 8);
	memcpy(p + 48, &sp, 8);
	if (saved_state != NULL) {
		memcpy(p + 56, saved_state, 272);
	}
	memcpy(STG_BLK + STG_STACK_OFF, (void *)sp, STG_STACK_SIZE);
	sweet_stage_commit();
}

static int
sweet_ufs_init(void)
{
	DTEntry node;
	uintptr_t const *reg = NULL;
	unsigned int size = 0;
	char want[64] = "userdata";
	int error;

	if (SecureDTLookupEntry(NULL, "/sweet-ufs", &node) != kSuccess ||
	    SecureDTGetProperty(node, "reg", (void const **)&reg, &size) != kSuccess ||
	    size < 2 * sizeof(uintptr_t)) {
		printf("SWEET UFS: no /sweet-ufs node in the device tree\n");
		return ENXIO;
	}
	PE_parse_boot_argn("ufsroot", want, sizeof(want));
	uint32_t rw = 0;
	PE_parse_boot_argn("ufsrw", &rw, sizeof(rw));
	uint32_t cache = 0, wait = 0;
	PE_parse_boot_argn("ufscache", &cache, sizeof(cache));
	PE_parse_boot_argn("ufswait", &wait, sizeof(wait));
	su.cache = (cache == 1);
	su.wait = (wait == 1);

	printf("SWEET UFS: init reg=0x%llx/0x%llx\n", (uint64_t)reg[0], (uint64_t)reg[1]);
	su.regs = ml_io_map(reg[0], reg[1]);
	printf("SWEET UFS: regs at 0x%llx, hce 0x%x hcs 0x%x\n", (uint64_t)su.regs,
	    ufs_rd(REG_HCE), ufs_rd(REG_HCS));
	if (kmem_alloc_contig(kernel_map, &su.dma, DMA_SIZE, PAGE_MASK, 0, 0,
	    KMA_DATA | KMA_ZERO | KMA_PERMANENT, VM_KERN_MEMORY_IOKIT) != KERN_SUCCESS) {
		printf("SWEET UFS: no contiguous DMA memory\n");
		return ENOMEM;
	}
	ppnum_t pn = pmap_find_phys(kernel_pmap, (addr64_t)su.dma);
	if (!pn) {
		return ENOMEM;
	}
	su.dma_pa = ptoa_64(pn);
	su.lun = 0;
	su.secsize = DEV_BSIZE;

	printf("SWEET UFS: dma ok, taking over the host\n");
	lck_mtx_lock(&sweet_ufs_lock);
	error = ufs_take_over_host();
	printf("SWEET UFS: take over rc=%d\n", error);
	if (!error) {
		static const uint8_t tur[6] = { 0x00 };
		/* The first command after the bootloader may report a unit attention. */
		for (int i = 0; i < 3 && (error = ufs_scsi(tur, sizeof(tur), 0, false)); i++) {
		}
	}
	if (!error) {
		printf("SWEET UFS: looking for partition \"%s\"\n", want);
		error = ufs_find_partition(want);
		printf("SWEET UFS: find partition rc=%d\n", error);
	}
	lck_mtx_unlock(&sweet_ufs_lock);
	if (error) {
		return error;
	}

	su.bmajor = bdevsw_add(-1, &sweet_ufs_bdevsw);
	if (su.bmajor < 0) {
		return ENXIO;
	}
	su.cmajor = cdevsw_add_with_bdev(-1, &sweet_ufs_cdevsw, su.bmajor);
	if (su.cmajor < 0) {
		return ENXIO;
	}
	su.bdev = makedev(su.bmajor, 0);
	devfs_make_node(su.bdev, DEVFS_BLOCK, UID_ROOT, GID_OPERATOR, 0640, "ufsroot0");
	devfs_make_node(makedev(su.cmajor, 0), DEVFS_CHAR, UID_ROOT, GID_OPERATOR, 0640, "rufsroot0");
	/* Only now, with the partition bounds known, can writes be allowed. */
	su.writable = (rw != 0);
	su.ready = true;
	printf("SWEET UFS: \"%s\" on LUN %u: first block 0x%llx, %llu MiB, %s, DMA at 0x%llx\n",
	    want, su.lun, su.first_block, su.nblocks * UFS_BLOCK >> 20,
	    su.writable ? "read-write" : "read-only", su.dma_pa);
	{
		uint32_t stg = 0;
		PE_parse_boot_argn("sweetstage", &stg, sizeof(stg));
		if (stg && su.writable && su.nblocks / (1024 * 1024 / UFS_BLOCK) > stg) {
			sweet_stage_lba = su.first_block + (uint64_t)stg * (1024 * 1024 / UFS_BLOCK);
			sweet_stage_on = true;
			sweet_stage_header();
			sweet_stage_commit();
			sweet_stage(0x100, stg);
			printf("SWEET STAGE: stages to device lba 0x%llx\n",
			    (unsigned long long)sweet_stage_lba);
		}
	}
	sweet_log_start();
	sweet_reboot_start();
	/*
	 * This is the sequence boot-journaled-userland.txt proves works end to end:
	 * sample_start -> keys_init -> touch_init -> usb_probe -> init complete ->
	 * BSD root: ufsroot0. Each sweet_log_sync() below is a synchronous flush and
	 * that is fine here - it did exactly this on every successful boot. What is
	 * NOT fine is doing slow hardware work in this path: sweet_touch_init()
	 * only starts the touch thread, while sweet_touch_start_at_init() ran the
	 * whole bring-up inline, and the synchronous sweet_log_mark() writes did
	 * eleven SCSI round trips inside keys_init.
	 */
	/*
	 * Every step is bracketed by a mark. The ring can be overwritten before
	 * it is read, and a stall between two prints then looks like a stall at
	 * the first one; the marks live in their own 64 blocks and are written
	 * by the log thread, so they survive (NOTES 2026-11-03).
	 */
	printf("SWEET UFS: sample_start\n");
	os_atomic_store(&sweet_init_step, "sample_start", relaxed);
	sweet_log_sync();
	sweet_sample_start();
	sweet_log_mark_sync("INIT: sample_start done");
	printf("SWEET UFS: sample_start done\n");
	sweet_log_sync();
	printf("SWEET UFS: keys_init\n");
	os_atomic_store(&sweet_init_step, "keys_init", relaxed);
	sweet_log_mark_sync("INIT: entering keys_init");
	sweet_log_sync();
	sweet_keys_init();
	sweet_log_mark_sync("INIT: keys_init done");
	printf("SWEET UFS: keys_init done\n");
	sweet_log_sync();
	printf("SWEET UFS: touch_init\n");
	os_atomic_store(&sweet_init_step, "touch_init", relaxed);
	sweet_log_mark_sync("INIT: entering touch_init");
	sweet_touch_init();
	sweet_log_mark_sync("INIT: touch_init done");
	printf("SWEET UFS: touch_init done\n");
	sweet_log_sync();
	printf("SWEET UFS: usb_probe\n");
	os_atomic_store(&sweet_init_step, "usb_probe", relaxed);
	sweet_log_mark_sync("INIT: entering usb_probe");
	sweet_usb_probe();
	sweet_log_mark_sync("INIT: usb_probe done");
	os_atomic_store(&sweet_init_step, "complete", relaxed);
	os_atomic_store(&sweet_init_done, 1, relaxed);
	printf("SWEET UFS: init complete\n");
	sweet_log_sync();
	return 0;
}

/*
 * Persistent console log ("sweetlog"). Filming the phone screen is the only
 * other way to see the console, so every character that reaches the
 * console (kernel printf and /dev/console writes of daemons, both through
 * _cnputs) is also kept in a 4 MiB ring, and once the partition is known
 * and writable a thread copies new ring blocks to the LAST 4 MiB + 4 KiB of
 * the partition every ufslogsecs seconds (default 10), far behind the HFS
 * image at its start. Device block 0 of that area is a header:
 *   "SWEETLOG" | u32 version 1 | u32 ring size | u64 total bytes written
 *   | u64 flush sequence
 * ring offset of byte n = n % ring size. Read it from a recovery with
 * tools/sweet-log-pull.sh. Disabled with boot-arg sweetlog=0.
 */
#define SWEET_LOG_SIZE          (4u << 20)
#define SWEET_LOG_BLOCKS        (1 + SWEET_LOG_SIZE / UFS_BLOCK)
#define SWEET_LOG_SECS          10u

static char sweet_log_ring[SWEET_LOG_SIZE];
static uint64_t _Atomic sweet_log_total;
static int sweet_log_chan;
static uint32_t sweet_log_secs = SWEET_LOG_SECS;
static uint32_t sweet_log_ms;            /* sweetlogms: flush interval in ms */

/* Called for all console output, any context: never blocks. */
void sweet_log_append(const char *c, int size);

void
sweet_log_append(const char *c, int size)
{
	if (size <= 0) {
		return;
	}
	uint64_t at = os_atomic_add_orig(&sweet_log_total, (uint64_t)size, relaxed);
	for (int i = 0; i < size; i++) {
		sweet_log_ring[(at + (uint64_t)i) % SWEET_LOG_SIZE] = c[i];
	}
}

/*
 * Copy console bytes [*pos, total) (at most max) for live log streaming
 * (sweet_usb.c). A reader that fell more than the ring behind skips ahead.
 * Returns the byte count; *pos advances.
 */
uint32_t sweet_log_copy(uint64_t *pos, char *out, uint32_t max);

uint32_t
sweet_log_copy(uint64_t *pos, char *out, uint32_t max)
{
	uint64_t total = os_atomic_load(&sweet_log_total, relaxed);
	if (total - *pos > SWEET_LOG_SIZE) {
		*pos = total - SWEET_LOG_SIZE;
	}
	uint32_t n = (uint32_t)MIN((uint64_t)max, total - *pos);
	for (uint32_t i = 0; i < n; i++) {
		out[i] = sweet_log_ring[(*pos + i) % SWEET_LOG_SIZE];
	}
	*pos += n;
	return n;
}

uint64_t sweet_log_position(void);

uint64_t
sweet_log_position(void)
{
	return os_atomic_load(&sweet_log_total, relaxed);
}

struct sweet_log_header {
	char magic[8];
	uint32_t version, size;
	uint64_t total, seq;
};

/*
 * A small area of its own for results that must survive a noisy boot.
 *
 * The 4 MiB ring is written by a thread every sweetlogms, and userland produces
 * far more than it drains, so anything printed early is overwritten within
 * minutes - the touch bring-up lines were lost this way three times in a row
 * while the kernel had in fact run fine (NOTES 21:20). Key results are written
 * here instead: 16 blocks that only this function ever touches, so whatever it
 * records is still there when the phone is powered off.
 */
/*
 * 64 blocks: the init tail alone records ~12 checkpoints, and the ring in front
 * of them is only SWEET_LOG_BLOCKS long, so the mark area must not grow past it.
 */
#define SWEET_MARK_BLOCKS      64u
/* Marks live here until the log thread writes them; see sweet_log_mark(). */
static char sweet_mark_ram[SWEET_MARK_BLOCKS * 4096];
static uint32_t sweet_mark_dirty[SWEET_MARK_BLOCKS / 32];
static uint32_t sweet_log_mark_flush(void);

void
sweet_log_mark(const char *text)
{
	/*
	 * MEMORY ONLY. This is called from the UFS init path (keys_init alone
	 * carries 11 of them) and the init thread must return before BSD can
	 * mount the root. Each synchronous 4 KiB write costs a full SCSI round
	 * trip - 11 of them in keys_init turned a sub-second step into a stall,
	 * which is what the 2026-11-03 runs showed as "stops at keys_init".
	 * So a mark only fills a slot in a RAM buffer; sweet_log_mark_flush()
	 * writes the pending blocks, and the log thread calls it when idle.
	 */
	static uint32_t mark_seq;

	if (!su.ready || !su.writable || su.nblocks < 2 * SWEET_LOG_BLOCKS) {
		return;
	}
	if (text == NULL) {
		return;
	}
	uint32_t seq = __atomic_fetch_add(&mark_seq, 1, __ATOMIC_RELAXED) + 1;
	uint32_t slot = (seq - 1) % SWEET_MARK_BLOCKS;
	uint8_t *blk = (uint8_t *)(sweet_mark_ram + (uint64_t)slot * UFS_BLOCK);
	uint32_t n = 0;

	/*
	 * Build the line in place without clearing the whole block: a mark is a
	 * short text line, and ten of these run inside keys_init on the path that
	 * must return before the root can be mounted. The newline is what the
	 * reader keys on, so the bytes after it need no clearing: the flush
	 * writes the whole block anyway, so the tail is whatever was there.
	 */
#define MARK_PUT(c) do { if (n < UFS_BLOCK - 2) { blk[n++] = (c); } } while (0)
	MARK_PUT('M'); MARK_PUT('A'); MARK_PUT('R'); MARK_PUT('K'); MARK_PUT(' ');
	/* 5-digit sequence, most significant first */
	uint32_t v = seq % 100000u;
	for (uint32_t d = 10000u; d > 0; d /= 10u) {
		MARK_PUT((char)('0' + (v / d) % 10u));
	}
	MARK_PUT(' ');
	for (const char *p = text; *p != 0; p++) {
		MARK_PUT(*p);
	}
	MARK_PUT('\n');
#undef MARK_PUT
	/* Dirty bitmap: one bit per slot, so a flush writes only new blocks. */
	__atomic_fetch_or(&sweet_mark_dirty[slot / 32], 1u << (slot % 32), __ATOMIC_RELAXED);
}

/*
 * Record a mark AND push it to flash from the calling thread.
 *
 * sweet_log_mark() only fills RAM, and the flush that writes it runs on the
 * log thread. That is fine while the boot is healthy, but the whole reason
 * marks exist is to survive a stall - and if the stall is in keys_init, the
 * log thread may never get to flush them. This variant does the write itself,
 * on the caller's context, using slot UFS_SLOT_MARK (which no other caller
 * touches, so it cannot collide with the main I/O slot the caller may hold).
 * It costs one 4 KiB SCSI write, so only the init path's step markers use it.
 */
void
sweet_log_mark_sync(const char *text)
{
	sweet_log_mark(text);
	(void)sweet_log_mark_flush();
}

/*
 * Write the pending mark blocks. Called from the log thread, and from
 * sweet_log_mark_sync() on the init path. Returns the number of blocks
 * written.
 */
static uint32_t
sweet_log_mark_flush(void)
{
	uint64_t base = su.first_block + su.nblocks - SWEET_LOG_BLOCKS - SWEET_MARK_BLOCKS;
	uint8_t *blk = (uint8_t *)(su.dma + DMA_MARK);
	uint32_t written = 0;

	if (!su.ready || !su.writable) {
		return 0;
	}
	lck_mtx_lock(&sweet_mark_lock);
	for (uint32_t i = 0; i < SWEET_MARK_BLOCKS; i++) {
		uint32_t word = __atomic_load_n(&sweet_mark_dirty[i / 32], __ATOMIC_RELAXED);
		if (!(word & (1u << (i % 32)))) {
			continue;
		}
		memcpy(blk, sweet_mark_ram + (uint64_t)i * UFS_BLOCK, UFS_BLOCK);
		clean_dcache64((addr64_t)(su.dma_pa + DMA_MARK), UFS_BLOCK, TRUE);
		if (ufs_scsi_slot((const uint8_t[]){ 0x2a, 0, 0, 0, 0, 0, 0, 0, 1, 0 },
		    sizeof(uint8_t[10]), UFS_BLOCK, true, su.dma_pa + DMA_MARK,
		    UFS_SLOT_MARK) == 0) {
			__atomic_fetch_and(&sweet_mark_dirty[i / 32], ~(1u << (i % 32)), __ATOMIC_RELAXED);
			written++;
		}
	}
	lck_mtx_unlock(&sweet_mark_lock);
	return written;
}

static int
sweet_log_flush(uint64_t *flushed, uint64_t *seq, bool panic_mode)
{
	uint64_t base = su.first_block + su.nblocks - SWEET_LOG_BLOCKS;
	void *bounce = (void *)(su.dma + DMA_BOUNCE_LOG);
	uint64_t total = os_atomic_load(&sweet_log_total, relaxed);

	if (total == *flushed) {
		return 0;
	}
	uint64_t pos = total - *flushed >= SWEET_LOG_SIZE ? total - SWEET_LOG_SIZE : *flushed;
	int error = 0;

	/*
	 * sweet_log_lock, not sweet_ufs_lock: this runs on the log thread while
	 * init is still inside sweet_ufs_rootdev(), and the two used to contend
	 * for the same lock *and* the same request slot (NOTES 2026-11-03).
	 * Everything here uses slot UFS_SLOT_LOG and DMA_BOUNCE_LOG.
	 */
	if (panic_mode) {
		/*
		 * Panic path: never wait. If the log thread holds the slot, its own
		 * write is already carrying these bytes out, so skip rather than
		 * deadlock on a lock no one will release.
		 */
		if (!lck_mtx_try_lock(&sweet_log_lock)) {
			return 0;
		}
	} else {
		lck_mtx_lock(&sweet_log_lock);
	}
	while (pos < total && !error) {
		uint32_t off = (uint32_t)(pos % SWEET_LOG_SIZE);
		uint32_t blk = off / UFS_BLOCK;
		uint64_t need = ((uint64_t)off % UFS_BLOCK + (total - pos) + UFS_BLOCK - 1) / UFS_BLOCK;
		uint32_t n = (uint32_t)MIN(MIN(need, (uint64_t)(SWEET_LOG_SIZE / UFS_BLOCK - blk)),
		    (uint64_t)(BOUNCE_SIZE / UFS_BLOCK));
		memcpy(bounce, sweet_log_ring + (uint64_t)blk * UFS_BLOCK, n * UFS_BLOCK);
		error = sweet_log_write_blocks(base + 1 + blk, n);
		pos += (uint64_t)(blk + n) * UFS_BLOCK - off;
	}
	if (!error) {
		struct sweet_log_header h = {
			.magic = { 'S', 'W', 'E', 'E', 'T', 'L', 'O', 'G' },
			.version = 1, .size = SWEET_LOG_SIZE, .total = total, .seq = ++*seq,
		};
		bzero(bounce, UFS_BLOCK);
		memcpy(bounce, &h, sizeof(h));
		error = sweet_log_write_blocks(base, 1);
	}
	if (!error) {
		error = sweet_log_sync_cache();
	}
	lck_mtx_unlock(&sweet_log_lock);
	if (error) {
		printf("SWEET LOG: write failed (%d), stopping\n", error);
	} else {
		*flushed = total;
	}
	return error;
}

/*
 * Panic-path flush (osfmk/kern/debug.c calls it weakly): panic() prints the
 * reason through printf, so one synchronous flush here puts the whole panic
 * text in the on-disk log before the reboot. The UFS controller can be in any
 * state by now, so this is best-effort and bounded by ufs_scsi's timeout.
 */
/*
 * Panic -> pstore. Qualcomm's ramoops sits at 0xd0000000 (gauguin DT
 * ramoops@d0000000, 1 MiB: 128 KiB record, 512 KiB console, 128 KiB ftrace),
 * and TWRP mounts it at /sys/fs/pstore. Writing the last 512 KiB of the
 * console log there in the panic path survives a hard reset that never lets
 * the UFS flush finish, so the panic text can be read from userspace.
 * Enabled with sweetpanicdump=1 (default off: the region is not ours).
 */
/* The region ABL reserved is what TWRP's own kernel prints: 0xb0000000/4 MiB,
 * console 0x80000 in, and TWRP reads the whole 4 MiB as the area. The flasher
 * view of it is readable from TWRP with `dd if=/dev/block/sda ...` near 0. */
#define SWEET_PSTORE_PA         0xb0000000ULL
#define SWEET_PSTORE_SIZE       0x400000u
#define SWEET_PSTORE_CONSOLE_OFF 0x80000u
#define SWEET_PSTORE_CONSOLE_LEN 0x200000u

void sweet_pstore_dump(void)
{
	int on = 0;
	PE_parse_boot_argn("sweetpanicdump", &on, sizeof(on));
	if (!on) {
		return;
	}
	static volatile uint8_t *ram;           /* mapped once, not from IOWorkLoop */
	if (ram == NULL) {
		ram = (volatile uint8_t *)ml_io_map(SWEET_PSTORE_PA, SWEET_PSTORE_SIZE);
	}
	if (ram == 0) {
		return;
	}
	uint64_t total = os_atomic_load(&sweet_log_total, relaxed);
	uint64_t len = MIN(total, (uint64_t)SWEET_PSTORE_CONSOLE_LEN);
	uint64_t start = total - len;
	for (uint64_t i = 0; i < len; i++) {
		ram[SWEET_PSTORE_CONSOLE_OFF + i] =
		    (uint8_t)sweet_log_ring[(start + i) % SWEET_LOG_SIZE];
	}
}

void sweet_log_flush_now(void);

void
sweet_log_flush_panic(void)
{
	uint64_t flushed = 0, seq = 0;
	if (!su.ready || !su.writable) {
		return;
	}
	/*
	 * panic_mode: try-lock only. sweet_log_flush() now takes sweet_log_lock,
	 * and the log thread may be holding it when the system dies; a normal
	 * lck_mtx_lock() there would hang the panic handler forever.
	 */
	(void)sweet_log_flush(&flushed, &seq, true);
	sweet_pstore_dump();
}

/* Called from the watchdog thread once a second (ioworkloop context): copies
 * whatever the console has now into the ramoops console view, so a boot that
 * just hangs - no panic, no reset, flush thread dead - still leaves the last
 * lines on the flash where TWRP can read them. Boot-arg sweetpstore=1. */
/* extern "C": called from IOKit C++ (SweetWatchdog.cpp, weak). */
extern void sweet_pstore_tick(void);
void
sweet_pstore_tick(void)
{
	static bool parsed, on;
	static uint32_t last_total;
	if (!parsed) {
		parsed = true;
		PE_parse_boot_argn("sweetpstore", &on, sizeof(on));
	}
	uint64_t total = os_atomic_load(&sweet_log_total, relaxed);
	if (!on || (uint32_t)total == last_total) {
		return;
	}
	last_total = (uint32_t)total;
	sweet_pstore_dump();
}

/* Same flush, callable from other files (bsd/dev/sweet_usb.c). */
void sweet_log_flush_now(void);

void
sweet_log_flush_now(void)
{
	uint64_t flushed = 0, seq = 0;
	(void)sweet_log_flush(&flushed, &seq, false);
}

/*
 * Debug reboot timer: with sweetreboot=<seconds> the kernel panics that many
 * seconds after the root device is up. A hung bring-up kernel cannot signal
 * anything, and a panic with the default panic_reboot reboots the phone, which
 * the bootloader then sends to recovery (misc holds boot-recovery), so
 * tools/fastboot-cycle.sh can pull the log without a human power-cycling it.
 */
static void
sweet_reboot_thread(__unused void *arg, __unused wait_result_t wr)
{
	int secs = 0;
	PE_parse_boot_argn("sweetreboot", &secs, sizeof(secs));
	if (secs <= 0) {
		return;
	}
	printf("SWEET: debug reboot in %d s\n", secs);
	(void)tsleep(&sweet_log_chan, PZERO, "sweetreboot", hz * secs);
	panic("SWEET: debug reboot timer (%d s)", secs);
}

static void
sweet_reboot_start(void)
{
	int secs = 0;
	thread_t thread;

	PE_parse_boot_argn("sweetreboot", &secs, sizeof(secs));
	if (secs <= 0) {
		return;
	}
	if (kernel_thread_start(sweet_reboot_thread, NULL, &thread) == KERN_SUCCESS) {
		thread_deallocate(thread);
	}
}

static void
sweet_log_sync(void)
{
	uint64_t flushed = 0, seq = 0;
	(void)sweet_log_flush(&flushed, &seq, false);
}

/*
 * Process watcher. SpringBoard runs, opens two services, queries the device
 * tree and then goes silent (NOTES 2026-11-03 (36), re-confirmed in (37) with
 * a per-process log budget). Device-tree echoes say what it asked for, never
 * what it is waiting on, so the log thread - which runs regardless of what
 * userland is doing - walks the process list and reports the ones we care
 * about: whether they exist, their state and what they last did.
 *
 * Read-only: proc_find/hold would take locks we do not need, and the list
 * itself is what we want (a process present but never progressing is the
 * interesting case, and it is still on allproc).
 */
struct sweet_proc_watch {
	const char *name;
	int         reported;   /* -1 not seen yet, else last state printed */
	uint32_t    ticks;
};

static struct sweet_proc_watch sweet_proc_watchers[] = {
	{ "SpringBoard", -1, 0 },
	{ "backboardd",  -1, 0 },
};
#define SWEET_PROC_WATCH_COUNT \
	(sizeof(sweet_proc_watchers) / sizeof(sweet_proc_watchers[0]))

static void sweet_proc_watch(void);
/* File scope, not a function-local static: tsleep() hashes the channel
 * address, and a local static that is only ever zero would be a poor one. */
static int sweet_proc_watch_chan;

/*
 * Own thread, not a hook on the log thread or the watchdog heartbeat: both
 * turned out to run far less often than they appear to (the log thread stops
 * for good on the first EIO, and the heartbeat's callback was only observed to
 * fire once in a boot). A dedicated thread that sleeps on its own channel is
 * the one thing whose cadence we control.
 */
static void
sweet_proc_watch_thread(__unused void *arg, __unused wait_result_t wr)
{
	for (;;) {
		/*
		 * Probe first, scan second. If the watcher disappears again, the beat
		 * counter tells us whether the loop stopped spinning or whether
		 * sweet_proc_watch() is what blocks - those are very different bugs
		 * and the earlier rounds could not tell them apart because the beat
		 * was printed after the scan.
		 */
		static uint32_t beat;
		if ((++beat % 15) == 0) {
			printf("SWEET PW: alive beat=%u\n", beat);
		}
		sweet_proc_watch();
		/*
		 * tsleep, not assert_wait_deadline + thread_block: the watcher stopped
		 * reporting at t=20 in four consecutive runs with that idiom, while
		 * tsleep keeps every other periodic thread in this file alive
		 * (sweet_log_thread, sweet_reboot_thread). tsleep also cannot leave
		 * the thread unqueued if the wait is restarted.
		 */
		(void)tsleep(&sweet_proc_watch_chan, PZERO, "sweetpw",
		    hz > 0 ? hz * 2 : 200);
	}
}

void
sweet_proc_watch_start(void)
{
	thread_t thread;
	if (kernel_thread_start(sweet_proc_watch_thread, NULL, &thread) == KERN_SUCCESS) {
		thread_deallocate(thread);
	}
}

static void
sweet_proc_watch(void)
{
	struct proc *p;
	bool found[SWEET_PROC_WATCH_COUNT];
	char line[160];
	int n = 0;

	for (size_t i = 0; i < SWEET_PROC_WATCH_COUNT; i++) {
		found[i] = false;
		sweet_proc_watchers[i].ticks++;
	}

	/*
	 * Lock-free read of allproc.
	 *
	 * The locking version (proc_list_lock/unlock) is what hung: with the
	 * heartbeat moved before the scan, it still stopped at beat=15, so the
	 * loop spins and sweet_proc_watch() is what never returns. Reading a
	 * list without its lock is normally wrong, but the failure mode here -
	 * a missing diagnostic - is far better than a dead thread, and the only
	 * thing we compare is a name prefix on entries that userland cannot free
	 * while this runs (processes on allproc are either running or zombies).
	 */
	for (p = allproc.lh_first; p != NULL && n < 4096; p = p->p_list.le_next, n++) {
		for (size_t i = 0; i < SWEET_PROC_WATCH_COUNT; i++) {
			if (!found[i] &&
			    strncmp(p->p_comm, sweet_proc_watchers[i].name,
			    MAXCOMLEN) == 0) {
				found[i] = true;
			}
		}
	}

	for (size_t i = 0; i < SWEET_PROC_WATCH_COUNT; i++) {
		int state = found[i] ? 1 : 0;
		/*
		 * Report on the first pass and whenever the liveness flips, plus a
		 * slow heartbeat so a long run still says something.
		 */
		/* Report on a change, and otherwise every 10 s: state alone cannot
		 * distinguish "alive and working" from "alive and stuck", so a
		 * periodic line at least proves the watcher keeps running. */
		bool due = sweet_proc_watchers[i].reported != state ||
		    (sweet_proc_watchers[i].ticks % 10) == 0;
		if (!due) {
			continue;
		}
		sweet_proc_watchers[i].reported = state;
		int len = snprintf(line, sizeof(line), "PROC: %s %s (t=%u)",
		    sweet_proc_watchers[i].name, state ? "present" : "gone",
		    sweet_proc_watchers[i].ticks);
		if (len > 0) {
			printf("SWEET %s\n", line);
			sweet_log_mark(line);
			n++;
		}
	}
	if (n == 0) {
		return;
	}
	(void)sweet_log_mark_flush();
}

static void
sweet_log_thread(__unused void *arg, __unused wait_result_t wr)
{
	uint64_t flushed = 0, seq = 0;

	int once = 0;
	PE_parse_boot_argn("sweetlogonce", &once, sizeof(once));
	printf("SWEET LOG: thread running, first flush follows\n");
	for (;;) {
		if (once) {
			/* Poll until quiet: a finishing boot settles (sweetlogonce). */
			for (int i = 0; i < 15; i++) {
				(void)sweet_log_flush(&flushed, &seq, false);
				tsleep(&sweet_log_chan, PZERO, "sweetlog", hz / 10);
			}
			printf("SWEETLOG. total=%llu seq=%llu\n",
			    (unsigned long long)flushed, (unsigned long long)seq);
			return;
		}
		(void)sweet_log_flush(&flushed, &seq, false);
		/* Marks are RAM-only until here: write any pending ones now. */
		(void)sweet_log_mark_flush();
		/*
		 * Init watchdog. The log thread keeps running whatever the init
		 * thread is doing, so it can report that init is stuck even when the
		 * stall is a device read with no timeout (a volatile load from an
		 * unresponsive SPMI/SMMU window never returns, and no in-code deadline
		 * can help). sweet_init_done is set by the last line of the init tail;
		 * if it is still clear a few seconds in, say so once and keep saying
		 * it only if the step marker changes.
		 */
		if (!os_atomic_load(&sweet_init_done, relaxed)) {
			/*
			 * The decision lives in sweet_init_watchdog.h so the host tests
			 * (tests/test_watchdog.py) exercise the same code the kernel
			 * runs; both defects this function had were found that way.
			 */
			const char *step = os_atomic_load(&sweet_init_step, relaxed);
			if (sweet_wd_should_report(&sweet_init_wd, step)) {
				printf("SWEET INIT: still inside the init tail after ~%u s "
				    "(last step: %s) - look at the mark blocks\n",
				    sweet_init_wd.ticks * sweet_log_ms / 1000, step);
			}
		}
		/*
		 * Block-ring report, driven from the log thread because it is the one
		 * periodic context observed to reach the end of a boot (13,094 scsi
		 * lines, last one on the final line of the log). The watchdog tick
		 * looks healthier - it counts to 130,732 - but its callback only ever
		 * ran ONCE, which is what silently defeated three earlier attempts to
		 * hook things onto it.
		 */
		{
			static uint32_t ring_waits;
			extern void sweet_block_ring_report(void);
			if (ring_waits < 200) {
				ring_waits++;
				sweet_block_ring_report();
			}
		}
		/* sweetlogms=<ms> narrows the window a crash can swallow; the flush
		 * only writes the bytes added since the last one. */
		int ticks = sweet_log_ms ? (hz * (int)sweet_log_ms) / 1000 : hz * (int)sweet_log_secs;
		(void)tsleep(&sweet_log_chan, PZERO, "sweetlog", ticks ? ticks : 1);
	}
}

static void
sweet_log_start(void)
{
	uint32_t on = 1;
	thread_t thread;

	PE_parse_boot_argn("sweetlog", &on, sizeof(on));
	if (!on || !su.writable || su.nblocks < 2 * SWEET_LOG_BLOCKS) {
		return;
	}
	PE_parse_boot_argn("ufslogsecs", &sweet_log_secs, sizeof(sweet_log_secs));
	if (sweet_log_secs == 0 || sweet_log_secs > 60) {
		sweet_log_secs = SWEET_LOG_SECS;
	}
	PE_parse_boot_argn("sweetlogms", &sweet_log_ms, sizeof(sweet_log_ms));
	if (sweet_log_ms > 2000) {
		sweet_log_ms = 2000;
	}
	/* One synchronous flush now: the boot can reset before the thread runs. */
	{
		uint64_t flushed = 0, seq = 0;
		printf("SWEET LOG: start, on=%d writable=%d nblocks=%llu\n", on, (int)su.writable,
		    (unsigned long long)su.nblocks);
		(void)sweet_log_flush(&flushed, &seq, false);
	}
	if (kernel_thread_start(sweet_log_thread, NULL, &thread) == KERN_SUCCESS) {
		thread_deallocate(thread);
	}
	/* Started here so it exists from the same moment as the log thread. */
	sweet_proc_watch_start();
}

/* Root device for rd=ufsroot0 (IOFindBSDRoot). */
int sweet_ufs_rootdev(dev_t *dev);

int
sweet_ufs_rootdev(dev_t *dev)
{
	printf("SWEET UFS: rootdev called (ready=%d)\n", (int)su.ready);
	if (!su.ready) {
		int error = sweet_ufs_init();
		printf("SWEET UFS: init returned %d\n", error);
		if (error) {
			return error;
		}
	}
	*dev = su.bdev;
	return 0;
}
#endif /* ARM64_BOARD_CONFIG_SWEET */
