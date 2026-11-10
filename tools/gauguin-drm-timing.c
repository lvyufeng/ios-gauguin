/* AArch64 Linux recovery probe. Build with the device kernel's DRM UAPI.
 * Queries the connected DSI CRTC, vblank timestamps or active DRM planes. */
#include <drm/drm.h>

enum {
    SYS_IOCTL = 29, SYS_OPENAT = 56, SYS_CLOSE = 57, SYS_WRITE = 64,
    SYS_NANOSLEEP = 101, SYS_CLOCK_GETTIME = 113,
    AT_FDCWD = -100, CLOCK_MONOTONIC = 1, O_CLOEXEC = 02000000,
    CONNECTED = 1, MAX_OBJECTS = 32, MAX_PROPERTIES = 96, SAMPLE_COUNT = 25,
    PRIMARY_PLANE = 1, CURSOR_PLANE = 2,
};

struct time_value {
    long seconds;
    long nanoseconds;
};

struct route {
    unsigned connector;
    unsigned encoder;
    unsigned crtc;
    unsigned pipe;
};

static long syscall4(long number, long a, long b, long c, long d)
{
    register long x0 __asm__("x0") = a;
    register long x1 __asm__("x1") = b;
    register long x2 __asm__("x2") = c;
    register long x3 __asm__("x3") = d;
    register long x8 __asm__("x8") = number;
    __asm__ volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x8) : "memory");
    return x0;
}

/* Clang can emit memset for initialized aggregate ioctl arguments. */
void *memset(void *buffer, int value, unsigned long length)
{
    unsigned char *bytes = buffer;
    for (unsigned long i = 0; i < length; ++i)
        bytes[i] = (unsigned char)value;
    return buffer;
}

static void emit(const char *text)
{
    unsigned long length = 0;
    while (text[length])
        ++length;
    while (length) {
        long count = syscall4(SYS_WRITE, 1, (long)text, (long)length, 0);
        if (count <= 0)
            return;
        text += count;
        length -= (unsigned long)count;
    }
}

static void number(unsigned long value)
{
    char digits[21] = {0};
    unsigned index = sizeof(digits) - 1;
    do {
        digits[--index] = (char)('0' + value % 10);
        value /= 10;
    } while (value);
    emit(&digits[index]);
}

static int failure(const char *stage, long status)
{
    emit("GDRM error ");
    emit(stage);
    emit(" ");
    if (status < 0)
        emit("-");
    number((unsigned long)(status < 0 ? -status : status));
    emit("\n");
    return 1;
}

static long query(long fd, unsigned long operation, void *argument)
{
    return syscall4(SYS_IOCTL, fd, (long)operation, (long)argument, 0);
}

static long connector_query(long fd, unsigned id, struct drm_mode_get_connector *connector)
{
    struct drm_mode_modeinfo unused = {0};
    connector->connector_id = id;
    // A nonzero capacity prevents GETCONNECTOR from triggering fill_modes.
    connector->count_modes = 1;
    connector->modes_ptr = (unsigned long)&unused;
    return query(fd, DRM_IOCTL_MODE_GETCONNECTOR, connector);
}

static long select_dsi(long fd, struct route *route)
{
    unsigned crtcs[MAX_OBJECTS] = {0}, connectors[MAX_OBJECTS] = {0};
    struct drm_mode_card_res resources = {
        .count_crtcs = MAX_OBJECTS, .count_connectors = MAX_OBJECTS,
        .crtc_id_ptr = (unsigned long)crtcs, .connector_id_ptr = (unsigned long)connectors,
    };
    long rc = query(fd, DRM_IOCTL_MODE_GETRESOURCES, &resources);
    if (rc < 0)
        return rc;
    if (resources.count_crtcs > MAX_OBJECTS || resources.count_connectors > MAX_OBJECTS)
        return -7;
    for (unsigned i = 0; i < resources.count_connectors; ++i) {
        struct drm_mode_get_connector connector = {0};
        rc = connector_query(fd, connectors[i], &connector);
        if (rc < 0)
            return rc;
        if (connector.connector_type != DRM_MODE_CONNECTOR_DSI || connector.connector_type_id != 1)
            continue;
        if (route->connector || connector.connection != CONNECTED || !connector.encoder_id)
            return -19;
        struct drm_mode_get_encoder encoder = {.encoder_id = connector.encoder_id};
        rc = query(fd, DRM_IOCTL_MODE_GETENCODER, &encoder);
        if (rc < 0)
            return rc;
        route->connector = connector.connector_id;
        route->encoder = connector.encoder_id;
        route->crtc = encoder.crtc_id;
    }
    if (!route->connector || !route->crtc)
        return -19;
    for (unsigned i = 0; i < resources.count_crtcs; ++i) {
        if (crtcs[i] == route->crtc) {
            route->pipe = i;
            return 0;
        }
    }
    return -19;
}

static int same_mode(const struct drm_mode_modeinfo *a, const struct drm_mode_modeinfo *b)
{
    return a->clock == b->clock && a->hdisplay == b->hdisplay &&
           a->hsync_start == b->hsync_start && a->hsync_end == b->hsync_end &&
           a->htotal == b->htotal && a->hskew == b->hskew &&
           a->vdisplay == b->vdisplay && a->vsync_start == b->vsync_start &&
           a->vsync_end == b->vsync_end && a->vtotal == b->vtotal &&
           a->vscan == b->vscan && a->vrefresh == b->vrefresh && a->flags == b->flags;
}

static int same_text(const char *a, const char *b)
{
    while (*a && *a == *b) {
        ++a;
        ++b;
    }
    return *a == *b;
}

static long plane_type(long fd, unsigned id, unsigned *type)
{
    unsigned ids[MAX_PROPERTIES] = {0};
    unsigned long values[MAX_PROPERTIES] = {0};
    struct drm_mode_obj_get_properties props = {
        .props_ptr = (unsigned long)ids, .prop_values_ptr = (unsigned long)values,
        .count_props = MAX_PROPERTIES, .obj_id = id, .obj_type = DRM_MODE_OBJECT_PLANE,
    };
    long rc = query(fd, DRM_IOCTL_MODE_OBJ_GETPROPERTIES, &props);
    if (rc < 0)
        return rc;
    if (props.count_props > MAX_PROPERTIES)
        return -7;
    int found = 0;
    for (unsigned i = 0; i < props.count_props; ++i) {
        struct drm_mode_get_property property = {.prop_id = ids[i]};
        rc = query(fd, DRM_IOCTL_MODE_GETPROPERTY, &property);
        if (rc < 0)
            return rc;
        if (!same_text(property.name, "type"))
            continue;
        if (found || !(property.flags & DRM_MODE_PROP_IMMUTABLE) || values[i] > CURSOR_PLANE)
            return -22;
        *type = (unsigned)values[i];
        found = 1;
    }
    return found ? 0 : -61;
}

struct active_plane {
    unsigned id;
    unsigned fb;
    unsigned type;
};

static long active_planes(long fd, const struct route *route,
                          struct active_plane *active, unsigned *count)
{
    unsigned ids[MAX_OBJECTS] = {0};
    struct drm_mode_get_plane_res resources = {
        .plane_id_ptr = (unsigned long)ids, .count_planes = MAX_OBJECTS,
    };
    long rc = query(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, &resources);
    if (rc < 0)
        return rc;
    if (resources.count_planes > MAX_OBJECTS)
        return -7;
    for (unsigned i = 0; i < resources.count_planes; ++i) {
        if (!ids[i] || (i && ids[i] == ids[i - 1]))
            return -22;
        struct drm_mode_get_plane plane = {.plane_id = ids[i]};
        rc = query(fd, DRM_IOCTL_MODE_GETPLANE, &plane);
        if (rc < 0)
            return rc;
        if (plane.crtc_id != route->crtc)
            continue;
        if (!plane.fb_id || !(plane.possible_crtcs & (1U << route->pipe)))
            return -22;
        struct active_plane *record = &active[*count];
        record->id = ids[i];
        record->fb = plane.fb_id;
        rc = plane_type(fd, record->id, &record->type);
        if (rc < 0)
            return rc;
        ++*count;
    }
    return *count ? 0 : -61;
}

static int inspect_planes(long fd)
{
    // Enables enumeration of primary/cursor planes on this file only.
    struct drm_set_client_cap cap = {.capability = DRM_CLIENT_CAP_UNIVERSAL_PLANES, .value = 1};
    long rc = query(fd, DRM_IOCTL_SET_CLIENT_CAP, &cap);
    if (rc < 0)
        return failure("universal-planes", rc);
    struct route before = {0}, after = {0};
    rc = select_dsi(fd, &before);
    if (rc < 0)
        return failure("route", rc);
    struct drm_mode_crtc first = {.crtc_id = before.crtc};
    rc = query(fd, DRM_IOCTL_MODE_GETCRTC, &first);
    if (rc < 0 || !first.mode_valid || first.mode.hdisplay != 1080 || first.mode.vdisplay != 2400)
        return failure("active-mode", rc < 0 ? rc : -22);

    struct active_plane initial[MAX_OBJECTS], final[MAX_OBJECTS];
    unsigned initial_count = 0, final_count = 0;
    rc = active_planes(fd, &before, initial, &initial_count);
    if (rc < 0)
        return failure("initial-planes", rc);
    const struct time_value pause = {.nanoseconds = 43000000};
    rc = syscall4(SYS_NANOSLEEP, (long)&pause, 0, 0, 0);
    if (rc < 0)
        return failure("sleep", rc);
    rc = select_dsi(fd, &after);
    if (rc < 0 || after.connector != before.connector || after.encoder != before.encoder ||
        after.crtc != before.crtc || after.pipe != before.pipe)
        return failure("route-changed", rc < 0 ? rc : -11);
    rc = active_planes(fd, &after, final, &final_count);
    if (rc < 0 || final_count != initial_count)
        return failure("planes-changed", rc < 0 ? rc : -11);
    struct drm_mode_crtc last = {.crtc_id = after.crtc};
    rc = query(fd, DRM_IOCTL_MODE_GETCRTC, &last);
    if (rc < 0 || !last.mode_valid || !same_mode(&first.mode, &last.mode) || first.fb_id != last.fb_id)
        return failure("mode-changed", rc < 0 ? rc : -11);

    unsigned primary = 0;
    for (unsigned i = 0; i < final_count; ++i) {
        if (final[i].id != initial[i].id || final[i].fb != initial[i].fb || final[i].type != initial[i].type)
            return failure("plane-state-changed", -11);
        if (final[i].type == PRIMARY_PLANE) {
            if (primary || (last.fb_id && last.fb_id != final[i].fb))
                return failure("primary-plane-disagrees", -22);
            primary = final[i].id;
        }
    }
    if (!primary)
        return failure("no-primary-plane", -61);

    emit("GDRM route ");
    number(after.connector); emit(" "); number(after.encoder); emit(" ");
    number(after.crtc); emit(" "); number(after.pipe); emit(" ");
    number(last.mode.vrefresh); emit(" "); number(last.fb_id); emit("\n");
    for (unsigned i = 0; i < final_count; ++i) {
        emit("GDRM plane ");
        number(final[i].id); emit(" "); number(final[i].fb); emit(" ");
        number(final[i].type); emit("\n");
    }
    emit("GDRM planes-complete "); number(final_count); emit("\n");
    return 0;
}

static long wait_vblank(long fd, unsigned pipe, unsigned relative,
                        unsigned long *sequence, unsigned long *stamp)
{
    union drm_wait_vblank wait = {0};
    wait.request.type = _DRM_VBLANK_RELATIVE | (pipe << _DRM_VBLANK_HIGH_CRTC_SHIFT);
    wait.request.sequence = relative;
    long rc = query(fd, DRM_IOCTL_WAIT_VBLANK, &wait);
    if (rc < 0)
        return rc;
    if (wait.reply.tval_sec < 0 || (unsigned long)wait.reply.tval_sec > 0xffffffffUL ||
        wait.reply.tval_usec < 0 || wait.reply.tval_usec >= 1000000)
        return -22;
    *sequence = wait.reply.sequence;
    *stamp = (unsigned long)wait.reply.tval_sec * 1000000000 +
             (unsigned long)wait.reply.tval_usec * 1000;
    return 0;
}

static long vblank_sample(long fd, const struct route *route, int *legacy, int first_sample,
                          unsigned long *sequence, unsigned long *stamp)
{
    if (!*legacy) {
        struct drm_crtc_get_sequence seq = {.crtc_id = route->crtc};
        long rc = query(fd, DRM_IOCTL_CRTC_GET_SEQUENCE, &seq);
        if (rc == 0) {
            if (!seq.active)
                return -112;
            if (seq.sequence_ns > 0) {
                *sequence = seq.sequence;
                *stamp = (unsigned long)seq.sequence_ns;
                return 0;
            }
            if (!first_sample)
                return -61;
        } else if (rc != -25 && rc != -22 && rc != -38 && rc != -95 && rc != -19) {
            return rc;
        }
        if (!first_sample)
            return rc;
        *legacy = 1;
    }
    // Relative zero queries the current count and does not queue a flip/event.
    long rc = wait_vblank(fd, route->pipe, 0, sequence, stamp);
    // An idle vblank counter can have no cached timestamp. Let it observe
    // one real interrupt, bounded by the recovery runner's timeout.
    if (rc == 0 && !*stamp && first_sample)
        rc = wait_vblank(fd, route->pipe, 1, sequence, stamp);
    if (rc < 0)
        return rc;
    return *stamp ? 0 : -61;
}

static int measure(long fd)
{
    struct route route = {0};
    long rc = select_dsi(fd, &route);
    if (rc < 0)
        return failure("route", rc);

    struct drm_mode_crtc first = {.crtc_id = route.crtc}, last = {.crtc_id = route.crtc};
    rc = query(fd, DRM_IOCTL_MODE_GETCRTC, &first);
    if (rc < 0 || !first.mode_valid || first.mode.hdisplay != 1080 || first.mode.vdisplay != 2400)
        return failure("active-mode", rc);

    struct drm_get_cap capability = {.capability = DRM_CAP_TIMESTAMP_MONOTONIC};
    rc = query(fd, DRM_IOCTL_GET_CAP, &capability);
    if (rc < 0 || capability.value != 1)
        return failure("clock-domain", rc);
    emit("GDRM mode ");
    number(first.mode.hdisplay); emit(" "); number(first.mode.vdisplay); emit(" ");
    number(first.mode.vrefresh); emit(" "); number(first.mode.clock); emit(" ");
    number(first.mode.htotal); emit(" "); number(first.mode.vtotal); emit("\n");

    int legacy = 0;
    const struct time_value pause = {.nanoseconds = 43000000};
    unsigned long sequence, stamp;
    // The first query may enable the IRQ and return an old cached timestamp.
    rc = vblank_sample(fd, &route, &legacy, 1, &sequence, &stamp);
    if (rc < 0)
        return failure(rc == -112 ? "inactive-crtc" : "vblank-warmup", rc);
    for (unsigned i = 0; i < SAMPLE_COUNT; ++i) {
        rc = syscall4(SYS_NANOSLEEP, (long)&pause, 0, 0, 0);
        if (rc < 0)
            return failure("sleep", rc);
        rc = vblank_sample(fd, &route, &legacy, 0, &sequence, &stamp);
        if (rc < 0)
            return failure(rc == -112 ? "inactive-crtc" : "vblank", rc);
        struct time_value now = {0};
        rc = syscall4(SYS_CLOCK_GETTIME, CLOCK_MONOTONIC, (long)&now, 0, 0);
        if (rc < 0 || now.seconds < 0 || now.nanoseconds < 0 || now.nanoseconds >= 1000000000)
            return failure("sample-clock", rc);
        unsigned long observed = (unsigned long)now.seconds * 1000000000 + now.nanoseconds;
        emit("GDRM sample ");
        number(sequence); emit(" "); number(stamp); emit(" "); number(observed); emit("\n");
    }

    struct route after = {0};
    rc = select_dsi(fd, &after);
    if (rc < 0 || after.connector != route.connector || after.encoder != route.encoder ||
        after.crtc != route.crtc || after.pipe != route.pipe)
        return failure("route-changed", rc);
    rc = query(fd, DRM_IOCTL_MODE_GETCRTC, &last);
    if (rc < 0 || !last.mode_valid || !same_mode(&first.mode, &last.mode))
        return failure("mode-changed", rc);
    emit(legacy ? "GDRM complete wait-query\n" : "GDRM complete crtc-sequence\n");
    return 0;
}

int probe_main(unsigned long argc, const char *const *argv)
{
    int planes = argc == 2 && same_text(argv[1], "--planes");
    if (argc != 1 && !planes)
        return failure("usage", -22);
    long fd = syscall4(SYS_OPENAT, AT_FDCWD, (long)"/dev/dri/card0", O_CLOEXEC, 0);
    if (fd < 0)
        return failure("open", fd);
    int result = planes ? inspect_planes(fd) : measure(fd);
    syscall4(SYS_CLOSE, fd, 0, 0, 0);
    return result;
}

__asm__(".text\n.global _start\n_start:\n"
        "ldr x0, [sp]\nadd x1, sp, #8\nbl probe_main\nmov x8, #93\nsvc #0\nbrk #0\n");
