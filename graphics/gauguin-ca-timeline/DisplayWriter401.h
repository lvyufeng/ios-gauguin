/* The existing display publication lock serializes these value-only receipts.
 * The GPU retains every submitted BO through its normal completion path. */
#ifndef GAUGUIN_DISPLAY_WRITER_401_H
#define GAUGUIN_DISPLAY_WRITER_401_H

#include <stdbool.h>
#include <stdint.h>

struct display401_writer {
    uint32_t cookie, surface, version;
    uint64_t ticket;
};

/* In the serialized GPU path, publication follows exact BO WRITE escrow.
 * A submission already bound to a normal display generation stays there. */
static inline bool
display401_publish(struct display401_writer *writer, uint32_t cookie,
    uint32_t surface, uint32_t version, uint64_t existing_ticket)
{
    if (writer->cookie || existing_ticket || !cookie || !surface || !version || (version & 3u))
        return false;
    *writer = (struct display401_writer){cookie, surface, version, 0};
    return true;
}

static inline bool
display401_matches(const struct display401_writer *writer, uint32_t cookie,
    uint32_t surface, uint32_t version)
{
    return cookie && cookie==writer->cookie && surface==writer->surface &&
        version==writer->version && !writer->ticket;
}

/* The caller independently checks the live busy state and that admitting
 * the ticket cannot conflict with an already-retained display writer. */
static inline bool
display401_claim(struct display401_writer *writer, uint32_t cookie,
    uint64_t ticket, uint32_t version)
{
    if (!(ticket>>32) || !display401_matches(writer,cookie,(uint32_t)ticket,version))
        return false;
    writer->ticket = ticket;
    return true;
}

/* Seal under the publication lock immediately before native issue. After
 * sealing, the ordinary ordered fence and cache path owns the returned ticket. */
static inline uint64_t
display401_seal(struct display401_writer *writer, uint32_t cookie,
    uint32_t surface, uint32_t version)
{
    if (!cookie || cookie!=writer->cookie || surface!=writer->surface ||
        version!=writer->version) return 0;
    const uint64_t ticket = writer->ticket;
    *writer = (struct display401_writer){0};
    return ticket;
}

#endif
