/*
 * Init watchdog decision, factored out of sweet_ufs.c's log thread so it can
 * be tested on the host.
 *
 * The log thread runs every `logms` milliseconds whatever the init thread is
 * doing. It counts the ticks during which the init tail has not finished and
 * asks this function whether to print a warning.
 *
 * Keeping this pure (no I/O, no globals) is what makes the behaviour testable;
 * the two defects found by simulation in NOTES 2026-11-03 (20) - a false alarm
 * on a healthy boot and a stale step name - would both have been caught by
 * tests/test_watchdog.py.
 */
#ifndef SWEET_INIT_WATCHDOG_H
#define SWEET_INIT_WATCHDOG_H

#include <stdbool.h>
#include <stdint.h>

/* Ticks of grace before anything may be reported (~8 s at logms=200). */
#define SWEET_WD_GRACE_TICKS   40u
/* Otherwise repeat every this many ticks (~10 s at logms=200). */
#define SWEET_WD_REPEAT_TICKS  50u

struct sweet_wd_state {
	uint32_t ticks;          /* ticks elapsed with the tail unfinished */
	uint32_t since;          /* ticks since the last report */
	const char *reported;    /* last step name this watchdog printed */
};

/*
 * Call once per log-thread tick while the init tail is unfinished.
 * `step` is the step currently being entered.
 *
 * Returns true when the caller should print a warning naming `step`. The state
 * is updated only when it returns true, so a silent call leaves `reported`
 * alone and the next real report still names the right step.
 */
static inline bool
sweet_wd_should_report(struct sweet_wd_state *s, const char *step)
{
	s->ticks++;
	/*
	 * Strictly greater: at exactly the grace boundary the tail may be one
	 * tick from finishing, and warning there would be a false alarm on a
	 * boot that is merely close to the limit.
	 */
	if (s->ticks <= SWEET_WD_GRACE_TICKS) {
		return false;
	}
	if (step != s->reported) {
		s->reported = step;     /* the tail moved: say so immediately */
		s->since = 0;           /* and restart the repeat countdown */
		return true;
	}
	if (++s->since >= SWEET_WD_REPEAT_TICKS) {
		s->since = 0;           /* still stuck on the same step */
		return true;
	}
	return false;
}

#endif /* SWEET_INIT_WATCHDOG_H */