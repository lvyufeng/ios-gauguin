# 0419 visible refresh probe

Run the 32-second workload on the byte-identical 0419 kernel and its original
60 Hz, 7.2 ms work phase, GPU profile and display ownership. Set the existing
SpringBoard diagnostic loader flag and reuse its reversible library slot.
The signed library runs the same 12-bit Gray marker and CADisplayLink as the
app in an opaque, non-key test window. The existing synthetic unlock and drag
still delimit the kernel trace. The marker window covers the Home Screen
before the diagnostic drag. Treat this as a SpringBoard-hosted workload.

Before sampling, the window holds the base symbol, all 12 single-bit
symbols and two independent combination symbols, then returns to base.
Require stable paired controller CRCs and a unique mapping across all 4,096
IDs. Verify the mapping against the held combinations and require increasing
decoded IDs from this run's timestamped callbacks. Score the central 30
seconds in complete fixed and rolling windows. Save the callback counts,
displayed IDs, skipped IDs, repeated scans and joined kernel timing. A
failed calibration leaves the marker's visible cadence unqualified.

Use the existing single temporary boot, CRC cleanup and independently
verified six-file and misc restoration. Score only after the readback.

Run the Home Screen pull-down and warm keyboard separately with physical
touch. Match physical contact and confirmed output timing. A full-screen
CRC transition alone cannot establish that a particular character appeared.
