// SPDX-License-Identifier: MIT
// Own patterns for graphics storage-image writes, ordered reads and both stages.
#include <metal_stdlib>
using namespace metal;

struct ImageVertexIn {
    float2 position [[attribute(0)]];
    float4 color [[attribute(1)]];
};
struct ImageVertexOut {
    float4 position [[position]];
    float4 color;
};
vertex ImageVertexOut image_vertex(ImageVertexIn in [[stage_in]])
{
    return {float4(in.position, 0, 1), in.color};
}
// Rasterizing vertex functions keep resources read-only. Writable vertex
// functions need a separate void/rasterization-disabled qualification.
vertex ImageVertexOut image_vertex_texture(ImageVertexIn in [[stage_in]],
                                         uint id [[vertex_id]],
                                         texture2d<uint> source [[texture(0)]])
{
    uint value = source.read(uint2(id, 0)).x;
    float4 color = float4((value & 1u) ? 1 : 0, (value & 2u) ? 1 : 0, (value & 4u) ? 1 : 0, 1);
    return {float4(in.position, 0, 1), color};
}
struct ImageBufferVertex { float4 position; float4 color; };
vertex ImageVertexOut image_buffer_vertex(device const ImageBufferVertex *vertices [[buffer(0)]],
                                                uint id [[vertex_id]],
                                                texture2d<uint> source [[texture(0)]])
{
    uint value = source.read(uint2(id, 0)).x ^ uint(vertices[id].color.x);
    float4 color = float4((value & 1u) ? 1 : 0, (value & 2u) ? 1 : 0, (value & 4u) ? 1 : 0, 1);
    return {vertices[id].position, color};
}
fragment float4 image_write_fragment(ImageVertexOut in [[stage_in]],
                                     texture2d<uint, access::write> output [[texture(3)]],
                                     constant uint &seed [[buffer(0)]])
{
    uint2 xy = uint2(in.position.xy);
    uint bits = uint(in.color.x > 0.5f) | (uint(in.color.y > 0.5f) << 1) | (uint(in.color.z > 0.5f) << 2);
    output.write(uint4(seed ^ (xy.x * 17u) ^ (xy.y * 29u) ^ bits, 0, 0, 0), xy);
    return float4(0, 0, 0, 1);
}
fragment float4 image_rw_fragment(ImageVertexOut in [[stage_in]],
                                  texture2d<uint, access::read_write> output [[texture(3)]],
                                  constant uint &seed [[buffer(0)]])
{
    uint2 xy = uint2(in.position.xy);
    output.write(uint4(output.read(xy).x ^ seed, 0, 0, 0), xy);
    return float4(0, 0, 0, 1);
}
fragment float4 image_sample_fragment(ImageVertexOut in [[stage_in]], texture2d<uint> source [[texture(0)]])
{
    uint value = source.read(uint2(in.position.xy)).x;
    return float4((value & 1u) ? 1 : 0, (value & 2u) ? 1 : 0, (value & 4u) ? 1 : 0, 1);
}
