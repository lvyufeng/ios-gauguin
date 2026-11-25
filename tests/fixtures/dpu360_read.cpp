#include <atomic>
#include <cassert>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <thread>

#include "gauguin_read360.h"

struct IOLock {
    std::mutex mutex;
    std::condition_variable events;
    std::atomic<void *> sleeping{nullptr};
};

static void IOLockLock(IOLock *lock) { lock->mutex.lock(); }
static void IOLockUnlock(IOLock *lock) { lock->mutex.unlock(); }
static void IOLockSleep(IOLock *lock, void *address, int)
{
    std::unique_lock<std::mutex> hold(lock->mutex, std::adopt_lock);
    lock->sleeping.store(address);
    lock->events.wait(hold);
    lock->sleeping.store(nullptr);
    hold.release();
}
static void IOLockWakeup(IOLock *lock, void *, bool) { lock->events.notify_all(); }

struct Memory { bool owned; };
struct SweetSurface {
    uint32_t id;
    uint32_t gpuState;
    bool readOnly;
    Memory *memory;
    std::atomic<unsigned> references{1};
    void retain() { ++references; }
    void release() { assert(references.fetch_sub(1)>0); }
};

#define OSDynamicCast(Type, memory) ((memory) && (memory)->owned)
static constexpr int THREAD_UNINT = 0;
static constexpr int GUT_READ_LOCK = 1, GUT_READ_END = 2, F344_LOCK = 43;
static IOLock gpuLock, readWait;
static IOLock *gLock = &gpuLock, *gReadWait = &readWait;
static uint32_t gTraceReader;
static uint32_t receipt;

static bool completePendingOwnerLocked(bool, bool) { return false; }
static uint64_t sweet_ui_trace_clock() { return 1; }
static uint64_t sweet_frame344_clock() { return 1; }
static uint64_t mach_absolute_time() { return 2; }
static void sweet_ui_trace_record(int, uint32_t, uint32_t, uint32_t, uint64_t, uint64_t, uint64_t) {}
static void sweet_frame344_record(int kind, uint32_t, uint32_t flags, uint64_t begin, uint64_t taken, uint64_t end)
{
    assert(kind==F344_LOCK && begin<=taken && taken<=end);
    receipt = flags;
}

#include "frame360-read.inc"

int main()
{
    Memory exclusive{true}, wrapped{false};
    SweetSurface display{1,4,false,&exclusive};
    SweetSurface other{2,4,false,&exclusive};
    SweetSurface borrowed{3,4,true,&wrapped};
    SweetSurface physical{4,4,false,&wrapped};

    // The serial GPU request is busy with another surface at acquisition.
    std::thread writer;
    IOLockLock(gLock);
    {
        SweetSurfaceGPURead guard(&display,4);
        assert(guard.valid() && receipt==3 && display.references==2);
        assert(scan360_reserved(__atomic_load_n(&display.gpuState,__ATOMIC_ACQUIRE)));
        assert(GauguinGPUSurfaceState(&display)==4);
        assert(!scan360_reserve(&display.gpuState,4));
        // The frame owner may drop its reference before the guard's destructor.
        display.retain(); // GPU buffer/escrow reference
        display.release();
        IOLockUnlock(gLock);

        writer = std::thread([&] {
            IOLockLock(gLock);
            setSurfaceGPUState(&other,1,true);
            setSurfaceGPUState(&display,1,true);
            IOLockUnlock(gLock);
        });
        while (readWait.sleeping.load()!=&display.gpuState)
            std::this_thread::yield();
        assert(GauguinGPUSurfaceState(&other)==9);
        assert(GauguinGPUSurfaceState(&display)==4 && display.references==2);
        assert(!gLock->mutex.try_lock());
    }
    writer.join();
    IOLockLock(gLock);
    assert(display.references==1 && GauguinGPUSurfaceState(&display)==9);
    assert(!scan360_reserve(&display.gpuState,4) && !scan360_reserve(&display.gpuState,8));
    setSurfaceGPUState(&display,0);
    IOLockUnlock(gLock);

    {
        SweetSurfaceGPURead newGuard(&display,8);
        assert(newGuard.valid() && receipt==3 && display.references==2);
        assert(!scan360_release(&display.gpuState,4));
    }
    assert(display.references==1 && GauguinGPUSurfaceState(&display)==8);
    for (auto *surface : {&display,&borrowed,&physical}) {
        SweetSurfaceGPURead oldGuard(surface,4);
        assert(oldGuard.valid() && receipt==2 && surface->references==1);
    }

    IOLockLock(gLock);
    setSurfaceGPUState(&display,1,true);
    IOLockUnlock(gLock);
    {
        SweetSurfaceGPURead pending(&display,12);
        assert(!pending.valid() && receipt==0);
    }
    IOLockLock(gLock);
    setSurfaceGPUState(&display,2);
    IOLockUnlock(gLock);
    {
        SweetSurfaceGPURead failed(&display,12);
        assert(!failed.valid() && receipt==0);
    }

    for (uint32_t state : {0u,1u,2u,3u,5u,6u,SCAN354_GPU_VERSION}) {
        uint32_t value = state;
        assert(!scan360_reserve(&value,state));
        assert(value==state);
    }
    gReadWait = nullptr;
    SweetSurfaceGPURead disabled(&borrowed,4);
    assert(disabled.valid() && receipt==2);
}
