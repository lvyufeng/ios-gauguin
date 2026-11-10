# Pre-mount GCC scan trial ready for review, 0261

[GitHub Actions run 42920974546](https://github.com/lvyufeng/ios-gauguin/actions/runs/42920974546)
built the complete gauguin ARM64 DEVELOPMENT kernel at commit
`4964df4b368a5df807ec5c3338fd354c39fcdf15`. Job 130195437896 succeeded
at 23:17:20 UTC on 2026-11-10. Eleven focused host groups passed locally
and in CI, including the single-block writer and four UFS regressions.
DSH confirmed the complete link, 284 retained definitions, two new
scan log definitions and zero undefined symbols. Kernel size is
17,883,392 bytes and SHA256 is
`8051aca7ac0bbe29bc849daaf59108083a10272e618bb5dd407e6a81348c6b7e`.
The archived 5,339-file source matches the build manifest. The difference
from native 0260 is the previously reviewed four dxb build adaptations.

The temporary image is `gauguin-0261-scan1-premount-261001.img`, 19,955,712
bytes, SHA256
`316b0bd43c871ebc0a11c252181d62ada27156e66f8880533ef07681a43051ea`.
It is in `image/` under the private work directory
`research/tmp/gauguin-build255-worktree-20261111/research/tmp/dsh-scanlog-build-0261`.
Independent readback verifies the ten embedded kernel segments, five
firmware assets and padding, proven shim and DTB, managed RAM and PAS
zero tail. The complete 183-byte command requests GCC mode 1, diagnostic
run 261001, and pre-mount record output. Ordinary UFS writes, root writes,
normal console logging and USB gadget are off.

## Exact trial scope

One temporary fastboot boot would read the GCC display clock branches
and write its result to a single 4 KiB block in the existing userdata
diagnostic tail. The absolute LBA is 30,943,225. The normal iOS root is
never mounted in this path. The trial then requests a quick reboot.
Recovery currently has an empty boot command in misc. To return to TWRP
automatically, the trial sets the existing `boot-recovery` marker using
13 bytes at misc offset zero. The original bytes of both locations are
saved. The plan specifies no partition flash or retry.

The read-only preflight read the target and its two neighbors through both
the userdata and raw UFS devices, verified byte equality, and read back
the 194 old blocks in the separate 0240 HFS proposal. The HFS header also
matched. The original slot SHA256 is
`c8e452dc869a673c2a23511a8e80f576df8f46fe19739871a845126b31c35baf`.
The original misc first block is zero. The writer repeats these read-only
checks immediately before any device change and stops if they differ.
After return it checks the run ID and both neighbor blocks and repeats
the HFS readback.

The mocked trial state machine passed absent and mismatched authorization,
changed preflight data, and one authorized attempt. The approval-bound
proposal SHA256 is
`b9c831c20e93ce2300ab1a627fc57a947322a4ad9a181274b855a2f3337b0e07`.
The independent review SHA256 is
`ad69aa57b18acfa6f2080f6543dadcac3d929724926f2edb6b907fcbe6d3c4ec`.
No authorization, trial claim, device write, or boot has occurred.

DSH dispatch, read-only backup and artifact stage PIDs 60265, 60624 and
62038 exited 0 with 9, 6 and 24 unchanged pins. Artifact download,
qualification and packaging all exited 0. Both device access scopes
remain separate. The 0240 HFS installation still requires its own approval.
