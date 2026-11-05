#include "nvt_firmware.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const size_t FILE_BYTES = 139264;
/* These are the pinned image's exact destination extents, not a claim about
 * the chip's complete SRAM capacity or authorization to program it. */
static struct nfw_policy policy = {2, {{0, 0x13608}, {0x27040, 0x44a0}}};
static void put32(uint8_t *p, uint32_t v)
{
    for (unsigned i = 0; i < 4; ++i) p[i] = (uint8_t)(v >> (8 * i));
}
static void reject(const uint8_t *bytes, size_t length, const struct nfw_policy *p, enum nfw_result want)
{
    struct nfw_image image, before;
    memset(&image, 0xa5, sizeof(image)); memcpy(&before, &image, sizeof(image));
    assert(nfw_parse(bytes, length, p, &image) == want);
    assert(!memcmp(&image, &before, sizeof(image)));
}
static void check_plan(const struct nfw_image *image, unsigned max_wire)
{
    uint32_t expected_count = 0, count = 0, total = 0;
    uint32_t covered[NFW_MAX_PARTITIONS] = {0};
    struct nfw_cursor cursor = {0};
    struct nfw_chunk chunk, sentinel; int done = -1;
    assert(nfw_chunk_count(image, max_wire, &expected_count) == NFW_OK);
    for (;;) {
        memset(&chunk, 0x5a, sizeof(chunk)); memcpy(&sentinel, &chunk, sizeof(chunk));
        assert(nfw_next(image, max_wire, &cursor, &chunk, &done) == NFW_OK);
        if (done) { assert(!memcmp(&chunk, &sentinel, sizeof(chunk))); break; }
        const struct nfw_partition *p = &image->parts[chunk.partition];
        assert(chunk.bin_offset == p->bin_offset + covered[chunk.partition]);
        assert(chunk.sram == p->sram + covered[chunk.partition]);
        assert(chunk.payload_bytes && chunk.wire_bytes == chunk.payload_bytes + 1);
        assert(chunk.wire_bytes <= max_wire);
        assert((chunk.sram & 127) + chunk.payload_bytes <= 128);
        assert(chunk.page[0] == 255 && chunk.command != 255);
        uint32_t page = ((uint32_t)chunk.page[1] << 15) | ((uint32_t)chunk.page[2] << 7);
        assert((page | (chunk.command & 127)) == chunk.sram);
        assert(chunk.command & 128);
        covered[chunk.partition] += chunk.payload_bytes;
        total += chunk.payload_bytes; ++count;
        assert(count <= image->total_write_bytes);
    }
    assert(count == expected_count && total == image->total_write_bytes);
    for (size_t i = 0; i < image->part_count; ++i) assert(covered[i] == image->parts[i].bytes);
    assert(cursor.partition == image->part_count && cursor.offset == 0);
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    FILE *file = fopen(argv[1], "rb"); assert(file);
    uint8_t *original = malloc(FILE_BYTES), *bytes = malloc(FILE_BYTES); assert(original && bytes);
    assert(fread(original, 1, FILE_BYTES, file) == FILE_BYTES && fgetc(file) == EOF); fclose(file);
    struct nfw_image image;
    assert(nfw_parse(original, FILE_BYTES, &policy, &image) == NFW_OK);
    assert(image.header_bytes == 0x100 && image.needed_file_bytes == 0x20000 && image.version == 0x10);
    assert(image.part_count == 3 && image.table_entries == 15 && image.reserved_entries == 12);
    assert(image.total_write_bytes == 96936);
    const uint32_t offsets[] = {0x100, 0x18100, 0};
    const uint32_t addresses[] = {0, 0x27140, 0x27040};
    const uint32_t sizes[] = {79368, 17312, 256};
    const uint32_t crc[] = {0x15fe9c6d, 0x90fe20f8, 0xb0183db6};
    for (size_t i = 0; i < 3; ++i) {
        assert(image.parts[i].bin_offset == offsets[i] && image.parts[i].sram == addresses[i]);
        assert(image.parts[i].bytes == sizes[i] && image.parts[i].size_field == sizes[i] - 1);
        assert(image.parts[i].golden_crc == crc[i]);
    }
    assert(image.parts[2].kind == NFW_INFO && image.parts[2].index == 12);
    for (unsigned wire = 3; wire <= NFW_MAX_WIRE; ++wire) check_plan(&image, wire);
    uint32_t count; assert(nfw_chunk_count(&image, 64, &count) == NFW_OK && count == 2274);
    struct nfw_cursor cursor = {1, 0}; struct nfw_chunk chunk; int done;
    assert(nfw_next(&image, 64, &cursor, &chunk, &done) == NFW_OK && chunk.payload_bytes == 62);
    assert(nfw_next(&image, 64, &cursor, &chunk, &done) == NFW_OK && chunk.payload_bytes == 2 && chunk.command == 0xfe);

    reject(original, 0, &policy, NFW_BOUNDS);
    reject(original, 0x2f, &policy, NFW_BOUNDS);
    reject(original, 4096, &policy, NFW_END_MARKER);
    reject(original, NFW_MAX_FILE + 1u, &policy, NFW_BOUNDS);
#define MUTATE(pos, value, result) do { memcpy(bytes, original, FILE_BYTES); put32(bytes + (pos), (value)); reject(bytes, FILE_BYTES, &policy, (result)); } while (0)
    MUTATE(0, 0x20, NFW_HEADER); MUTATE(0, 0x31, NFW_HEADER);
    MUTATE(0, UINT32_MAX, NFW_HEADER); MUTATE(0, 0x430, NFW_CAPACITY);
    MUTATE(8, 0, NFW_CRC_LENGTH); MUTATE(20, 0x20000, NFW_CRC_LENGTH);
    MUTATE(12, UINT32_MAX - 8, NFW_BOUNDS);
    MUTATE(12, (uint32_t)FILE_BYTES - 0x439f, NFW_BOUNDS); /* size+1 fencepost */
    MUTATE(16, UINT32_MAX, NFW_SRAM); MUTATE(16, NFW_ADDRESS_LIMIT, NFW_SRAM);
    MUTATE(0xf4, UINT32_MAX, NFW_BOUNDS); MUTATE(0xf8, UINT32_MAX, NFW_BOUNDS);
    MUTATE(0xf0, 0x27140, NFW_OVERLAP); /* Info-12 overwrites DLM */
    MUTATE(0xf0, 0, NFW_OVERLAP); /* duplicate coverage of ILM */
    MUTATE(0xf0, 0x2703f, NFW_SRAM); MUTATE(16, 0x27141, NFW_SRAM);
    memcpy(bytes, original, FILE_BYTES); bytes[0x1f001] ^= 1;
    reject(bytes, FILE_BYTES, &policy, NFW_VERSION);
    memcpy(bytes, original, FILE_BYTES);
    for (size_t end = FILE_BYTES; end >= 4096; end -= 4096) memset(bytes + end - 3, 0, 3);
    reject(bytes, FILE_BYTES, &policy, NFW_END_MARKER);
    struct nfw_policy bad = policy; bad.windows[1] = (struct nfw_window){0, 256};
    reject(original, FILE_BYTES, &bad, NFW_OVERLAP);
    bad = policy; bad.windows[0] = (struct nfw_window){0xfffffff0u, 32};
    reject(original, FILE_BYTES, &bad, NFW_SRAM);
    bad = policy; bad.window_count = NFW_MAX_WINDOWS + 1; reject(original, FILE_BYTES, &bad, NFW_ARGUMENT);
    /* Reserved entry: no size+1 write of a spurious one byte. */
    memcpy(bytes, original, FILE_BYTES); put32(bytes + 0x30, UINT32_MAX); put32(bytes + 0x38, UINT32_MAX);
    assert(nfw_parse(bytes, FILE_BYTES, &policy, &image) == NFW_OK && image.part_count == 3);
    /* Overlay metadata needs to be contained in DLM before dereferencing it. */
    memcpy(bytes, original, FILE_BYTES); bytes[0x28] = 0x11; put32(bytes + 20, 3);
    reject(bytes, FILE_BYTES, &policy, NFW_HEADER);
    memcpy(bytes, original, FILE_BYTES); bytes[0x28] = 0x11;
    put32(bytes + 0x18100, 0x30000); put32(bytes + 0x18104, 31);
    put32(bytes + 0x18108, 0x100); put32(bytes + 0x1810c, 0x12345678);
    struct nfw_policy overlay_policy = policy; overlay_policy.window_count = 3;
    overlay_policy.windows[2] = (struct nfw_window){0x30000, 4096};
    assert(nfw_parse(bytes, FILE_BYTES, &overlay_policy, &image) == NFW_OK && image.part_count == 4);
    check_plan(&image, 64); /* structural fixture only; altered DLM is not CRC-qualified */
    put32(bytes + 0x18100, 0x27140); reject(bytes, FILE_BYTES, &overlay_policy, NFW_OVERLAP);
    /* Planner rejects invalid/ambiguous offsets atomically. */
    assert(nfw_parse(original, FILE_BYTES, &policy, &image) == NFW_OK);
    struct nfw_chunk before; memset(&chunk, 0x5a, sizeof(chunk)); memcpy(&before, &chunk, sizeof(chunk));
    cursor = (struct nfw_cursor){0, 127}; struct nfw_cursor old = cursor; done = 72;
    assert(nfw_next(&image, 64, &cursor, &chunk, &done) == NFW_UNQUALIFIED_OFFSET);
    assert(!memcmp(&chunk, &before, sizeof(chunk)) && !memcmp(&cursor, &old, sizeof(cursor)) && done == 72);
    count = 123; assert(nfw_chunk_count(&image, 2, &count) == NFW_ARGUMENT && count == 123);
    image.parts[1].bytes = UINT32_MAX;
    assert(nfw_next(&image, 64, &cursor, &chunk, &done) == NFW_BOUNDS);
    /* Boundary mutations must never partly publish a rejected parse. */
    uint32_t random = 0x3667502;
    for (unsigned i = 0; i < 10000; ++i) {
        memcpy(bytes, original, FILE_BYTES);
        random ^= random << 13; random ^= random >> 17; random ^= random << 5;
        put32(bytes + 0x30 + (i % 13) * 16 + (i % 4) * 4, random);
        struct nfw_image before_image; memset(&image, 0xa5, sizeof(image)); memcpy(&before_image, &image, sizeof(image));
        enum nfw_result result = nfw_parse(bytes, FILE_BYTES, &policy, &image);
        if (result != NFW_OK) assert(!memcmp(&image, &before_image, sizeof(image)));
        else check_plan(&image, 64);
    }
    free(bytes); free(original);
    puts("firmware parser/page plans passed; no SPI, hardware CRC, identity or boot success simulated");
    return 0;
}
