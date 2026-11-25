#ifndef GAUGUIN_DISPLAY_PREVIOUS_404_H
#define GAUGUIN_DISPLAY_PREVIOUS_404_H

/* Included beside the exact busy-producer record. The display publication
 * lock serializes both paths. Only one generation can claim this version. */
static inline bool
display404_previous_allowed(const struct display401_writer *writer, uint32_t surface, uint32_t version)
{
    return !writer->ticket || writer->surface!=surface || writer->version!=version;
}

static inline void
display404_previous_claimed(struct display401_writer *writer, uint32_t surface, uint32_t version)
{
    if (writer->cookie && !writer->ticket && writer->surface==surface && writer->version==version)
        *writer = (struct display401_writer){0};
}

#endif
