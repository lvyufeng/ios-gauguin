# Isolated Metal desktop frontend candidate, 0244

Source commit `0d9f05f52bc449dadf7da13c61fdfa76dcf3f5d0` on
`codex/gauguin-metal-desktop-20261111` adds a separate experimental compositor
frontend above native clock candidate 0242. It is not installed and has not
run on the phone. MAIN's physically qualified kernel and installed root remain
unchanged.

## Implemented connections

`prepare-hakios-metal-ca.py --profile gauguin-ca-desktop` applies a sixth patch
after the qualified FP16 frontend. Its separate overlay admits only backboardd
with real/effective uid 501, OS 20H392 and exact single boot selectors
`sweeteagl=2 gmt=2 sweet_dyld_probe=1`. Other processes, root, duplicate or
conflicting selectors and an alternate M2V backend are refused. The existing
kernel still independently enforces its protected compositor identity,
single-owner policy and released-root fence requirement.

The original twelve method/two ivar ABI checks remain. The candidate requires
its own mobile-owned 0700 cache at
`/private/var/mobile/Library/Caches/gauguin-metal244` and clears inherited cache
and shader-seed environment values. Cache persistence and initialization have
not been exercised in backboardd.

The desktop compatibility experiment selects private limits profile 1 and
reports Apple1/Apple2/Common1 to the framework. This follows the actual MPS
family checks and the reference integration; it does not certify those public
families. Unsupported operations still fail explicitly. Native FP16 selection
reuses actual 0239's qualified A619 core/LPH shader route instead of leaving the
root probe's per-instance enable handshake as an unreachable desktop gate.
The new desktop still needs its own pixel and operation acceptance.

The formerly refused buffer upload now supports a bounded snapshot for one
actual 20H392 QuartzCore call. It checks the framework path, Mach-O UUID
`9e40b2eb260c3af1ae45a1a551a8c1b9`, ASLR-adjusted return offset `0x200390`,
nonzero/nonoverflowing bytes, at most 64 MiB and the observed zero resource
options. It copies initial bytes and preserves the deallocator through resource
release. Later CPU/GPU writes are not shared; all other no-copy buffer callers
remain refused. The caller binding narrows the upstream workaround to the
current decoded-image upload. It does not qualify general no-copy semantics or
prove the cause of earlier EAGL image defects.

The bundle is named `GauguinMetalDesktop.bundle`. All eighteen frontend
Objective-C classes use a `GauguinDesktopMetal` prefix, preventing collisions
with the retained root diagnostic classes if both bundles are loaded. Its
principal class is `GauguinDesktopMetalDevice`. The builder records the intended
system bundle path and `MetalPluginName`/`MetalPluginClassName`; it performs no
installation or kernel publication.

## Software evidence

DSH final software stage v4, PID 82015, exited 0 in 5.813922 seconds with 43
unchanged pinned inputs. It verifies:

- All six old profiles generate byte-identical sources against 0242, including
  the existing root FP16 diagnostic.
- 2,586 admission, uid/version, caller UUID/offset, range and option boundary
  checks pass under ASan/UBSan.
- The actual extracted upload method and original buffer deallocator/setter
  pass host allocation-transport checks for snapshot contents, later caller
  changes, retained references, exactly-once callback, allocation failure,
  rejected admission and a nil callback. Admission in this fixture is modeled;
  it is not a QuartzCore or GPU execution test.
- The old diagnostic still refuses the upload. Applying the positive desktop
  expectation to that old method functionally fails with exit 42, as intended.
- The complete arm64 iOS 16 bundle links, signs and verifies. All eighteen
  class exports are renamed; no original `HakiosMetal` class remains defined.

The final native binary is 428,368 bytes, SHA256
`dab751c31c62154052194f113c6326873dec05e071a531c8cde15e422aa9db32`,
linked to the unchanged qualified core
`8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1`.
Four compiler warnings remain: deprecated feature-set API/type, its omitted
declaration in the local private superclass interface, and the now-unused FP16
probe hash helper. Actual 20H392 metadata contains the superclass selector;
this does not replace runtime verification.

DSH ABI stage v1, PID 82384, exited 0 in 9.564280 seconds with 52 unchanged
pins. It resolves 554 core/frontend imports against the fresh verified 20H392
backup, including reexports from 40 cache images. No strong or newly unresolved
weak import is missing; the five preexisting optional M2V hooks remain disabled.
There are no added frontend imports. This is static compatibility evidence.

Codex independently rehashed both final stage input sets/logs and the artifact,
and disassembled four native entries. The upload method passes its original
link register to the caller check before any helper call. The profile and FP16
methods compile to the intended values. These checks do not prove system
discovery, cache behavior, real uploads or desktop rendering.

Private evidence: `research/tmp/dsh-desktop-0244-profile` in the 0244 worktree.
`review244-v1.json` SHA256:
`a56bc2330b1fe8669ae0e6ce500a049ee6f1b83648ac38815d6f102c2b545def`.
The earlier v1 invocation rejected a missing cwd-specific dispatcher pin before
launch; v3 invoked a missing profile after an authoring count assertion, also
before launch. Both outputs remain. V2's first successful build preceded class
isolation; v4 is the final qualified source/build, not a relabeled old artifact.

## Remaining integration

The current installed root job runs `gauguin-metal-frontend-probe --metal230`.
Its existing diagnostic profile requires `sweeteagl=1 gmt=1`, whereas this
candidate requires mode 2. The kernel compositor needs six root native fences
and a released GPU owner. Consequently, simply publishing the new plugin now
would not provide a valid bootstrap. The next source task must coordinate a
mode-2 root qualification companion, compositor readiness and discovery timing,
preserving the old diagnostic. Metal's per-process device discovery must not
cache a premature nil device before the GPU handoff.

Kernel plugin publication, compositor read-only task import, actual shared
output, producer completion and presentation still require integration and
physical qualification. The held/phase candidates 0241/0242 have not run either.
Future acceptance must cover populated icons/widgets, color/effects, repeated
lock/unlock and app transitions, then sustained measured 60 Hz and physical
90/120 Hz. General app Metal/no-copy support and the remaining phone peripherals
remain within the full goal.

Pending 0240 is unchanged and still awaits the genuine write reply. Do not
repeat its existing question or boot another image and stale its root delta.
Its paired physical 0239 kernel must run first once that reply arrives. This
milestone issued no device command, write, reboot, CI build or push.
