/* Included after the primary EAGL methods. Only new contexts adopt this class. */
struct gauguin_eagl_method {
    const char *name;
    IMP ours;
};

typedef id (*gauguin_eagl_init_fn)(id, SEL, unsigned long, id);
static Class gauguin_eagl_parent, gauguin_eagl_class;
static gauguin_eagl_init_fn gauguin_eagl_original_init;

static id
gauguin_eagl_initialize(id self, SEL selector, unsigned long api, id properties)
{
    Class parent = __atomic_load_n(&gauguin_eagl_parent, __ATOMIC_ACQUIRE);
    Class subclass = __atomic_load_n(&gauguin_eagl_class, __ATOMIC_ACQUIRE);
    gauguin_eagl_init_fn original = __atomic_load_n(&gauguin_eagl_original_init, __ATOMIC_ACQUIRE);
    Class actual = object_getClass(self);
    if ((actual != parent && actual != subclass) || subclass == Nil) {
        return original(self, selector, api, properties);
    }
    pthread_mutex_lock(&gauguin_context_lock);
    id result = my_initWithAPI(self, selector, api, properties);
    if (result != nil) {
        object_setClass(result, subclass);
    } else {
        if (actual == subclass) {
            object_setClass(self, parent);
        }
        result = original(self, selector, api, properties);
    }
    pthread_mutex_unlock(&gauguin_context_lock);
    return result;
}

static void
gauguin_eagl_deallocate(id self, SEL selector)
{
    pthread_mutex_lock(&gauguin_context_lock);
    my_dealloc(self, selector);
    pthread_mutex_unlock(&gauguin_context_lock);
}

static unsigned
gauguin_eagl_install_subclass(Class parent, const struct gauguin_eagl_method *methods,
                             size_t count)
{
    const char *name = "GauguinA619EAGLContext";
    SEL initializer = sel_registerName("initWithAPI:properties:");
    SEL deallocator = sel_registerName("dealloc");
    Method init_method = class_getInstanceMethod(parent, initializer);
    if (count != 8 || !init_method || objc_lookUpClass(name)) {
        say("GAUGUIN EAGL BRIDGE rejected existing class or initializer\n");
        return 0;
    }
    Class subclass = objc_allocateClassPair(parent, name, 0);
    if (subclass == Nil) {
        say("GAUGUIN EAGL BRIDGE subclass allocation failed\n");
        return 0;
    }
    for (size_t i = 0; i < count; ++i) {
        SEL selector = sel_registerName(methods[i].name);
        Method method = class_getInstanceMethod(parent, selector);
        if (method == NULL) {
            objc_disposeClassPair(subclass);
            return 0;
        }
        IMP implementation = methods[i].ours;
        if (selector == initializer) {
            implementation = (IMP)gauguin_eagl_initialize;
        } else if (selector == deallocator) {
            implementation = (IMP)gauguin_eagl_deallocate;
        }
        if (!class_addMethod(subclass, selector, implementation, method_getTypeEncoding(method))) {
            objc_disposeClassPair(subclass);
            return 0;
        }
    }
    if (class_getInstanceSize(parent) != class_getInstanceSize(subclass)) {
        objc_disposeClassPair(subclass);
        return 0;
    }
    IMP original = method_getImplementation(init_method);
    if (original == NULL) {
        objc_disposeClassPair(subclass);
        return 0;
    }
    objc_registerClassPair(subclass);
    __atomic_store_n(&gauguin_eagl_parent, parent, __ATOMIC_RELEASE);
    __atomic_store_n(&gauguin_eagl_class, subclass, __ATOMIC_RELEASE);
    __atomic_store_n(&gauguin_eagl_original_init, (gauguin_eagl_init_fn)original, __ATOMIC_RELEASE);
    Method inherited = class_getInstanceMethod(class_getSuperclass(parent), initializer);
    if (init_method == inherited) {
        if (!class_addMethod(parent, initializer, (IMP)gauguin_eagl_initialize,
                             method_getTypeEncoding(init_method))) {
            return 0;
        }
    } else {
        IMP previous = method_setImplementation(init_method, (IMP)gauguin_eagl_initialize);
        __atomic_store_n(&gauguin_eagl_original_init, (gauguin_eagl_init_fn)previous, __ATOMIC_RELEASE);
    }
    say("GAUGUIN EAGL BRIDGE installed subclass methods=%zu initializer=1 pid=%d\n", count, getpid());
    return (unsigned)count;
}

__attribute__((visibility("default"))) int
gauguin_eagl_bridge_installed(void)
{
    Class parent = __atomic_load_n(&gauguin_eagl_parent, __ATOMIC_ACQUIRE);
    Class subclass = __atomic_load_n(&gauguin_eagl_class, __ATOMIC_ACQUIRE);
    if (parent == Nil || subclass == Nil) {
        return 0;
    }
    Method method = class_getInstanceMethod(parent, sel_registerName("initWithAPI:properties:"));
    return method && method_getImplementation(method) == (IMP)gauguin_eagl_initialize;
}
