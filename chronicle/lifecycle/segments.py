"""The shape catalog: small, named curves that get stitched into a civ's
full radius(t) envelope by `envelope.Lifecycle`. Nothing here touches RNG
or config -- these are pure functions of a normalized local time
u in [0, 1], reused across every tier. Picking WHICH kind a given civ
gets, and with what parameters, is `profiles.py`'s job.

EXTENSION POINT: to add a new growth/life/death archetype, add one entry
to the matching catalog dict below (and, for a new death kind, its
inverse) -- `envelope.Lifecycle` and `profiles.py` don't need to change,
they just look kinds up by name. If you add a kind, add it to the
matching Literal type too so type checkers catch typos.
"""

import math
from dataclasses import dataclass
from typing import Callable, Literal

GrowthKind = Literal["explosive", "slow_buildup", "steady_climb"]
LifeKind = Literal["steady", "expanding", "contracting", "oscillating"]
DeathKind = Literal["inward_collapse", "outward_collapse", "sublimation", "fracture"]

GROWTH_KINDS: tuple[GrowthKind, ...] = ("explosive", "slow_buildup", "steady_climb")
LIFE_KINDS: tuple[LifeKind, ...] = ("steady", "expanding", "contracting", "oscillating")
DEATH_KINDS: tuple[DeathKind, ...] = ("inward_collapse", "outward_collapse", "sublimation", "fracture")

# ----------------------------------------------------------------------
# Growth phase: fraction of the reachable peak radius attained at local
# time u in [0, 1]. All three are monotonic increasing 0 -> 1 -- that
# invariant is what lets `Lifecycle.peak_radius_by` treat "current radius
# during growth" as "the running historical peak" for free, with no
# inversion needed anywhere in this phase.
# ----------------------------------------------------------------------

def _growth_steady_climb(u: float) -> float:
    return u

def _growth_explosive(u: float) -> float:
    """Fast early rise, leveling off -- most of the climb happens early."""
    return 1.0 - (1.0 - u) ** 3

def _growth_slow_buildup(u: float) -> float:
    """Slow start, accelerating -- most of the climb happens late."""
    return u ** 3

GROWTH_SHAPES: dict[GrowthKind, Callable[[float], float]] = {
    "steady_climb": _growth_steady_climb,
    "explosive": _growth_explosive,
    "slow_buildup": _growth_slow_buildup,
}

# ----------------------------------------------------------------------
# Life phase: multiplier applied to the growth-phase peak, at local time
# u in [0, 1]. `param` means different things per kind (documented
# inline); `cycles` is only meaningful for "oscillating". Every shape
# here is chosen to return exactly 1.0 at u=0 (continuity with the end of
# growth) -- "expanding"/"contracting" ramp linearly to `param` by u=1;
# "oscillating" returns to 1.0 at u=1 too, as long as `cycles` is a whole
# number, so the death phase always gets a clean, non-jarring handoff.
# ----------------------------------------------------------------------

def _life_steady(u: float, param: float, cycles: int) -> float:
    return 1.0

def _life_expanding_or_contracting(u: float, param: float, cycles: int) -> float:
    """Linear ramp from 1.0 to `param`. `param` > 1 reads as 'expanding'
    (target growth multiplier); `param` < 1 reads as 'contracting' (target
    shrink multiplier) -- same formula, opposite sides of 1.0. They're
    kept as separate catalog entries (rather than folded into one) so
    per-tier weighting can favor one direction over the other."""
    return 1.0 + (param - 1.0) * u

def _life_oscillating(u: float, param: float, cycles: int) -> float:
    """Sinusoidal wobble of amplitude `param` around 1.0, `cycles` full
    periods across the phase. With integer `cycles` this starts AND ends
    at 1.0, so growth and death both get a seamless handoff regardless of
    how many boom/bust cycles happened in between."""
    return 1.0 + param * math.sin(2.0 * math.pi * cycles * u)

LIFE_SHAPES: dict[LifeKind, Callable[[float, float, int], float]] = {
    "steady": _life_steady,
    "expanding": _life_expanding_or_contracting,
    "contracting": _life_expanding_or_contracting,
    "oscillating": _life_oscillating,
}


@dataclass(frozen=True)
class DeathShape:
    """A death phase's radius curve, as a fraction of the radius entering
    the phase (1.0 at u=0 -> 0.0 at u=1), plus its closed-form inverse
    (given a target fraction, at what u did the boundary recede past it).
    Every shape is monotonic non-increasing, which is what preserves the
    'frontier is abandoned before the core' rule regardless of which
    death kind a civ rolled -- only the RATE of that recession differs."""

    forward: Callable[[float], float]
    inverse: Callable[[float], float]


def _inward_forward(u: float) -> float:
    return 1.0 - u

def _inward_inverse(frac: float) -> float:
    return 1.0 - frac

def _outward_forward(u: float) -> float:
    """Fast initial recession, long lingering core -- most of the
    territory is gone almost immediately, but a small enclave clings on
    nearly to the end."""
    return (1.0 - u) ** 3

def _outward_inverse(frac: float) -> float:
    return 1.0 - frac ** (1.0 / 3.0)

_SUBLIMATION_CLIFF = 0.85  # fraction of death_dur spent fully intact before the cliff

def _sublimation_forward(u: float) -> float:
    """Nothing recedes at all until near the very end, then everything
    goes at once -- signal of a population that didn't dwindle so much as
    vanish together."""
    if u < _SUBLIMATION_CLIFF:
        return 1.0
    return (1.0 - u) / (1.0 - _SUBLIMATION_CLIFF)

def _sublimation_inverse(frac: float) -> float:
    return 1.0 - (1.0 - _SUBLIMATION_CLIFF) * frac

DEATH_SHAPES: dict[DeathKind, DeathShape] = {
    "inward_collapse": DeathShape(_inward_forward, _inward_inverse),
    "outward_collapse": DeathShape(_outward_forward, _outward_inverse),
    "sublimation": DeathShape(_sublimation_forward, _sublimation_inverse),
    # EXTENSION POINT: "fracture" borrows sublimation's curve as a
    # placeholder. The interesting behavior -- spawning child civs at
    # decline-start instead of just decaying in place -- is deliberately
    # not implemented yet; see docs/lifecycle_and_emergence.md. Whoever
    # builds it can either give it its own DeathShape or keep this one.
    "fracture": DeathShape(_sublimation_forward, _sublimation_inverse),
}

# Flavor text for Lifecycle.status() -- purely cosmetic, safe to extend
# independently of the math above.
LIFE_STATUS_LABELS: dict[LifeKind, str] = {
    "steady": "steady state",
    "expanding": "expanding",
    "contracting": "contracting",
    "oscillating": "cyclical",
}

DEATH_STATUS_LABELS: dict[DeathKind, str] = {
    "inward_collapse": "collapsing",
    "outward_collapse": "collapsing (outer rim holding)",
    "sublimation": "sublimating",
    "fracture": "fracturing",
}
