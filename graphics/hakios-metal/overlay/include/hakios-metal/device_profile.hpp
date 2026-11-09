// SPDX-License-Identifier: MIT
// Target facts from Mesa 25.0.7 freedreno_devices.py; kernel wire pipe is
// platform-specific. Compiler feature selection still uses Mesa's full table.
#pragma once
#include <cstdint>

namespace hakios::metal::device {

struct Magic {
    uint32_t pcPower = 1;
    uint32_t tpl1Dbg = 0x05008000;
    uint32_t grasDbg = 0;
    uint32_t spChicken = 0x1400;
    uint32_t ucheClient = 0x84;
    uint32_t pcMode = 0x1f;
    uint32_t spDbg = 6;
    uint32_t rbDbg = 0x04100000;
    uint32_t hlsqDbg = 0;
    uint32_t rbUnknown8e01 = 0;
    uint32_t vpcDbg = 0x02000000;
    uint32_t ucheUnknown0e12 = 1;
};

struct Profile {
    uint32_t chipId = 0x06030500, gpuId = 0;
    uint32_t pipe = 1;
    uint32_t numSp = 2, numCcu = 2, fibersPerSp = 4096;
    uint32_t instrCacheSize = 127, regSizeVec4 = 64;
    uint32_t csSharedBytes = 32768;
    uint32_t threadsizeBase = 64, maxWaves = 16, waveGranularity = 2;
    uint32_t gmemBytes = 512 * 1024;
    uint32_t depthCacheBytes = 65536, colorCacheBytes = 65536;
    uint32_t gmemColorCacheDivisor = 4;
    uint32_t tileAlignW = 32, tileAlignH = 16;
    uint32_t gmemAlignW = 16, gmemAlignH = 4;
    uint32_t tileMaxW = 1024, tileMaxH = 1008, numVscPipes = 32;
    uint32_t highestBankBit = 14, ubwcSwizzle = 6, macrotileMode = 1;
    bool hasLpac = true;
    bool supportsDoubleThreadsize = true;
    bool hasGmemFastClear = true, concurrentResolve = false;
    bool hasEarlyPreamble = false;
    bool hasCubicFilter = true;
    bool indirectDrawWfm = false, depthBoundsRequireDepthTest = false;
    bool hasScalarAlu = true, hasGetFiberId = true;
    bool hasDp2Acc = true, hasDp4Acc = true;
    bool hasCpRegWrite = false, has8bppUbwc = false;
    bool requireExplicitChip = false;
    Magic magic;
};

inline constexpr Profile kA635{};

constexpr Profile a619() {
    Profile p;
    p.chipId = 0x06010900;
    p.gpuId = 619;
    p.pipe = 0x10; // gauguin GET_PARAM and GEM_SUBMIT both require MSM_PIPE_3D0.
    p.numSp = p.numCcu = 1;
    p.fibersPerSp = 2048;
    p.instrCacheSize = 64;
    p.regSizeVec4 = 96;
    p.tileAlignH = 32;
    p.highestBankBit = 14;
    p.macrotileMode = 0;
    p.hasLpac = false;
    p.hasCubicFilter = false;
    p.indirectDrawWfm = true;
    p.depthBoundsRequireDepthTest = true;
    p.hasScalarAlu = p.hasGetFiberId = false;
    p.hasDp2Acc = p.hasDp4Acc = false;
    p.hasCpRegWrite = p.has8bppUbwc = true;
    p.requireExplicitChip = true;
    p.magic.pcPower = 0;
    p.magic.tpl1Dbg = 0x00108000;
    p.magic.grasDbg = 0x00000880;
    p.magic.spChicken = 0x00000430;
    p.magic.ucheClient = 4;
    p.magic.spDbg = 0;
    p.magic.hlsqDbg = 0x00080000;
    p.magic.rbUnknown8e01 = 1;
    p.magic.vpcDbg = 0;
    return p;
}
inline constexpr Profile kA619 = a619();

#if defined(HAKIOS_METAL_TARGET_A619)
inline constexpr Profile kTarget = kA619;
#else
inline constexpr Profile kTarget = kA635;
#endif

constexpr bool acceptsChip(uint32_t chip) {
    return chip == kTarget.chipId || (chip == 0 && !kTarget.requireExplicitChip);
}

static_assert(kTarget.numSp && kTarget.numSp == kTarget.numCcu);
static_assert(kTarget.gmemBytes > kTarget.numCcu * kTarget.colorCacheBytes);
} // namespace hakios::metal::device
