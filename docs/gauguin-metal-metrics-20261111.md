# Diagnose persistent desktop latency

0293 restored normal desktop graphics, but the user reports unchanged lag.
Its strict full-trace check failed on an interleaved submission record; the
original evidence remains failed. Independent checks retain the initial eight
offscreen pixel stages and owner handoff without claiming desktop pixel or
physical frame-rate qualification.

Patch 0218 changes only the sampled submission logger. It frames the existing
line with newlines and uses one bounded console reservation, preserving the
persistent mark payload and flush. The console entry point uses the exact OSFMK
prototype, which is not exported in BSD headers. This local path bypasses the
printf secondary os_log output. Early, panic and unbuffered writers can still
interleave; strict parsing remains required. Oversized future callers have only
a best-effort fallback.

The actual-emitter harness reproduces the old strict-parser failure beside an
unfinished IOK message. It verifies the candidate bytes, one-call boundary and
persistent-mark behavior. Native ARM64 compilation verifies the real declaration.

The diagnostic boot command removes only redundant `sweetreboot=0` and appends
bare `metal_fps`, shrinking 607 to 603 bytes while retaining `-noprogress` and
all other tokens. Tests execute all nine real kernel consumers and the installed
frontend flag reader, including a positive reboot-control counterexample. The
installed frontend already provides CP counter timestamps at 19.2 MHz; this
requires no userdata update. CPU submission envelopes, held-frame counters and
software callbacks remain distinct from actual GPU pass times and scanout.

This is diagnostic instrumentation. It does not establish a speedup, physical
60/90/120 Hz, or daily usability. Timing results must account for profiling cost.
