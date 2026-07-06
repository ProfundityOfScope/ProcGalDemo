"""Per-tier lifecycle weighting. `Lifecycle`'s runtime cost doesn't depend
on which growth/life/death kind a civ rolled -- evaluating any recipe is
still O(1). So "how varied should this tier feel" isn't a performance
question, it's a narrative-economy one: rare civs (Great Powers) can
afford a wide-open catalog since there are few enough that every
distinctive biography lands, while common ones (minor civs) are weighted
back toward the plain, familiar shape so the rare exotic one still reads
as a find. This mirrors how a game like Minecraft keeps common
structures (mineshafts) template-simple and rare ones (strongholds)
elaborately varied -- not because the common ones COULDN'T be complex,
but because that's what makes the rare ones feel rare.

EXTENSION POINT: to add a new civ archetype (or retune an existing tier),
add or edit a `LifecycleProfile` below. Nothing outside this module
needs to change -- `tier1.py` just passes whichever profile matches the
tier it's spawning into `roll_recipe`.
"""

from dataclasses import dataclass

from .segments import DeathKind, GrowthKind, LifeKind

# Parameter ranges shared across every profile -- tier flavor comes from
# WHICH kinds get chosen (the weights below), not from different numeric
# ranges per tier. (Splitting these per-tier later is a easy follow-on if
# it turns out, say, Great Power oscillations should swing wider than a
# minor civ's.)
LIFE_PARAM_RANGES: dict[LifeKind, tuple[float, float]] = {
    "expanding": (1.05, 1.4),     # target size multiplier by end of life
    "contracting": (0.5, 0.9),    # target size multiplier by end of life
    "oscillating": (0.05, 0.3),   # wave amplitude, as a fraction of peak radius
}
LIFE_CYCLES_RANGE: tuple[int, int] = (2, 4)  # inclusive, only used by "oscillating"


@dataclass(frozen=True)
class LifecycleProfile:
    """Weighted choices for each phase, keyed by kind name. Weights don't
    need to sum to 1 -- `roll_recipe` normalizes them."""

    growth_weights: dict[GrowthKind, float]
    life_weights: dict[LifeKind, float]
    death_weights: dict[DeathKind, float]


@dataclass(frozen=True)
class LifecycleRecipe:
    """A fully-resolved, ready-to-construct set of Lifecycle segment
    choices -- everything `tier1.py` needs to hand to `Lifecycle(...)`."""

    growth_kind: GrowthKind
    life_kind: LifeKind
    death_kind: DeathKind
    life_param: float
    life_cycles: int


# ---------------------------------------------------------------- Tier 1A
# Great Powers: the "stronghold" tier -- rare enough that the full,
# most-varied catalog is affordable, and encounters between them (see
# overlap.py) are meant to be dramatic since there are so few pairs.
GREAT_POWER_PROFILE = LifecycleProfile(
    growth_weights={"explosive": 0.35, "slow_buildup": 0.35, "steady_climb": 0.30},
    life_weights={"steady": 0.25, "expanding": 0.25, "contracting": 0.25, "oscillating": 0.25},
    death_weights={"inward_collapse": 0.30, "outward_collapse": 0.30,
                  "sublimation": 0.20, "fracture": 0.20},
)

# ---------------------------------------------------------------- Tier 1C
# Cluster Leagues: the "village" tier -- biome-gated, moderate frequency.
# A league's defining trait is cohesion, not growth speed, so life-phase
# variety is weighted up; and "fracture" is favored for its death because
# a league dissolving back into its member systems basically IS what a
# league's death means.
CLUSTER_LEAGUE_PROFILE = LifecycleProfile(
    growth_weights={"explosive": 0.20, "slow_buildup": 0.30, "steady_climb": 0.50},
    life_weights={"steady": 0.35, "expanding": 0.15, "contracting": 0.20, "oscillating": 0.30},
    death_weights={"inward_collapse": 0.20, "outward_collapse": 0.15,
                  "sublimation": 0.15, "fracture": 0.50},
)

# ---------------------------------------------------------------- Tier 1B
# Minor civs: the highest-volume tier -- weighted heavily toward the
# plain rise/plateau/decline shape, specifically so the rare minor civ
# that rolls something exotic feels like a genuine find rather than
# background noise.
MINOR_CIV_PROFILE = LifecycleProfile(
    growth_weights={"explosive": 0.10, "slow_buildup": 0.15, "steady_climb": 0.75},
    life_weights={"steady": 0.70, "expanding": 0.12, "contracting": 0.13, "oscillating": 0.05},
    death_weights={"inward_collapse": 0.75, "outward_collapse": 0.12,
                  "sublimation": 0.08, "fracture": 0.05},
)


def _weighted_pick(rng, weights: dict) -> str:
    keys = list(weights.keys())
    total = sum(weights.values())
    probs = [weights[k] / total for k in keys]
    idx = int(rng.choice(len(keys), p=probs))
    return keys[idx]


def roll_recipe(rng, profile: LifecycleProfile) -> LifecycleRecipe:
    """Draw one deterministic (growth_kind, life_kind, death_kind, ...)
    recipe from `rng` per the given profile's weights. Call once per
    civ, from the same per-cell/epoch `rng` stream everything else in
    that spawn draws from, so the whole civ stays reproducible."""
    growth_kind = _weighted_pick(rng, profile.growth_weights)
    life_kind = _weighted_pick(rng, profile.life_weights)
    death_kind = _weighted_pick(rng, profile.death_weights)

    life_param = 1.0
    life_cycles = 1
    if life_kind in LIFE_PARAM_RANGES:
        life_param = float(rng.uniform(*LIFE_PARAM_RANGES[life_kind]))
    if life_kind == "oscillating":
        life_cycles = int(rng.integers(LIFE_CYCLES_RANGE[0], LIFE_CYCLES_RANGE[1] + 1))

    return LifecycleRecipe(growth_kind, life_kind, death_kind, life_param, life_cycles)
