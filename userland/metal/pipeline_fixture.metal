// SPDX-License-Identifier: MIT
// Known-input public Metal compute/render tests. No system shader dependencies.
#include <metal_stdlib>
using namespace metal;

kernel void gauguin_fill(device uint *out [[buffer(0)]],
                         constant uint &seed [[buffer(1)]],
                         uint i [[thread_position_in_grid]])
{
    if (i < 256) out[i] = i * 0x9e3779b1u + seed;
}

struct VertexIn {
    float2 position [[attribute(0)]];
    float4 color [[attribute(1)]];
};
struct VertexOut {
    float4 position [[position]];
    float4 color;
};
vertex VertexOut gauguin_vertex(VertexIn in [[stage_in]])
{
    VertexOut out;
    out.position = float4(in.position, 0, 1);
    out.color = in.color;
    return out;
}
fragment float4 gauguin_fragment(VertexOut in [[stage_in]])
{
    return in.color;
}

fragment float4 gauguin_uniform_fragment(constant float4 &color [[buffer(0)]])
{
    return color;
}

fragment float4 gauguin_texture_fragment(VertexOut in [[stage_in]],
                                       texture2d<float> image [[texture(0)]],
                                       sampler sample_state [[sampler(0)]])
{
    // The quad interpolates normalized x/y in color.rg, with affine w=1.
    return image.sample(sample_state, in.color.rg);
}
