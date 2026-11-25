"""Replay the finite-deadline path and validate explicitly observed CA versions."""

from dataclasses import dataclass

from frame344_log import require


@dataclass(frozen=True)
class NextUpdate:
    deadline: int | None
    reasons: int = 0
    qualifiers: int = 0


def merge_update(current, proposed):
    """A finite request can replace or share the earliest eligible deadline."""
    require(type(proposed.deadline) is int and proposed.deadline>=0, 'request lacks a finite deadline')
    qualifiers = current.qualifiers | proposed.qualifiers
    if current.deadline is not None and current.deadline < proposed.deadline:
        return NextUpdate(current.deadline,current.reasons,qualifiers)
    reasons = proposed.reasons
    if proposed.deadline in (0,current.deadline):
        reasons |= current.reasons
    return NextUpdate(proposed.deadline,reasons,qualifiers)


@dataclass(frozen=True)
class Version:
    context: int
    lifetime: int
    commit_seed: int


class Replay:
    """Track identity separately from the deadline that schedules several contexts."""

    def __init__(self):
        self.current = {}
        self.lifetimes = {}
        self.applied = {}
        self.requested = set()
        self.pending = NextUpdate(None)
        self.updates = {}
        self.last_update = 0
        self.last_swap = 0
        self.inflight = {}

    def open_context(self, version):
        require(version.context > 0 and 0<=version.commit_seed<1<<32 and
                version.context not in self.current and version.lifetime > self.lifetimes.get(version.context,0),
                'invalid or reused CA lifetime')
        self.current[version.context] = version
        self.lifetimes[version.context] = version.lifetime

    def apply(self, version, receipt):
        previous = self.current.get(version.context)
        require(previous is not None and version.lifetime==previous.lifetime and
                version.commit_seed==(previous.commit_seed+1)&0xffffffff and
                version not in self.applied and receipt>0, 'CA commit seed or lifetime differs')
        self.current[version.context] = version
        self.applied[version] = receipt

    def schedule(self, version, deadline):
        require(self.current.get(version.context)==version and version in self.applied,
                'update request has no applied version')
        self.requested.add(version)
        self.pending = merge_update(self.pending,deadline)
        return self.pending

    def consume(self, update, versions):
        require(update>self.last_update and versions and
                len({v.context for v in versions})==len(versions), 'ambiguous render update membership')
        require(all(self.current.get(v.context)==v and v in self.requested for v in versions),
                'render version lacks its live apply and schedule identity')
        observation = tuple(versions)
        self.last_update = update
        self.updates[update] = observation
        self.pending = NextUpdate(None)
        return observation

    def swap(self, update, sequence):
        require(update==next(iter(self.updates),None) and sequence>self.last_swap,
                'swap identity or ordering differs')
        self.last_swap = sequence
        membership = self.updates.pop(update)
        self.inflight[sequence] = membership
        return membership

    def complete(self, sequence):
        require(sequence==next(iter(self.inflight),None), 'out-of-order display completion')
        return self.inflight.pop(sequence)

    def close_context(self, version):
        require(self.current.get(version.context)==version, 'invalid CA lifetime end')
        del self.current[version.context]
