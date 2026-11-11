# Original ABL memory handoff reader in XNU, 0265

The default-off `sweethandoff=1` option enables an early XNU reader for the
0252 loader's `GauguinHandoffFDT` property. The property contains the
original ABL device tree and the ranges recorded at handoff. The kernel
reads the copy in its existing Apple device tree mapping. It treats the
recorded physical addresses as numbers.
[0252 producer and wire format](gauguin-handoff-fdt-producer-20261111.md).

## Validation and output

The reader requires the ready property, valid version, exact capacity and
zero unused bytes, and rejects pending capture or PAS properties. It
compares the record to the live managed range, physical ADT mapping,
framebuffer geometry and `topOfKernelData`. `PE_state.bootArgs` points
to the immutable XNU copy. The original boot-args page is derived from
`topOfKernelData` and checked against the page-aligned end of the live
ADT. The reader verifies the PAS owner record and pmap I/O tuple against
the input, original FDT, shim and PAS ranges.

The FDT reader bounds headers, memory-reservation entries, structure
tokens, strings and node depth. It verifies the board compatibility and
initrd placement, then reports memory banks, FDT header reservations,
fixed `/reserved-memory` regions, dynamic pool sizes and their declared
`alloc-ranges`. The report has a SHA256 for the copied FDT, bounded node
names, and a matching begin/end marker. Dynamic allocation windows are
reported as declarations with no placement assigned. The managed-memory
size is reported as a domain. VM admission remains a future milestone.
[Flattened Devicetree format](https://devicetree-specification.readthedocs.io/en/stable/flattened-format.html),
[device node requirements](https://devicetree-specification.readthedocs.io/en/stable/devicenodes.html).

## Verification

Patch `0220-gauguin-original-handoff-memory-reader.patch`, SHA256
`90ff646b35be53bbb58ea6ffedad3fa5c3d60721861050ea46f80a7cb7acf992`.
Source commit `104482754a9bdc60ba99d975a4792f57342a9f27`, branch
`codex/gauguin-handoff-memory-20261111`. Private evidence is in
`research/tmp/dsh-handoff-reader-0265` inside the
`research/tmp/gauguin-build255-worktree-20261111` worktree.

The host test uses the 20,480,000-byte 0252 capture payload and the
588,757-byte handset recovery FDT with its two initrd fields adapted to
the test placement. It runs the actual shim prepare and both commit
functions, with the source PAS tail protected by `PROT_NONE`. The
destination is a host-mapped managed range. The actual XNU reader sees
three memory banks, 21 fixed reservations, six dynamic pools and six
allocation windows. It refuses the pending record, the ready record
before PAS commit, a truncated record, changes to all header and PAS
metadata bytes, a bad live context, overlapping FDT sections and
malformed dynamic allocation windows. ASan and UBSan were enabled.

DSH stage v1, PID 73335, failed because the modeled 32 MiB destination
was smaller than the real payload's load footprint. Stage v2, PID 73616,
used a 64 MiB host mapping and passed in 10.831 s with 24 unchanged
pins. The scan cadence, route and pre-mount receipt regressions also
passed. DSH built the two new XNU translation units and `bsd_init.c`
using the selected native ARM64 recipe. The strict replay produced 5,342
files with five changes and source SHA256
`9004cf565771c70171524a05819213c38c5ef3227ad662d956ba3e7f08e9fd40`.
Independent review checked the model inputs, all native objects, the
existing kernel definitions and the exact 0263 scanout image.

DSH dispatcher 74063 passed the 11 local focused checks and dispatched
the full ARM64 kernel build at the exact source commit. It completed
with ten unchanged pins in 26.475 s.
[GitHub Actions run 42929203205](https://github.com/lvyufeng/ios-gauguin/actions/runs/42929203205).

Physical verification needs a combined image with the producer enabled,
the validated reader and a readback path for the report. The test will
first establish the actual ABL handoff and then resolve ownership and
release of candidate lower ranges before any admission or DMA trial.
This milestone issued no phone command, boot or persistent write.
