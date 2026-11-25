#include <assert.h>
#include "gauguin_ready353.h"
#include "gauguin_ready354.h"

int main(void)
{
    assert(!scan354_single_surface(1, false));
    assert(scan354_single_surface(1, true));
    assert(!scan354_single_surface(2, true));
    assert(!scan354_single_surface(0x80000001u, true));

    uint32_t ready_surface = scan354_gpu_state(0, 1, true);
    assert(ready_surface == 5);
    assert(!scan354_can_promote(ready_surface, 4, 9, 0));
    ready_surface = scan354_gpu_state(ready_surface, 0, false);
    assert(scan354_can_promote(ready_surface, 4, 9, 0));

    uint32_t waiting_surface = 4;
    uint32_t waiting = scan354_next_version(waiting_surface);
    assert(!scan354_can_promote(waiting_surface, waiting, 10, 9));
    assert(scan354_can_retry(ready_surface, 4, 9, 0));
    waiting_surface = scan354_gpu_state(waiting_surface, 1, true);
    assert(!scan354_can_promote(waiting_surface, waiting, 10, 9));
    assert(!scan354_can_promote(scan354_gpu_state(waiting_surface, 2, false), waiting, 10, 9));
    waiting_surface = scan354_gpu_state(waiting_surface, 0, false);
    assert(scan354_can_promote(waiting_surface, waiting, 10, 9));
    assert(!scan354_can_retry(ready_surface, 4, 9, 10));

    uint32_t later_writer = scan354_gpu_state(ready_surface, 1, true);
    assert(!scan354_has_version(later_writer, 4));
    assert(!scan354_has_version(scan354_gpu_state(later_writer, 0, false), 4));
    assert(scan354_has_version(scan354_gpu_state(ready_surface, 1, false), 4));
    assert(!scan354_can_promote(8, 8, 9, 9));

    uint32_t exhausted = scan354_gpu_state(SCAN354_GPU_VERSION - 4, 1, true);
    assert(scan354_next_version(exhausted) == SCAN354_GPU_VERSION);
    assert(!scan354_can_retry(exhausted, SCAN354_GPU_VERSION, 11, 0));
    assert(!scan354_can_promote(SCAN354_GPU_VERSION, SCAN354_GPU_VERSION, 11, 0));

    uint64_t first_same_surface = scan352_ticket(9, 7);
    uint64_t second_same_surface = scan352_ticket(10, 7);
    assert(!scan352_matches(first_same_surface, second_same_surface, 10, 10, 7));
    assert(scan352_matches(second_same_surface, second_same_surface, 10, 10, 7));
    return 0;
}
