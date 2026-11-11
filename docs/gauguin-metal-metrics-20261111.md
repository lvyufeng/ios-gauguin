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

## Complete image, not yet booted

Source `bdfabdcc9d71b30a77fd68b37693dd3ecca4cf68` is committed and pushed.
The fresh local native build and retained symbol/provenance checks passed in
182.69 seconds. The temporary image is 20,021,248 bytes, SHA-256
`31f23fe81d8609d8bb65846e6d9603977ce03c92865cc826fd088ba266e518fc`.
Its 603-byte command, payload padding, original assets, 6 GiB managed memory,
shim and DTB are verified. Fresh read-only checks match the actual post-0293
27 files, four directories and router targets. No userdata modification is planned.

Plan `5ef9423cec5835cf1f8723c8e6b7e786d0a61ce1bf489b1267389daecea1bd92`
requires fresh individual approval for one 13-byte recovery marker and one
temporary boot; only the touched marker bytes are restored on marker write or
readback failure. This trial has not run. Current storage is 436.5 GB with a
128 MiB trial reserve, below the 500 GB cap.

Timing limitations: CP pass intervals include flush/wait-idle. Above 64 passes,
the last profiling slot may include later passes. Missing hardware summaries
mean unobserved, while rounded zero remains possible for valid stamps. Frontend
CPU labels measure overlapping host wall-clock intervals, and logical presents
or kernel queue counters do not prove physical panel FPS.
