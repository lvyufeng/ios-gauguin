/* SPDX-License-Identifier: MIT
 * Real Gpu/Bo request generation with a typed Transport seam. */
#include "task_surface_permissions.h"
#include <hakios-metal/gpu.hpp>
#include <hakios-metal/pm4.hpp>
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <map>
#include <vector>
using namespace hakios::metal;
enum class Defect { None, LostRO, Alias, CPUWrite, NewBO, MapBO, Queue, AllowSubmit,
                    WaitTimeout, NoFence, Close, CPURead, CPUFini, WrongErrno };
struct Wire final : Transport {
    Defect defect;
    uint64_t bytes, bias;
    unsigned calls = 0, maps = 0, unmaps = 0, closes = 0, queueCloses = 0, waits = 0, submits = 0;
    std::vector<uint32_t> words = std::vector<uint32_t>(4096);
    Wire(Defect d, uint64_t b, uint64_t o): defect(d), bytes(b), bias(o) {}
    int call(uint32_t request, void* data, size_t size) override {
        ++calls;
        switch (request) {
        case kHakiosSurface: {
            assert(size == sizeof(HakiosSurface)); auto& r = *static_cast<HakiosSurface*>(data);
            assert(r.surface == 77); r.handle = 1; r.size = bytes; return 0;
        }
        case kGemInfo: {
            assert(size == sizeof(MsmGemInfo)); auto& r = *static_cast<MsmGemInfo*>(data);
            assert(r.handle == 1 || r.handle == 2);
            if (r.info == 1) r.value = 0x10000000 + (r.handle == 1 ? bias : 0x10000);
            else { assert(r.handle == 1 && r.info == 5); r.value = defect == Defect::LostRO ? 0 : kBoGpuReadOnly; }
            return 0;
        }
        case kGemNew: {
            assert(size == sizeof(MsmGemNew)); auto& r = *static_cast<MsmGemNew*>(data);
            assert(r.size == 16384 && r.flags == (kBoGpuReadOnly | kBoWriteCombined));
            if (defect == Defect::NewBO) return ENOMEM;
            r.handle = 2; return 0;
        }
        case kGemCpuPrep: {
            assert(size == sizeof(MsmGemCpuPrep)); auto& r = *static_cast<MsmGemCpuPrep*>(data);
            assert(r.handle == 1 && (r.op == 1 || r.op == 2));
            assert(r.timeout.seconds == 1 && r.timeout.nanoseconds == 100);
            if (r.op == 1) return defect == Defect::CPURead ? EIO : 0;
            return defect == Defect::CPUWrite ? 0 : (defect == Defect::WrongErrno ? EIO : EINVAL);
        }
        case kGemCpuFini:
            assert(size == sizeof(MsmGemCpuFini) && static_cast<MsmGemCpuFini*>(data)->handle == 1);
            return defect == Defect::CPUFini ? EIO : 0;
        case kSubmitQueueNew: {
            assert(size == sizeof(MsmSubmitQueue)); auto& r = *static_cast<MsmSubmitQueue*>(data);
            assert(r.prio == 0 && r.flags == 0);
            if (defect == Defect::Queue) return ENOMEM;
            r.id = 8; return 0;
        }
        case kGemSubmit: {
            ++submits; assert(size == sizeof(MsmGemSubmit)); auto& r = *static_cast<MsmGemSubmit*>(data);
            assert(r.flags == kPipe3D && r.queueid == 8 && r.nr_bos == 2 && r.nr_cmds == 1 && r.fence_fd == -1);
            const auto* bos = reinterpret_cast<const MsmSubmitBo*>(r.bos);
            assert(bos[0].handle == 2 && bos[0].flags == kSubmitBoRead);
            assert(bos[1].handle == 1 && bos[1].flags == kSubmitBoWrite && bos[1].presumed == 0x10000000 + bias);
            const auto& cmd = *reinterpret_cast<const MsmSubmitCmd*>(r.cmds);
            assert(cmd.type == 1 && cmd.submit_idx == 0 && cmd.submit_offset == 0 && cmd.size == 8 && !cmd.nr_relocs);
            assert(words[0] == pm4::type7(pm4::kNop, 1) && words[1] == 0);
            if (defect == Defect::AllowSubmit || defect == Defect::WaitTimeout || defect == Defect::NoFence) {
                r.fence = defect == Defect::NoFence ? 0 : 5; return 0;
            }
            return EINVAL;
        }
        case kWaitFence: {
            ++waits; assert(size == sizeof(MsmWaitFence)); auto& r = *static_cast<MsmWaitFence*>(data);
            assert(r.queueid == 8 && r.fence == 5);
            return defect == Defect::WaitTimeout ? ETIMEDOUT : 0;
        }
        case kSubmitQueueClose:
            ++queueCloses; assert(size == 4 && *static_cast<uint32_t*>(data) == 8);
            return defect == Defect::Close ? EIO : 0;
        case kGemClose:
            ++closes; assert(size == sizeof(DrmGemClose)); return 0;
        default: assert(false); return EINVAL;
        }
    }
    void* map(uint32_t handle, uint64_t size) override {
        ++maps;
        if (handle == 1) { assert(size == bytes); return defect == Defect::Alias ? words.data() : nullptr; }
        assert(handle == 2 && size == 16384);
        return defect == Defect::MapBO ? nullptr : words.data();
    }
    void unmap(uint32_t, void*) override { ++unmaps; }
    int64_t nowNs() override { return 100; }
};
int main() {
    unsigned scenarios = 0;
    for (uint64_t bias : {0, 64, 4032}) for (uint64_t bytes : {65, 4095, 16384, 65549}) {
        auto transport = std::make_unique<Wire>(Defect::None, bytes, bias); auto* wire = transport.get();
        Gpu gpu(std::move(transport)); SurfaceInfo info; int error = -1;
        auto source = gpu.surfaceBo(77, &info, &error); assert(source && !error);
        gauguin_surface_permissions report;
        assert(gauguin_inspect_surface(gpu, *source, bytes, bias, report));
        assert(report.cpu_write_errno == EINVAL && report.gpu_write_errno == EINVAL && report.fence == 0);
        assert(!report.uncertain_dma && wire->submits == 1 && wire->queueCloses == 1 && !wire->waits);
        assert(gpu.allocatedBytes() == 0); source.reset(); assert(wire->closes == 2 && wire->unmaps == 1);
        ++scenarios;
    }
    for (Defect defect : {Defect::LostRO, Defect::Alias, Defect::CPUWrite, Defect::NewBO, Defect::MapBO,
          Defect::Queue, Defect::AllowSubmit, Defect::WaitTimeout, Defect::NoFence, Defect::Close,
          Defect::CPURead, Defect::CPUFini, Defect::WrongErrno}) {
        auto transport = std::make_unique<Wire>(defect, 65549, 64); auto* wire = transport.get();
        Gpu gpu(std::move(transport)); SurfaceInfo info; int error = 0;
        auto source = gpu.surfaceBo(77, &info, &error); assert(source && !error);
        gauguin_surface_permissions report;
        assert(!gauguin_inspect_surface(gpu, *source, 65549, 64, report));
        if (defect == Defect::WaitTimeout || defect == Defect::NoFence) {
            assert(report.uncertain_dma && gpu.allocatedBytes() == 16384 && !wire->queueCloses && !wire->unmaps);
        } else { assert(!report.uncertain_dma && gpu.allocatedBytes() == 0); }
        if (defect == Defect::AllowSubmit) assert(wire->waits == 1 && wire->queueCloses == 1 && wire->closes == 1);
        source.reset(); ++scenarios;
    }
    std::printf("task-surface permission probe: %u real-Gpu request/lifetime scenarios PASS (typed Transport, not hardware)\n", scenarios);
}
