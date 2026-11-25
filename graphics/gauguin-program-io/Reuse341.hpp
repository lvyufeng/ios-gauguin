#pragma once
#include "hakios-metal/compute.hpp"
#include "hakios-metal/gpu.hpp"
#include <array>
#include <algorithm>
#include <limits>
#include <new>
#include <optional>

#ifndef GAUGUIN_REUSE340_ENABLED
#define GAUGUIN_REUSE340_ENABLED 1
#endif

#pragma GCC visibility push(hidden)
namespace gauguin341 {
using hakios::metal::Bindings;
using hakios::metal::MsmSubmitBo;
constexpr size_t bindingCapacity=128,boCapacity=1024,bucketCount=2048;
static_assert(bucketCount>=2*boCapacity && (bucketCount&(bucketCount-1))==0);

struct ReuseCounts {
    // borrowed calls, local fallback calls, vectors growing capacity, oversize drops
    std::array<uint64_t,4> values{};
    uint32_t flags=0;
    void add(unsigned i,uint64_t n) noexcept {
        if (i>=values.size() || UINT64_MAX-values[i]<n) {flags|=1;return;}
        values[i]+=n;
    }
};

struct DrawStorage {
    Bindings vs,fs;
    std::vector<std::shared_ptr<const void>> members;
};

struct Workspace {
    DrawStorage draw;
    std::vector<MsmSubmitBo> bos;
    std::array<uint32_t,bucketCount> buckets{}; // index+1, so handle0 is valid
    bool drawing=false,submitting=false;
};
// The existing recorder State owns this workspace. TLS only borrows it for a
// job; it owns no memory or GPU reference and has no destructor of its own.
extern thread_local Workspace* activeWorkspace;
extern thread_local uint64_t activeJobSequence;
struct WorkspaceScope {
    Workspace* previous;
    uint64_t previousSequence;
    WorkspaceScope(Workspace& value,uint64_t sequence) noexcept : previous(activeWorkspace),previousSequence(activeJobSequence) {
        activeWorkspace=&value;activeJobSequence=sequence;
    }
    ~WorkspaceScope() {activeWorkspace=previous;activeJobSequence=previousSequence;}
};

template<class T> inline unsigned clearBounded(std::vector<T>& value,size_t capacity) noexcept {
    value.clear();
    if (value.capacity()<=capacity) return 0;
    std::vector<T>().swap(value);return 1;
}

class DrawLease {
public:
    explicit DrawLease(ReuseCounts* counts=nullptr) : counts_(counts) {
#if GAUGUIN_REUSE340_ENABLED
        if (activeWorkspace && !activeWorkspace->drawing) {
            owner_=activeWorkspace;owner_->drawing=true;storage_=&owner_->draw;
        }
#endif
        if (!storage_) {local_.emplace();storage_=&*local_;}
        before_=capacities();
    }
    ~DrawLease() {
        const auto after=capacities();unsigned grew=0,dropped=0;
        for (unsigned i=0;i<after.size();i++) grew+=after[i]>before_[i];
        // Same ownership release order as the original locals: members, fs, vs.
        dropped+=clearBounded(storage_->members,bindingCapacity);
        for (Bindings* b:{&storage_->fs,&storage_->vs}) {
            dropped+=clearBounded(b->samplers,bindingCapacity);
            dropped+=clearBounded(b->textures,bindingCapacity);
            dropped+=clearBounded(b->buffers,bindingCapacity);
            b->privateMemory={};b->sharedBytes=0;b->nullMask=0;
        }
        if (counts_) {counts_->add(owner_?0:1,1);counts_->add(2,grew);counts_->add(3,dropped);}
        if (owner_) owner_->drawing=false;
    }
    DrawStorage& get() noexcept {return *storage_;}
    bool borrowed() const noexcept {return owner_!=nullptr;}
    DrawLease(const DrawLease&)=delete;
    DrawLease& operator=(const DrawLease&)=delete;
private:
    std::array<size_t,7> capacities() const noexcept {
        const auto& s=*storage_;
        return {s.vs.buffers.capacity(),s.vs.textures.capacity(),s.vs.samplers.capacity(),
            s.fs.buffers.capacity(),s.fs.textures.capacity(),s.fs.samplers.capacity(),s.members.capacity()};
    }
    Workspace* owner_=nullptr;
    DrawStorage* storage_=nullptr;
    std::optional<DrawStorage> local_;
    std::array<size_t,7> before_{};
    ReuseCounts* counts_;
};

class SubmitLease {
public:
    explicit SubmitLease(ReuseCounts* counts=nullptr) : counts_(counts) {
#if GAUGUIN_REUSE340_ENABLED
        if (activeWorkspace && !activeWorkspace->submitting) {
            owner_=activeWorkspace;owner_->submitting=true;bos_=&owner_->bos;
            owner_->buckets.fill(0);indexed_=true;
        }
#endif
        if (!bos_) bos_=&local_;
        before_=bos_->capacity();
    }
    ~SubmitLease() {
        const bool grew=bos_->capacity()>before_;
        unsigned dropped=clearBounded(*bos_,boCapacity);
        if (counts_) {counts_->add(owner_?0:1,1);counts_->add(2,grew);counts_->add(3,dropped);}
        if (owner_) owner_->submitting=false;
    }
    void seed(const MsmSubmitBo& command,size_t anticipated) {
        if (owner_) {
            // Optional eager capacity is allowed to fail: original push_back
            // behavior still decides whether this submission can be built.
            try {bos_->reserve(std::min(anticipated,boCapacity));}
            catch (...) {reserveFailures++;}
        }
        bos_->push_back(command);
        if (indexed_) owner_->buckets[slot(command.handle)]=1;
    }
    void add(const MsmSubmitBo& use) {
        if (indexed_) {
            size_t at=slot(use.handle);
            for (;;) {
                const uint32_t entry=owner_->buckets[at];
                if (!entry) {
                    if (bos_->size()>=boCapacity) {indexed_=false;overflowed_=true;break;}
                    bos_->push_back(use);owner_->buckets[at]=uint32_t(bos_->size());return;
                }
                comparisons++;
                auto& old=(*bos_)[entry-1];
                if (old.handle==use.handle) {old.flags|=use.flags;return;}
                at=(at+1)&(bucketCount-1);
            }
        }
        // Original stable linear algorithm for sync/reentrant/oversize paths.
        bool seen=false;
        for (auto& old:*bos_) {
            comparisons++;
            if (old.handle==use.handle) {old.flags|=use.flags;seen=true;}
        }
        if (!seen) bos_->push_back(use);
    }
    std::vector<MsmSubmitBo>& get() noexcept {return *bos_;}
    unsigned mode() const noexcept {return owner_?(overflowed_?2:1):0;}
    uint64_t comparisons=0,reserveFailures=0;
    SubmitLease(const SubmitLease&)=delete;
    SubmitLease& operator=(const SubmitLease&)=delete;
private:
    static size_t slot(uint32_t handle) noexcept {return (handle*uint32_t(2654435761u))&(bucketCount-1);}
    Workspace* owner_=nullptr;
    std::vector<MsmSubmitBo> local_;
    std::vector<MsmSubmitBo>* bos_=nullptr;
    size_t before_=0;
    bool indexed_=false,overflowed_=false;
    ReuseCounts* counts_;
};
} // namespace gauguin341
#pragma GCC visibility pop
