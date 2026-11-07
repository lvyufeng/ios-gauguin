/* Native packet semantics only. No GPU emulation, MMIO, or device access. */
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "a619_event_source_profile.h"

static struct fd_bo control_bo;
static unsigned attachments;
extern "C" uint32_t fd_bo_size(struct fd_bo *bo)
{
   assert(bo == &control_bo && !bo->map && !bo->dev);
   return bo->size;
}
static void attached(struct fd_ringbuffer *, struct fd_bo *bo)
{
   assert(bo == &control_bo && !bo->map && !bo->dev);
   attachments++;
}
static void forbidden_grow(struct fd_ringbuffer *, uint32_t) { abort(); }
static const struct fd_ringbuffer_funcs functions = {
   .grow = forbidden_grow,
   .emit_bo = attached,
   .assert_attached = attached,
};

int main(int argc, char **argv)
{
   struct fd_ringbuffer ring = {};
   uint32_t words[32] = {};
   ring.start = ring.cur = words;
   ring.end = words + 32;
   ring.size = sizeof(words);
   ring.refcnt = 1;
   ring.funcs = &functions;
   control_bo.iova = 0xfc018c00u;
   control_bo.size = 288;
   control_bo.refcnt = 1;

   /* Invalid combinations must abort before a packet write. A read-only ring
    * distinguishes the intended SIGABRT from any accidental write/SIGSEGV. */
   if (argc == 4) {
      const long page = sysconf(_SC_PAGESIZE);
      assert(page > 0);
      void *p = mmap(NULL, (size_t)page, PROT_READ,
                     MAP_PRIVATE | MAP_ANON, -1, 0);
      assert(p != MAP_FAILED);
      ring.start = ring.cur = (uint32_t *)p;
      ring.end = ring.cur + page / 4;
      __event_write<A6XX>(&ring, (fd_gpu_event)strtoul(argv[1], NULL, 0),
                         (event_write_src)strtoul(argv[2], NULL, 0),
                         (event_write_dst)strtoul(argv[3], NULL, 0),
                         7, &control_bo, 0, 0, 0);
      fputs("UNEXPECTED unsupported event accepted\n", stderr);
      return 90;
   }
   assert(argc == 1);
   const uint32_t values[] = {0, 1, 6, 7, 0x7fffffffu, 0xffffffffu};
   const int shifts[] = {-1, 0, 1};
   unsigned cases = 0;
   for (uint32_t e = 0; e < FD_GPU_EVENT_MAX; e++) {
      const struct fd_gpu_event_info info = fd_gpu_events<A6XX>[e];
      for (uint32_t val : values) {
         for (int shift : shifts) {
            ring.cur = ring.start;
            memset(words, 0xa5, sizeof(words));
            attachments = 0;
            __event_write<A6XX>(&ring, (fd_gpu_event)e, EV_WRITE_USER_32B,
                               EV_DST_RAM, val, &control_bo, 4, 0x100000000ull,
                               shift);
            const unsigned len = info.needs_seqno ? 4 : 1;
            assert(ring.cur - ring.start == len + 1);
            assert(words[0] == pm4_pkt7_hdr(CP_EVENT_WRITE, len));
            uint32_t header = CP_EVENT_WRITE_0_EVENT(info.raw_event);
#if !A619_EVENT_SOURCE_PROFILE
            if (info.needs_seqno) header |= CP_EVENT_WRITE_0_TIMESTAMP;
#endif
            assert(words[1] == header && !(words[1] & CP_EVENT_WRITE_0_IRQ));
            if (info.needs_seqno) {
               uint64_t address = control_bo.iova + 4;
               address = shift < 0 ? address >> -shift : address << shift;
               address |= 0x100000000ull;
               assert(words[2] == (uint32_t)address);
               assert(words[3] == (uint32_t)(address >> 32));
               assert(words[4] == val && attachments == 1);
            } else {
               assert(!attachments);
            }
            for (unsigned i = len + 1; i < 32; i++) assert(words[i] == 0xa5a5a5a5u);
            cases++;
         }
      }
   }
   ring.cur = ring.start;
   attachments = 0;
   fd6_record_ts<A6XX>(&ring, &control_bo, 0, 0, 0);
   assert(ring.cur - ring.start == 5 && attachments == 1);
   assert(words[1] == (CP_EVENT_WRITE_0_EVENT(RB_DONE_TS) |
                       CP_EVENT_WRITE_0_TIMESTAMP));
   assert(words[2] == 0xfc018c00u && !words[3] && !words[4]);
   printf("PASS: native event source profile=%u USER32 cases=%u; ALWAYSON query preserved; no GPU execution\n",
          A619_EVENT_SOURCE_PROFILE, cases);
   return 0;
}
