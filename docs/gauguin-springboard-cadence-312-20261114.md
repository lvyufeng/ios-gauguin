# 0312: locate the five-second producer gap

0310 generated only nine C4 command buffers during its 32.768-second scripted
interaction. Seventeen adjacent creation gaps in the full boot log were
4.9–5.3 seconds. Its selected four-second capture had 68 accepted HID queue
reports, one C4 creation, and no completed presentation. Queue acceptance
does not establish SpringBoard receipt. The phone is restored in recovery;
0310 approval is consumed. No new trial has run.

## Read-only evidence and reference

The current HFSX header is
`492c57e711dcb89e40330f8c4ffce88fc63ceec09edb519ad3e24dc75740c8c0`.
Read-only capture found no CA_FORCE_TIMER or CA_HEARTBEAT_RATE in the actual
SpringBoard/backboardd launch jobs. The SpringBoard log has startup warnings,
but no input or scheduling instrumentation. Its appended portion spans
multiple startups and cannot be attributed to one boot or to the delay.

[HakiOS issue 40](https://github.com/oosexgang/hakios-xnu-kernel/issues/40)
describes CA_HEARTBEAT_RATE raising a 60 Hz application ceiling for high-refresh
operation. It does not explain a five-second producer gap. The pinned HakiOS
`inject_sb.c` places run-loop observers around order 2000000; its stall monitor
suspends and unwinds the main thread. This observer instead samples atomic
milestones from a background thread without suspending or waking the main
thread. The CA observer order remains unverified on this device's iOS build.

## Observation points

- Patch 0234 appends UI254 kind 31: userclient registry identity, owning PID,
  queue head/tail/capacity, enqueue result, port presence and notification
  attempts. A head change on the same consistent queue shows consumer-index
  progress. An unchanged head can conceal wrap; notifications are attempts.
- The opt-in SpringBoard library records public `sendEvent:` touch entry and
  return, UIEvent timestamps, touch phases, and view/window class names.
  It forwards the original event exactly once, preserving exceptions. It
  records no touch coordinates, typed text or key data. This observes UIKit
  dispatch, not raw HID receipt or successful gesture recognition.
- Four main-loop milestones and one-second background snapshots distinguish
  last-before-wait, after-wake, before-CA and after-CA observations. These are
  milestones, not stack samples, CPU occupancy or proof of sleep.
- Existing CAAnimation/CADisplayLink request observations remain read-only.
  No display link, timer wakeup, frame-rate override or new GPU policy is added.
- `analyze-sb-cadence.py` aligns the three logs, including callbacks that start
  before a long C4 gap and return after it. Loss, write failures, metadata
  failures and missing activation prevent an unsupported no-input conclusion.

The kernel's default-off `sbp=1` switch permits only dyld PATH mask 2 for the
protected root-owned, nonwritable SpringBoard executable and mobile UID 501.
It preserves the prior backboardd gate and does not grant GPU privileges.
The observer occupies the existing EAGL library slot only during an approved
trial; the original bytes and launch jobs must be restored afterward.

## Offline validation

Private receipts are under `research/tmp/sb-cadence-312/`:

- Actual observer body and Objective-C method installation: 117 ASAN/UBSAN
  checks, including inherited/own methods, ABI refusal, exceptions, reentry,
  contended/full logging ring and unchanged event forwarding.
- Actual AMFI policy/dispatcher under typed host seams: 47 cases passed.
- Actual queue/enqueue/snapshot bodies under typed IOKit seams: 20 checks.
- Native ARM64 compilation passed for AMFI, HID userclient and queue against
  the pinned 0301 build configuration, with unchanged input/reference files.
- Native UIKit library build, ad-hoc signature and strict verification passed.
  Final slot library is 89,168 bytes, SHA
  `c829d5568ebf137b152e743db2e3147527b6d9bafddf43032cf4751e9d0ddb03`.
- Patch 0234 replayed exactly onto frozen 0310 source; reverse dry-run passed.
- Input/rate/queue parsers and actual UI254 host capture tests passed. Joint
  parsing of 0310 reproduces 17 five-second gaps and leaves missing SB input
  observations unknown.

These checks do not qualify loading or behavior on the phone, gesture response,
physical refresh rate, or 60fps. Next prepare a combined C4/SpringBoard trial
and its complete rollback before requesting individual write approval.

## Storage

After a 60 MB offline admission, 234 duplicate non-log blobs in completed
0299/0300/0309 fresh/installed/post captures were retired: 334,105,572 logical
bytes. Each matched a retained 0310 static file by SHA256 and byte count.
Original partition backups, all restored captures, logs, receipts and paths
pinned by ready plans were preserved. Private cleanup manifest SHA:
`d592cd4172c5bfcc2d3c3c64d2dd4407fa402a940daac6d2a88fbb027e70fe3a`.
