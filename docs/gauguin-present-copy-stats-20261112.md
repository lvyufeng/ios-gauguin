# Opt-in CPU present-copy statistics

Patch 0221 adds `sweetfb_stats=1` as an **off-by-default diagnostic** to the
0297 framebuffer source. It does not change the timer rate, surface ownership,
GPU completion policy or panel mode. The candidate has not been booted on the
phone and is not evidence of a faster UI or physical refresh.

For each record passed to the existing CPU `present()` path, the diagnostic
counts attempted records, records with at least one nonzero-byte copy, zero-byte
records, copied bytes and layers, GPU read-guard attempts and refusals. A record
with copied bytes may still have skipped other layers; it is not necessarily a
fully correct frame. The measured guard interval includes acquiring the GPU
read protection and its checks; it is not pure lock wait or GPU execution time.
Copy intervals cover the existing `memcpy` loops. Both are CPU wall intervals,
not panel scanout or input-to-photon latency.

Eight upper-exclusive histogram bins are `.5, 1, 2, 4, 8, 16, 33.333333 ms,
infinity`. Every valid present attempt with at least one read guard contributes
to the guard histogram; every valid attempt with nonzero bytes contributes to
the copy histogram. Zero-work records cannot bias the latter downward. Invalid
or reversed-clock/overflow timing samples increment an invalid count and do
not enter either histogram, although their byte and outcome counts remain.
Aggregates saturate rather than wrap. The numbers are bucket bounds, not exact
percentiles; each sampled copy duration sums all copied layers in one present.

Output is emitted after the existing held-frame retirement or unheld record
free, at powers of two and then every 300 attempts. It contains aggregate
counts and histograms rather than per-frame records. Logging and timing can
still perturb future scheduling; compare an otherwise identical trace-disabled
control before drawing performance conclusions. The counters are not a
substitute for correlating touch, command, surface and swap identities, nor do
they establish a physical vblank, panel latch or tear-free image.

The source normalizes exactly to 0297 after removing the ten marked opt-in
additions. Local ARM64 framebuffer TU compilation and host ASan/UBSan checks
cover header arithmetic, zero-work samples, mocked actual `present()`/timer
behavior and existing held-surface and software-clock paths. These are mock
and compilation checks only: actual overhead, concurrent workloop behavior,
successful on-device copying, long-run stability and the full UI remain
unverified. Preserve the separately approved 0297 trial and require a new
specific authorization before any later diagnostic boot or marker write.
