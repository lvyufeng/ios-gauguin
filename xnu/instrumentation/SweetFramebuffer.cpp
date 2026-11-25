/*
 * Built-in IOMobileFramebuffer for SWEET: the ABL's continuous-splash
 * framebuffer (1080x2400 a8r8g8b8 in RAM, the panel scans it out by
 * itself) as the main display, driven by CoreAnimation's CPU renderer.
 *
 * IOMobileFramebuffer.framework (iOS 16.7) counts /arm-io children with
 * device_type "display-subsystem", waits for that many services matching
 * IOServiceMatching("IOMobileFramebuffer"), opens each with type 0 and
 * reads canvas-width/canvas-height from the service's provider. The class
 * here (AppleCLCD, an IOMobileFramebuffer) matches the /arm-io/disp0 nub.
 *
 * User client selectors used by CoreAnimation:
 *   3  GetLayerDefaultSurface [layer, ?] -> [IOSurface port name]
 *   4  SwapBegin -> [swap id]
 *   5  SwapEnd, struct 0x46c: +0x50 swap id, +0x54 IOSurface id per layer
 *      (4 layers), +0x64 rect a / +0xc4 rect b per layer (int x,y,w,h),
 *      +0x104 enabled layer mask
 *   6  SwapWait, 7 GetID, 8 GetDisplaySize -> [w, h],
 *   12 RequestPowerChange [state]: 0 = display off (backboardd, power
 *      button / auto-lock), else on. Off fades the panel out over a few
 *      vsyncs (halving each pixel) and keeps it black until on again;
 *      the panel itself stays powered (AMOLED black pixels are off).
 *   18 IsMainDisplay,
 *   28 GetDotPitch, 72 Enable/DisableNotifications [func, refcon, type, 0]
 * Everything else is accepted and logged once.
 *
 * SwapEnd copies the enabled layers' surfaces into the panel memory (no
 * scaling, CPU copy). Vsync (notification type 5) is a 60 Hz timer that
 * sends (count, mach_absolute_time, 0) as 32-bit halves to clients that
 * enabled it, through the port they registered (IOConnectSetNotificationPort).
 *
 * The panel memory itself is published as an IOSurface and returned as the
 * default framebuffer surface. The kernel text console keeps drawing over
 * the GUI by default: boot-arg sweetfb_noconsole=1 stops drawing it from
 * the first swap on (it still reaches the persistent log; panics draw).
 */
#include "SweetSurface.h"

extern "C" int sweet_console_muted;     /* osfmk/console/serial_console.c */

#if defined(SWEET)
#include <IOKit/IOService.h>
#include <IOKit/IOUserClient.h>
#include <IOKit/IOKitKeys.h>
#include <IOKit/IOLib.h>
#include <IOKit/IOLocks.h>
#include <IOKit/IOWorkLoop.h>
#include <IOKit/IOTimerEventSource.h>
#include <IOKit/system.h>
#include <pexpert/pexpert.h>
#include <kern/clock.h>
#include <sys/proc.h>

enum {
	kSweetFBGetLayerDefaultSurface  = 3,
	kSweetFBSwapBegin               = 4,
	kSweetFBSwapEnd                 = 5,
	kSweetFBSwapWait                = 6,
	kSweetFBGetID                   = 7,
	kSweetFBGetDisplaySize          = 8,
	kSweetFBRequestPowerChange      = 12,
	kSweetFBIsMainDisplay           = 18,
	kSweetFBGetDotPitch             = 28,
	kSweetFBNotifications           = 72,
	/*
	 * Selectors backboardd actually calls on the shipping driver (NOTES
	 * 21:50); meanings inferred from the call signatures, each logged until
	 * the boot makes progress.
	 */
	kSweetFBUnknown15               = 15,
	kSweetFBUnknown22               = 22,
	kSweetFBUnknown29               = 29,
	kSweetFBUnknown33               = 33,
	kSweetFBTimingInfo              = 74,
	kSweetFBDisplayModes            = 79,
};

#define SWEET_FB_SWAP_REC_SIZE          0x46c
#define SWEET_FB_LAYERS                 4
#define SWEET_FB_NOTIFY_TYPES           8
#define SWEET_FB_NOTIFY_VSYNC           5
#define SWEET_FB_VSYNC_US               16667
#define SWEET_FB_DOT_PITCH              458     /* ppi, as the iPhone X panel */
/*
 * The iOS userland only has status bar / layout data for real iPhone
 * screens (UIKit: "No status bar visual provider for screen", the red
 * rdar://45025538 bar for 360x800 points). The display is therefore
 * presented as the iPhone X panel, 1125x2436 (375x812 points @3x), and the
 * centered 1080x2400 part of it is shown on the 1080x2400 panel.
 * Boot-arg sweetfb_native=1 presents the real panel size instead.
 */
#define SWEET_FB_LOGICAL_W              1125
#define SWEET_FB_LOGICAL_H              2436
#define SWEET_FB_FORMAT_BGRA            0x42475241

/*
 * SWEET: a *stub* GPU accelerator.
 *
 * backboardd looks up IOAcceleratorES, gets "0 found", and then segfaults
 * (NOTES 21:23, 13 crashes per boot). There is no GPU driver in the tree, so
 * this publishes the service name only: enough for the lookup to succeed and
 * for us to learn whether backboardd needs *a real GPU* or merely *the service
 * to exist*. Every method returns an error, nothing pretends to render.
 */
/* sweetgpuok=1: see the comment in externalMethod. */
static bool sweet_gpu_ok;

class IOAcceleratorESUserClient;

class IOAcceleratorES : public IOService {
	OSDeclareDefaultStructors(IOAcceleratorES);
public:
	bool start(IOService *provider) override;
	void stop(IOService *provider) override;
	IOReturn newUserClient(task_t owningTask, void *securityID, UInt32 type,
	    OSDictionary *properties, IOUserClient **handler) override;
};

/*
 * Minimal user client. Its only job so far is to exist, be advertised through
 * kIOUserClientClassKey, and answer methods with an error rather than a crash.
 *
 * Why this matters: backboardd *finds* IOAcceleratorES (214 matches in a boot,
 * "1 found") but never calls open on it, while it opens every other service it
 * matches. The difference is that the stub never set kIOUserClientClassKey, so
 * there is nothing to open - IOService::newUserClient() would fail. Whether
 * backboardd gets further once an open succeeds is exactly what this is for;
 * it is not expected to make the UI appear on its own.
 */
class IOAcceleratorESUserClient : public IOUserClient {
	OSDeclareDefaultStructors(IOAcceleratorESUserClient);
public:
	IOAcceleratorES *fProvider;
	bool start(IOService *provider) override;
	void stop(IOService *provider) override;
	IOReturn clientClose(void) override;
	IOReturn externalMethod(uint32_t selector, IOExternalMethodArguments *args,
	    IOExternalMethodDispatch *dispatch, OSObject *target,
	    void *reference) override;
};

OSDefineMetaClassAndStructors(IOAcceleratorESUserClient, IOUserClient);

bool
IOAcceleratorESUserClient::start(IOService *provider)
{
	{
		int v = 0;
		PE_parse_boot_argn("sweetgpuok", &v, sizeof(v));
		sweet_gpu_ok = (v != 0);
	}
	fProvider = OSDynamicCast(IOAcceleratorES, provider);
	if (fProvider == nullptr || !IOUserClient::start(provider)) {
		return false;
	}
	{
		extern void proc_selfname(char *buf, int size);
		char who[32] = "?";
		proc_selfname(who, sizeof(who));
		IOLog("SWEET GPU: user client opened by %s\n", who[0] ? who : "?");
	}
	return true;
}

void
IOAcceleratorESUserClient::stop(IOService *provider)
{
	IOLog("SWEET GPU: user client closed\n");
	IOUserClient::stop(provider);
}

IOReturn
IOAcceleratorESUserClient::clientClose(void)
{
	terminate();
	return kIOReturnSuccess;
}

/*
 * Every method reports "unsupported" - deliberately. A method that lies about
 * having rendered would send userland down a path with no pixels at the end;
 * an error lets it fall back, and the call is logged so the *set* of methods
 * iOS actually needs is visible.
 */
IOReturn
IOAcceleratorESUserClient::externalMethod(uint32_t selector,
    IOExternalMethodArguments *args, IOExternalMethodDispatch *dispatch,
    OSObject *target, void *reference)
{
	static uint32_t logged;
	if (logged < 64) {
		logged++;
		/*
		 * Print the scalar inputs as well as the counts: selector 33 is
		 * called 29 times with two scalars and no outputs, and without the
		 * values there is no way to tell a submit from a signal. Only the
		 * first few of each selector are printed, so a per-frame call does
		 * not flood the ring.
		 */
		/*
		 * Name the caller. These lines never carried a process name, so "did
		 * SpringBoard ever touch the GPU?" could not be answered from them -
		 * only from the IOKit match trace, which covers a different code
		 * path (NOTES (73)). sweet_iolog() resolves the current task's name.
		 */
		char gpu_who[32] = "?";
		{
			extern void proc_selfname(char *buf, int size);
			proc_selfname(gpu_who, sizeof(gpu_who));
			if (gpu_who[0] == '\0') {
				gpu_who[0] = '?';
				gpu_who[1] = '\0';
			}
		}
		if (args != nullptr && args->scalarInputCount >= 1) {
			IOLog("SWEET GPU: %s method %u (%u in, %u out) in0=%llu in1=%llu out0=%llu\n",
			    gpu_who, selector, args->scalarInputCount, args->scalarOutputCount,
			    (unsigned long long)(args->scalarInputCount > 0 ? args->scalarInput[0] : 0),
			    (unsigned long long)(args->scalarInputCount > 1 ? args->scalarInput[1] : 0),
			    (unsigned long long)(args->scalarOutputCount > 0 && args->scalarOutput ? args->scalarOutput[0] : 0));
		} else {
			IOLog("SWEET GPU: %s method %u (%u in, %u out) -> %s\n",
			    gpu_who, selector, args ? args->scalarInputCount : 0,
			    args ? args->scalarOutputCount : 0,
			    sweet_gpu_ok ? "ok" : "unsupported");
		}
	}
	/*
	 * sweetgpuok=1 makes every method succeed instead of failing.
	 *
	 * Why: with kIOReturnUnsupported backboardd asks exactly one question
	 * (selector 2, no arguments, no outputs) and closes the connection
	 * immediately - so the log never shows what it would ask *next*. A
	 * failing first question proves nothing about the ones behind it.
	 * Returning success here is a probe, not a fix: it tells us which
	 * selectors userland goes on to use, at the cost of any checks inside
	 * the client that would have rejected the service. Outputs are left
	 * zeroed, so a caller that validates what it reads will still fail.
	 */
	return sweet_gpu_ok ? kIOReturnSuccess : kIOReturnUnsupported;
}

IOReturn
IOAcceleratorES::newUserClient(task_t owningTask, void *securityID, UInt32 type,
    OSDictionary *properties, IOUserClient **handler)
{
	IOAcceleratorESUserClient *client = new IOAcceleratorESUserClient;
	if (client == nullptr) {
		return kIOReturnNoMemory;
	}
	if (!client->initWithTask(owningTask, securityID, type)) {
		client->release();
		return kIOReturnBadArgument;
	}
	if (!client->attach(this) || !client->start(this)) {
		client->detach(this);
		client->release();
		return kIOReturnError;
	}
	*handler = client;
	return kIOReturnSuccess;
}

OSDefineMetaClassAndStructors(IOAcceleratorES, IOService);

/*
 * AGXAccelerator: the class name iOS 16 actually asks for.
 *
 * backboardd publishes three matching dictionaries that MISS in a boot
 * (IOServiceGetMatchingService -> kIOReturnNotFound):
 *
 *   matching1 MISS IOProviderClass=AGXAccelerator      -> none
 *   matching1 MISS IOProviderClass=AppleM              -> none
 *   matching1 MISS IOProviderClass=ApplePearlSEPDriver -> none
 *
 * and then logs "NEVER FOUND class AGXAccelerator". IOAcceleratorES is matched
 * 218 times but is not what it wants - that name came from an older
 * investigation. This subclass exists so the registry entry carries the class
 * name AGXAccelerator; it inherits the stub behaviour unchanged (no rendering,
 * every user method returns an error) so the only thing that changes is
 * whether the lookup succeeds.
 */
class AGXAccelerator : public IOAcceleratorES {
	OSDeclareDefaultStructors(AGXAccelerator);
public:
	bool start(IOService *provider) override;
};

OSDefineMetaClassAndStructors(AGXAccelerator, IOAcceleratorES);

bool
AGXAccelerator::start(IOService *provider)
{
	if (!IOAcceleratorES::start(provider)) {
		return false;
	}
	setProperty("IOClass", "AGXAccelerator");
	setProperty("IOGPUFamilyStub", true);
	IOLog("SWEET GPU: AGXAccelerator published (stub)\n");
	return true;
}

bool
IOAcceleratorES::start(IOService *provider)
{
	if (!IOService::start(provider)) {
		return false;
	}
	setProperty("IOClass", "IOAcceleratorES");
	setProperty("IOProviderClass", "IOResources");
	setProperty("stub", true);
	setProperty("IOGPUFamilyStub", true);
	/* Without this, matching succeeds but nothing can open the service -
	 * backboardd found it 214 times and never opened it (NOTES (43)). */
	setProperty(kIOUserClientClassKey, "IOAcceleratorESUserClient");
	registerService();
	IOLog("SWEET GPU: stub IOAcceleratorES published\n");
	return true;
}

void
IOAcceleratorES::stop(IOService *provider)
{
	IOService::stop(provider);
}

class IOMobileFramebuffer : public IOService {
	OSDeclareDefaultStructors(IOMobileFramebuffer);
};

OSDefineMetaClassAndStructors(IOMobileFramebuffer, IOService);

class IOMobileFramebufferUserClient;

extern "C" void sweet_log_flush_now(void);
/* Defined in SweetSurface.cpp; samples a surface's pixels (NOTES (47)). */
extern "C" int sweet_surface_sample(uint32_t id, uint32_t *nonblack,
    uint32_t *distinct, uint32_t *px0);

class AppleCLCD : public IOMobileFramebuffer {
	OSDeclareDefaultStructors(AppleCLCD);

	IOWorkLoop         *fWorkLoop;
	IOTimerEventSource *fVsync;
	uint64_t            fVsyncCount;

	static void vsyncFired(OSObject *owner, IOTimerEventSource *sender);

public:
	uint64_t      fPhys;
	uint32_t      fWidth, fHeight, fRowBytes;
	uint32_t      fLogicalW, fLogicalH;     /* size reported to userland */
	int32_t       fOffX, fOffY;             /* logical origin of the panel */
	uintptr_t     fPixels;          /* kernel mapping of the panel memory */
	IOMemoryMap  *fMap;
	SweetSurface *fSurface;         /* the panel memory as an IOSurface */
	IOLock       *fLock;            /* swaps and client list */
	OSArray      *fClients;
	uint32_t      fSwapID;
	uint64_t      fLastSet;      /* last argument of the 22/33 setters */
	bool          fConsolePaused;
	uint8_t       fPending[SWEET_FB_SWAP_REC_SIZE];     /* latest swap, not yet shown */
	bool          fDirty;
	uint32_t      fFlushTicks;    /* vsync ticks between panel copies */
	bool          fPowerOff;      /* RequestPowerChange(0) */
	uint32_t      fFadeStep;      /* fade-out steps done while off */

	bool start(IOService *provider) APPLE_KEXT_OVERRIDE;
	void addClient(IOMobileFramebufferUserClient *client);
	void removeClient(IOMobileFramebufferUserClient *client);
	void swap(const uint8_t *rec);
	void present(const uint8_t *rec);
	void mark(uint32_t colour);     /* panel colour block: stage witness */
};

static AppleCLCD *gSweetFB;

OSDefineMetaClassAndStructors(AppleCLCD, IOMobileFramebuffer);

class IOMobileFramebufferUserClient : public IOUserClient {
	OSDeclareDefaultStructors(IOMobileFramebufferUserClient);

public:
	AppleCLCD          *fFB;
	task_t              fTask;
	mach_port_t         fPort;
	io_user_reference_t fFunc[SWEET_FB_NOTIFY_TYPES];
	io_user_reference_t fRefcon[SWEET_FB_NOTIFY_TYPES];

	bool initWithTask(task_t owningTask, void *securityID, UInt32 type) APPLE_KEXT_OVERRIDE;
	bool start(IOService *provider) APPLE_KEXT_OVERRIDE;
	IOReturn clientClose(void) APPLE_KEXT_OVERRIDE;
	IOReturn registerNotificationPort(mach_port_t port, UInt32 type,
	    io_user_reference_t refCon) APPLE_KEXT_OVERRIDE;
	IOReturn externalMethod(uint32_t selector, IOExternalMethodArguments *args,
	    IOExternalMethodDispatch *dispatch, OSObject *target,
	    void *reference) APPLE_KEXT_OVERRIDE;
	void notify(uint32_t type, const uint64_t *values, uint32_t count);
	bool hasNotification(uint32_t type) const;
};

OSDefineMetaClassAndStructors(IOMobileFramebufferUserClient, IOUserClient);

/* Colour block in the top-left corner of the panel; see sweet_fb_mark callers. */
void
AppleCLCD::mark(uint32_t colour)
{
	/*
	 * Disabled by default via sweetfb_mark=0 (see the call site): even a
	 * 320x96 block costs ~30k uncached stores, and a full panel costs millions -
	 * measured as "the boot is just very slow", not as a hang (NOTES 15:35).
	 * Painting is a debugging aid; it must never be on the boot path.
	 */
	static int painting = -1;
	if (painting < 0) {
		painting = 1;
		PE_parse_boot_argn("sweetfb_mark", &painting, sizeof(painting));
	}
	if (!painting) {
		return;
	}
	if (fPixels == 0 || fWidth == 0 || fHeight == 0 || fRowBytes == 0) {
		return;
	}
	/* Whole panel: a stage colour must be readable at a glance. */
	/*
	 * Corner block, not the whole panel: painting 1080x2400 with strongly
	 * ordered stores at boot is slow enough to look like a hang (NOTES 15:30),
	 * and it hides everything underneath. 320x96 is plenty to identify a colour.
	 */
	/*
	 * A quarter of the panel: large enough to read from across a room, small
	 * enough that the cost stays ~650k stores instead of 2.6M.
	 */
	uint32_t w = fWidth / 2;
	uint32_t h = fHeight / 2;
	for (uint32_t y = 0; y < h; y++) {
		volatile uint32_t *row = (volatile uint32_t *)(fPixels + (uint64_t)y * fRowBytes);
		for (uint32_t x = 0; x < w; x++) {
			row[x] = colour;
		}
	}
	/*
	 * Optional hold so a human can read the colour. OFF by default: the busy
	 * ring blocks the boot long enough that console output written straight
	 * after a mark was being lost (NOTES 15:10), which made page walks look
	 * like hangs. Pass sweetmarkhold=1 when the panel is the only witness.
	 */
	static int hold = -1;
	if (hold < 0) {
		hold = 0;
		PE_parse_boot_argn("sweetmarkhold", &hold, sizeof(hold));
	}
	if (hold) {
		for (volatile uint64_t spin = 0; spin < 2000000000ULL; spin++) {
			;
		}
	}
}

/* Called from C: paint the marker without needing the C++ instance type. */
extern "C" void
sweet_fb_mark(uint32_t colour)
{
	if (gSweetFB != NULL) {
		gSweetFB->mark(colour);
	}
}

bool
AppleCLCD::start(IOService *provider)
{
	PE_Video video;

	if (!IOService::start(provider)) {
		return false;
	}
	PE_current_console(&video);
	fPhys = video.v_baseAddr;
	fWidth = (uint32_t)video.v_width;
	fHeight = (uint32_t)video.v_height;
	fRowBytes = (uint32_t)video.v_rowBytes;
	if (fPhys == 0 || fWidth == 0 || fHeight == 0 || fRowBytes < fWidth * 4) {
		IOLog("SWEET FB: no boot framebuffer\n");
		return false;
	}
	int native = 0;
	PE_parse_boot_argn("sweetfb_native", &native, sizeof(native));
	fLogicalW = fWidth;
	fLogicalH = fHeight;
	if (!native && fWidth <= SWEET_FB_LOGICAL_W && fHeight <= SWEET_FB_LOGICAL_H) {
		fLogicalW = SWEET_FB_LOGICAL_W;
		fLogicalH = SWEET_FB_LOGICAL_H;
	}
	fOffX = (int32_t)(fLogicalW - fWidth) / 2;
	fOffY = (int32_t)(fLogicalH - fHeight) / 2;
	fLock = IOLockAlloc();
	fClients = OSArray::withCapacity(4);
	fSurface = sweet_surface_create_physical(fPhys, fWidth, fHeight, fRowBytes, SWEET_FB_FORMAT_BGRA);
	fPixels = fSurface != NULL ? fSurface->kernelAddress() : 0;
	fWorkLoop = IOWorkLoop::workLoop();
	if (fLock == NULL || fClients == NULL || fPixels == 0 || fWorkLoop == NULL) {
		IOLog("SWEET FB: setup failed\n");
		OSSafeReleaseNULL(fSurface);    /* stays published: also held by the table */
		OSSafeReleaseNULL(fWorkLoop);
		return false;
	}
	gSweetFB = this;
	fVsync = IOTimerEventSource::timerEventSource(this, &AppleCLCD::vsyncFired);
	if (fVsync == NULL || fWorkLoop->addEventSource(fVsync) != kIOReturnSuccess) {
		IOLog("SWEET FB: no vsync timer\n");
		return false;
	}
	uint32_t hz = 10;
	PE_parse_boot_argn("sweetfb_hz", &hz, sizeof(hz));
	fFlushTicks = (hz == 0 || hz >= 60) ? 1 : 60 / hz;
	fVsync->setTimeoutUS(SWEET_FB_VSYNC_US);

	setProperty(kIOUserClientClassKey, "IOMobileFramebufferUserClient");
	setProperty("external", false);
	setProperty("DisplayPipePlaneBaseAlignment", 64ULL, 32);
	registerService();
	IOLog("SWEET FB: AppleCLCD %ux%u stride %u at 0x%llx, default surface %u, presented as %ux%u\n",
	    fWidth, fHeight, fRowBytes, fPhys, fSurface->id, fLogicalW, fLogicalH);
	/*
	 * Panel marker, because the log is not a reliable witness (NOTES 14:00):
	 * once the framebuffer is fully up, paint a colour block in the top-left
	 * corner. The colour names the stage a later probe reached, so progress can
	 * be read off the screen with no console at all.
	 *    red = AppleCLCD::start finished
	 */
	sweet_fb_mark(0x0000ff00u);   /* RGB(0,255,0) green */
	return true;
}

void
AppleCLCD::vsyncFired(OSObject *owner, IOTimerEventSource *sender)
{
	AppleCLCD *fb = (AppleCLCD *)owner;
	uint64_t now = mach_absolute_time();
	uint64_t count = ++fb->fVsyncCount;
	uint64_t values[6] = {
		(uint32_t)count, (uint32_t)(count >> 32),
		(uint32_t)now, (uint32_t)(now >> 32),
		0, 0,
	};

	IOLockLock(fb->fLock);
	for (unsigned int i = 0; i < fb->fClients->getCount(); i++) {
		IOMobileFramebufferUserClient *client =
		    (IOMobileFramebufferUserClient *)fb->fClients->getObject(i);
		client->notify(SWEET_FB_NOTIFY_VSYNC, values, 6);
		/*
		 * Deliver to every other registered notification type as well: today
		 * only vsync (5) fires, so a client waiting on type 3 - which is what
		 * backboardd registers, NOTES 21:14 - never hears anything, and a
		 * registered notification that never fires looks exactly like a
		 * display that never scans out. Sending the same payload to all
		 * registered types costs nothing and tells us whether type 3 is the
		 * one backboardd is waiting on.
		 */
		for (uint32_t t = 0; t < SWEET_FB_NOTIFY_TYPES; t++) {
			if (t != SWEET_FB_NOTIFY_VSYNC && client->hasNotification(t)) {
				client->notify(t, values, 6);
			}
		}
	}
	if (fb->fPowerOff) {
		/* Fade out: halve every channel each vsync, then black, then idle. */
		uint32_t step = fb->fFadeStep;
		if (step <= 6) {
			fb->fFadeStep = step + 1;
		}
		IOLockUnlock(fb->fLock);
		if (step <= 6) {
			for (uint32_t y = 0; y < fb->fHeight; y++) {
				volatile uint32_t *row = (volatile uint32_t *)(fb->fPixels + (uint64_t)y * fb->fRowBytes);
				for (uint32_t x = 0; x < fb->fWidth; x++) {
					row[x] = step < 6 ? (row[x] >> 1) & 0x7f7f7f7f : 0;
				}
			}
		}
		sender->setTimeoutUS(SWEET_FB_VSYNC_US);
		return;
	}
	/*
	 * Counters for the bring-up: how many vsyncs actually run, how many of
	 * them had a dirty surface and how many frames were presented. A GUI
	 * problem is much easier to place with these three numbers in the log.
	 */
	static uint64_t presents;
	bool flush = fb->fDirty && (count % fb->fFlushTicks) == 0;
	if (flush) {
		presents++;
	}
	if ((count % 600) == 0 || count == 2) {
		/*
		 * Sample the panel to say *what* is on screen, not just that frames
		 * were presented: count non-black samples and how many distinct
		 * colours they hold. 4,096 evenly spaced pixels is enough to tell a
		 * black panel from a drawn one and a flat fill from real content.
		 */
		unsigned nonblack = 0, distinct = 0, samples = 0;
		uint32_t seen[16] = { 0 };
		/*
		 * Bounding box of the non-black samples. "nonblack=60" has never said
		 * *where* those pixels are: a 60-pixel status bar and 60 scattered
		 * specks look identical to the counter yet mean completely different
		 * things (NOTES (71)).
		 */
		uint32_t minx = 0xffffffff, maxx = 0, miny = 0xffffffff, maxy = 0;
		/*
		 * One-shot ASCII map of the centre region.
		 *
		 * The panel has had "distinct=5" and a 632x341 box for many rounds
		 * without anyone knowing what is in it. A coarse luminance map costs
		 * one pass and settles it: a logo, a progress bar and noise all look
		 * different, and none of them need a pixel dump to identify.
		 */
		static bool mapped;
		if (!mapped && count >= 4200 && fb->fPixels != 0) {
			mapped = true;
			/*
			 * Whole panel, not just the centre box: what surrounds the
			 * shape says as much as the shape - a full-bleed background
			 * means a UI is up, black around it means nothing else drew.
			 */
			/*
			 * Zoom on the band found in NOTES (72): the whole panel was
			 * black except one narrow horizontal strip near the vertical
			 * centre. 128 columns over 400 px and 24 rows over 300 px is
			 * enough resolution to tell a progress bar from text.
			 */
			uint32_t x0 = 240, x1 = 840, y0 = 1100, y1 = 1400;
			uint32_t sx = (x1 - x0) / 128, sy = (y1 - y0) / 24;
			if (sx == 0) sx = 1;
			if (sy == 0) sy = 1;
			IOLog("SWEET FB: centre map %ux%u..%ux%u step %u,%u\n", x0, y0, x1, y1, sx, sy);
			for (uint32_t yy = y0; yy < y1 && yy < fb->fHeight; yy += sy) {
				char row[160];
				int n = 0;
				for (uint32_t xx = x0; xx < x1 && xx < fb->fWidth && n < 128; xx += sx) {
					uint32_t px = ((const uint32_t *)fb->fPixels)[yy * fb->fWidth + xx];
					uint32_t lum = ((px >> 16) & 0xff) + ((px >> 8) & 0xff) + (px & 0xff);
					/*
					 * Colour-coded instead of luminance: R/G/B/W tell apart
					 * a white logo, a blue button, a coloured icon and a grey
					 * panel at a glance, where a luminance ramp cannot.
					 */
					if (lum == 0) {
						row[n++] = '.';
					} else {
						uint32_t r = (px >> 16) & 0xff, g = (px >> 8) & 0xff, b = px & 0xff;
						uint32_t mx = r > g ? (r > b ? r : b) : (g > b ? g : b);
						uint32_t mn = r < g ? (r < b ? r : b) : (g < b ? g : b);
						if (mx - mn < 32) {
							row[n++] = mx > 160 ? 'W' : (mx > 64 ? 'g' : 'd');
						} else if (r == mx) {
							row[n++] = 'R';
						} else if (g == mx) {
							row[n++] = 'G';
						} else {
							row[n++] = 'B';
						}
					}
				}
				row[n] = 0;
				IOLog("SWEET FB: |%s|\n", row);
			}
		}

		if (fb->fPixels != 0 && fb->fWidth > 0 && fb->fHeight > 0) {
			uint32_t step = (uint32_t)(fb->fWidth * fb->fHeight / 4096);
			if (step == 0) {
				step = 1;
			}
			for (uint32_t i = 0; i < fb->fWidth * fb->fHeight; i += step) {
				uint32_t px = ((const uint32_t *)fb->fPixels)[i];
				samples++;
				if ((px & 0x00ffffffu) != 0) {
					nonblack++;
					{
						uint32_t ix = i % fb->fWidth, iy = i / fb->fWidth;
						if (ix < minx) minx = ix;
						if (ix > maxx) maxx = ix;
						if (iy < miny) miny = iy;
						if (iy > maxy) maxy = iy;
					}
					uint32_t c = px & 0x00ffffffu;
					unsigned k = 0;
					for (; k < distinct && k < 16; k++) {
						if (seen[k] == c) {
							break;
						}
					}
					if (k == distinct && distinct < 16) {
						seen[distinct++] = c;
					}
				}
			}
		}
		/*
		 * The vsync timer is programmed for 16,667 us, so the tick delta
		 * between two reports tells us the *real* timebase: if 600 frames
		 * take 600*16667 us of hardware time, ticks/600/16667us gives Hz.
		 * NOTES 23:00 suspects 24 MHz is the truth and 19.2 MHz is declared.
		 */
		uint64_t ticknow = mach_absolute_time();
		static uint64_t lastticks, lastcount;
		uint64_t dhz = 0;
		if (lastcount != 0 && ticknow > lastticks) {
			uint64_t dticks = ticknow - lastticks;
			uint64_t dframes = count - lastcount;
			if (dframes != 0) {
				/* declared Hz implied by this delta, in whole Hz */
				dhz = dticks * 1000000ull / (dframes * 16667ull);
			}
		}
		/*
		 * Wall-clock interval per vsync, in microseconds, straight from the
		 * counter: if each callback is costing hundreds of ms the number shows
		 * it directly instead of through the implied_hz ratio (NOTES 16:50).
		 */
		if (lastcount != 0 && count > lastcount) {
			uint64_t dt = ticknow - lastticks;
			uint64_t nv = count - lastcount;
			IOLog("SWEET FB: vsync interval %llu us over %llu frames (%llu ticks)\n",
			    (unsigned long long)(dt * 1000000ull / nv /
			    (gPEClockFrequencyInfo.timebase_frequency_hz ? gPEClockFrequencyInfo.timebase_frequency_hz : 1)),
			    (unsigned long long)nv, (unsigned long long)dt);
		}
		lastticks = ticknow;
		lastcount = count;
		/*
		 * Print the colours, not just how many. "distinct=5" has been read
		 * for a hundred rounds without anyone knowing what those five colours
		 * are - if they are a startup logo and a clear colour, the panel is
		 * showing the boot splash; if they are arbitrary, something else
		 * painted them (NOTES (71)).
		 */
		{
			char colours[128];
			int pos = 0;
			for (unsigned i = 0; i < distinct && i < 16 && pos < (int)sizeof(colours); i++) {
				pos += snprintf(colours + pos, sizeof(colours) - pos,
				    " %06x", seen[i]);
			}
			IOLog("SWEET FB: vsync=%llu dirty=%u presents=%llu client=%u "
			    "px sample %u nonblack=%u distinct=%u colours:%s hz=%llu\n",
			    (unsigned long long)count, fb->fDirty ? 1u : 0u,
			    (unsigned long long)presents, fb->fClients->getCount(),
			    samples, nonblack, distinct, pos ? colours : " (none)",
			    (unsigned long long)dhz);
			if (nonblack != 0) {
				IOLog("SWEET FB: nonblack box x=%u..%u y=%u..%u (panel %ux%u)\n",
				    minx, maxx, miny, maxy, fb->fWidth, fb->fHeight);
			}
		}
	}
	uint8_t *rec = NULL;
	if (flush) {
		rec = (uint8_t *)IOMallocData(SWEET_FB_SWAP_REC_SIZE);
		if (rec != NULL) {
			memcpy(rec, fb->fPending, SWEET_FB_SWAP_REC_SIZE);
			fb->fDirty = false;
		}
	}
	IOLockUnlock(fb->fLock);
	if (rec != NULL) {
		fb->present(rec);
		IOFreeData(rec, SWEET_FB_SWAP_REC_SIZE);
	}
	sender->setTimeoutUS(SWEET_FB_VSYNC_US);
}

void
AppleCLCD::addClient(IOMobileFramebufferUserClient *client)
{
	IOLockLock(fLock);
	fClients->setObject(client);
	IOLockUnlock(fLock);
}

void
AppleCLCD::removeClient(IOMobileFramebufferUserClient *client)
{
	IOLockLock(fLock);
	unsigned int i = fClients->getNextIndexOfObject(client, 0);
	if (i != (unsigned int)-1) {
		fClients->removeObject(i);
	}
	IOLockUnlock(fLock);
}

static uint32_t
get32(const uint8_t *p, uint32_t off)
{
	uint32_t v;
	memcpy(&v, p + off, 4);
	return v;
}

static uint32_t sweet_fb_swaps_logged;
static uint64_t sweet_fb_swap_count;

/* Copy each enabled layer's surface into the panel memory (no scaling). */
/*
 * A swap only records the frame: copying 10 MB into the panel on every
 * swap (backboardd presents at 60 Hz) took the whole CPU. The vsync timer
 * shows the latest frame every fFlushTicks ticks (boot-arg sweetfb_hz,
 * default 10 Hz).
 */
void
AppleCLCD::swap(const uint8_t *rec)
{
	IOLockLock(fLock);
	memcpy(fPending, rec, SWEET_FB_SWAP_REC_SIZE);
	fDirty = true;
	IOLockUnlock(fLock);
	if ((++sweet_fb_swap_count % 1000) == 0) {
		IOLog("SWEET FB: %llu swaps\n", sweet_fb_swap_count);
	}
}

void
AppleCLCD::present(const uint8_t *rec)
{
	uint32_t mask = get32(rec, 0x104);


	if (!fConsolePaused) {
		int quiet = 0;
		fConsolePaused = true;
		if (PE_parse_boot_argn("sweetfb_noconsole", &quiet, sizeof(quiet)) && quiet != 0) {
			/* Not PE_initialize_console(kPEDisableScreen): its console switch
			 * writes the read-only-late cons_ops_index and panics. */
			sweet_console_muted = 1;
		}
	}

	for (uint32_t layer = 0; layer < SWEET_FB_LAYERS; layer++) {
		uint32_t id = get32(rec, 0x54 + 4 * layer);
		const uint8_t *a = rec + 0x64 + 16 * layer;
		const uint8_t *b = rec + 0xc4 + 16 * layer;
		int32_t sx = (int32_t)get32(a, 0), sy = (int32_t)get32(a, 4);
		int32_t dx = (int32_t)get32(b, 0), dy = (int32_t)get32(b, 4);
		int32_t w = (int32_t)get32(b, 8), h = (int32_t)get32(b, 12);

		if (!(mask & (1u << layer)) || id == 0) {
			continue;
		}
		SweetSurface *s = sweet_surface_copy(id);
		if (sweet_fb_swaps_logged < 16) {
			sweet_fb_swaps_logged++;
			IOLog("SWEET FB: swap %u layer %u surface %u %ux%u fmt 0x%x bpr %u a %d,%d %ux%u b %d,%d %dx%d\n",
			    get32(rec, 0x50), layer, id, s ? s->width : 0, s ? s->height : 0,
			    s ? s->pixelFormat : 0, s ? s->bytesPerRow : 0, sx, sy, get32(a, 8),
			    get32(a, 12), dx, dy, w, h);
		}
		if (s == NULL || s == fSurface) {
			OSSafeReleaseNULL(s);
			continue;
		}
		/*
		 * Sample the surface being swapped - the one userland just handed
		 * us - and not fSurface, which is the panel's own surface. The
		 * earlier attempt sampled fSurface and concluded "the image never
		 * changes"; it was reading the wrong object (NOTES (48)).
		 */
		{
			static uint64_t sampled;
			if ((++sampled % 8) == 1) {
				uint32_t nb = 0, dist = 0, px0 = 0;
				if (sweet_surface_sample(id, &nb, &dist, &px0)) {
					IOLog("SWEET FB: src id=%u swap=%u nonblack=%u distinct=%u px0=%#x\n",
					    id, get32(rec, 0x50), nb, dist, px0);
				}
			}
		}
		uintptr_t src = s->kernelAddress();
		uint32_t bpe = s->bytesPerElement ? s->bytesPerElement : 4;
		if (w <= 0 || h <= 0) {
			w = (int32_t)s->width;
			h = (int32_t)s->height;
		}
		if (sx < 0 || sy < 0) {
			sx = sy = 0;
		}
		if (dx < 0 || dy < 0) {
			dx = dy = 0;
		}
		/* Logical (presented) display coordinates -> panel coordinates. */
		dx -= fOffX;
		dy -= fOffY;
		if (dx < 0) {
			sx -= dx;
			w += dx;
			dx = 0;
		}
		if (dy < 0) {
			sy -= dy;
			h += dy;
			dy = 0;
		}
		if (w > (int32_t)s->width - sx) {
			w = (int32_t)s->width - sx;
		}
		if (h > (int32_t)s->height - sy) {
			h = (int32_t)s->height - sy;
		}
		if (w > (int32_t)fWidth - dx) {
			w = (int32_t)fWidth - dx;
		}
		if (h > (int32_t)fHeight - dy) {
			h = (int32_t)fHeight - dy;
		}
		uint64_t last = (uint64_t)s->offset + (uint64_t)(sy + h - 1) * s->bytesPerRow +
		    (uint64_t)(sx + w) * 4;
		if (w <= 0 || h <= 0 || s->elementWidth != 1 || s->elementHeight != 1 ||
		    s->memory == NULL || last > s->memory->getLength()) {
			src = 0;
		}
		if (src != 0 && bpe == 4) {
			/*
			 * Rows of the swap record's dirty rectangle only. Comparing pixels
			 * one by one was tried and was SLOWER: reads through the write-
			 * combined panel mapping cost as much as writes, so scanning 2.6M
			 * pixels to save a few thousand stores is a loss (NOTES 16:35).
			 * The rectangle is already in the record - use it.
			 */
			for (int32_t y = 0; y < h; y++) {
				memcpy((void *)(fPixels + (uint64_t)(dy + y) * fRowBytes + (uint64_t)dx * 4),
				    (const void *)(src + s->offset + (uint64_t)(sy + y) * s->bytesPerRow + (uint64_t)sx * 4),
				    (size_t)w * 4);
			}
		}
		s->release();
	}
}

bool
IOMobileFramebufferUserClient::initWithTask(task_t owningTask, void *securityID, UInt32 type)
{
	if (!IOUserClient::initWithTask(owningTask, securityID, type)) {
		return false;
	}
	fTask = owningTask;
	return true;
}

bool
IOMobileFramebufferUserClient::start(IOService *provider)
{
	fFB = OSDynamicCast(AppleCLCD, provider);
	if (fFB == NULL || !IOUserClient::start(provider)) {
		return false;
	}
	fFB->addClient(this);
	return true;
}

IOReturn
IOMobileFramebufferUserClient::clientClose(void)
{
	if (fFB != NULL) {
		{
			char name[32];
			proc_selfname(name, sizeof(name));
			IOLog("SWEET FB: %s closing its client\n", name);
		}
		fFB->removeClient(this);
		IOLockLock(fFB->fLock);
		mach_port_t old = fPort;
		fPort = MACH_PORT_NULL;
		IOLockUnlock(fFB->fLock);
		if (old != MACH_PORT_NULL) {
			releaseNotificationPort(old);
		}
	}
	terminate();
	return kIOReturnSuccess;
}

IOReturn
IOMobileFramebufferUserClient::registerNotificationPort(mach_port_t port, __unused UInt32 type,
    __unused io_user_reference_t refCon)
{
	mach_port_t old;
	IOLockLock(fFB->fLock);
	old = fPort;
	fPort = port;
	IOLockUnlock(fFB->fLock);
	if (old != MACH_PORT_NULL) {
		releaseNotificationPort(old);
	}
	return kIOReturnSuccess;
}

bool
IOMobileFramebufferUserClient::hasNotification(uint32_t type) const
{
	return type < SWEET_FB_NOTIFY_TYPES && fFunc[type] != 0 &&
	    fPort != MACH_PORT_NULL;
}

/* Called with the framebuffer lock held. */
void
IOMobileFramebufferUserClient::notify(uint32_t type, const uint64_t *values, uint32_t count)
{
	OSAsyncReference64 ref;

	if (type >= SWEET_FB_NOTIFY_TYPES || fFunc[type] == 0 || fPort == MACH_PORT_NULL) {
		return;
	}
	bzero(ref, sizeof(ref));
	setAsyncReference64(ref, fPort, (mach_vm_address_t)fFunc[type], fRefcon[type], fTask);
	sendAsyncResult64WithOptions(ref, kIOReturnSuccess, (io_user_reference_t *)values, count,
	    kIOUserNotifyOptionCanDrop);
}

static uint64_t sweet_fb_logged;        /* selectors already logged (< 64) */

IOReturn
IOMobileFramebufferUserClient::externalMethod(uint32_t selector, IOExternalMethodArguments *args,
    __unused IOExternalMethodDispatch *dispatch, __unused OSObject *target,
    __unused void *reference)
{
	IOReturn ret = kIOReturnSuccess;
	uint64_t out[4] = { 0, 0, 0, 0 };
	uint32_t outCount = 0;

	switch (selector) {
	case kSweetFBGetLayerDefaultSurface:
		out[0] = sweet_surface_port_in_task(fFB->fSurface, fTask);
		outCount = 1;
		break;
	case kSweetFBSwapBegin:
		IOLockLock(fFB->fLock);
		out[0] = ++fFB->fSwapID;
		IOLockUnlock(fFB->fLock);
		outCount = 1;
		break;
	case kSweetFBSwapEnd: {
		uint8_t rec[SWEET_FB_SWAP_REC_SIZE];
		if (args->structureInputDescriptor != NULL ||
		    args->structureInputSize < SWEET_FB_SWAP_REC_SIZE) {
			ret = kIOReturnBadArgument;
			break;
		}
		memcpy(rec, args->structureInput, sizeof(rec));
		fFB->swap(rec);
		break;
	}
	case kSweetFBGetID:
		out[0] = 0;
		outCount = 1;
		break;
	case kSweetFBGetDisplaySize:
		out[0] = fFB->fLogicalW;
		out[1] = fFB->fLogicalH;
		outCount = 2;
		break;
	case kSweetFBIsMainDisplay:
		out[0] = 1;
		outCount = 1;
		break;
	case kSweetFBGetDotPitch:
		out[0] = SWEET_FB_DOT_PITCH;
		outCount = 1;
		break;
	case kSweetFBNotifications:
		if (args->scalarInputCount >= 3 && args->scalarInput[2] < SWEET_FB_NOTIFY_TYPES) {
			uint32_t type = (uint32_t)args->scalarInput[2];
			IOLockLock(fFB->fLock);
			fFunc[type] = args->scalarInput[0];
			fRefcon[type] = args->scalarInput[1];
			IOLockUnlock(fFB->fLock);
			char name[32];
			proc_selfname(name, sizeof(name));
			IOLog("SWEET FB: %s notifications type %u %s\n", name, type,
			    args->scalarInput[0] ? "on" : "off");
		}
		break;
	case kSweetFBRequestPowerChange:
		if (args->scalarInputCount >= 1) {
			bool off = args->scalarInput[0] == 0;
			IOLockLock(fFB->fLock);
			if (off != fFB->fPowerOff) {
				fFB->fPowerOff = off;
				fFB->fFadeStep = 0;
				fFB->fDirty = true;     /* on: redraw the latest frame */
			}
			IOLockUnlock(fFB->fLock);
			IOLog("SWEET FB: display %s\n", off ? "off" : "on");
		}
		break;
	case kSweetFBSwapWait:
		break;
	/*
	 * The ABI backboardd actually uses. Filling these with self-consistent
	 * values is the cheapest way to learn which one gates the pipeline: if
	 * swaps start after this, the mode/timing query was the gate.
	 */
	case kSweetFBUnknown15:
		out[0] = args->scalarInputCount >= 2 ? args->scalarInput[1] : 0;
		outCount = 1;
		break;
	case kSweetFBUnknown22:
	case kSweetFBUnknown33:
		if (args->scalarInputCount >= 1) {
			fFB->fLastSet = args->scalarInput[0];
		}
		break;
	case kSweetFBUnknown29: {
		if (args->structureOutput != NULL && args->structureOutputSize >= 8) {
			uint32_t pair[2] = { fFB->fLogicalW, fFB->fLogicalH };
			memcpy(args->structureOutput, pair, sizeof(pair));
		}
		break;
	}
	case kSweetFBTimingInfo: {
		/* Also all-zero for the same experiment (NOTES 21:44). */
		break;
	}
	case kSweetFBDisplayModes: {
		/*
		 * Deliberately all-zero (the common path bzero()s it anyway): the
		 * invented header filled "a mode count of 1" and a size that the
		 * userland may have parsed as a string. Test whether removing it
		 * moves the crash - NOTES 21:44.
		 */
		break;
	}
	default:
		break;
	}

	for (uint32_t i = 0; i < args->scalarOutputCount; i++) {
		args->scalarOutput[i] = i < outCount ? out[i] : 0;
	}
	if (args->structureOutputDescriptor == NULL && args->structureOutput != NULL) {
		bzero(args->structureOutput, args->structureOutputSize);
	}
	{
		/*
		 * Log EVERY call with the values we hand back, not just the first of
		 * each selector: the crash is a 0..15 pointer used as a C string by
		 * CoreFoundation/IOKit (NOTES 21:55), so the call immediately before
		 * the fault is the one whose reply is being misused. The first 200
		 * calls are enough to cover backboardd's whole start-up sequence.
		 */
		static unsigned sweet_fb_calls;
		if (sweet_fb_calls < 200) {
			sweet_fb_calls++;
			char name[32];
			proc_selfname(name, sizeof(name));
			IOLog("SWEET FB: %u %s sel %u in %u/%u out %u/%u -> "
			    "0x%x [%llx %llx %llx]\n", sweet_fb_calls, name, selector,
			    args->scalarInputCount, args->structureInputSize,
			    args->scalarOutputCount, args->structureOutputSize, ret,
			    (unsigned long long)out[0], (unsigned long long)out[1],
			    (unsigned long long)out[2]);
		}
	}
	return ret;
}
#endif /* SWEET */
