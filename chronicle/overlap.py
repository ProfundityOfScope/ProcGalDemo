"""Bones of an overlap-detection system. This module answers exactly one
question, cheaply and deterministically: "at time t, which of these
civs' living bubbles intersect?" It does NOT decide what an overlap
MEANS -- no war rolls, no mergers, no debris. That's future work.

Why this stays cheap at galaxy scale: `radius(t)` is a closed-form
function per civ, so "do two bubbles intersect" is a single distance
comparison, not a simulation. And this is only ever meant to run over
the small, already-local candidate list a point-query assembles (e.g.
`minor_civs_near`'s 3x3 cell neighborhood) -- never over "every civ in
the galaxy" -- so the O(n^2) pair scan below is O(1)-ish in practice: n
is a handful, not a billion.

EXTENSION POINT: this is deliberately just detection. A future pass can
fold `find_overlaps` into `query.py`'s candidate list and add resolution
logic on top -- e.g. hash `(a.name, b.name)` (sorted, so order doesn't
matter) into a deterministic roll for "nothing / skirmish / war / merger"
via the same `sub_rng` pattern every other lazy spawn in this package
uses. See docs/lifecycle_and_emergence.md for the fuller design sketch
(war debris as an `Lifecycle.instant_ruin`, cross-tier encounters needing
an asymmetric outcome instead of a peer "merge", etc.) -- none of it is
built yet, this module just picks out WHERE the overlaps are so that
future layer has something to consume.
"""

import math
from dataclasses import dataclass
from typing import Sequence

from .lifecycle import Civ


@dataclass(frozen=True)
class Overlap:
    """Two civs whose living bubbles intersect at time `t`. Detection
    only -- no outcome is attached."""

    a: Civ
    b: Civ
    t: float
    separation: float   # distance between homes, ly
    penetration: float  # how far the bubbles interpenetrate, ly (> 0 always, here)


def find_overlaps(civs: Sequence[Civ], t: float) -> list[Overlap]:
    """All pairs among `civs` whose living envelopes intersect at time t.
    O(n^2) in len(civs) -- fine, since callers pass an already-local,
    bounded candidate list (e.g. from `minor_civs_near`), never the whole
    galaxy's civ population."""
    out: list[Overlap] = []
    n = len(civs)
    for i in range(n):
        ra = civs[i].life.radius(t)
        if ra <= 0.0:
            continue
        for j in range(i + 1, n):
            rb = civs[j].life.radius(t)
            if rb <= 0.0:
                continue
            sep = math.hypot(civs[i].home[0] - civs[j].home[0],
                             civs[i].home[1] - civs[j].home[1])
            penetration = ra + rb - sep
            if penetration > 0.0:
                out.append(Overlap(civs[i], civs[j], t, sep, penetration))
    return out
