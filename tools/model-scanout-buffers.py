"""Verify the two-buffer lifetime contract before attempting an MMIO flip."""

from dataclasses import dataclass, replace
from collections import deque
import json


@dataclass(frozen=True)
class Display:
    front: int = 0
    presented: int = 0
    next_token: int = 1
    staged_token: int = 0
    staged_generation: int = 0
    stage: str = 'idle'
    request_scan: int = 0
    pending_observed: bool = False

    @property
    def back(self):
        # Slot 0 is the inherited/default IOSurface. Clients can still hold it.
        return 2 if self.front==1 else 1

    def start_copy(self, generation, guard_held):
        if guard_held and self.stage in ('idle','ready') and generation>max(self.presented,self.staged_generation):
            return replace(self,staged_token=self.next_token,staged_generation=generation,
                next_token=self.next_token+1,stage='writing')
        return self

    def copy_finished(self, token, memory_visible):
        if self.stage!='writing' or self.staged_token!=token:
            return self
        if memory_visible:
            return replace(self,stage='ready')
        return replace(self,stage='idle',staged_token=0,staged_generation=0)

    def request(self, scan, route_ok, flush_idle):
        if self.stage=='ready' and route_ok and flush_idle:
            # CPU writers lose access to both buffers before the first MMIO store.
            return replace(self,stage='pending',request_scan=scan,pending_observed=False)
        return self

    def observe(self, token, scan, source, flush, route_ok):
        if self.stage!='pending' or self.staged_token!=token:
            return self
        if not route_ok:
            return self.timeout()
        if flush and source==self.back:
            return replace(self,pending_observed=True)
        advanced = 0 < ((scan-self.request_scan)&0xffffffff) < 1<<31
        if self.pending_observed and advanced and source==self.back:
            return replace(self,front=source,presented=self.staged_generation,
                staged_generation=0,staged_token=0,stage='idle',pending_observed=False,request_scan=0)
        return self

    def timeout(self):
        return replace(self,stage='quarantined') if self.stage=='pending' else self


def exercise():
    initial = Display()
    writing = initial.start_copy(1,True)
    assert writing.front==0 and writing.back==1 and writing.stage=='writing'
    assert initial.start_copy(1,False)==initial and writing.request(0,True,True)==writing
    assert writing.copy_finished(2,True)==writing
    assert writing.copy_finished(1,False).stage=='idle'
    ready = writing.copy_finished(1,True)
    assert ready.request(0,False,True)==ready and ready.request(0,True,False)==ready
    pending = ready.request(0xffffffff,True,True)
    for obs in [(2,0,1,False,True),(1,0,1,False,True),(1,0xffffffff,1,False,True)]:
        assert pending.observe(*obs)==pending
    seen = pending.observe(1,0xffffffff,1,True,True)
    assert seen.observe(1,0xffffffff,1,False,True)==seen
    assert seen.observe(1,0,0,False,True)==seen
    assert seen.start_copy(2,True)==seen
    assert seen.observe(1,0,1,False,False).stage=='quarantined'
    quarantined = seen.timeout()
    assert quarantined.observe(1,0,1,False,True)==quarantined
    assert quarantined.start_copy(2,True)==quarantined
    flipped = seen.observe(1,0,1,False,True)
    assert flipped.front==1 and flipped.back==2 and flipped.presented==1
    new = flipped.start_copy(2,True).copy_finished(2,True)
    assert new.start_copy(1,True)==new
    assert new.start_copy(3,True).copy_finished(2,True).stage=='writing'

    # Explore duplicate and stale events, inferred timing that does not
    # confirm a latch, a wrapping frame counter, and failure ordering.
    def transitions(s):
        yield s.timeout()
        for g in (0,1,2,3):
            for held in (False,True):
                yield s.start_copy(g,held)
        for t in (s.staged_token, s.next_token):
            yield s.copy_finished(t,True)
            yield s.copy_finished(t,False)
        for scan in (0,1,0xffffffff):
            yield s.request(scan,True,True)
            for source in (s.front,s.back):
                for flush in (False,True):
                    yield s.observe(s.staged_token,scan,source,flush,True)
            yield s.observe(s.staged_token,scan,s.back,False,False)

    visited = {initial}
    queue = deque([(initial,0)])
    edges = 0
    while queue:
        before, depth = queue.popleft()
        if depth==10:
            continue
        for after in transitions(before):
            edges+=1
            assert after.presented>=before.presented
            if before.stage=='quarantined':
                assert after==before
            if before.stage=='pending':
                assert after.stage in ('pending','idle','quarantined')
                if after.stage=='idle':
                    assert before.pending_observed and after.front==before.back
                    assert after.presented==before.staged_generation
            if before.front!=after.front:
                assert before.stage=='pending' and after.stage=='idle'
            if after.stage in ('writing','ready','pending','quarantined'):
                assert 0<after.staged_token<after.next_token and after.staged_generation>after.presented
            assert after.back in (1,2) and after.back!=after.front
            if after not in visited:
                visited.add(after)
                queue.append((after,depth+1))
    return dict(states=len(visited),transitions=edges,read_protected_staging=True,
        inherited_user_surface_excluded_from_writable_staging=True,
        requires_pending_flush_and_later_scan=True,ambiguous_timeout_reuses_either_buffer=False,
        device_commands=0,physical_latch_tested=False)


if __name__=='__main__':
    print(json.dumps(exercise(),indent=2))
