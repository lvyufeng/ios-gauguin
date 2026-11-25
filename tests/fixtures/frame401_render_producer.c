#include <assert.h>
#include "RenderProducer401.h"

enum { RENDERER = 11, THREAD = 12, SURFACE = 13, OBJECT = 14, CREATED = 19, END = 40 };

static uint32_t declare(struct render401_producer *scope, uint64_t object, uint32_t cookie)
{
    return render401_declare(scope, RENDERER, THREAD, 20, END, object, CREATED, SURFACE, cookie);
}

static uint32_t lookup(const struct render401_producer *scope)
{
    return render401_lookup(scope, RENDERER, THREAD, 25, END, SURFACE);
}

int main(void)
{
    struct render401_producer scope = {0};
    assert(!declare(&scope, OBJECT, 1));
    render401_begin(&scope, RENDERER, THREAD, 19, 101);
    assert(!lookup(&scope));
    assert(!render401_declare(&scope, RENDERER, THREAD, 20, END, OBJECT, 18, SURFACE, 1));
    assert(!render401_declare(&scope, RENDERER, THREAD, 20, END, OBJECT, 21, SURFACE, 1));
    assert(declare(&scope, OBJECT, 1) == 1 && lookup(&scope) == 1);
    assert(declare(&scope, OBJECT, 2) == 1);
    assert(!render401_lookup(&scope, RENDERER + 1, THREAD, 25, END, SURFACE));
    assert(!render401_lookup(&scope, RENDERER, THREAD + 1, 25, END, SURFACE));
    assert(!render401_lookup(&scope, RENDERER, THREAD, END, END, SURFACE));
    assert(!render401_lookup(&scope, RENDERER, THREAD, 18, END, SURFACE));
    assert(!render401_lookup(&scope, RENDERER, THREAD, 25, END, SURFACE + 1));
    render401_end(&scope, RENDERER, THREAD + 1, 30);
    render401_begin(&scope, RENDERER + 1, THREAD, 31, 102);
    assert(lookup(&scope) == 1);
    assert(!declare(&scope, OBJECT + 1, 2) && !lookup(&scope));
    render401_end(&scope, RENDERER, THREAD, 31);
    assert(!lookup(&scope) && !scope.depth);

    render401_begin(&scope, RENDERER, THREAD, 19, 102);
    assert(declare(&scope, OBJECT, 3) == 3);
    render401_begin(&scope, RENDERER, THREAD, 21, 103);
    assert(!lookup(&scope));
    render401_end(&scope, RENDERER, THREAD, 22);
    assert(!lookup(&scope));
    render401_end(&scope, RENDERER, THREAD, 23);
    render401_begin(&scope, RENDERER, THREAD, 24, 104);
    assert(!lookup(&scope));
    assert(render401_declare(&scope, RENDERER, THREAD, 25, END, OBJECT, 24, SURFACE, 4) == 4);
    assert(lookup(&scope) == 4);
}
