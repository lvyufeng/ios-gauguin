/* SPDX-License-Identifier: MIT
 * A619 port profile for Mesa24.3.4 (769e51468b49b2a42f0a0eaf71cf9eed5ff4e5de).
 * Include before any instantiation of fd6_emit.h templates, in every selected
 * native TU. The primary Mesa tree is never modified.
 *
 * fd6_emit.h passes USER_32B for sequence fences and ALWAYSON for queries,
 * but its A6XX branch ignores that distinction. adreno_pm4.xml documents
 * bit30 as timestamp-instead-of-packet-value. The same release's computerator
 * emits addressed USER_32B events without bit30, as does historical Gallium.
 * This explicit port profile preserves ALWAYSON for RB_DONE timestamp queries
 * and selects packet values for sequence fences. It is not a claim about all
 * A6xx firmware, an upstream fix, or hardware/rendering qualification.
 *
 * A619_EVENT_SOURCE_PROFILE=0 retains the original implementation as a byte
 * comparison control. No captured packet is edited after native generation.
 */
#ifndef GAUGUIN_A619_EVENT_SOURCE_PROFILE_H
#define GAUGUIN_A619_EVENT_SOURCE_PROFILE_H

#if !defined(FD_BO_NO_HARDPIN) || FD_BO_NO_HARDPIN != 1
#error "Match the original selected A6xx TUs' hardpin path before including headers"
#endif
#if !defined(A619_EVENT_SOURCE_PROFILE) || \
    (A619_EVENT_SOURCE_PROFILE != 0 && A619_EVENT_SOURCE_PROFILE != 1)
#error "Explicitly select original control (0) or A619 event-source profile (1)"
#endif

#include <stdlib.h>
#include "fd6_emit.h"

#if A619_EVENT_SOURCE_PROFILE
template <>
inline void
__event_write<A6XX>(struct fd_ringbuffer *ring, enum fd_gpu_event event,
                    enum event_write_src esrc, enum event_write_dst edst,
                    uint32_t val, struct fd_bo *bo, uint32_t offset,
                    uint64_t orval, int32_t shift)
{
   /* Reject unsupported sources/destinations before emitting even a header.
    * The original timestamp-query caller uses RB_DONE/ALWAYSON/RAM. */
   if ((uint32_t)event >= FD_GPU_EVENT_MAX || edst != EV_DST_RAM ||
       !(esrc == EV_WRITE_USER_32B ||
         (esrc == EV_WRITE_ALWAYSON && event == FD_RB_DONE)))
      abort();

   const struct fd_gpu_event_info info = fd_gpu_events<A6XX>[event];
   const unsigned len = info.needs_seqno ? 4 : 1;
   OUT_PKT7(ring, CP_EVENT_WRITE, len);
   OUT_RING(ring, CP_EVENT_WRITE_0_EVENT(info.raw_event) |
                 COND(esrc == EV_WRITE_ALWAYSON, CP_EVENT_WRITE_0_TIMESTAMP));

   if (info.needs_seqno) {
      OUT_RELOC(ring, bo, offset, orval, shift);
      OUT_RING(ring, val);
   }
}
#endif
#endif
