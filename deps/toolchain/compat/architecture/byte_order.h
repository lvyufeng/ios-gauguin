/* Darwin <architecture/byte_order.h> for the host tools. */
#pragma once
#include <stdint.h>
enum NXByteOrder { NX_UnknownByteOrder, NX_LittleEndian, NX_BigEndian };
static inline uint32_t OSSwapInt32(uint32_t x) { return __builtin_bswap32(x); }
static inline uint64_t OSSwapInt64(uint64_t x) { return __builtin_bswap64(x); }
static inline uint16_t OSSwapInt16(uint16_t x) { return __builtin_bswap16(x); }
static inline uint32_t OSSwapConstInt32(uint32_t x) { return __builtin_bswap32(x); }
static inline uint16_t OSSwapBigToHostInt16(uint16_t x) { return __builtin_bswap16(x); }
static inline uint32_t OSSwapBigToHostInt32(uint32_t x) { return __builtin_bswap32(x); }
static inline uint64_t OSSwapBigToHostInt64(uint64_t x) { return __builtin_bswap64(x); }
static inline uint16_t OSSwapHostToBigInt16(uint16_t x) { return __builtin_bswap16(x); }
static inline uint32_t OSSwapHostToBigInt32(uint32_t x) { return __builtin_bswap32(x); }
static inline uint64_t OSSwapHostToBigInt64(uint64_t x) { return __builtin_bswap64(x); }
static inline uint16_t OSSwapLittleToHostInt16(uint16_t x) { return x; }
static inline uint32_t OSSwapLittleToHostInt32(uint32_t x) { return x; }
static inline uint64_t OSSwapLittleToHostInt64(uint64_t x) { return x; }
static inline uint16_t OSSwapHostToLittleInt16(uint16_t x) { return x; }
static inline uint32_t OSSwapHostToLittleInt32(uint32_t x) { return x; }
static inline uint64_t OSSwapHostToLittleInt64(uint64_t x) { return x; }
static inline enum NXByteOrder NXHostByteOrder(void) { return NX_LittleEndian; }
