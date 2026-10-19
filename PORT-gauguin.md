# sweet → gauguin port: what differs (hardware facts)

Date: 2026-10-19. Device: Redmi Note 9 Pro 5G / Mi 10T Lite, `gauguin`, Qualcomm
**SM7125** (platform `lagoip`, DT compatible `qcom,lagoon-qrd` / `qcom,lagoon`).
Bootloader unlocked, currently running TWRP (recovery, not flashed by us).

Sources (all read-only, captured 2026-10-19):

| Source | Where |
| --- | --- |
| Live FDT of the running TWRP kernel | `/sys/firmware/devicetree/base` → `dtb/base/` (not in git: serial) |
| Stock base DTB + the applied dtbo entry (`dtbo_idx=4`) | `backup/boot.img`, `backup/dtbo.img` → `dtb/boot_unpacked/dtb`, `dtb/gauguin_*.dts` |
| Kernel-side DTS (vendor overlays, symbols) | LineageOS `android_kernel_xiaomi_gauguin` @ `lineage-24.0`, sparse clone in `research/kernel-gauguin` |
| Focaltech touch protocol + driver config | same repo, `drivers/input/touchscreen/focaltech_touch` (FT3518/FT5452 driver used by the stock ROM) |

Observations are marked with the source; guesses are marked *guess*.

## What is the same (sweet code works unchanged)

| Item | Value on gauguin | Note |
| --- | --- | --- |
| UFS controller | `ufshc@1d84000`, `ufs_mem_phy@1d87000`, `androidboot.boot_devices=soc/1d84000.ufshc` | Same base as sweet |
| UFS LUN / partition layout | LUN0 no GPT partitions (whole 128 MiB `boot`), LUN4 sda, `userdata` = `sda35`; everything else LUN5 (sde/sdf) | Same as sweet ⇒ `ufsroot0`, log ring at the end of userdata unchanged |
| GIC | GICD `0x17a00000`, GICR `0x17a60000`, stride `0x20000`, "arm,gic-v3" | Same |
| Timer | `timer` clock-frequency `0x124f800` = 19.2 MHz, PPI: hyp 0 / secure-phys 1 / phys 2 / virt 3 ⇒ vtimer INTID 19 | Same as sweet |
| PSCI | `psci` node (`method` = smc), 8 CPUs | Same |
| CPU topology | cpu@0..500 = CPU0..5 (Aff0 split 0x000..0x400), cpu@600/700 = CPU6/7, MPIDR `Aff1:Aff0` = `0x600` / `0x700`, cluster nodes cluster0 = cpu0-5, cluster1 = cpu6-7 | Same MPIDR numbering as sweet (`0x81000n00`) ⇒ `cpus=8` works |
| SPMI PMIC arbiter | `qcom,spmi@c440000`: core 0xc440000, chnls 0xc600000, obsrvr 0xe600000, intr 0xe700000, cnfg 0xc40a000, `qcom,ee=0` | Identical to the constants in `sweet_keys.c` |
| Power key | PM6350 (`qcom,spmi-pmic` at USID 0), `qcom,power-on@800` (`kpdpwr`, `resin`) | PON read at 0x810 bit0/bit1 works as on sweet |
| USB controller | `ssusb@a600000` (dwc3, `qcom,dwc-usb3-msm`), QSCRATCH at +0xf8800 (0x0a6f8800), `qusb@88e3000` | `sweet_usb.c` bases unchanged |
| Panel | 1080×2400, DSC **video** mode (`dsi-panel-j17-36-02-0a`, framerate 120, `panel_otp=0x46,0x36,0x32,0x01`), MIPI DSI | Same geometry and the same "continuous splash, no refresh kick" property |
| fbcon / boot video | `cont_splash_region` `0xa0000000` + `0x2300000` (35 MiB, 1080×2400×4 = 9.98 MiB) | Base address differs? **No**: see table below |
| SoC base / `/arm-io ranges` | Mkadt uses `SOC_BASE 0x01000000`; every gauguin MMIO address is below 4 GiB and above it | Fine |

## What differs (must be changed)

| Item | sweet | gauguin | Where it is hardcoded |
| --- | --- | --- | --- |
| Chip name | SM7150 (`xiaomi,sweet`) | SM7125 / `lagoip` (`qcom,lagoon`) | `mkadt.py` root `compatible`, XNU `SWEET` machine config strings, README |
| CPUs (big) | 2× Cortex-A76? (sweet: 2 A76 + 6 A55) | cpu6/cpu7 = Cortex-A77-style Kryo 465 Gold, cluster1 | cosmetic (`compatible`, clock-frequency) |
| RAM (memory node) | `<0x80000000 2G>`, `<0x100000000 0xfcc00000>` | `<0x80000000 0x3bb00000>`, `<0x180000000 0x100000000>`, `<0xc0000000 0xc0000000>` (last one dropped by `mem-offline`/`removed_region@c0000000`) | `mkadt.py` `HIGH_PHYS_BASE/HIGH_MEM_SIZE`, swapped by this port to match |
| Kernel RAM bank | upper bank at `0x100000000`, 0xfcc00000 | upper bank at **`0x180000000`**, 0x100000000 (4 GiB) | `mkadt.py`, `shim/loader.c` (takes it from the payload header — unchanged code) |
| Firmware carve-outs in the low bank | sdm/sm7150 layout, highest `xbl_aop_mem` 0x80700000 | modem 0x8b800000 (248 MiB), ipa/wlan 0x8b500000-0x8b715400, adsp 0x88d00000 (40 MiB), npu 0x86500000, video 0x86a00000, cdsp 0x86f00000, camera 0x86000000, qseecom (dynamic), mem_dump, removed_region@c0000000 (123 MiB) | not mapped by XNU when using the upper bank; the shim maps RAM Device-only |
| Touch controller | Goodix GT9896 @0x5d on **QUPv3 SE7** (`0xa84000`), interrupt from the PMIC | **Focaltech FT5452 (driver "FT3518" family)** @**0x38** on **QUPv3 SE8** (`0x988000`), reset = TLMM gpio21, IRQ = TLMM gpio22 (active low, falling), power `vdd-supply = L6A` (pm6150l LDO6), display-coords 0..1080×0..2340 | `bsd/dev/sweet_touch.c` (protocol), `sweet_rpmh.c` (L11C vs L6A) |
| Volume up | PM6150L GPIO2 (SPMI SID 4, PPID 0x4c1, 0xc110) | **PM6350 GPIO2 (SPMI SID 0, PPID 0x4c0, 0xc110)** | `bsd/dev/sweet_keys.c` (`keys_find_apid(0x4c1, …)`) |
| PMIC set | PM6150/PM6150L/PM8009 | **PM6350/PM6150L/PM7250B** + PM8008 | keys/battery/RPMh |
| Charger / fuel gauge | PM6150 SMB5 | **PM7250B SMB5 + bq25970 standalone + smb1396/1398**, battery profile `qg-gauguin-cosmx-4820mah` (4820 mAh) | `SweetBattery.cpp` (static 100 % for now) |
| Fingerprint | (none) | Goodix / FPC under-display (not needed) | — |
| Display DCS/backlight | sweet panel | j17 panels: pm6150l WLED backlight, `mi,cabcoff-dbv` etc. | not used (ABL splash + panel stays on) |

## Verified device facts (read-only, from TWRP)

- `getprop`: `ro.product.device=gauguin`, `ro.product.model=Mi 10T Lite`,
  `ro.board.platform=lito`, `ro.boot.hardware=gauguin`, `ro.crypto.state=encrypted`,
  `androidboot.hwversion=1.9.2`, `androidboot.dtbo_idx=4`, `androidboot.dtb_idx=0`,
  `androidboot.usbcontroller=a600000.dwc3`, `androidboot.bootdevice=1d84000.ufshc`.
- `misc` = `/dev/block/sda11`, `recovery` = `sda29`, `super` = `sda33`,
  `userdata` = `sda35` (sda = 247554048 KiB ≈ 236 GiB), `boot` = `sde55` (128 MiB),
  `dtbo` = `sde45` (32 MiB), `vbmeta` = `sde15` (AVB1.0, flags 0, `invalidate_on_error=yes`,
  `device_state=unlocked`).
- Stock `boot.img` is v2 (kernel 0x8000, ramdisk 0x1000000, dtb 0x1f00000, pagesize 4096) —
  same header geometry as sweet, so `shim/build.sh` works as is.
- Dumped to `backup/`: `boot.img`, `dtbo.img`, `vbmeta.img` (git-ignored).

## Port plan (implementation order)

1. **shim**: read `/memory` from the live FDT (`shim/loader.c`, `shim/mmu.c`), so RAM
   base/size and the fbcon block come from the phone instead of sweet constants. Keep the
   payload header as the source of phys_base (mkadt writes it).
2. **mkadt.py**: `--device gauguin` with the gauguin dram-base `0x180000000` / size
   `0x100000000`, SoC compatible `qcom,sm7125`, and the same iPhone X identity.
3. **XNU drivers**: keys PPID 0x4c0 on SID 0; Focaltech touch on SE8 (`0x988000`) with the
   FT5452 protocol; RPMh LDO6 (L6A) vote for the touch rail; everything else unchanged.
4. **CI build**, QEMU smoke test, then `fastboot boot` (slow-boot header disabled for now).
5. **iOS root**: needs `userdata` (236 GiB, encrypted Android data) — *user approval and
   backup first*. The root image is device independent, so only the flash step differs.