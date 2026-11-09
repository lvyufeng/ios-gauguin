#include <objc/runtime.h>
#include <objc/message.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static pthread_mutex_t gauguin_context_lock = PTHREAD_RECURSIVE_MUTEX_INITIALIZER;
static _Atomic unsigned assertions, allocated, disposed, native_initializers, custom_initializers;
static bool fail_custom;
static Class test_parent;

static void check(bool value, unsigned line)
{
    atomic_fetch_add(&assertions, 1);
    if (!value) {
        fprintf(stderr, "late installer assertion failed at line %u\n", line);
        exit(1);
    }
}
#define CHECK(value) check(!!(value), __LINE__)

static void say(const char *format, ...)
{
    char line[512];
    va_list args;
    va_start(args, format);
    vsnprintf(line, sizeof(line), format, args);
    va_end(args);
}

static id native_init(id self, SEL selector, unsigned long api, id properties)
{
    (void)selector;
    (void)api;
    (void)properties;
    atomic_fetch_add(&native_initializers, 1);
    return self;
}

static id my_initWithAPI(id self, SEL selector, unsigned long api, id properties)
{
    (void)selector;
    (void)properties;
    CHECK(api == 3);
    if (fail_custom) return nil;
    atomic_fetch_add(&custom_initializers, 1);
    return self;
}

static unsigned long native_api(id self, SEL selector)
{
    (void)self;
    (void)selector;
    return 777;
}

static unsigned long custom_api(id self, SEL selector)
{
    (void)self;
    (void)selector;
    return 3;
}

static id unused_object_method(id self, SEL selector)
{
    (void)self;
    (void)selector;
    return nil;
}

static void native_dealloc(id self, SEL selector)
{
    (void)selector;
    atomic_fetch_add(&disposed, 1);
    object_dispose(self);
}

static void my_dealloc(id self, SEL selector)
{
    native_dealloc(self, selector);
}

static bool ca_allowed;
static int gauguin_ca_install(void) { return ca_allowed; }

@BRIDGE@

static id make_context(Class cls)
{
    id object = class_createInstance(cls, 0);
    CHECK(object != nil);
    atomic_fetch_add(&allocated, 1);
    object = ((id (*)(id, SEL, unsigned long, id))objc_msgSend)(
        object, sel_registerName("initWithAPI:properties:"), 3, nil);
    CHECK(object != nil);
    return object;
}

static unsigned long api(id object)
{
    return ((unsigned long (*)(id, SEL))objc_msgSend)(object, sel_registerName("API"));
}

static void destroy(id object)
{
    ((void (*)(id, SEL))objc_msgSend)(object, sel_registerName("dealloc"));
}

static void *create_concurrently(void *unused)
{
    (void)unused;
    for (unsigned i = 0; i < 2000; ++i) {
        id object = make_context(test_parent);
        Class actual = object_getClass(object);
        if (actual == test_parent) {
            CHECK(api(object) == 777);
        } else {
            CHECK(actual == objc_lookUpClass("GauguinA619EAGLContext"));
            CHECK(api(object) == 3);
        }
        destroy(object);
    }
    return NULL;
}

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    bool inherited = strcmp(argv[1], "inherited") == 0;
    Class root = objc_getClass("NSObject");
    CHECK(root != Nil);
    if (inherited) {
        root = objc_allocateClassPair(root, "NativeEAGLBase", 0);
        CHECK(class_addMethod(root, sel_registerName("initWithAPI:properties:"),
                              (IMP)native_init, "@32@0:8Q16@24"));
        objc_registerClassPair(root);
    }
    test_parent = objc_allocateClassPair(root, "EAGLContext", 0);
    CHECK(test_parent != Nil);
    if (!inherited) {
        CHECK(class_addMethod(test_parent, sel_registerName("initWithAPI:properties:"),
                              (IMP)native_init, "@32@0:8Q16@24"));
    }
    const struct {
        const char *name, *type;
        IMP original, replacement;
    } definitions[] = {
        {"initWithAPI:properties:", "@32@0:8Q16@24", (IMP)native_init, (IMP)my_initWithAPI},
        {"API", "Q16@0:8", (IMP)native_api, (IMP)custom_api},
        {"sharegroup", "@16@0:8", (IMP)unused_object_method, (IMP)unused_object_method},
        {"setParameter:to:", "Q28@0:8I16^i20", (IMP)unused_object_method, (IMP)unused_object_method},
        {"getMacroContextPrivate", "^{EAGLMacroContext=}16@0:8", (IMP)unused_object_method, (IMP)unused_object_method},
        {"texImageIOSurface:target:internalFormat:width:height:format:type:plane:invert:",
         "B72@0:8^{__IOSurface=}16Q24Q32I40I44Q48Q56I64B68", (IMP)unused_object_method, (IMP)unused_object_method},
        {"attachImage:toCoreSurface:invertedRender:", "B36@0:8Q16^{__IOSurface=}24B32",
         (IMP)unused_object_method, (IMP)unused_object_method},
        {"dealloc", "v16@0:8", (IMP)native_dealloc, (IMP)my_dealloc},
    };
    struct gauguin_eagl_method methods[8];
    for (unsigned i = 0; i < 8; ++i) {
        if (i) CHECK(class_addMethod(test_parent, sel_registerName(definitions[i].name),
                                     definitions[i].original, definitions[i].type));
        methods[i] = (struct gauguin_eagl_method){definitions[i].name, definitions[i].replacement};
    }
    objc_registerClassPair(test_parent);
    Class child = objc_allocateClassPair(test_parent, "OtherEAGLContext", 0);
    objc_registerClassPair(child);
    id existing = make_context(test_parent);
    CHECK(api(existing) == 777);
    CHECK(!gauguin_eagl_bridge_installed());
    CHECK(gauguin_eagl_install_subclass(test_parent, methods, 7) == 0);
    CHECK(api(existing) == 777 && !gauguin_eagl_bridge_installed());
    CHECK(gauguin_eagl_install_subclass(test_parent, methods, 8) == 0);
    CHECK(api(existing) == 777 && !gauguin_eagl_bridge_installed());
    CHECK(objc_lookUpClass("GauguinA619EAGLContext") == Nil);
    ca_allowed = true;
    pthread_t threads[4];
    for (unsigned i = 0; i < 4; ++i) CHECK(pthread_create(&threads[i], NULL, create_concurrently, NULL) == 0);
    CHECK(gauguin_eagl_install_subclass(test_parent, methods, 8) == 8);
    CHECK(gauguin_eagl_bridge_installed());
    for (unsigned i = 0; i < 4; ++i) CHECK(pthread_join(threads[i], NULL) == 0);
    CHECK(object_getClass(existing) == test_parent && api(existing) == 777);
    destroy(existing);
    id custom = make_context(test_parent);
    CHECK(object_getClass(custom) == objc_lookUpClass("GauguinA619EAGLContext") && api(custom) == 3);
    destroy(custom);
    id subclass_context = make_context(objc_lookUpClass("GauguinA619EAGLContext"));
    CHECK(api(subclass_context) == 3);
    destroy(subclass_context);
    id other = make_context(child);
    CHECK(object_getClass(other) == child && api(other) == 777);
    destroy(other);
    fail_custom = true;
    id fallback = make_context(test_parent);
    CHECK(object_getClass(fallback) == test_parent && api(fallback) == 777);
    destroy(fallback);
    id subclass_fallback = make_context(objc_lookUpClass("GauguinA619EAGLContext"));
    CHECK(object_getClass(subclass_fallback) == test_parent && api(subclass_fallback) == 777);
    destroy(subclass_fallback);
    CHECK(gauguin_eagl_install_subclass(test_parent, methods, 8) == 0 && gauguin_eagl_bridge_installed());
    CHECK(atomic_load(&allocated) == atomic_load(&disposed));
    CHECK(atomic_load(&native_initializers) > 0 && atomic_load(&custom_initializers) > 0);
    printf("PASS %u real Objective-C late-installer assertions (%s)\n", atomic_load(&assertions), argv[1]);
    return 0;
}
