# Gauguin 60 Hz display baseline

Trial 0427 on 2026-11-25 used the 0419 display deadline instrumentation and
the 0425 passive GPU submission and completion trace. The 0427 boot image
changed the compositor work allowance from 7.2 ms to 12.2 ms on the same
kernel and renderer.

```text
sweetfb_hz=60 sweet_ca_work_us=12200
```

| Trial | New hardware images in 30 s | Repeated scans | Lowest rolling 1 s |
| --- | ---: | ---: | ---: |
| 0425, 7.2 ms | 1,790–1,791 | 17 | 57 |
| 0427, 12.2 ms | 1,801 | 7 | 59 |

The measurement used paired display-controller CRCs to count changed output
images during the central 30 seconds of a 32-second animated marker. The
observed 60.03 images/s is specific to that workload. Spotlight and the
software keyboard need a separate input-to-frame measurement.

The normal kernel build replays [the active patch series](../xnu/patches/series)
as described in [the build guide](../deps/REPRODUCIBILITY.md). Its final patch
matches the 175 source files in the tested kernel relink. Reproducing the
measured image also requires the matching renderer overlays, userland and
boot inputs. The 0419 and 0425 relink recipes are recorded in
[build-frame419.py](../tools/build-frame419.py) and
[build-frame425.py](../tools/build-frame425.py). These historical recipes
reference local build archives and the corresponding iOS renderer inputs.
Those artifacts and the temporary boot image remain outside the repository.
