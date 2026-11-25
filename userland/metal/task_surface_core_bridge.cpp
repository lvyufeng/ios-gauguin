/* SPDX-License-Identifier: MIT
 * Two exact C API object definitions extracted from the pinned core source by
 * the build script. No Apple object layout or private framework ivar is used. */
#include "task_surface_permissions.h"
#include "GauguinTaskCoreABI.h"

extern "C" bool gauguin_task_surface_permissions(hakios_metal_device* device,
    hakios_metal_texture* source, uint32_t surfaceId, uint64_t bytes, uint64_t pageBias,
    gauguin_surface_permissions* report)
{
    if (!report) return false;
    *report = {}; report->phase = "project-core-handles";
    if (!device || !device->gpu || !source || !source->texture ||
        source->texture->surface() != surfaceId || !source->texture->buffer()) return false;
    return gauguin_inspect_surface(*device->gpu, source->texture->buffer()->bo(),
                                  bytes, pageBias, *report);
}
