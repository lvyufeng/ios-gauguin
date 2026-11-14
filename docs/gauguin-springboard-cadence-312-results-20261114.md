# 0312 result: HID consumer progresses; SpringBoard observer not seen

The approved one-shot completed and all four original files were restored.
It returned automatically to TWRP after 745 seconds; the kernel banner matched
the fixed 0312 image. Install and restore each wrote and read back 1,814,528
bytes across eight ranges. Misc's 13-byte marker was verified. No boot retry,
restore retry or recovery fallback was used. The final 31-file static comparison
passed, allowing only expected log growth. Independent readback verified all
four original logical and allocated byte images, HFSX identities/forks and
the original misc 4 KiB. Current root header is
`7faaeed238ab8ad51846767eb8e6f98ecfd1d8a6243196f998bfd514892c522d`.
The 0312 authorization is consumed; never rerun its executor.

## Input and drawing observations

The display-on gate passed with zero power-button pairs. All 13 generated
strokes and 442 reports completed in 32.775527 seconds, from 226.257649 to
259.033176 seconds in the CPU clock domain. Physical touch remains untested.

The selected four-second UI254 window contains 519 records, loss zero,
deadline stop and no capacity truncation. One queue, owned by PID 57
(backboardd), has 68 valid snapshots, capacity 16,384 bytes and a nonnull
notification port throughout. Its head changes between 67 adjacent snapshots;
notification attempts also advance by 67. This establishes consumer-index
progress, not a causal mapping from each report to a SpringBoard event.

C4 reports 31 completed buffers in the full tail and eight creations during
the scripted interaction. Fifteen adjacent creation gaps are 4.9–5.3 seconds;
the full-tail median gap is 5.011996 seconds. The selected four-second window
contains one creation, commit and completion, one SwapEnd and one present-end.
These counts are not physical frame-rate measurements; 60fps is not achieved.

## Missing SpringBoard observation

SpringBoard's actual dyld policy calls returned PATH mask 2 successfully for
mobile PID 26 and the protected executable. The new SB log tail is 966 bytes
and preserves the previous log exactly as a prefix. It contains startup
warnings but no observer activation, input, watch or run-loop rows. No other
captured text log contains those observer markers either.

The installed observer and both changed launch plists matched their planned
contents at postboot restore preflight. The native library includes the
`start_rate_trace` constructor and an `__init_offsets` entry. These checks do
not prove dyld loaded it or that initialization passed its early gates. Its
constructor can currently exit before producing an activation/refusal log.
Therefore zero input rows do not establish that SpringBoard received no touch.

Next inspect the actual SpringBoard exec environment and library initialization,
then restore the missing observation boundary. Historical backboardd work also
observed absent DYLD_INSERT at exec, but minimal xpcproxy environments alone
do not prove filtering and cannot establish the same cause for SpringBoard.
No new GPU or frame-rate policy was changed on this evidence.

## Receipts

Private evidence is `research/tmp/sb-cadence-312/execution/`.

- Result: `SpringBoard-observer-not-seen-root-restored`, restored=true,
  observer exit 0, executor diagnostic exit 1; SHA
  `5ad47a727c839e86e57da32c41bef81359e7efac17b3930ec6ae96b741ffaa0b`.
- Independent restore receipt SHA
  `8778cbbdac3aeb7c95897d5758a50ec746145ed2d3a0732506f13e21a144eb53`.
- Focused cadence summary SHA
  `17435f1b942acb8339e04789eb88dbf4352c186882ac6e163402b901bf1fbd59`.
- Actual direct approval receipt SHA
  `12a2bbe38cba01e37e9a679a419f8b5f1d77f7ef0066f3c5ee870d0eaca65339`.

Executor PID 20172/session 58470 and observer PID 21183 are terminal. Preserve
the new restored capture, prior backups and all pinned inputs; future plans
must use the new root header and fresh preimages.
