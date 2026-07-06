"""Tier 2: the query layer a system generator would consume.

query_star(sid, t) is a pure function of (MASTER_SEED, sid, t). It walks
one uniform list of `Event`s -- the Tier 0 mythic registry (checked
exhaustively -- it's tiny), the great-powers registry (also tiny), lazy
neighborhood queries for minor civs and cluster leagues, and the
hand-authored ruins -- and asks each one `contains()` then `manifest()`.
No type-specific dispatch: every kind of Event answers the same two
questions, so this loop doesn't need to know or care whether a given
candidate is a civilization, a ruin, or a relic network.

Cost is constant regardless of galaxy size. No global Event list exists.
"""

from functools import lru_cache

from .core import Event, Manifestation, StarID, Vec
from .core.stars import star_position
from .ruins import AUTHORED_RUINS
from .tiers.tier0 import build_tier0
from .tiers.tier1 import cluster_leagues_near, great_powers, minor_civs_near


@lru_cache(maxsize=1)
def tier0_registry() -> list:
    return build_tier0()


def query_point(p: Vec, t: float, sid: StarID | None = None) -> list[Manifestation]:
    """Everything true at point p at coordinate time t."""
    candidates: list[Event] = [
        *tier0_registry(),
        *great_powers(t),
        *minor_civs_near(p, t),
        *cluster_leagues_near(p, t),
        *AUTHORED_RUINS,
    ]
    out: list[Manifestation] = []
    for event in candidates:
        if event.contains(p, t):
            m = event.manifest(p, t, sid)
            if m is not None:
                out.append(m)
    return out


def query_star(sid: StarID, t: float) -> list[Manifestation]:
    """Everything true about star `sid` at time t. Pure function."""
    return query_point(star_position(sid), t, sid=sid)
