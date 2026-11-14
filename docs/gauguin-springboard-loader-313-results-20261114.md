# 0313 result: exact loader rejection found; original files restored

The approved 0313 boot returned automatically to TWRP after 745 seconds and
matched the fixed image banner. Install and restore each wrote and read back
1,814,528 bytes across eight ranges. The 13-byte misc marker was verified.
No boot retry, restore retry or recovery fallback was used. The final 31-file
static comparison passed, allowing expected log growth. An independent read
verified all four original logical and allocated files, their HFSX identities
and the original misc 4 KiB. Current root header is
`0605fd307cdb25e0a76fc28b1ae93f181b16b57368c6caee882f9de5151cb34b`.
The 0313 one-shot authorization is consumed; do not rerun its executor.

## Actual input and drawing

This time the display was initially off. Exactly one power press/release pair
was sent; display-on observation and the one-second settle gate passed. All
13 synthetic strokes and 442 reports completed in 32.771470 seconds, from
226.331843 to 259.103313 seconds. This qualifies the scripted wake branch, not
physical touch or visual unlocking.

The selected four-second trace has 506 events, loss zero, deadline stop and
one unpaired span. The backboardd PID 57 queue again has 68 consistent samples,
67 head changes, 68 nonnull-port observations and 67 notification attempts.
Consumer progress is established; SpringBoard receipt remains unobserved.

The completed C4 log has 28 buffers, six with creation times during the script.
Fourteen adjacent completed-buffer creation times differ by 4.9–5.3 seconds;
the median full-tail gap is 5.010485 seconds. One create/commit/done and one
SwapEnd/present-end fall inside the selected window. The C4 line is emitted
on completion, so these records do not exclude uncommitted or incomplete
buffers. These are not physical frame counts; 60fps remains unachieved.

## Exact observer loading boundary

The actual SpringBoard exec reported `insert_before=0`, `expected_before=0`,
`envc=10`, `added=0`, `outcome=6`, `reason=9`. Thus the insertion variable was
absent at the target exec boundary, and the new loader rejected process
provenance before querying credentials. The printed UID/RUID value 4294967295
is an uninitialized sentinel for that refusal path, not the process's UID.
Later AMFI calls for protected PID 26 report UID/RUID 501 and PATH-mask success.
The observer has no constructor/activation rows; the SB log tail is 966 bytes
and preserves its previous prefix.

The reason-9 branch accepts the current process or a matching exec shadow;
it has no branch for a child directly spawned by launchd. Kernel source confirms
that ordinary `posix_spawn` selects the new thread's child proc and marks
IMGPF_SPAWN while the calling proc remains the parent. The current trace does
not print caller PID/flags, so direct launchd spawn is the source-backed next
case to handle and observe, rather than a fully logged runtime attribution.

Credential inspection needs care: the spawn VFS context captures `proc_ucred(p)`
before spawn attributes can adopt new credentials. A future probe should use
a referenced credential from the actual target child and a matching temporary
VFS context for its ACL check. This keeps the mobile-only check meaningful for
the new launchd-child branch. Do not simply admit any foreign proc or a root
credential. Add explicit caller/flags/identity diagnostics with the fix.

The separate [20H392 synchronization inspection](gauguin-five-second-sync-paths-20261114.md)
found actual five-second deadlines and confirmed the CA observer order. It
does not prove which waiting path caused the handset's completed-buffer gaps.

## Receipts

Private evidence is `research/tmp/sb-loader-313/execution/`.

- Result: `SpringBoard-observer-not-seen-root-restored`, restored=true,
  observer exit 0, executor diagnostic exit 1; SHA
  `3e07e32633729b3d7f34ae175388debe834479fb904c6db80be66eb3b3e7c574`.
- Independent restore SHA
  `3d8c0d7adedde9477a0452fcf5433b62076846ebf4b8fa932f370727b6cad92e`.
- Focused summary SHA
  `3a493b2360b3670ffa50c16cd7aba0b85c6bf3f5e6c5c8025a990ef016d0cc9c`.
- Actual direct approval SHA
  `0cc1711cc4cfb63f0c5d8ac139995a8368a9ac46da2c8a58f67453ce3e90bd89`.

Executor PID 46732/session 85430 and observer PID 47978 are terminal.
Use fresh preimages and the new header for any future trial. Preserve the
original backups, current rollback capture, fixed inputs and user edits.
