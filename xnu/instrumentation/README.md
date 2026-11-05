# Instrumented kernel sources, preserved

These four files are **copies** of the instrumented sources from
`.deps-cache/xnu-patched-0082-2/`, which git ignores and which
`deps/build-macos.sh` rebuilds from `xnu/patches`. Without this directory the
instrumentation added in rounds 115-152 would be destroyed by the next
`deps/apply-patches.sh` run.

| file | what it carries |
| --- | --- |
| `SweetFramebuffer.cpp` | colour list on the `vsync=` line, non-black bounding box, the one-shot ASCII panel map, `AGXAccelerator` method logging |
| `SweetHID.cpp` | caller name on GPU method logs, `deduped` diagnostics, explicit zeroing of `SweetHIDTouch` state |
| `sweet_touch.c` | `sweettap` / `sweettapdelay` injected tap on its own `thread_call`, `IOSleep`-loop bring-up delay |
| `sweet_ufs.c` | `sweetufsquiet=1`, which silences the per-command UFS line (84 % of the log) |

## Status: verified or not

**Verified on hardware:**

- `sweetufsquiet=1` - log drops from 16,910 to 1,695 lines (round 115)
- ASCII panel map - shows the centred solid mass (rounds 140-142)
- colour list - `ffffff b7b7b7 818181 bfbfbf 4d4d4d`, identical over five boots (round 136-146)
- non-black bounding box - `x=200..832 y=1037..1378`, identical over five boots
- `sweettap`/`sweettapdelay` - `touch 0 down -> dispatched` reaches the HID
  client, and SpringBoard does not react (rounds 131-134)
- `deduped` diagnostics and the state zeroing - compile and run

**NOT verified:** the caller name on GPU method logs (`gpu_who` in
`SweetFramebuffer.cpp`). It compiles and links, but no boot has run it - the
phone dropped off USB before that could be tested.

## Why this is a copy and not a patch

A hand-written patch has to match context lines exactly, and a wrong one breaks
`deps/apply-patches.sh` for every later build - worse than losing the change.
The device was offline when this was written, so the patch could not be
generated and tested. Restore the phone, confirm the sources still build from
`.deps-cache`, and only then fold them into `xnu/patches` with a real diff
(`diff -u` against a clean checkout after applying 0001-0086).

## Reinstating

```sh
cp research/instrumentation/*.cpp research/instrumentation/*.c \
   .deps-cache/xnu-patched-0082-2/<matching path>/
bash deps/build-macos.sh gauguin
```

Paths: `SweetFramebuffer.cpp` and `SweetHID.cpp` -> `iokit/Kernel/arm/`
(`SweetHID.cpp` under `hid/`), `sweet_touch.c` and `sweet_ufs.c` -> `bsd/dev/`.