/* Darwin <libkern/OSByteOrder.h> subset. */
#pragma once
#include <stdint.h>
#define OSSwapInt16(x) __builtin_bswap16(x)
#define OSSwapInt32(x) __builtin_bswap32(x)
#define OSSwapInt64(x) __builtin_bswap64(x)
#define OSSwapConstInt32(x) __builtin_bswap32(x)
