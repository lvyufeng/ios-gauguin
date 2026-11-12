# 0301 UI timeline analysis, prepared offline

The 0301 phone trial is still awaiting its own partition-write approval. This
analyzer is read-only and does not change the pinned 0301 image, install plan,
or trace parser. The 0300 logs do not contain the new UI254 ring, so they
cannot be used for a touch-to-frame result.

HakiOS's [Metal completion hook](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetalCA.m#L6257)
prints `tl: M made US committed US done US gpu US` when `touch_lat=1` is set.
Its [`hm_now`](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/HakiosMetalCA.m#L372)
converts `mach_absolute_time` with `mach_timebase_info` to seconds. The 0301
kernel [UI254 header](../xnu/patches/0224-gauguin-causal-ui-trace.patch)
records the same clock's numerator and denominator. `gpu` is a duration, not
an absolute timestamp. The hook's timestamp text is rounded to whole
microseconds, so close ordering across userland/kernel may have a roughly
one-microsecond ambiguity.

After an authorized 0301 collection, run:

```sh
python3 tools/analyze-ui-timeline.py KERNEL_LOG BACKBOARDD_LOG --out TIMELINE.json
```

The tool requires a complete, validated UI254 header/events/footer and
rejects an invalid clock or malformed `tl: M` line. It aligns changed physical
touch reports, explicit HID queue outcomes, Metal made/commit/done, SwapEnd,
and presenter completion. It reports gaps between successive frame-production
points, as well as the next observed point after each physical report.
`hid_begin_to_queue_us` starts at HID dispatch, while `next_*_us` starts at
the physical report timestamp. If that timestamp is invalid, those gaps are
null. A queued digitizer event with `flags=0` is counted as **rejected** even
though its trace record has kind `hid-enqueue`; the actual queue result is in
the flag.

The JSON marks kernel record loss, capacity truncation, unpaired spans, and
missing Metal records. A null future gap is right-censored at the four-second
window; an empty Metal slice could mean no produced buffers, inactive hook,
different-process logging, or lost userland output. Neither proximity nor a
successful HID queue push establishes which SpringBoard frame consumed a
touch. SwapEnd and presenter completion are not panel latches, so this tool
cannot certify visible 60 fps. A SpringBoard request observer and optical or
scanout evidence remain separate steps if the timeline is sparse.

`python3 tests/test_analyze_ui_timeline.py` passes synthetic alignment,
accepted/rejected queue, invalid physical timestamp, loss/missing Metal and
malformed-record checks. This is an offline contract test, not a phone result.
