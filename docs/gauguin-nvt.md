# Gauguin Novatek input bring-up

This driver is specific to the observed Redmi Note 9 Pro 5G controller and
boot state. Register access has been verified on hardware. SPI transactions and full firmware SRAM readback have now succeeded.
Firmware readiness and physical input still require hardware qualification.
See `NOTES.md` for the current tested image and results.

The default is disabled. `sweetnvt=1` selects a separate worker after a 30 second
delay and takes priority over the old touch initialization path. Conflicting
`sweetnvtprobe` or `sweettouchmode` arguments cause refusal, with no fallthrough
to either older path. Worker creation failure never runs initialization inline.

## Profile and ownership

- QUP0 SE0 at `0x880000`, wrapper0 at `0x8c0000`; Linux names this `spi2.0`.
- Wrapper 2.7, SPI firmware 1, 16-word FIFOs with 32-bit words.
- The observed source is XO 19.2 MHz. Divider 20 gives 960 kHz; SPI mode 0,
  8-bit words, CS0. A different source/profile is refused.
- Only GCC vote bits 6, 7 and 10 are acquired. No PLL/RCG/RPMh programming.
- GPIO 0–3 carry SPI; GPIO 21 is reset, GPIO 22 is the input interrupt pin.
  This first driver polls; it installs no competing GPIO/SE interrupt handler.
- One ordinary kernel worker owns the bus from acquisition through polling.
  PIO uses bounded FIFO credit, drains RX before adding TX and never retries a
  failed transaction. An error permanently quarantines this owner for the boot.
  Software deadlines cannot interrupt a synchronous stalled MMIO access.

The bus and setup modules distinguish ordinary configuration restoration from
action writes such as FORCE_DEFAULT and interrupt acknowledgements. Failed
restoration never reports success. Final reports are copied while ownership
is still held; the handle is invalid after close or abort.

## Firmware and initialization

`tools/mkpayload.py --nvt-firmware FILE` accepts only the local 139264-byte image
with SHA256 `007143e7d0a816e4ef228b5a08bf3132285230a5cd16164e8086696115d60f88`.
The binary is not included in this repository. The payload reserves 147456
bytes, records the raw size in `NovatekFirmware` and includes the reserved
pages below `topOfKernelData`. The kernel independently checks these bounds
and computes SHA256 before acquiring the bus. It uses the existing RWNX RAM
mapping. Without this option, payload bytes remain unchanged.

The native reference is [LineageOS's gauguin kernel at the pinned commit](https://github.com/LineageOS/android_kernel_xiaomi_gauguin/tree/19b63c8192b1c9b7c4d931d7d3be92024bc2d778/drivers/input/touchscreen/nt36672c).
The implementation uses these observed/native contracts:

| Step | Contract | Native source |
| --- | --- | --- |
| Engineering reset | GPIO 21 LOW, SPI `0x7fff80=0x5a`, wait 1 ms, GPIO HIGH, wait 10 ms | `nt36xxx.c`, probe/reset functions |
| Bootloader reset | `0x3f0fe=0x69`, wait 5 ms, `0x3f310=0` | `nvt_bootloader_reset` and live DT |
| Identity | Read six actual trim bytes `0c 00 00 72 66 03`; select NT36675 map, event base `0x22d00`, hardware CRC mode 2 | `nvt_ts_check_chip_ver_trim`, `nt36xxx_mem_map.h` |
| Download | Three nonempty partitions: ILM 79368 bytes, DLM 17312 bytes, Info-12 256 bytes | `nt36xxx_fw_update.c` partition parsing/download |
| Readback | Read and compare all 96936 bytes before starting firmware | Native optional SRAM dump supports these reads before CRC setup |
| CRC banks | Destination 3 bytes, raw size 3 bytes with 17 significant bits, golden CRC 4 bytes | `nvt_set_bld_hw_crc` |
| Start | Enable bootloader/FW CRC, write BOOT_READY, poll bounded reset/CRC state | `nvt_bld_crc_enable`, `nvt_fw_crc_enable`, `nvt_boot_ready` |
| Verification | Actual CRC_DONE, no bank error, reset A0–AF, version 16, type 1, PID 5937 | Native status/FWINFO/PID reads; values observed in recovery |

CRC history before loading is recorded, not assumed to clear on reset.
Post-start R/G checksum registers are diagnostic observations, not stable
loader results: the native hardware-CRC success path checks reset readiness
and reads those registers only on failure. On the first hardware run, DLM's
result matched Info-12's CRC after reset A1 and complete SRAM readback. Reuse
by running firmware is an inference; no special value is accepted as a
substitute for the retained integrity/readiness gates. Info-12
has no third hardware CRC bank, so its complete byte readback matters. No trim,
PID, geometry, CRC or readiness response is synthesized. All bootstrap
transactions fit 64 wire bytes; subsequent point samples use 67 wire bytes.
Raw reads retain the two leading wire bytes until the protocol decoder.

## Input and failure behavior

Only decoded physical reports become complete ten-slot HID snapshots. IDs
1–10 map to slots 0–9; observed sensor geometry maps to the 1080×2400 panel.
The HID layer applies its existing logical display offset once, publishes one
parent collection with a common timestamp and commits state only after event
allocation succeeds. It does not inject a tap, home action or unlock gesture.

Transport failure, ESD/watchdog signatures, repeated malformed data or repeated
HID refusal stop the worker. Previously published contacts get bounded release
attempts; failure is reported as unconfirmed. The driver then aborts the bus,
without resetting or restarting firmware. Persistent diagnostics describe the
last phase and which hardware observations are valid.

Host tests exercise actual code with modeled kernel/MMIO boundaries, including
allocation failures, finite FIFO overflow controls and failure at bootstrap
phases. Synthetic firmware fixtures contain no downloaded program bytes.
Local tests may additionally use the exact pinned binary. These checks and
single-file ARM64 compilation do not establish physical touch or unlock.
