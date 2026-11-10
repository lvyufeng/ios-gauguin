// SPDX-License-Identifier: MIT
// Native half buffer loads, vertex arithmetic, half varyings, fragment
// arithmetic and RGBA16F stores; all colors and parameters arrive at runtime.
#include <metal_stdlib>
using namespace metal;

struct NativeFP16Out {
    float4 position [[position]];
    half4 color;
};
struct NativeFP16Params { half4 scale; half4 bias; };

vertex NativeFP16Out gauguin_fp16_vertex(uint id [[vertex_id]],
                                       const device float4 *positions [[buffer(0)]],
                                       const device half4 *colors [[buffer(1)]])
{
    NativeFP16Out out;
    out.position = positions[id];
    out.color = colors[id] * half4(0.5h);
    return out;
}

fragment half4 gauguin_fp16_fragment(NativeFP16Out in [[stage_in]],
                                   constant NativeFP16Params &params [[buffer(0)]])
{
    return in.color * params.scale + params.bias;
}
