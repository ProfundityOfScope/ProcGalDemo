"""Tier 1: transient civilizations. Three placement strategies, one query
pattern (the strongholds / mineshafts / dripstone lesson):

  A. Great powers  -- guaranteed count per annulus, small resident registry.
  B. Minor civs    -- lazy per-cell Poisson spawn; nothing exists until a
                      cell is asked. O(1) per cell, constant-cost queries.
  C. Cluster leagues -- same lazy cell machinery at a coarser scale, but
                      GATED on the density 'biome', with reach scaled by it.
"""

import math
from functools import lru_cache

from .config import (CIV_CELL, CIV_DECAY_TAU, CIV_LIFESPAN,
                     CIV_R_MAX, CIV_SPEED, CLUSTER_CELL, CLUSTER_DECAY_TAU,
                     CLUSTER_DENSITY_GATE, CLUSTER_LIFESPAN,
                     CLUSTER_R_MAX, CLUSTER_R_PER_DENSITY, CLUSTER_SPEED,
                     GALAXY_R, GP_DECAY_TAU, GP_LIFESPAN, GP_R_MAX,
                     GP_RINGS, GP_SPEED, EPOCH_LEN, CIV_RATE_PER_EPOCH,
                     CIV_LOOKBACK, SALIENCE_CUTOFF, CLUSTER_RATE_PER_EPOCH,
                     GP_RATE_PER_EPOCH, GP_LOOKBACK, CLUSTER_LOOKBACK)
from .density import Vec, stellar_density
from .era import era_curve
from .lifecycle import Civ, Lifecycle
from .rng import sub_rng
from .stars import nearest_star

# ----------------------------------------------------------------------
# Helpers!
# ----------------------------------------------------------------------

def epoch_window(t: float, lookback: float) -> range:
    """Birth windows whose civs could still matter at time t.
    
    The window is over BIRTH epochs: a civ born late in epoch e manifests
    well into e+1 and beyond, which is why lookback years back
    """
    e_lo = math.floor((t - lookback) / EPOCH_LEN)
    e_hi = math.floor(t / EPOCH_LEN)
    return range(e_lo, e_hi + 1)

# ----------------------------------------------------------------------
# Tier 1A -- great powers: exactly-N annulus placement (stronghold-style)
# ----------------------------------------------------------------------

@lru_cache(maxsize=None)
def great_powers_in_cell(e: int) -> tuple[Civ, ...]:
    """Small materialized registry -- they're nearly Tier 0 in rarity.
    Placement scales with GALAXY_R, so growing the disk redistributes
    them instead of stranding them downtown."""
    rng = sub_rng("tier1", "great_powers", e)
    epoch_mid = (e + 0.5) * EPOCH_LEN
    lam = GP_RATE_PER_EPOCH * era_curve(epoch_mid)
    n = int(rng.poisson(lam))
    birth = (e + rng.random()) * EPOCH_LEN  # uniform within the epoch
    civs: list[Civ] = []
    
    base_angle = rng.random() * 2 * math.pi
    base_rad_frac = rng.choice(GP_RINGS)
    for i in range(n):
        ang = base_angle + i * 2 * math.pi / n + rng.normal(0, 0.15)
        rad = base_rad_frac * GALAXY_R * rng.uniform(0.85, 1.15)
        _, home = nearest_star((rad * math.cos(ang), rad * math.sin(ang)))
        life = Lifecycle(
            birth=birth,
            expansion_speed=rng.uniform(*GP_SPEED),
            max_radius=rng.uniform(GP_R_MAX),
            lifespan=rng.uniform(*GP_LIFESPAN),
            decay_tau=GP_DECAY_TAU,
        )
        civs.append(Civ(
            name=f"Great Power R{base_rad_frac}-{i}", kind="stronghold-style",
            home=home, life=life,
            genome={"aggression": round(float(rng.random()), 2),
                    "aesthetic_seed": int(rng.integers(1e9))},
        ))
    return tuple(civs)

def great_powers(t: float) -> list[Civ]:
    """Here we check the whole galaxy but over given lookback epochs."""
    out: list[Civ] = []
    for e in epoch_window(t, GP_LOOKBACK):
        for c in great_powers_in_cell(e):
            if c.life.is_relevant(t, SALIENCE_CUTOFF):
                out.append(c)
    return out

# ----------------------------------------------------------------------
# Tier 1B -- minor civs: lazy per-cell Poisson spawn (mineshaft-style)
# ----------------------------------------------------------------------

def _cell_of(p: Vec, cell: float) -> tuple[int, int]:
    return int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))


@lru_cache(maxsize=None)
def minor_civs_in_cell(cx: int, cy: int, e: int) -> tuple[Civ, ...]:
    """All minor civs this cell ever produced across the whole 2 Myr
    history. Pure function of (seed, cx, cy) -- never iterated eagerly."""
    rng = sub_rng("tier1", "minor", cx, cy, e)
    center: Vec = ((cx + 0.5) * CIV_CELL, (cy + 0.5) * CIV_CELL)
    if math.hypot(center[0], center[1]) > GALAXY_R:
        return ()
    epoch_mid = (e + 0.5) * EPOCH_LEN
    lam = CIV_RATE_PER_EPOCH * stellar_density(center) * era_curve(epoch_mid)
    n = int(rng.poisson(lam))
    birth = (e + rng.random()) * EPOCH_LEN  # uniform within the epoch
    civs: list[Civ] = []
    for i in range(n):
        p: Vec = ((cx + rng.random()) * CIV_CELL, (cy + rng.random()) * CIV_CELL)
        if math.hypot(p[0], p[1]) > GALAXY_R:
            continue
        _, home = nearest_star(p)
        life = Lifecycle(
            birth=birth,
            expansion_speed=rng.uniform(*CIV_SPEED),
            max_radius=min(CIV_R_MAX, rng.uniform(100.0, CIV_R_MAX)),
            lifespan=rng.uniform(*CIV_LIFESPAN),
            decay_tau=CIV_DECAY_TAU,
        )
        civs.append(Civ(
            name=f"Minor {cx:+d}{cy:+d}.{i}", kind="mineshaft-style",
            home=home, life=life,
            genome={"aggression": round(float(rng.random()), 2)},
        ))
    return tuple(civs)


def minor_civs_near(p: Vec, t: float) -> list[Civ]:
    """Only cells within CIV_R_MAX of p can possibly reach it: with these
    numbers that's the 3x3 neighborhood. Constant cost at ANY galaxy size."""
    cx0, cy0 = _cell_of(p, CIV_CELL)
    reach_cells = int(math.ceil(CIV_R_MAX / CIV_CELL))   # = 1 here
    out: list[Civ] = []
    for cx in range(cx0 - reach_cells, cx0 + reach_cells + 1):
        for cy in range(cy0 - reach_cells, cy0 + reach_cells + 1):
            for e in epoch_window(t, CIV_LOOKBACK):
                for c in minor_civs_in_cell(cx, cy, e):
                    if c.life.is_relevant(t, SALIENCE_CUTOFF):
                        out.append(c)
    return out


# ----------------------------------------------------------------------
# Tier 1C -- cluster leagues: biome-gated lazy cells (dripstone-style)
# ----------------------------------------------------------------------

@lru_cache(maxsize=None)
def cluster_leagues_in_cell(cx: int, cy: int, e: int) -> tuple[Civ, ...]:
    """Same lazy-cell machinery as minors, coarser scale, but the spawn is
    GATED on the analytic density field (the 'biome'), and reach scales
    with the density that birthed them: dense regions breed bigger leagues."""
    rng = sub_rng("tier1", "cluster", cx, cy, e)
    center: Vec = ((cx + 0.5) * CLUSTER_CELL, (cy + 0.5) * CLUSTER_CELL)
    dens = stellar_density(center)
    if dens < CLUSTER_DENSITY_GATE:          # biome check
        return ()
    epoch_mid = (e + 0.5) * EPOCH_LEN
    lam = CLUSTER_RATE_PER_EPOCH * dens * era_curve(epoch_mid)
    n = int(rng.poisson(lam))
    birth = (e + rng.random()) * EPOCH_LEN  # uniform within the epoch
    civs: list[Civ] = []
    for i in range(n):
        p: Vec = ((cx + rng.random()) * CLUSTER_CELL,
                  (cy + rng.random()) * CLUSTER_CELL)
        local = stellar_density(p)
        if local < CLUSTER_DENSITY_GATE or math.hypot(p[0], p[1]) > GALAXY_R:
            continue
        _, home = nearest_star(p)
        life = Lifecycle(
            birth=birth,
            expansion_speed=rng.uniform(*CLUSTER_SPEED),
            max_radius=min(CLUSTER_R_MAX, local * CLUSTER_R_PER_DENSITY),
            lifespan=rng.uniform(*CLUSTER_LIFESPAN),
            decay_tau=CLUSTER_DECAY_TAU,
        )
        civs.append(Civ(
            name=f"Cluster League {cx:+d}{cy:+d}.{i}", kind="dripstone-style",
            home=home, life=life,
            genome={"density_at_birth": round(local, 2)},
        ))
    return tuple(civs)


def cluster_leagues_near(p: Vec, t: float) -> list[Civ]:
    cx0, cy0 = _cell_of(p, CLUSTER_CELL)
    reach_cells = int(math.ceil(CLUSTER_R_MAX / CLUSTER_CELL))   # = 1
    out: list[Civ] = []
    for cx in range(cx0 - reach_cells, cx0 + reach_cells + 1):
        for cy in range(cy0 - reach_cells, cy0 + reach_cells + 1):
            for e in epoch_window(t, CLUSTER_LOOKBACK):
                for c in cluster_leagues_in_cell(cx, cy, e):
                    if c.life.is_relevant(t, SALIENCE_CUTOFF):
                        out.append(c)
    return out