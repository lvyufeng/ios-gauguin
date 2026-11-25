# 0419 Spotlight submission timing

The temporary workload uses the 0419 rendering, readiness and flip objects.
It replaces the 33-second drag with the existing unlock gesture, a synthetic
Home Screen pull-down, a three-second wait and nine isolated keyboard-position
taps. Check UIKit keyboard visibility and target view classes before drawing
conclusions about keyboard handling. Record timing and class names without
storing text or key contents.

The passive userland observer records input begin, release, keyboard notices,
and a bounded set of main-loop and explicit CA transaction intervals. The
existing device CA trace supplies exact renderer and swap links when their
IDs, thread and timestamp agree. Compare touch release, CA render begin,
accepted swap, native writer and the first changed output from paired DPU
CRCs. A full-display signature change supplies a timing bracket for the
whole screen. Individual glyphs still need visible evidence.

The independent temporary run restores the same six files and misc
preimage before it interprets the frame data.
