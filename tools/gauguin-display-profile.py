#!/usr/bin/env python3
"""Inventory the gauguin panel and display resources from a captured DTB."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

MDP = "/soc/qcom,mdss_mdp"
DSI = "/soc/qcom,dsi-display-primary"
PANEL_SELECTOR = "msm_drm.dsi_display0="
# MiCode gauguin-q-oss, e601e14, techpack/display/msm/sde/sde_hw_intf.c.
# Descriptions for an eventual hardware probe. This tool never accesses MMIO.
INTF_READ_OFFSETS = {
    "timing_engine_enable": 0x000,
    "frame_line_count_enable": 0x0A8,
    "frame_count": 0x0AC,
    "line_count": 0x0B0,
    "status": 0x26C,
}
# sde_hw_sspp.c and sde_hw_ctl.c in the same Lagoon source revision.
SSPP_READ_OFFSETS = {
    "source_size": 0x00,
    "source_address_0": 0x14,
    "source_stride_0": 0x24,
    "source_format": 0x30,
    "source_op_mode": 0x38,
}
CTL_READ_OFFSETS = {"top": 0x14, "flush": 0x18, "interface_active": 0xF4}


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Tree:
    def __init__(self, path, fdtget):
        self.path = path
        self.fdtget = fdtget
        self.digest = hashlib.sha256(path.read_bytes()).hexdigest()

    def query(self, *args, properties=()):
        result = subprocess.run(
            [self.fdtget, *args, str(self.path), *properties],
            capture_output=True, text=True, timeout=5,
        )
        require(result.returncode == 0, "unreadable DT node/property: " + " ".join(properties))
        return result.stdout.strip()

    def strings(self, node, prop):
        return self.query("-t", "s", properties=(node, prop))

    def cells(self, node, prop):
        return [int(value, 16) for value in
                self.query("-t", "x", properties=(node, prop)).split()]

    def cell(self, node, prop):
        cells = self.cells(node, prop)
        require(len(cells) == 1, f"expected one DT cell for {prop}")
        return cells[0]

    def children(self, node):
        return self.query("-l", properties=(node,)).splitlines()

    def props(self, node):
        return self.query("-p", properties=(node,)).splitlines()

    def region(self, node, name):
        names = self.strings(node, "reg-names").split()
        cells = self.cells(node, "reg")
        require(len(cells) == 2 * len(names) and names.count(name) == 1,
                f"ambiguous DT region {name}")
        index = names.index(name)
        address, length = cells[2 * index:2 * index + 2]
        require(length > 0 and address + length <= 1 << 32, f"invalid DT region {name}")
        return address, length

    def region64(self, node):
        cells = self.cells(node, "reg")
        require(len(cells) == 4, f"expected one 64-bit region for {node}")
        address, length = ((cells[0] << 32) | cells[1], (cells[2] << 32) | cells[3])
        require(address > 0 and length > 0 and address + length <= 1 << 64,
                f"invalid region for {node}")
        return address, length


def display_inventory(tree):
    # On this device /soc uses 32-bit ranges with identity translation.
    require(tree.cell("/", "#address-cells") == 2
            and tree.cell("/soc", "#address-cells") == 1
            and tree.cell("/soc", "#size-cells") == 1
            and tree.cells("/soc", "ranges") == [0, 0, 0, 0xFFFFFFFF],
            "unexpected /soc address translation")
    require(tree.strings(MDP, "compatible") == "qcom,sde-kms", "unexpected SDE node")
    selectors = [arg[len(PANEL_SELECTOR):] for arg in tree.strings("/chosen", "bootargs").split()
                 if arg.startswith(PANEL_SELECTOR)]
    require(len(selectors) == 1, "expected one primary DSI boot selector")
    panel_name = selectors[0].split(":", 1)[0]
    require(re.fullmatch(r"qcom,mdss_dsi_j17_(?:36_02_0a|42_02_0b)_dsc_video", panel_name),
            "unsupported gauguin panel selector")
    panel = MDP + "/" + panel_name
    require(tree.strings(panel, "qcom,mdss-dsi-panel-type") == "dsi_video_mode",
            "expected DSI video mode")
    require(tree.cell(DSI, "qcom,dsi-default-panel") == tree.cell(panel, "phandle"),
            "primary DSI phandle disagrees with boot selector")
    for prop in ("qcom,mdss-dsi-pan-enable-dynamic-fps", "qcom,dsi-dyn-clk-enable"):
        require(prop in tree.props(panel), f"missing panel declaration {prop}")
    rates = tree.cells(panel, "qcom,dsi-supported-dfps-list")
    require(len(rates) == len(set(rates)) and all(0 < rate <= 240 for rate in rates),
            "invalid dynamic refresh list")
    method = tree.strings(panel, "qcom,mdss-dsi-pan-fps-update")
    require(method == "dfps_immediate_porch_mode_vfp", "unexpected dynamic refresh method")
    timing_parent = panel + "/qcom,mdss-dsi-display-timings"
    children = tree.children(timing_parent)
    require(len(children) == 1, "expected one base timing")
    timing_node = timing_parent + "/" + children[0]
    timing = {key: tree.cell(timing_node, "qcom,mdss-dsi-panel-" + key)
              for key in ("framerate", "width", "height")}
    for axis in ("h", "v"):
        for field in ("pulse-width", "back-porch", "front-porch"):
            key = f"{axis}-{field}"
            timing[key] = tree.cell(timing_node, "qcom,mdss-dsi-" + key)
    require(timing["framerate"] in rates and timing["width"] == 1080 and timing["height"] == 2400,
            "base timing disagrees with gauguin panel")
    require(tree.strings(timing_node, "qcom,compression-mode") == "dsc", "expected DSC")
    controller = tree.cell(panel, "qcom,dsi-ctrl-num")
    phy = tree.cell(panel, "qcom,dsi-phy-num")
    ctrl_node, phy_node = f"/soc/qcom,mdss_dsi{controller}_ctrl", f"/soc/qcom,mdss_dsi_phy{phy}"
    for node, index, prop in ((ctrl_node, controller, "qcom,dsi-ctrl"),
                              (phy_node, phy, "qcom,dsi-phy")):
        require(tree.cell(node, "cell-index") == index
                and tree.cell(node, "phandle") == tree.cell(DSI, prop),
                "primary DSI controller/PHY selection disagrees")
    mdp, length = tree.region(MDP, "mdp_phys")
    offsets = tree.cells(MDP, "qcom,sde-intf-off")
    types = tree.strings(MDP, "qcom,sde-intf-type").split()
    dsi_interfaces = [index for index, kind in enumerate(types) if kind == "dsi"]
    require(len(offsets) == len(types) and controller < len(dsi_interfaces),
            "cannot resolve DSI controller in SDE catalog")
    index = dsi_interfaces[controller]
    offset, span = offsets[index], tree.cell(MDP, "qcom,sde-intf-size")
    require(offset % 4 == 0 and span >= max(INTF_READ_OFFSETS.values()) + 4
            and offset + span <= length, "SDE interface outside MDP region")
    return {
        "selected_panel_node": panel_name, "declared_hz": rates, "dynamic_refresh_method": method,
        "base_timing": timing, "dsi_controller": controller, "dsi_phy": phy,
        "dsi_region": tree.region(ctrl_node, "dsi_ctrl"),
        "phy_region": tree.region(phy_node, "dsi_phy"),
        "mdp_region": [mdp, length], "sde_interface": index, "sde_interface_region": [mdp + offset, span],
        "candidate_registers": {name: mdp + offset + reg for name, reg in INTF_READ_OFFSETS.items()},
        "source_dtb_sha256": tree.digest,
    }


def refresh_catalog(tree, display):
    panel = MDP + "/" + display["selected_panel_node"]
    parent = panel + "/qcom,mdss-dsi-display-timings"
    timing_node = parent + "/" + tree.children(parent)[0]
    timing = display["base_timing"]
    require(len(tree.cells(DSI, "qcom,dsi-ctrl")) == 1
            and tree.strings(panel, "qcom,dsi-dyn-clk-type") == "constant-fps-adjust-hfp",
            "unsupported controller count or dynamic clock adjustment")
    properties = tree.props(panel)
    lanes = sum(f"qcom,mdss-dsi-lane-{i}-state" in properties for i in range(4))
    bpp = tree.cell(panel, "qcom,mdss-dsi-bpp")
    compressed_bpp = tree.cell(timing_node, "qcom,mdss-dsc-bit-per-pixel")
    slice_width = tree.cell(timing_node, "qcom,mdss-dsc-slice-width")
    require(lanes == 4 and bpp == 24 and compressed_bpp == 8
            and tree.cell(timing_node, "qcom,mdss-dsc-bit-per-component") == 8
            and 0 < slice_width <= timing["width"] and timing["width"] % slice_width == 0,
            "unsupported Gauguin DSC transport geometry")
    require(tree.cell(timing_node, "qcom,mdss-dsc-slice-per-pkt") == timing["width"] // slice_width,
            "unsupported DSC packet grouping")
    slice_bytes = (slice_width * compressed_bpp + 7) // 8
    transport_width = (slice_bytes * (timing["width"] // slice_width) + 2) // 3
    bit_clocks = tree.cells(panel, "qcom,dsi-dyn-clk-list")
    rates = display["declared_hz"]
    require(1 <= len(bit_clocks) <= 4 and len(set(bit_clocks)) == len(bit_clocks)
            and all(0 < clock < 2_000_000_000 for clock in bit_clocks)
            and all(rate <= timing["framerate"] for rate in rates),
            "unsupported clock family or refresh rate")
    count = len(bit_clocks) * len(rates)
    vertical_corrections = tree.cells(panel, "mi,mdss-dsi-dfps-dec-vfp-list")
    horizontal_corrections = tree.cells(panel, "mi,mdss-dsi-dfps-dec-hfp-list")
    require(len(vertical_corrections) == len(horizontal_corrections) == count,
            "porch correction count disagrees with clock/rate combinations")
    base_vertical_total = sum(timing[key] for key in
                              ("height", "v-pulse-width", "v-back-porch", "v-front-porch"))
    modes = []
    for clock in bit_clocks:
        for rate in rates:
            vertical_total = base_vertical_total + base_vertical_total * (timing["framerate"] - rate) // rate
            transport_total = clock * lanes // (bpp * vertical_total * rate)
            horizontal_front = transport_total - transport_width - timing["h-pulse-width"] - timing["h-back-porch"]
            vertical_front = vertical_total - timing["height"] - timing["v-pulse-width"] - timing["v-back-porch"]
            # Xiaomi applies its per-mode reductions after all clock families.
            index = len(modes)
            horizontal_front -= horizontal_corrections[index]
            vertical_front -= vertical_corrections[index]
            require(horizontal_front >= 0 and vertical_front >= 0,
                    "porch correction exceeds the modeled front porch")
            horizontal_total = timing["width"] + timing["h-pulse-width"] + timing["h-back-porch"] + horizontal_front
            vertical_total = timing["height"] + timing["v-pulse-width"] + timing["v-back-porch"] + vertical_front
            transport_total = transport_width + timing["h-pulse-width"] + timing["h-back-porch"] + horizontal_front
            require(horizontal_total < 1 << 16 and vertical_total < 1 << 16 and transport_total > 0,
                    "modeled timing exceeds the DRM geometry range")
            pixel_clock = clock * lanes // bpp
            modes.append({
                "reported_hz": rate, "reported_clock_khz": pixel_clock // 1000,
                "lane_bit_clock_hz": clock, "horizontal_front_porch": horizontal_front,
                "vertical_front_porch": vertical_front, "horizontal_total": horizontal_total,
                "vertical_total": vertical_total, "transport_horizontal_total": transport_total,
                "modeled_transport_hz": pixel_clock / (transport_total * vertical_total),
            })
    return {"dsc_transport_width": transport_width, "lanes": lanes,
            "source_bits_per_pixel": bpp, "compressed_bits_per_pixel": compressed_bpp,
            "clock_adjustment": "constant-fps-adjust-hfp",
            "vertical_front_porch_reductions": vertical_corrections,
            "horizontal_front_porch_reductions": horizontal_corrections,
            "modeled_modes": modes}


def boot_framebuffer(tree):
    framebuffers = [node for node in tree.children("/chosen") if node.startswith("framebuffer@")]
    require(len(framebuffers) == 1, "expected one inherited boot framebuffer")
    node = "/chosen/" + framebuffers[0]
    require(tree.strings(node, "compatible") == "simple-framebuffer", "unexpected framebuffer")
    return node


def boot_inventory(tree):
    node = boot_framebuffer(tree)
    geometry = {key: tree.cell(node, key) for key in ("width", "height", "stride")}
    return {
        "dtb_sha256": tree.digest, "framebuffer": geometry,
        "format": tree.strings(node, "format"),
        "display_subsystem_status": tree.strings("/soc@0/display-subsystem@ae00000", "status"),
    }


def scanout_catalog(tree, display):
    mdp, length = display["mdp_region"]
    interface = display["sde_interface"]
    require(interface < 32, "SDE interface index outside CTL mask")
    source_offsets = tree.cells(MDP, "qcom,sde-sspp-off")
    kinds = tree.strings(MDP, "qcom,sde-sspp-type").split()
    require(len(kinds) == len(source_offsets) and set(kinds) <= {"vig", "dma"},
            "unexpected Lagoon source pipe types")
    controllers = tree.cells(MDP, "qcom,sde-ctl-off")
    ranges = [(display["sde_interface_region"][0] - mdp, display["sde_interface_region"][1])]

    def blocks(offsets, size_property, registers):
        size = tree.cell(MDP, size_property)
        require(1 <= len(offsets) <= 8 and size >= max(registers.values()) + 4,
                f"invalid Lagoon block count or size for {size_property}")
        for offset in offsets:
            require(offset % 4 == 0 and offset + size <= length
                    and all(offset + size <= start or start + span <= offset for start, span in ranges),
                    f"overlapping or out-of-range Lagoon block for {size_property}")
            ranges.append((offset, size))
            yield {"base": mdp + offset, "size": size,
                   "registers": {name: mdp + offset + reg for name, reg in registers.items()}}

    sources = []
    for kind, block in zip(kinds, blocks(source_offsets, "qcom,sde-sspp-src-size", SSPP_READ_OFFSETS)):
        index = sum(pipe["type"] == kind for pipe in sources)
        sources.append({"name": f"{kind}{index}", "type": kind, **block})
    require(sources, "no Lagoon source pipes")
    control_paths = [{"index": index, **block} for index, block in enumerate(
        blocks(controllers, "qcom,sde-ctl-size", CTL_READ_OFFSETS))]
    return {
        "source_pipes": sources, "control_paths": control_paths,
        "interface_active_mask": 1 << interface,
        "active_source_pipe": None, "active_control_path": None,
    }


def splash_reservation(tree, boot, geometry):
    reserve = "/reserved-memory"
    require(tree.cell(reserve, "#address-cells") == 2 and tree.cell(reserve, "#size-cells") == 2
            and tree.cells(reserve, "ranges") == [], "unexpected splash address translation")
    require(boot.cell("/", "#address-cells") == 2 and boot.cell("/", "#size-cells") == 2,
            "unexpected boot framebuffer address format")
    base, length = tree.region64(reserve + "/cont_splash_region")
    front, size = boot.region64(boot_framebuffer(boot))
    require(size == geometry["stride"] * geometry["height"]
            and geometry["stride"] >= geometry["width"] * 4
            and base <= front < front + size <= base + length,
            "boot framebuffer disagrees with splash reservation")
    page_size = 16384
    second = (front + size + page_size - 1) & -page_size
    mapped_size = (size + page_size - 1) & -page_size
    return {
        "recovery_reservation": [base, length], "boot_framebuffer": [front, size],
        "aligned_second_frame_geometry_only": [second, mapped_size]
        if second + mapped_size <= min(base + length, 1 << 32) else None,
    }


def recovery_modes(path, status_path, display):
    require(status_path.read_text().strip() == "connected", "recovery DSI connector is not connected")
    modes = set()
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"(\d+)x(\d+)x(\d+)x(\d+)vid", line)
        require(match, "unexpected recovery DSI mode")
        width, height, rate, clock = map(int, match.groups())
        base = display["base_timing"]
        require((width, height) == (base["width"], base["height"])
                and rate in display["declared_hz"] and clock > 0,
                "recovery DSI mode disagrees with panel declaration")
        modes.add((rate, clock))
    require(modes, "empty recovery mode list")
    return [{"hz": rate, "reported_clock_khz": clock} for rate, clock in sorted(modes)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captured_dtb", type=Path)
    parser.add_argument("--boot-dtb", type=Path)
    parser.add_argument("--recovery-modes", type=Path)
    parser.add_argument("--recovery-status", type=Path)
    parser.add_argument("--fdtget", default="fdtget")
    parser.add_argument("--scanout-catalog", action="store_true")
    parser.add_argument("--refresh-catalog", action="store_true")
    parser.add_argument("--drm-mode-log", type=Path,
                        help="bind every DRM timing field to this captured DTB")
    args = parser.parse_args()
    if bool(args.recovery_modes) != bool(args.recovery_status):
        parser.error("--recovery-modes and --recovery-status must be supplied together")
    try:
        tree = Tree(args.captured_dtb, args.fdtget)
        result = display_inventory(tree)
        if args.refresh_catalog or args.drm_mode_log:
            result["refresh_timing_catalog"] = refresh_catalog(tree, result)
        if args.drm_mode_log:
            import importlib.util
            from gauguin_mode_contract import validate_catalog
            spec = importlib.util.spec_from_file_location(
                "gauguin_drm_mode_reader", Path(__file__).with_name("gauguin-drm-timing.py"))
            reader = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(reader)
            panel = MDP + "/" + result["selected_panel_node"]
            parent = panel + "/qcom,mdss-dsi-display-timings"
            timing_node = parent + "/" + tree.children(parent)[0]
            skew = tree.cell(timing_node, "qcom,mdss-dsi-h-sync-skew")
            result["drm_timing_contract"] = validate_catalog(
                result, reader.analyze_modes(args.drm_mode_log.read_text()), skew)
        if args.scanout_catalog:
            result["scanout_catalog"] = scanout_catalog(tree, result)
        if args.boot_dtb:
            boot = Tree(args.boot_dtb, args.fdtget)
            result["boot_dtb"] = boot_inventory(boot)
            if args.scanout_catalog:
                result["scanout_catalog"]["splash"] = splash_reservation(
                    tree, boot, result["boot_dtb"]["framebuffer"])
        if args.recovery_modes:
            result["recovery_advertised_modes"] = recovery_modes(
                args.recovery_modes, args.recovery_status, result)
        result["active_scan_hz"] = None
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"gauguin display profile: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
