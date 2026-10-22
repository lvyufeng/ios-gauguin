/*
 * Workloop timer that gates the touch bring-up.
 *
 * The touch thread cannot sleep: a kernel thread started from userland context
 * arms its deadline but is never woken in this port (NOTES 23:11). An
 * IOTimerEventSource on an IOWorkLoop does fire - that is how this framebuffer
 * gets its 60 Hz vsync - so the start-up delay lives here instead.
 */
#include <IOKit/IOService.h>
#include <IOKit/IOWorkLoop.h>
#include <IOKit/IOTimerEventSource.h>

extern "C" void touch_bringup(void);

class SweetTouchTimer : public OSObject {
	OSDeclareDefaultStructors(SweetTouchTimer);
public:
	static void fired(OSObject *owner, IOTimerEventSource *sender);
	bool setup(unsigned seconds);
	IOWorkLoop *fWorkLoop;
	IOTimerEventSource *fTimer;
};
OSDefineMetaClassAndStructors(SweetTouchTimer, OSObject);

static SweetTouchTimer *gSweetTouchTimer;

void
SweetTouchTimer::fired(OSObject *owner, IOTimerEventSource *sender)
{
	(void)owner;
	(void)sender;
	IOLog("SWEET TOUCH: timer fired, running bring-up\n");
	touch_bringup();
}

bool
SweetTouchTimer::setup(unsigned seconds)
{
	/*
	 * Hold a reference: the framebuffer keeps its workloop in a member and its
	 * timer fires at 60 Hz, so a workloop that nobody retains is the difference
	 * between a live timer and a silent one (NOTES 23:18).
	 */
	fWorkLoop = IOWorkLoop::workLoop();
	if (fWorkLoop == NULL) {
		return false;
	}
	fWorkLoop->retain();
	fTimer = IOTimerEventSource::timerEventSource(this, &SweetTouchTimer::fired);
	if (fTimer == NULL || fWorkLoop->addEventSource(fTimer) != kIOReturnSuccess) {
		return false;
	}
	fTimer->retain();
	fTimer->setTimeoutMS(seconds * 1000);
	return true;
}

extern "C" int
sweet_touch_timer_arm(unsigned seconds)
{
	if (gSweetTouchTimer != NULL) {
		return 1;       /* already armed once */
	}
	SweetTouchTimer *t = new SweetTouchTimer;
	if (t == NULL || !t->setup(seconds)) {
		return 0;
	}
	gSweetTouchTimer = t;
	return 1;
}
