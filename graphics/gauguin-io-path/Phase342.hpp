#pragma once
#include <stdint.h>
#include <stddef.h>

// No allocation, thread, ownership, device call or synchronization operation.
// Clocks return ns; kernel callers explicitly convert both mach tick clocks.
namespace gauguin342phase {
constexpr uint64_t slop=2000;
enum : uint64_t { clockError=1,backward=2,overflow=4,orderError=8,incoherent=16 };
inline bool add(uint64_t& target,uint64_t value) noexcept {
    if(value>UINT64_MAX-target)return false;
    target+=value;return true;
}
template<size_t N> struct Data {
    uint64_t begin[N]{},end[N]{},cpu[N]{},envelope[N]{};
    uint64_t first=0,last=0,queryWall=0,queries=0,mask=0,flags=0;
};
struct Bounds {uint64_t cpuLower,cpuUpper,offLower,offUpper;};
inline Bounds bounds(uint64_t wall,uint64_t cpu,uint64_t envelope) noexcept {
    uint64_t lower=(envelope<=UINT64_MAX-slop&&cpu>envelope+slop)?cpu-envelope-slop:0;
    uint64_t upper=cpu>UINT64_MAX-slop?UINT64_MAX:cpu+slop;
    if(upper>wall)upper=wall;
    if(lower>upper)lower=upper; // Invalid data is separately rejected by flags.
    return {lower,upper,wall-upper,wall-lower};
}
template<size_t N> class Probe {
public:
    using Wall=uint64_t(*)() noexcept;
    using CPU=bool(*)(uint64_t*) noexcept;
    Probe(Data<N>* data,Wall wall,CPU cpu) noexcept : data_(data),wall_(wall),cpu_(cpu) {
        static_assert(N>0&&N<64,"bounded phase mask");
        if(data_){*data_={};previous_=sample();data_->first=previous_.before;}
    }
    ~Probe(){finish();}
    void phase(size_t next) noexcept {
        if(!data_||finished_)return;
        if(next<=index_||next>N){data_->flags|=orderError;return;}
        Tick now=sample();
        const size_t i=index_;data_->mask|=uint64_t(1)<<i;
        data_->begin[i]=previous_.after;data_->end[i]=now.before;
        if(now.before<previous_.after||now.cpu<previous_.cpu){data_->flags|=backward;}
        else {
            data_->cpu[i]=now.cpu-previous_.cpu;
            uint64_t envelope=previous_.width;
            if(!add(envelope,now.width)){data_->flags|=overflow;envelope=UINT64_MAX;}
            data_->envelope[i]=envelope;
            uint64_t maximum=now.before-previous_.after;
            if(!add(maximum,envelope)||!add(maximum,slop))data_->flags|=overflow;
            else if(data_->cpu[i]>maximum)data_->flags|=incoherent;
        }
        data_->last=now.after;previous_=now;index_=next;
        if(next==N)finished_=true;
    }
    void finish() noexcept {if(data_&&!finished_)phase(N);}
    Probe(const Probe&)=delete;Probe& operator=(const Probe&)=delete;
private:
    struct Tick {uint64_t before=0,cpu=0,after=0,width=0;};
    Tick sample() noexcept {
        Tick value;value.before=wall_();
        if(!cpu_(&value.cpu))data_->flags|=clockError;
        value.after=wall_();
        if(value.after<value.before)data_->flags|=backward;
        else value.width=value.after-value.before;
        if(!add(data_->queryWall,value.width)||!add(data_->queries,1))data_->flags|=overflow;
        return value;
    }
    Data<N>* data_;Wall wall_;CPU cpu_;Tick previous_{};size_t index_=0;bool finished_=false;
};
} // namespace gauguin342phase
