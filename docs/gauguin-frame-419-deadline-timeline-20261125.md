# Gauguin 0419 60 Hz display deadline trial

The kernel keeps the 0418 post-store completion timestamp and tracks the same
33-second drag as 0417. It scores the 30 full seconds following the two-second
warm-up. The 7.2 ms Core Animation work duration, operating point, 60 Hz panel
mode, private copy limit, CRC preimage and original-front drain remain those
of the 0417 plan.

The optional diagnostic, enabled with the same sustained profile and
f419=1, uses a parallel 45-second trace. It records the actual observation of
the native GPU fence and post-cache visibility for an admitted display ticket.
The display workloop records which generation and surface version were
promoted. A private copy carries the exact attempt, source and requested
presentation timestamp, joined to the existing post-barrier, issue and latch
receipts. The aligned Core Animation callback records its predicted DPU
edge, scan number and ready deadline. The capture has a 12,288-record limit
and a 786,432-byte wire limit. Timeline exhaustion does not stop scanout or
the compact physical CRC trace.

As in Android FrameTimeline, compare expected presentation against measured
presentation under the same writer and generation. A requested target is
matched only if the predicted edge and hardware edge bracket agree within
1 ms. For a repeat with no such target, the next observed latch gives a
conditional timing comparison. A new buffer with the same CRC is counted as
repeated content. The GPU completion observation can follow the device's
actual execution completion, and copy time includes the store barrier.
[Android FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)

The trial stages the same six reversible files and changes only the helper's
kernel identity and signature. The same one temporary boot, hardware CRC
writes, display register bound, root rollback and independent readback
apply. Score only after verified restoration. The Spotlight keyboard
workload is a separate comparison.
