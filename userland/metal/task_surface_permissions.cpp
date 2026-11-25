/* SPDX-License-Identifier: MIT */
#include "task_surface_permissions.h"
#include <hakios-metal/gpu.hpp>
#include <hakios-metal/pm4.hpp>
#include <cerrno>
#include <cstring>
using namespace hakios::metal;

bool gauguin_inspect_surface(Gpu& gpu, const Bo& source, uint64_t bytes,
                            uint64_t pageBias, gauguin_surface_permissions& r)
{
    r = {}; r.phase = "source-geometry";
    r.handle = source.handle(); r.gpu_address = source.gpuAddress(); r.bytes = source.size();
    if (!r.handle || r.bytes != bytes || !r.gpu_address ||
        (r.gpu_address & 4095) != pageBias || source.cpu()) return false;
    auto& t = gpu.transport();
    r.phase = "source-flags";
    MsmGemInfo info{}; info.handle = r.handle; info.info = 5;
    if (t.call(kGemInfo, &info, sizeof(info))) return false;
    r.flags = info.value;
    if (!(r.flags & kBoGpuReadOnly)) return false;
    r.phase = "source-map";
    void* alias = t.map(r.handle, bytes);
    if (alias) { t.unmap(r.handle, alias); return false; }
    r.phase = "cpu-read";
    if (gpu.cpuPrep(source, 1, 1000000000)) return false;
    MsmGemCpuFini fini{r.handle};
    if (t.call(kGemCpuFini, &fini, sizeof(fini))) return false;
    r.phase = "cpu-write";
    r.cpu_write_errno = gpu.cpuPrep(source, 2, 1000000000);
    if (r.cpu_write_errno != EINVAL) return false;

    /* A structurally valid NOP submission with the source listed as WRITE.
     * Correct rejection happens before the doorbell. If a broken driver accepts
     * it, the payload still performs no memory access, and we wait before free.
     * A failed/uncertain wait must never release a potentially live command BO. */
    r.phase = "command-allocation";
    int error = 0;
    auto command = gpu.newBo(8, kBoGpuReadOnly | kBoWriteCombined, &error);
    if (!command || error || !command->cpu()) return false;
    const uint32_t nop[] = {pm4::type7(pm4::kNop, 1), 0};
    std::memcpy(command->cpu(), nop, sizeof(nop));
    r.phase = "queue-create";
    uint32_t queue = 0;
    if (gpu.newQueue(0, &queue) || !queue) return false;
    r.phase = "gpu-write";
    r.gpu_write_errno = gpu.submit(queue, *command, 0, 2, {{&source, true}}, &r.fence);
    const bool rejected = r.gpu_write_errno == EINVAL && r.fence == 0;
    if (!r.gpu_write_errno) {
        r.phase = "unexpected-submit-wait";
        r.wait_errno = r.fence ? gpu.wait(queue, r.fence, 1000000000) : EINVAL;
        if (r.wait_errno) {
            r.uncertain_dma = true;
            (void)command.release();  // task exits on failure; kernel keeps DMA ownership
            return false;           // do not close a queue with uncertain DMA
        }
    }
    r.phase = "queue-close";
    r.close_errno = t.call(kSubmitQueueClose, &queue, sizeof(queue));
    if (r.close_errno || !rejected) return false;
    r.phase = "passed";
    return true;
}
