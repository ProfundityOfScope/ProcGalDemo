"""Civ lifecycle: a growth/life/death envelope built from named, reusable
segment shapes (see `segments.py`), assembled per-civ by `envelope.py`,
with per-tier variety controlled by `profiles.py`. The shared `Event`
contract (and `Manifestation`/`StarID`) lives in `..core.event` now,
not here -- `Civ`/`Ruin` implement it, but this package is scoped to
the growth/life/death envelope specifically, not the general contract.
Re-exports the public surface so callers can keep writing `from
.lifecycle import Civ, Lifecycle` exactly as when this was a single
flat module."""

from .envelope import Civ, Lifecycle, Ruin
from .profiles import (CLUSTER_LEAGUE_PROFILE, GREAT_POWER_PROFILE,
                       LIFE_CYCLES_RANGE, LIFE_PARAM_RANGES, MINOR_CIV_PROFILE,
                       LifecycleProfile, LifecycleRecipe, roll_recipe)
from .segments import (DEATH_KINDS, GROWTH_KINDS, LIFE_KINDS, DeathKind,
                       GrowthKind, LifeKind)

__all__ = [
    "Civ",
    "Lifecycle",
    "Ruin",
    "LifecycleProfile",
    "LifecycleRecipe",
    "roll_recipe",
    "GREAT_POWER_PROFILE",
    "CLUSTER_LEAGUE_PROFILE",
    "MINOR_CIV_PROFILE",
    "LIFE_PARAM_RANGES",
    "LIFE_CYCLES_RANGE",
    "GrowthKind",
    "LifeKind",
    "DeathKind",
    "GROWTH_KINDS",
    "LIFE_KINDS",
    "DEATH_KINDS",
]
