#pragma once
#include "Phase342.hpp"
#include <array>
#include <cerrno>
#include <pthread.h>
#pragma GCC visibility push(hidden)
namespace gauguin342 {
struct NewBoData {
    std::array<uint64_t,6> wall{},cpu{},envelope{};
    uint64_t calls=0,ok=0,failed=0,queries=0,queryWall=0,flags=0;
    uint64_t maxJob=0,maxTid=0,maxHandle=0,maxBytes=0;
    gauguin342phase::Data<6> maximum;
};
inline thread_local NewBoData* activeProgramBo=nullptr;
struct ProgramAllocationScope {
    NewBoData* previous;
    explicit ProgramAllocationScope(NewBoData* value) noexcept : previous(activeProgramBo){activeProgramBo=value;}
    ~ProgramAllocationScope(){activeProgramBo=previous;}
    ProgramAllocationScope(const ProgramAllocationScope&)=delete;
    ProgramAllocationScope& operator=(const ProgramAllocationScope&)=delete;
};
inline bool threadID(uint64_t* value) noexcept {
    const int saved=errno;const int answer=pthread_threadid_np(nullptr,value);errno=saved;
    return answer==0&&*value!=0;
}
class NewBoScope {
public:
    using Phase=gauguin342phase::Probe<6>;
    using ID=bool(*)(uint64_t*) noexcept;
    NewBoScope(NewBoData* data,int* error,uint64_t job,Phase::Wall wall,Phase::CPU cpu,ID id=threadID) noexcept :
        data_(data),error_(error),job_(job),probe_(data?&span_:nullptr,wall,cpu) {
        if(data_){add(data_->calls,1);if(!id(&tid_))span_.flags|=32;}
    }
    ~NewBoScope(){
        if(!data_)return;
        probe_.finish();data_->flags|=span_.flags;
        add(data_->queries,span_.queries);add(data_->queryWall,span_.queryWall);
        add(complete_&&*error_==0?data_->ok:data_->failed,1);
        for(unsigned i=0;i<6;i++){
            if(span_.end[i]<span_.begin[i]){data_->flags|=gauguin342phase::backward;continue;}
            add(data_->wall[i],span_.end[i]-span_.begin[i]);add(data_->cpu[i],span_.cpu[i]);add(data_->envelope[i],span_.envelope[i]);
        }
        if(!data_->maxJob||span_.last-span_.first>data_->maximum.last-data_->maximum.first){
            data_->maximum=span_;data_->maxJob=job_;data_->maxTid=tid_;data_->maxHandle=handle_;data_->maxBytes=bytes_;
        }
    }
    void phase(unsigned next) noexcept {probe_.phase(next);}
    void identity(uint64_t handle,uint64_t bytes) noexcept {handle_=handle;bytes_=bytes;}
    void complete() noexcept {complete_=true;}
    NewBoScope(const NewBoScope&)=delete;NewBoScope& operator=(const NewBoScope&)=delete;
private:
    void add(uint64_t& to,uint64_t value) noexcept {if(!gauguin342phase::add(to,value))data_->flags|=gauguin342phase::overflow;}
    NewBoData* data_;int* error_;uint64_t job_,tid_=0,handle_=0,bytes_=0;
    gauguin342phase::Data<6> span_{};Phase probe_;bool complete_=false;
};
} // namespace gauguin342
#pragma GCC visibility pop
