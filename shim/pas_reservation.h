#ifndef LOW_PAS_RESERVATION_H
#define LOW_PAS_RESERVATION_H
#include <stddef.h>
#include <stdint.h>
#define PAS_REQUEST_BYTES 128u
#define PAS_TAIL_BYTES UINT64_C(0x200000)
#define PAS_REGION_BYTES UINT64_C(0x100000)
#define PAS_ALIGNMENT UINT64_C(0x100000)
#define PAS_WIMG UINT32_C(0xd0000006)
#define PAS_SIGNATURE UINT32_C(0x50415331)
enum pas_status {
    PAS_DISABLED = 0,
    PAS_READY = 1,
    PAS_BAD_INPUT = -1,
    PAS_BAD_PAYLOAD = -2,
    PAS_BAD_ADT = -3,
    PAS_BAD_REQUEST = -4,
    PAS_BAD_FDT = -5,
    PAS_RANGE = -6,
    PAS_OVERLAP = -7,
    PAS_AMBIGUOUS = -8
};
struct pas_context {
    const uint8_t *payload, *fdt;
    size_t payload_bytes, fdt_bytes;
    uint64_t payload_pa, fdt_pa, shim_pa, shim_bytes;
};
struct pas_plan {
    uint64_t pa, bytes, tail_offset, payload_pa, payload_bytes;
    uint64_t fdt_pa, fdt_bytes, shim_pa, shim_bytes, managed_pa, managed_bytes;
    uint32_t adt_offset, adt_bytes, request_name, request_value, io_name, io_value;
    uint32_t exact_initrd_reservations, fixed_reservations, dynamic_pools;
};
/* Caller guarantees that the ABL FDT pointer has at least its40-byte header.
 * This only obtains a bounded extent; prepare validates all offsets/tokens. */
size_t pas_fdt_header_size(const uint8_t *fdt);
/* Read-only metadata planning. NEVER reads/hashes/zeros the tail or selected
 * PAS bytes. Context is the actual loader handoff, not supplied by the ADT.
 * Output is untouched on disabled/error. No heap, MMIO or secure calls. */
/* Bounded original-FDT parser used before legacy initrd lookups/accesses. */
int pas_initrd(const uint8_t *, size_t, uint64_t *start, uint64_t *end);
int pas_prepare(const struct pas_context *, struct pas_plan *);
/* Patch only the already copied ADT after successful prepare and normal
 * copies. Caller keeps the private plan immutable. Every check precedes the
 * first write; only success publishes actual owner and pmap property names.
 * No PAS mapping, access, loading or authentication is performed. */
int pas_commit(uint8_t *copied_adt, size_t adt_bytes, const struct pas_plan *);
#endif
