# 0419 native completion timing

Use the same 32-second SpringBoard marker, 0419 row copy, 7.2 ms work
budget, GPU profile and 60 Hz route as 0423. The ARM64 link replaces the
GPU client and display trace producer. Only the passive selector enables
the new writer timing and reads the already mapped completion word in the
existing display poll. The normal readiness worker, caches, GPU lease,
copy and flip take the same path. The passive sampler does not schedule
another work item or change a register.

Bracket the native issue call against the same writer's observation.
The last pending raw load gives a conservative lower bound for physical
completion. The first matching load or the original guarded observation
provides the upper bound. Join by writer ticket, surface version and
native fence. Keep confirmed target scans separate from conditional
comparisons with the next latched frame. Preserve the full paired output
CRC count even if the Gray-code calibration is unavailable.

The one-boot and six-file restoration procedure is shared with 0423.
Independent restoration and log-prefix verification precede scoring.
