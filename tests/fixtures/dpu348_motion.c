#include "gauguin_scanout345.h"
#include <assert.h>

int main(void)
{
    struct scan348_motion motion = {0};
    scan348_sample(&motion, 0, 42, 240);
    scan348_sample(&motion, 0, 42, 700);
    scan348_sample(&motion, 0, 43, 20);
    motion.previous_valid = false; // a rejected control or counter bracket
    scan348_sample(&motion, 0, 50, 35);
    scan348_sample(&motion, 3, 51, 10);
    scan348_sample(&motion, 3, 51, 10);
    scan348_sample(&motion, 3, 52, 8);
    assert(motion.zero.samples == 4 && motion.zero.compared_pairs == 2);
    assert(motion.zero.frame_changes == 1 && motion.zero.line_changes == 2 && motion.zero.line_wraps == 1);
    assert(motion.enabled.samples == 3 && motion.enabled.compared_pairs == 2);
    assert(motion.enabled.frame_changes == 1 && motion.enabled.line_changes == 1 && motion.enabled.line_wraps == 1);
    return 0;
}
