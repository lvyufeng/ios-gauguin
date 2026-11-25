"""Check exact GPU/cache/lease and display-flush ordering on the host."""

from dataclasses import dataclass, replace

FRAME_BYTES = 1080 * 2400 * 4
VIG0_FLUSH = 1
SCAN_MASK = 0xffffffff


@dataclass(frozen=True)
class Lease:
    generation: int
    surface: int
    version: int
    fence: int
    issue_tick: int
    eop_tick: int
    visible_tick: int
    acquired_tick: int

    def valid(self, live_version, now):
        return (self.generation > 0 and self.surface > 0 and self.version == live_version and
                self.fence > 0 and 0 < self.issue_tick < self.eop_tick <= self.visible_tick <= self.acquired_tick <= now)


@dataclass(frozen=True)
class TwoBuffers:
    """Events are values observed while holding the framebuffer owner's lock."""

    front: int = 0
    displayed_generation: int = 0
    phase: str = 'idle'
    token: int = 0
    lease: Lease | None = None
    published_tick: int = 0
    request_scan: int = 0
    pending_seen: bool = False

    @property
    def back(self):
        # Zero is the inherited client-visible IOSurface.
        return 2 if self.front == 1 else 1

    @property
    def writable(self):
        return self.back if self.phase in ('idle','copying') else None

    def start(self, lease, live_version, now, *, ownership):
        if (self.phase == 'idle' and ownership and lease.generation > self.displayed_generation and
                lease.valid(live_version, now)):
            return replace(self,phase='copying',token=self.token+1,lease=lease,published_tick=0)
        return self

    def publish(self, token, lease, stores, barrier, bytes_written, *, same_guard):
        if self.phase != 'copying' or token != self.token:
            return self
        if not self.lease.acquired_tick < stores <= barrier:
            # A later writer cannot assume earlier WC stores have drained.
            return replace(self,phase='quarantined')
        if self.lease == lease and bytes_written == FRAME_BYTES and same_guard:
            return replace(self,phase='ready',published_tick=barrier)
        return replace(self,phase='idle',lease=None)

    def request(self, token, scan, tick, earliest_latch, flush, *, route, dma_coverage):
        if (self.phase == 'ready' and token == self.token and self.published_tick <= tick < earliest_latch and
                route and dma_coverage and flush == 0):
            # Ownership transfers before the first register store.
            return replace(self,phase='pending',request_scan=scan,pending_seen=False)
        return self

    def observe(self, token, before_scan, after_scan, source, flush, *, route):
        if self.phase != 'pending' or token != self.token:
            return self
        if not route or flush & ~VIG0_FLUSH:
            return self.timeout()
        if before_scan != after_scan:
            return self
        delta = (after_scan - self.request_scan) & SCAN_MASK
        if delta == 0:
            return replace(self,pending_seen=True) if source == self.back and flush == VIG0_FLUSH else self
        if delta == 1 and self.pending_seen and flush == 0 and source == self.back:
            return replace(self,front=source,displayed_generation=self.lease.generation,phase='idle',
                           lease=None,published_tick=0,pending_seen=False)
        return self.timeout()

    def timeout(self):
        return replace(self,phase='quarantined') if self.phase == 'pending' else self


def exercise():
    lease = Lease(1,2,7,10,10,20,22,25)
    initial = TwoBuffers()
    for incomplete in (
        replace(lease,eop_tick=0), replace(lease,visible_tick=19),
        replace(lease,acquired_tick=21), replace(lease,fence=0), replace(lease,version=6),
    ):
        assert initial.start(incomplete,7,26,ownership=True) == initial
    assert initial.start(lease,7,24,ownership=True) == initial
    assert initial.start(lease,7,26,ownership=False) == initial
    copy = initial.start(lease,7,26,ownership=True)
    assert copy.writable == 1 and copy.front == 0
    assert copy.publish(0,lease,30,31,FRAME_BYTES,same_guard=True) == copy
    for bad_lease,stores,barrier,bytes_written,guard in (
        (replace(lease,fence=11),30,31,FRAME_BYTES,True),
        (lease,30,31,FRAME_BYTES-1,True),
        (lease,30,31,FRAME_BYTES,False),
    ):
        assert copy.publish(1,bad_lease,stores,barrier,bytes_written,same_guard=guard).phase == 'idle'
    unflushed = copy.publish(1,lease,30,29,FRAME_BYTES,same_guard=True)
    assert unflushed.phase == 'quarantined' and unflushed.writable is None
    assert unflushed.start(lease,7,32,ownership=True) == unflushed
    ready = copy.publish(1,lease,30,31,FRAME_BYTES,same_guard=True)
    assert ready.writable is None
    assert ready.request(1,SCAN_MASK,39,39,0,route=True,dma_coverage=True) == ready
    assert ready.request(1,SCAN_MASK,38,39,0,route=True,dma_coverage=False) == ready
    assert ready.request(1,SCAN_MASK,38,39,0,route=False,dma_coverage=True) == ready
    assert ready.request(1,SCAN_MASK,38,39,1,route=True,dma_coverage=True) == ready
    waiting = ready.request(1,SCAN_MASK,38,39,0,route=True,dma_coverage=True)
    assert waiting.observe(1,0,0,1,0,route=True).phase == 'quarantined'
    assert waiting.observe(1,SCAN_MASK,0,1,0,route=True) == waiting
    assert waiting.observe(2,SCAN_MASK,SCAN_MASK,1,1,route=True) == waiting
    armed = waiting.observe(1,SCAN_MASK,SCAN_MASK,1,1,route=True)
    assert armed.pending_seen and armed.writable is None
    assert armed.observe(1,SCAN_MASK,SCAN_MASK,1,0,route=True) == armed
    for past,source,flush,route in ((1,1,0,True),(0,0,0,True),(0,1,1,True),(0,1,0,False)):
        assert armed.observe(1,past,past,source,flush,route=route).writable is None
    assert armed.observe(1,SCAN_MASK,SCAN_MASK,1,3,route=True).phase == 'quarantined'
    quarantined = armed.timeout()
    assert quarantined.writable is None
    assert quarantined.observe(1,0,0,1,0,route=True) == quarantined
    assert quarantined.start(replace(lease,generation=2),7,50,ownership=True) == quarantined
    flipped = armed.observe(1,0,0,1,0,route=True)
    assert flipped.front == 1 and flipped.writable == 2 and flipped.displayed_generation == 1
    assert flipped.start(lease,7,50,ownership=True) == flipped
    subsequent = flipped.start(replace(lease,generation=2),7,50,ownership=True)
    next_ready = subsequent.publish(2,subsequent.lease,52,53,FRAME_BYTES,same_guard=True)
    next_pending = next_ready.request(2,4,54,59,0,route=True,dma_coverage=True)
    confirmed = next_pending.observe(2,4,4,2,1,route=True).observe(2,5,5,2,0,route=True)
    assert confirmed.front == 2 and confirmed.writable == 1 and confirmed.displayed_generation == 2
    return dict(gpu_cache_and_read_lease=True,complete_stores_before_request=True,
                vblank_latch_and_old_buffer_release=True,timeout_pins_both=True,
                missing_store_barrier_prevents_reuse=True,physical_latch_tested=False)
