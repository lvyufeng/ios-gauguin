#include "Recording342.hpp"
#include <cassert>
template<size_t N> static void fill(gauguin342::Times<N>& t){
    t.ns.fill(UINT64_MAX);t.worstPhases.fill(UINT64_MAX);
    t.calls=t.ok=t.skipped=t.failed=t.worst=t.worstJob=t.worstStart=t.worstEnd=UINT64_MAX;t.flags=UINT32_MAX;
}
int main(){
    gauguin342::Trace t;t.enabled=true;t.object=UINTPTR_MAX;t.madeUs=t.queue=UINT64_MAX;t.ticket=UINT64_MAX;
    t.flags=UINT32_MAX;t.jobs=t.execution=t.queueSum=t.queueMax=UINT64_MAX;t.counts.fill(UINT64_MAX);
    t.executionByClass.fill(UINT64_MAX);t.maxExecution.fill(UINT64_MAX);t.worstCategory=UINT32_MAX;
    t.worstSequence=t.worstEnqueued=t.worstStart=t.worstEnd=UINT64_MAX;
    t.submit.elapsed.fill(UINT64_MAX);t.submit.beginNs=t.submit.endNs=UINT64_MAX;
    t.submit.mask=t.submit.calls=t.submit.outcome=t.submit.flags=UINT32_MAX;
    auto& d=t.draw;fill(d.common);fill(d.render);d.reuse.values.fill(UINT64_MAX);d.reuse.flags=UINT32_MAX;
    auto& p=d.program;fill(p.address);fill(p.resident);fill(p.table);fill(p.piece);fill(p.pool);p.counts.fill(UINT64_MAX);p.flags=UINT32_MAX;
    auto& n=p.newBo;n.wall.fill(UINT64_MAX);n.cpu.fill(UINT64_MAX);n.envelope.fill(UINT64_MAX);
    n.calls=n.ok=n.failed=n.queries=n.queryWall=n.flags=n.maxJob=n.maxTid=n.maxHandle=n.maxBytes=UINT64_MAX;
    auto& m=n.maximum;m.first=m.last=m.queryWall=m.queries=m.mask=m.flags=UINT64_MAX;
    for(unsigned i=0;i<6;i++)m.begin[i]=m.end[i]=m.cpu[i]=m.envelope[i]=UINT64_MAX;
    auto& g=t.gpu;fill(g.stages);g.reuse.values.fill(UINT64_MAX);g.reuse.flags=UINT32_MAX;
    g.ioCalls=g.ioBegin=g.ioEnd=g.ioNs=g.uses=g.unique=g.comparisons=g.reserveFailures=UINT64_MAX;
    g.thread=g.driverQueue=g.driverFence=g.commandHandle=g.commandOffset=g.commandWords=UINT64_MAX;
    g.mode=g.flags=g.identityFlags=UINT32_MAX;auto& c=g.cpu;
    c.calls=c.ok=c.queries=c.before=c.after=c.outerBegin=c.outerEnd=c.overhead=c.lower=c.upper=c.offLower=c.offUpper=UINT64_MAX;c.flags=UINT32_MAX;
    gauguin342::Values waited;waited.fill(UINT64_MAX);
    gauguin342::observe(t,1,gauguin342::Commit,UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX,waited,UINT32_MAX,true);
    return 0;
}
