# 0314 result: SpringBoard receives input and has multi-second main-thread stalls

The authorized 0314 boot completed once and returned automatically to TWRP
after 746 seconds. Its kernel banner matched the fixed image. The temporary
four-file installation and restoration each wrote and verified 1,814,528 bytes
across eight ranges. The misc marker was 13 bytes. No boot retry, restore retry
or recovery fallback was used. The final 31-file static comparison passed,
allowing expected log growth.

An independent read verified the four original logical and allocated files,
their CNIDs/forks, and the original misc 4 KiB. The current root header is
`3c5af5b175dabaa759a1ff22523a103d30cfe375a421f7757a2f37f80fea672e`.
0314 permission is consumed. Executor PID 78096/session 1853 and observer PID
78980 are terminal; do not rerun them.

## The observer now loads

The actual exec reported outcome 1, reason 0, added 1, envc 11 and effective/
real UID 501. Caller PID 1, flags `0x41c`, init 1, shadow 0 and original parent
PID 1 establish the launchd spawn-child case missing in 0313. Its incoming
insertion variable was absent. The new guard admitted the protected child and
added the observer path. Later dyld policy checks also passed.

SpringBoard emitted the reused library's `constructor=313` marker, all four
rate/loop activation flags, and `send_event=1`. The 313 constructor number is
the library version; the kernel was the independently checked 0314 image.
The new SpringBoard log tail is 1,379,299 bytes, with 16,495 observation records,
no reported lost rows, metadata errors or write errors. Old log prefixes are
preserved.

## Input reaches the desktop process

Exactly one power press/release woke the initially off display. The on-state
gate and settle interval passed. All 13 strokes and 442 synthetic reports ran
from 226.277680 to 259.048340 seconds, lasting 32.770660 seconds. The selected
kernel window again showed 67 queue-head changes over 68 consistent samples
on backboardd PID 57's 16,384-byte queue.

During the scripted interval, 77 public touch callbacks entered SpringBoard,
all on the main thread, and all have matching normal returns. There are no
unpaired entries or exits. Their median wrapper duration is 1.774 ms, but two
last 4.561708 s and 5.013756 s. These spans include the observer's metadata
collection and forwarding wrapper; they are not a sampled stack attribution.
Windows include `SBHomeScreenWindow` (35 entries), `_UISystemGestureWindow`
(39) and `SBCoverSheetWindow` (3); 28 entries identify `SBIconListView`.
This proves public input delivery. It does not prove every synthetic report
became a separate event, gesture acceptance or physical touch latency.

There are 117 main-loop turns overlapping the script. Several spend seconds
between wake and the before-CA observer; four spend 3.84–4.69 seconds between
the before/after-CA observers. The independent watch covers the entire script:
15 samples are in the wake/body phase and 17 in the before-CA phase, with ages
up to 4.67 seconds. These are main-thread progress observations, not CPU stacks
or proof of a particular blocking syscall.

## The long gaps align with renderer work starting

Four long CA-observer brackets end within 419 microseconds of a C4 creation
timestamp, and before that command buffer is committed or completed:

| Bracket duration | C4 creation minus bracket end | Commit after bracket end | Completion after bracket end |
| --- | --- | --- | --- |
| 4.558078 s | −123 µs | 5.311 ms | 27.387 ms |
| 4.689667 s | +22 µs | 7.448 ms | 20.147 ms |
| 3.840996 s | −419 µs | 9.301 ms | 23.160 ms |
| 3.843831 s | −106 µs | 7.584 ms | 25.677 ms |

This timing favors investigating CA client/server transaction delivery and
renderer wakeup waits. It does not identify the blocking function or prove
causality. The earlier actual-OS static inspection found synchronization
timeouts, which are now specific stack/call-span candidates. No timeout value
should be shortened solely because it resembles the measured interval.

C4 still has 27 completed-buffer log records, six created during the script,
and fifteen 4.9–5.3-second creation gaps; the median is 5.013188 s. Its log is
emitted at completion and cannot exclude other uncommitted/incomplete buffers.
The long CA brackets end before these GPU completions, so their entire duration
cannot be attributed to execution of those particular GPU jobs.

The script also records one display-link request for 30 fps, eleven range
requests and 53 animation requests, 49 with maximum zero. Requests/defaults
are not the effective frame rate of the entire compositor. Neither forcing
all these values to 60 nor the software present clock establishes 60fps.

## Next action and preserved candidates

Locate the main-thread wait with bounded PC/call-stack or call-span observation
during the already reproduced long turns. Distinguish the CA synchronization
path from other observers and scheduler stalls before changing wakeup policy.
No new device write is authorized yet; use fresh preimages and the new root
header for a future plan.

The separate C4 handler-wait correction (`dc032fd`, binary `2f7891bf…`) remains
uninstalled. 0314 used the fixed original C4 binary `560284dd…`; the experiment
did not silently incorporate that correction or the pending 0311 frame fix.
Full GPU-backed smooth 60 Hz operation remains unachieved.

Private evidence: `research/tmp/sb-spawn-314/execution/`.

- Result state: `SpringBoard-cadence-observed-root-restored`, executor/observer
  exit 0. SHA256 `840af1b22c1342d07d6c9ff87b1262825063a062e17779d506edf6af0f891954`.
- Independent restore: `df9c4f901f1f1cd97606bbbb8b1798e562a49cb29be26571320999fc437498cb`.
- Focused cadence summary: `94e0de597d6b59d37cb763d9486344d6a7e194f63ae88aa2ba2857bacb790d92`.
- Actual approval: `48d23f298d60138d31d3e36a381103d1fd819fa65a6d9e6076eaa6054dbe1064`.

Preserve original backups, current 0314 restored capture, all fixed inputs,
the uninstalled C4 candidate and the user's unrelated `mkadt.py` edit.
