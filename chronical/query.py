"""Tier 2: the query layer a system generator would consume.

query_star(sid, t) is a pure function of (MASTER_SEED, sid, t). It composes:
  - the Tier 0 mythic registry (checked exhaustively -- it's tiny),
  - the great-powers registry (also tiny),
  - lazy neighborhood queries for minor civs and cluster leagues.

Cost is constant regardless of galaxy size. No global civ list exists.
"""

import math
from functools import lru_cache

from .config import SALIENCE_CUTOFF
from .density import Vec
from .lifecycle import Civ
from .stars import StarID, star_position
from .tier0 import Manifestation, build_tier0
from .tier1 import cluster_leagues_near, great_powers, minor_civs_near


@lru_cache(maxsize=1)
def tier0_registry() -> list:
    return build_tier0()


def _civ_manifestation(c: Civ, p: Vec, t: float) -> Manifestation | None:
    """Status is a property of the POINT, not the civ: during a collapse,
    a system in the receded annulus is already ruins even though the civ
    still lives at its core. Ruins faded below the noise floor return
    None -- undetectable by passive observation (a deliberate survey
    mechanic could still find them later; the geometry is in contains())."""
    d = math.hypot(c.home[0] - p[0], c.home[1] - p[1])
    peak = max(c.life.peak_radius(), 1e-9)
    base: Manifestation = {"entity": c.name, "kind": c.kind,
                           "influence": round(max(0.0, 1.0 - d / peak), 2),
                           "genome": c.genome}
    if c.is_living_at(p, t):
        base["status"] = c.life.status(t)
        return base
    age = c.ruin_age(p, t)
    if age is None:
        return None
    salience = c.ruin_salience(p, t)
    if salience < SALIENCE_CUTOFF:
        return None
    base["status"] = ("RUINS (abandoned mid-collapse)"
                      if t < c.life.death else "RUINS")
    base["ruin_age"] = round(age)
    base["salience"] = round(salience, 2)
    return base


def query_point(p: Vec, t: float, sid: StarID | None = None) -> list[Manifestation]:
    """Everything true at point p at coordinate time t."""
    out: list[Manifestation] = []
    if sid is not None:
        for entity in tier0_registry():
            m = entity.manifest(sid, p, t)
            if m is not None:
                out.append(m)
    for c in (*great_powers(t), *minor_civs_near(p, t), *cluster_leagues_near(p, t)):
        if c.contains(p, t): # may need to slip an is_relevant in here
            m = _civ_manifestation(c, p, t)
            if m is not None:
                out.append(m)
    return out


def query_star(sid: StarID, t: float) -> list[Manifestation]:
    """Everything true about star `sid` at time t. Pure function."""
    return query_point(star_position(sid), t, sid=sid)