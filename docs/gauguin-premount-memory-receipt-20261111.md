# Pre-mount ABL memory report, 0266

The diagnostic serializes the validated ABL handoff before mounting the
iOS root. `sweethandoff=1 sweethandofflog=1 sweethandoffid=<run>` selects
the capture and its exact run identity. It requires ordinary root and UFS
writes to be off and the scan log selector to be inactive. An opted-in
diagnostic returns through the existing quick reboot path before mount.
The console-only handoff report still uses `sweethandoff=1` by itself.

The report uses the same reserved userdata block as the existing scan
receipts at absolute LBA `30943225`. Both writers use the same partition
geometry check, DMA ownership guard, single `WRITE(10)` and cache sync.
The memory path builds the report before taking the UFS DMA lock. Its
boot and one-block overwrite require a separate, exact authorization.
[Reserved-slot design](gauguin-pre-mount-scan-log-20261111.md).

## Receipt and reader

`GAUHRAM1` is a 4,096-byte little-endian block. The 80-byte header carries
the encoded length, run ID, status, five inventory counts and the original
FDT SHA256. A complete report contains eight handoff ranges, then the
banks, header reservations, fixed reservations, named dynamic pools and
their allocation windows. Names are limited to 63 printable characters.
The final 32 encoded bytes are SHA256 over the preceding bytes. The
remaining block bytes are zero. A failure, including an inventory too
large for one block, writes a status-only report with a digest.

`tools/gauguin-read-memory-handoff.py` accepts a saved block and the
expected run ID. It rejects an incomplete block, stale run, digest or
padding mismatch, invalid ranges and inconsistent pool window indices.
The output identifies dynamic pools as unresolved. A report provides
handoff observations for later ownership analysis. Lower page admission
and DMA use still need physical qualification.

## Verification

- 0265 full ARM64 kernel linked successfully in CI run `42929203205`,
  job `130223371043`, ending at 00:20:11 UTC on 2026-11-11. The 5,342-file
  source archive matched its manifest, all 11 focused CI checks passed,
  and the link had zero undefined symbols. DSH PID 76552 downloaded and
  qualified the exact artifact in 42.736 s with 869 pinned inputs. Kernel
  SHA256 `69fca4adda400014b32f597c97fba53f05150d2aad5086b4746b0eaad69907cc`.
  [0265 CI](https://github.com/lvyufeng/ios-gauguin/actions/runs/42929203205).
- 0266 source commit `063a51c1db6ecfc99d6d04ef086487b42641146d` on
  `codex/gauguin-handoff-receipt-20261111`. Patch 0221 SHA256
  `5e889e1faa4c6613cafa3495546d58a09d4e68cb66fb66ee01f15ac71e8289b9`.
  DSH first identified a mock assertion that counted a timed-out write as
  requiring a sync. The corrected fixture tracks the most recent synced
  request. Dispatcher 75941 passed in 10.669 s with 24 pins, strict patch
  replay, three host groups and four native ARM64 translation units.
- The C encoder generated a 2,544-byte receipt from the actual shim and
  reader model. The recovery-side parser round trip and six malformed
  block tests passed. The writer mock verified the exact LBA, one 4 KiB
  write, sync ordering, conflicting profile rejection and DMA failure
  guards. 0266 source SHA256
  `ced9350a84e3262c8da3a8848edf6da2ca82e6c604862dc6d27b057c59262063`.
- DSH PID 76234 completed 11 local focused checks, pushed and dispatched
  the 0266 full build with ten unchanged pins. The capture-enabled package
  and independent readback steps are staged under
  `research/tmp/dsh-handoff-receipt-0266` in the active worktree.
  [0266 CI](https://github.com/lvyufeng/ios-gauguin/actions/runs/42930522816).

No phone command, boot, partition write or physical memory admission
occurred. The existing 0261 and 0240 approval scopes remain independent.
