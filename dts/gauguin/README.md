# gauguin device tree sources (reference copy)

Vendor kernel DTS for the Redmi Note 9 Pro 5G / Mi 10T Lite (`gauguin`,
SM7125 "lagoip"), copied from LineageOS `android_kernel_xiaomi_gauguin`
(`lineage-24.0`, sparse checkout) so the hardware facts this port relies on
can be checked without downloading ~1.8 GB of kernel.

Kept: the gauguin board files and the platform files they include (lagoon*,
pm6350/pm6150l/pm7250b, the j17 panels). `dtb/gauguin_*.dts` (not in git)
are the decompiled stock base DTB and the dtbo entry that ABL applies; the
live tree is captured in `dtb/base/` while a kernel with CONFIG_OF is
running (e.g. TWRP).

What this port reads from them (see `PORT-gauguin.md`):

| File | Fact |
| --- | --- |
| `gauguin-sm6350.dtsi` | `&qupv3_se8_i2c` active (I2C SE8 at `0x988000`); `gpio_keys` volume-up = `&pm6350_gpios 2` (SPMI SID 0) |
| `lagoon-pinctrl.dtsi` | `ts_active` gpio21/22, so touch reset = TLMM 21, interrupt = TLMM 22 |
| stock `dtbo` fragment 39 | `focaltech@38` on SE8, `vdd-supply = <&L6A>` (PM6350 LDO6A), display 0 0 1080 2340 |
| `lagoon-regulators.dtsi` | `rpmh-regulator-ldoa6`, `qcom,resource-name = "ldoa6"` = L6A 1.71–3.54 V, init LPM 1.71 V |
| `pm6350.dtsi`, `pm6150l.dtsi`, `pm7250b.dtsi` | PMIC SPMI USIDs 0/1, 4/5, 2/3; PON at 0x800 on the main PMIC |
| `lagoon-qupv3.dtsi` | SE bases (`i2c@988000 0x4000`) and SPI numbers |
| `lagoon-thermal*.dtsi` | thermal trips: 125 °C passive / 115 °C `reset-mon` (vendor APSS watchdog reset) |
| `dsi-panel-j17-*` | 1080×2400 DSC video-mode panels, 120 Hz |