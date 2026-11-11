#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "pas_reservation.h"
#include "gauguin_handoff_memory.h"

static uint64_t get64(const uint8_t *p)
{
    uint64_t v;
    memcpy(&v, p, sizeof(v));
    return v;
}

static void set64(uint8_t *p, uint64_t value)
{
    memcpy(p, &value, sizeof(value));
}

static uint32_t be32(const uint8_t *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
}

static size_t find(const uint8_t *p, size_t size, const char *tag)
{
    size_t len = strlen(tag);
    for (size_t i = 0; i + len <= size; ++i) {
        if (!memcmp(p + i, tag, len))
            return i;
    }
    assert(!"required fixture property missing");
    return 0;
}

static size_t load(const char *path, uint8_t **out)
{
    FILE *f = fopen(path, "rb");
    assert(f && fseek(f, 0, SEEK_END) == 0);
    long len = ftell(f);
    assert(len > 0 && len <= (32 << 20) && fseek(f, 0, SEEK_SET) == 0);
    size_t mapped = ((size_t)len + 0x3fff) & ~(size_t)0x3fff;
    *out = mmap(NULL, mapped, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    assert(*out != MAP_FAILED && fread(*out, 1, (size_t)len, f) == (size_t)len);
    assert(fclose(f) == 0);
    return (size_t)len;
}

struct fixture {
    uint8_t *capture, *pas, *io;
    struct gh_live live;
    struct gh_inventory inventory;
};

static enum gh_status read_inventory(struct fixture *f, size_t size)
{
    return gh_read_memory(f->capture, size, f->pas, 128, f->io, 24, &f->live, &f->inventory);
}

int main(int argc, char **argv)
{
    assert(argc == 5);
    uint8_t *input, *fdt;
    size_t input_size = load(argv[1], &input), fdt_size = load(argv[2], &fdt);
    assert(input_size == 20480000 && fdt_size == 588757);
    size_t offset = get64(input + 32), adt_bytes = get64(input + 40);
    assert(offset + adt_bytes < input_size - PAS_TAIL_BYTES);
    size_t value = find(input + offset, adt_bytes, "GHFDREQ1");
    size_t pas = find(input + offset, adt_bytes, "LPASREQ1");
    size_t tuple = find(input + offset, adt_bytes, "LowPASIOPending") + 36;

    const size_t bytes = 0x4000000;
    uint8_t *mapping = mmap(NULL, 2 * bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    assert(mapping != MAP_FAILED);
    uint64_t managed = ((uintptr_t)mapping + bytes - 1) & ~(uint64_t)(bytes - 1);
    set64(input + 56, managed);
    set64(input + 64, bytes);
    set64(input + offset + find(input + offset, adt_bytes, "dram-base") + 36, managed);
    set64(input + offset + find(input + offset, adt_bytes, "dram-size") + 36, bytes);

    struct pas_context context = {input, fdt, input_size, fdt_size, 0xb0000000, 0xb8000000, 0x80080000, 233472};
    assert(!mprotect(input + input_size - PAS_TAIL_BYTES, PAS_TAIL_BYTES, PROT_NONE));
    uint64_t copy_pa = managed + get64(input + 48) - get64(input + 16);
    uint64_t args = (copy_pa + adt_bytes + 0x3fff) & ~UINT64_C(0x3fff);
    uint8_t *copy = (uint8_t *)(uintptr_t)copy_pa;
    memcpy(copy, input + offset, adt_bytes);
    struct pas_handoff_plan plan;
    const struct gh_range fb = {0xa0000000, 10368000};
    int prepared = pas_handoff_prepare(&context, fb.base, fb.size, &plan);
    if (prepared != PAS_READY)
        fprintf(stderr, "actual handoff producer returned %d\n", prepared);
    assert(prepared == PAS_READY);
    struct fixture f = {
        .capture = copy + value, .pas = copy + pas, .io = copy + tuple,
        .live = {{managed, bytes}, {copy_pa, adt_bytes}, fb, args, args + 0x4000},
    };
    const size_t size = GH_HEADER + GH_MAX_FDT;
    assert(read_inventory(&f, size) == GH_BAD_RECORD);
    assert(pas_handoff_commit(&context, copy, adt_bytes, fb.base, fb.size, &plan) == PAS_READY);
    assert(read_inventory(&f, size) == GH_BAD_PAS);
    assert(pas_commit(copy, adt_bytes, &plan.owner) == PAS_READY);
    assert(read_inventory(&f, size) == GH_OK);

    struct gh_inventory *m = &f.inventory;
    assert(m->bank_count == 3 && m->header_reserve_count == 0);
    assert(m->fixed_count == 21 && m->pool_count == 6 && m->alloc_count == 6);
    assert(m->banks[0].base == 0x80000000 && m->banks[0].size == 0x3bb00000);
    assert(m->banks[1].base == UINT64_C(0x180000000) && m->banks[1].size == UINT64_C(0x100000000));
    assert(m->banks[2].base == 0xc0000000 && m->banks[2].size == 0xc0000000);
    assert(m->input.base == context.payload_pa && m->pas.base == plan.owner.pa);
    assert(m->original_fdt.base == context.fdt_pa && m->original_fdt.size == fdt_size);
    for (uint32_t i = 0; i < m->pool_count; ++i) {
        assert(m->pools[i].alloc_count == 1 && m->pools[i].first_alloc == i);
        assert(m->allocations[i].base == 0 && m->allocations[i].size == 0xffffffff);
    }
    assert(!memcmp(f.capture + GH_HEADER, fdt, fdt_size));

    assert(read_inventory(&f, size - 1) == GH_BAD_RECORD);
    assert(read_inventory(&f, GH_HEADER - 1) == GH_BAD_RECORD);
    for (size_t i = 0; i < GH_HEADER; ++i) {
        f.capture[i] ^= 0x80;
        assert(read_inventory(&f, size) != GH_OK);
        f.capture[i] ^= 0x80;
    }
    f.capture[size - 1] = 1;
    assert(read_inventory(&f, size) == GH_BAD_RECORD);
    f.capture[size - 1] = 0;
    f.live.top -= 0x4000;
    assert(read_inventory(&f, size) == GH_BAD_CONTEXT);
    f.live.top += 0x4000;
    for (size_t i = 0; i < 128; ++i) {
        f.pas[i] ^= 1;
        assert(read_inventory(&f, size) == GH_BAD_PAS);
        f.pas[i] ^= 1;
    }
    for (size_t i = 0; i < 24; ++i) {
        f.io[i] ^= 1;
        assert(read_inventory(&f, size) == GH_BAD_PAS);
        f.io[i] ^= 1;
    }

    uint8_t *tree = f.capture + GH_HEADER;
    size_t structure = be32(tree + 8), strings = be32(tree + 12);
    tree[structure + 3] = 7;
    assert(read_inventory(&f, size) == GH_BAD_FDT);
    tree[structure + 3] = 1;
    memcpy(tree + 12, tree + 8, 4);
    assert(read_inventory(&f, size) == GH_BAD_FDT);
    memcpy(tree + 12, fdt + 12, 4);
    size_t name = find(tree + strings, fdt_size - strings, "alloc-ranges");
    unsigned windows = 0;
    for (size_t i = structure; i + 28 <= strings; i += 4) {
        if (be32(tree + i) == 3 && be32(tree + i + 4) == 16 && be32(tree + i + 8) == name) {
            memset(tree + i + 20, 0, 8);
            assert(read_inventory(&f, size) == GH_BAD_FDT);
            memcpy(tree + i + 20, fdt + i + 20, 8);
            ++windows;
        }
    }
    assert(windows == 6 && read_inventory(&f, size) == GH_OK);
    assert(!memcmp(tree, fdt, fdt_size));

    uint8_t block[GH_RECEIPT_BLOCK], hash[GH_DIGEST];
    assert(strlen(argv[3]) == 2 * GH_DIGEST);
    for (unsigned i = 0; i < GH_DIGEST; ++i) {
        unsigned byte;
        assert(sscanf(argv[3] + 2 * i, "%2x", &byte) == 1 && byte < 256);
        hash[i] = (uint8_t)byte;
    }
    assert(gh_pack_memory(block, 266001, GH_OK, &f.live, m, tree, hash) == 2512);
    FILE *receipt = fopen(argv[4], "wb");
    assert(receipt && fwrite(block, 1, sizeof(block), receipt) == sizeof(block) && fclose(receipt) == 0);
    m->fixed_count = GH_FIXED_LIMIT;
    assert(gh_pack_memory(block, 266001, GH_OK, &f.live, m, tree, hash) == GH_RECEIPT_HEADER);
    assert(block[16] == GH_RECEIPT_OVERFLOW);
    for (unsigned i = 20; i < GH_RECEIPT_BLOCK; ++i)
        assert(!block[i]);
    assert(gh_pack_memory(block, 266001, GH_UNAVAILABLE, NULL, NULL, NULL, NULL) == GH_RECEIPT_HEADER);
    assert(block[16] == GH_UNAVAILABLE);
    assert(gh_pack_memory(block, 0, GH_UNAVAILABLE, NULL, NULL, NULL, NULL) == 0);
    assert(munmap(input, (input_size + 0x3fff) & ~(size_t)0x3fff) == 0);
    assert(munmap(fdt, (fdt_size + 0x3fff) & ~(size_t)0x3fff) == 0);
    assert(munmap(mapping, 2 * bytes) == 0);
    puts("Actual shim producer and XNU reader: 3 banks, 21 fixed reservations, 6 unresolved pools; corrupt metadata rejected.");
}
