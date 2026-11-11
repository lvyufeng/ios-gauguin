"""Bind a recovery DRM catalog to the captured Gauguin DSC timing model.

The generic DRM reader accepts legal timings. This contract checks their
identity, including sync widths, skew, scan and all public flags. It does
not perform a mode check, modeset or physical refresh measurement.
"""

TIMING_FIELDS = (
    "reported_clock_khz", "reported_hz", "width", "height",
    "horizontal_front_porch", "horizontal_sync", "horizontal_back_porch",
    "horizontal_total", "horizontal_skew", "vertical_front_porch",
    "vertical_sync", "vertical_back_porch", "vertical_total", "vertical_scan",
    "flags",
)
# Xiaomi e601e14, include/uapi/drm/drm_mode.h. This supported catalog is
# video-mode with zero polarity and no public SEAMLESS flag. DFPS and
# dynamic-clock transition bits belong to private_flags, not this field.
VIDEO_MODE_PANEL = 1 << 29


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(row, field, maximum=(1 << 32) - 1):
    value = row.get(field)
    require(type(value) is int and 0 <= value <= maximum,
            "missing or invalid integer field: " + field)
    return value


def mode_key(row):
    return integer(row, "reported_hz", 240), integer(row, "reported_clock_khz", 1_000_000)


def expected_timings(profile, horizontal_skew):
    """Use final DFPS porches and base sync/back fields from the same DTB."""
    require(type(horizontal_skew) is int and 0 <= horizontal_skew < 1 << 16,
            "invalid DTB horizontal skew")
    base = profile["base_timing"]
    rows = []
    for model in profile["refresh_timing_catalog"]["modeled_modes"]:
        row = {
            "reported_clock_khz": integer(model, "reported_clock_khz", 1_000_000),
            "reported_hz": integer(model, "reported_hz", 240),
            "width": integer(base, "width", 65535),
            "height": integer(base, "height", 65535),
            "horizontal_front_porch": integer(model, "horizontal_front_porch", 65535),
            "horizontal_sync": integer(base, "h-pulse-width", 65535),
            "horizontal_back_porch": integer(base, "h-back-porch", 65535),
            "horizontal_total": integer(model, "horizontal_total", 65535),
            "horizontal_skew": horizontal_skew,
            "vertical_front_porch": integer(model, "vertical_front_porch", 65535),
            "vertical_sync": integer(base, "v-pulse-width", 65535),
            "vertical_back_porch": integer(base, "v-back-porch", 65535),
            "vertical_total": integer(model, "vertical_total", 65535),
            "vertical_scan": 0,
            "flags": VIDEO_MODE_PANEL,
        }
        require(row["horizontal_total"] == sum(row[name] for name in
                ("width", "horizontal_front_porch", "horizontal_sync", "horizontal_back_porch")),
                "inconsistent modeled horizontal total")
        require(row["vertical_total"] == sum(row[name] for name in
                ("height", "vertical_front_porch", "vertical_sync", "vertical_back_porch")),
                "inconsistent modeled vertical total")
        rows.append(row)
    require(bool(rows) and len({mode_key(row) for row in rows}) == len(rows),
            "empty or ambiguous modeled catalog")
    return rows


def validate_catalog(profile, catalog, horizontal_skew):
    """Check all advertised timings and active timing; retain type as metadata."""
    expected = {mode_key(row): row for row in expected_timings(profile, horizontal_skew)}
    observed = catalog["advertised_timings"]
    require(type(observed) is list and len(observed) == len(expected),
            "DRM/model catalog size differs")
    keyed = {mode_key(row): row for row in observed}
    require(len(keyed) == len(observed) and keyed.keys() == expected.keys(),
            "DRM/model rate-clock keys differ or repeat")

    def check(row, label):
        key = mode_key(row)
        require(key in expected, label + " rate-clock key is not modeled")
        for field in TIMING_FIELDS:
            require(integer(row, field) == expected[key][field],
                    f"{label} {key}: {field} differs from captured DTB model")
        integer(row, "type")
        return key

    for row in observed:
        check(row, "advertised")
    active = catalog["active_timing"]
    active_key = check(active, "active")
    active_index = next(index for index, row in enumerate(observed) if mode_key(row) == active_key)
    require(type(catalog["matching_active_timing_index"]) is int
            and catalog["matching_active_timing_index"] == active_index,
            "active timing does not match the advertised catalog")
    return {
        "scope": "captured DTB model and recovery DRM timing identity only",
        "source_dtb_sha256": profile["source_dtb_sha256"],
        "matched_modes": len(expected), "timing_fields": list(TIMING_FIELDS),
        "active_mode_key": list(active_key), "matching_active_timing_index": active_index,
        "selection_metadata": {
            "active_type": active["type"],
            "advertised": [{"mode_key": list(mode_key(row)), "type": row["type"]} for row in observed],
        },
        "physical_refresh_qualified": False, "modeset_qualified": False,
    }
