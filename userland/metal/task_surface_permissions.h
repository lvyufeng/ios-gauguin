/* SPDX-License-Identifier: MIT
 * Diagnostic only: use the existing project-owned device/texture getters.
 * A generated projection must match the exact linked core receipt. */
#ifndef GAUGUIN_TASK_SURFACE_PERMISSIONS_H
#define GAUGUIN_TASK_SURFACE_PERMISSIONS_H
#include <stdint.h>
#include <stdbool.h>
#include <hakios-metal/hakios_metal.h>
struct gauguin_surface_permissions {
    const char *phase;
    uint64_t gpu_address, bytes, flags;
    uint32_t handle, fence;
    int cpu_write_errno, gpu_write_errno, wait_errno, close_errno;
    bool uncertain_dma;
};
#ifdef __cplusplus
namespace hakios::metal { class Gpu; class Bo; }
bool gauguin_inspect_surface(hakios::metal::Gpu&, const hakios::metal::Bo&,
                            uint64_t bytes, uint64_t page_bias,
                            struct gauguin_surface_permissions&);
extern "C" {
#endif
bool gauguin_task_surface_permissions(hakios_metal_device*, hakios_metal_texture*,
                                     uint32_t surface_id, uint64_t bytes, uint64_t page_bias,
                                     struct gauguin_surface_permissions*);
#ifdef __cplusplus
}
#endif
#endif
