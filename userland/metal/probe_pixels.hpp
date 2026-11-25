// SPDX-License-Identifier: MIT
// CPU expectations for synthetic probe images, independent of GPU readback.
#pragma once
#include <cstddef>
#include <cstdint>

namespace gauguin::metal_probe {
constexpr uint32_t kWidth=64,kHeight=64,kPixels=kWidth*kHeight;
constexpr uint32_t rgba(uint32_t r,uint32_t g,uint32_t b,uint32_t a=255) {
    return r|(g<<8)|(b<<16)|(a<<24);
}
constexpr uint32_t binaryColor(uint32_t bits) {
    return rgba(bits&1?255:0,bits&2?255:0,bits&4?255:0);
}
constexpr uint32_t checker(uint32_t seed,uint32_t x,uint32_t y) {
    return binaryColor((seed&7)^((((x/8)+(y/8)+(seed>>3))&1)?7:0));
}
constexpr bool inTriangle(uint32_t x,uint32_t y) {
    // Screen vertices (0,0),(64,0),(0,63). No pixel center is on its
    // diagonal: 63*(2*x+1)+64*(2*y+1) is odd, the boundary8064 even.
    return 63u*(2*x+1)+64u*(2*y+1)<8064u;
}
constexpr uint32_t triangle(uint32_t x,uint32_t y) {
    return inTriangle(x,y)?rgba(255,0,0):rgba(0,0,255);
}
constexpr uint32_t computeWord(uint32_t seed,uint32_t i) {
    return i*UINT32_C(0x9e3779b1)+seed;
}
struct Vertex { float x,y;uint8_t color[4]; };
static_assert(sizeof(Vertex)==12 && offsetof(Vertex,color)==8);
inline constexpr Vertex kTriangle[3]={
    {-1,1,{255,0,0,255}},{1,1,{255,0,0,255}},
    {-1,-0.96875f,{255,0,0,255}}
};
inline constexpr Vertex kQuad[6]={
    {-1,1,{0,0,0,255}},{1,1,{255,0,0,255}},{-1,-1,{0,255,0,255}},
    {1,1,{255,0,0,255}},{1,-1,{255,255,0,255}},{-1,-1,{0,255,0,255}}
};
constexpr uint64_t kPremultipliedHalf=UINT64_C(0x3c00000038003800);

struct Comparison {
    bool equal=true;
    size_t checked=0,firstBad=0;
    uint64_t actual=0,expected=0,hash=UINT64_C(14695981039346656037);
};
template<class T,class Expected>
Comparison compare(const T* values,size_t count,Expected expected) {
    Comparison r;
    for (size_t i=0;i<count;i++) {
        T want=expected(i),got=values[i];
        if (got!=want && r.equal) {
            r.equal=false;r.firstBad=i;r.actual=got;r.expected=want;
        }
        for (size_t b=0;b<sizeof(T);b++) r.hash=(r.hash^uint8_t(uint64_t(got)>>(8*b)))*UINT64_C(1099511628211);
        ++r.checked;
    }
    return r;
}
} // namespace gauguin::metal_probe
