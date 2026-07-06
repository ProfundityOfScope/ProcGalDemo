"""Civ lifecycle envelope. All times in ABSOLUTE years.

A civ's radius(t) is three segments stitched end to end:

    growth (0 -> peak)  ->  life (peak -> r2)  ->  death (r2 -> 0)

`growth_kind`/`life_kind`/`death_kind` each pick a named curve shape from
`segments.py` -- see that module for the catalog and the invariants each
shape must satisfy (continuity at the handoffs). Which kinds a given civ
rolls, and with what parameters, is `profiles.py`'s job; this module only
know how to EVALUATE a fully-specified recipe. With every kind left at
its default ("steady_climb" growth, "steady" life, "inward_collapse"
death) this reduces exactly to the old rise/plateau/decline trapezoid.

Ruins appear where the LIVING envelope has receded -- during collapse
that's a growing annulus of abandonment chasing the shrinking frontier
inward; at death it completes into a disk. `historical_peak`/
`peak_radius_by` track the largest extent ever reached -- that
bookkeeping itself never shrinks, which is what lets "influence" stay
normalizable and lets a ruin's per-distance age/salience be computed at
all. But an ordinary `Civ`/`Ruin`'s `Event.contains()` is NOT permanent:
it folds that geometry together with salience, so once a spot has faded
below the noise floor, `contains()` returns False -- the Event is
simply gone for ordinary query purposes, not "still technically present
but undetectable forever." Only the mythic tier (no decay machinery at
all) gets genuine permanence, and that's a deliberate, rare exception,
not the default. Salience -- how detectable a ruin still is -- decays as
exp(-age / decay_tau).

SCOPE NOTE: `abandoned_at`/`ruin_age` give an exact, distance-dependent
answer for anything abandoned during the death phase (always) or during
a "contracting" life phase (which permanently gives up ground before
death even starts). They deliberately do NOT track fine-grained history
inside an "oscillating" life phase's troughs -- a point that's briefly
outside the envelope mid-wave reads as neither living nor a confirmed
ruin (`ruin_age` returns None there) rather than guessing. See
docs/lifecycle_and_emergence.md for why, and for how a future pass could
extend this.
"""

import math
from dataclasses import dataclass, field

from ..core import Event, Manifestation, StarID, Vec
from ..core.config import SALIENCE_CUTOFF
from .segments import (DEATH_SHAPES, DEATH_STATUS_LABELS, GROWTH_SHAPES,
                       LIFE_SHAPES, LIFE_STATUS_LABELS, DeathKind, GrowthKind,
                       LifeKind)


@dataclass(frozen=True)
class Lifecycle:
    """Influence radius as a pure function of time, plus the post-mortem
    salience curve. Growth, life, death -- three named shapes stitched
    together; see the module docstring."""

    birth: float
    expansion_speed: float          # ly / year (well below c)
    max_radius: float
    lifespan: float                 # years, birth -> final silence
    decay_tau: float = 50_000.0     # ruin salience e-folding time (years)
    death_frac: float = 0.25        # fraction of lifespan spent in the death phase

    growth_kind: GrowthKind = "steady_climb"
    life_kind: LifeKind = "steady"
    death_kind: DeathKind = "inward_collapse"
    life_param: float = 1.0         # meaning depends on life_kind: target
                                     # multiplier for expanding/contracting,
                                     # amplitude for oscillating, unused
                                     # for steady
    life_cycles: int = 2            # only meaningful for "oscillating"

    @property
    def death(self) -> float:
        return self.birth + self.lifespan

    # ------------------------------------------------------- phase timing
    @property
    def death_dur(self) -> float:
        return self.lifespan * self.death_frac

    @property
    def growth_dur(self) -> float:
        """Time actually spent growing -- capped by whatever's left of
        the lifespan before the death phase must start (mirrors the old
        model: a civ that's still climbing when decline begins just
        never reaches max_radius)."""
        available = self.lifespan - self.death_dur
        uncapped = (self.max_radius / self.expansion_speed
                   if self.expansion_speed > 0 else 0.0)
        return max(0.0, min(uncapped, available))

    @property
    def growth_end(self) -> float:
        return self.birth + self.growth_dur

    @property
    def life_dur(self) -> float:
        return max(0.0, self.lifespan - self.growth_dur - self.death_dur)

    @property
    def life_end(self) -> float:
        """Also the moment the death phase begins."""
        return self.growth_end + self.life_dur

    # ------------------------------------------------------- boundary radii
    @property
    def growth_peak(self) -> float:
        """Radius reached at the end of growth. Equals max_radius unless
        growth ran out of time before the death phase (see growth_dur)."""
        return self.expansion_speed * self.growth_dur

    def _life_end_multiplier(self) -> float:
        if self.life_dur <= 0.0:
            return 1.0  # no time for the life phase to do anything
        if self.life_kind in ("expanding", "contracting"):
            return self.life_param
        if self.life_kind == "oscillating":
            return 1.0 + self.life_param * math.sin(
                2.0 * math.pi * self.life_cycles)  # ~1.0 for whole-number cycles
        return 1.0  # steady

    @property
    def r2(self) -> float:
        """Radius entering the death phase (i.e. at the end of life)."""
        return self.growth_peak * self._life_end_multiplier()

    @property
    def historical_peak(self) -> float:
        """Max radius EVER reached, up to and including death. Growth is
        always monotonic increasing, so only `life` can push this past
        `growth_peak` -- and only "expanding"/"oscillating" do."""
        if self.life_dur <= 0.0:
            return self.growth_peak  # no time for the life phase to run at all
        if self.life_kind == "expanding":
            return self.growth_peak * self.life_param
        if self.life_kind == "oscillating":
            # Approximation: assumes the wave's first crest is reached,
            # which happens early in the phase (at u = 0.25/cycles) for
            # any realistic `cycles` -- see docs for the tradeoff.
            return self.growth_peak * (1.0 + max(0.0, self.life_param))
        return self.growth_peak  # steady / contracting: never exceeds this

    # ------------------------------------------------------- the envelope
    def radius(self, t: float) -> float:
        """Living envelope at absolute time t."""
        if t <= self.birth or t >= self.death:
            return 0.0
        if t <= self.growth_end:
            return self._growth_radius(t)
        if t <= self.life_end:
            return self._life_radius(t)
        return self._death_radius(t)

    def _growth_radius(self, t: float) -> float:
        if self.growth_dur <= 0.0:
            return self.growth_peak
        u = max(0.0, min(1.0, (t - self.birth) / self.growth_dur))
        return self.growth_peak * GROWTH_SHAPES[self.growth_kind](u)

    def _life_radius(self, t: float) -> float:
        if self.life_dur <= 0.0:
            return self.growth_peak
        u = max(0.0, min(1.0, (t - self.growth_end) / self.life_dur))
        mult = LIFE_SHAPES[self.life_kind](u, self.life_param, self.life_cycles)
        return self.growth_peak * mult

    def _death_radius(self, t: float) -> float:
        if self.death_dur <= 0.0:
            return 0.0
        u = max(0.0, min(1.0, (t - self.life_end) / self.death_dur))
        return self.r2 * DEATH_SHAPES[self.death_kind].forward(u)

    def peak_radius(self) -> float:
        """Backwards-compatible alias: the civ's all-time peak reach,
        used by the query layer to normalize 'influence' by distance."""
        return self.historical_peak

    def peak_radius_by(self, t: float) -> float:
        """Max radius achieved UP TO time t -- the historical footprint."""
        if t <= self.birth:
            return 0.0
        if t <= self.growth_end:
            return self._growth_radius(t)  # monotonic increasing: current IS the running max
        if t <= self.life_end:
            if self.life_kind == "expanding":
                return self._life_radius(t)
            if self.life_kind == "oscillating":
                return self.growth_peak * (1.0 + max(0.0, self.life_param))
            return self.growth_peak  # steady / contracting: peak stayed here
        return self.historical_peak  # death phase or beyond: no new peak possible

    # ------------------------------------------------------- abandonment
    def abandoned_at(self, d: float) -> float | None:
        """When the living envelope permanently receded past distance d
        from home. None if never covered. Exact for the death phase
        (always) and for a "contracting" life phase (the one life kind
        that permanently gives up ground before death); see the module
        docstring for the oscillating-troughs scope note."""
        peak = self.historical_peak
        if peak <= 0.0 or d > peak:
            return None
        if self.life_kind == "contracting" and d > self.r2:
            span = self.growth_peak - self.r2
            u = (self.growth_peak - d) / span if span > 0.0 else 0.0
            return self.growth_end + u * self.life_dur
        if self.r2 <= 0.0:
            return self.life_end
        frac = min(1.0, d / self.r2)
        u = DEATH_SHAPES[self.death_kind].inverse(frac)
        return self.life_end + u * self.death_dur

    def ruin_age(self, d: float, t: float) -> float | None:
        """Age of the ruins at distance d, at time t. None if that spot is
        still living, was never covered, hasn't been reached (yet), or
        falls in the untracked oscillating-trough gap (see scope note)."""
        if d > self.peak_radius_by(t):
            return None
        t_ab = self.abandoned_at(d)
        if t_ab is None or t < t_ab:
            return None
        return t - t_ab

    def ruin_salience(self, d: float, t: float) -> float:
        """Detectability of the ruins at distance d: 1.0 fresh -> 0.0 gone."""
        age = self.ruin_age(d, t)
        return 0.0 if age is None else math.exp(-age / self.decay_tau)

    def visible_ruin_radius(self, t: float, cutoff: float) -> float:
        """Outermost distance whose ruins still clear the salience cutoff.
        Ruins erode inward (frontier faded first); this is just 'where
        was the living boundary, age_max years ago' -- which is exactly
        `radius()` evaluated at that earlier time, for free."""
        if self.r2 <= 0.0 or t <= self.life_end:
            return 0.0
        age_max = -self.decay_tau * math.log(cutoff)
        probe_t = t - age_max
        if probe_t <= self.life_end:
            return self.r2  # nothing abandoned so far has had time to fade yet
        return self.radius(probe_t)

    # ------------------------------------------------------- status
    def status(self, t: float) -> str:
        if t < self.birth:
            return "not yet"
        if t >= self.death:
            return "RUINS"
        if t > self.life_end:
            return DEATH_STATUS_LABELS[self.death_kind]
        if t > self.growth_end:
            return LIFE_STATUS_LABELS[self.life_kind]
        return "expanding"

    def is_relevant(self, t: float, cutoff: float) -> bool:
        """An instantaneous version of is_relevant_between, useful if we
        make some assumptions skipping relativity"""
        return self.is_relevant_between(t, t, cutoff)

    def is_relevant_between(self, t0: float, t1: float, cutoff: float) -> bool:
        """Could this civ manifest at ANY time in [t0, t1]? Used by the
        Lightcone, where every point on the map is evaluated at its own
        retarded time somewhere in that interval."""
        fade_horizon = self.death + self.decay_tau * math.log(1.0 / cutoff)
        return self.birth < t1 and fade_horizon > t0

    # ------------------------------------------------------- instant ruins
    @classmethod
    def instant_ruin(cls, spawn_time: float, radius: float, decay_tau: float,
                     death_kind: DeathKind = "sublimation",
                     materialize_dur: float = 100.0,
                     death_dur: float = 1_000.0) -> "Lifecycle":
        """A degenerate Lifecycle with no growth or life phase -- it
        appears already at `radius`, decaying, at `spawn_time`. This is
        the machinery behind 'instant ruins': war debris, failed
        colonies, anything that should read as pure history with no
        living population ever queryable there. Growth is compressed
        into `materialize_dur` (years, small relative to civ timescales)
        so any query at ordinary resolution sees it as already-present.
        Like any ordinary `Ruin`, its `contains()` genuinely expires once
        salience fades below the noise floor -- it isn't a special case,
        just a recipe with a vanishingly short growth+life prefix."""
        return cls(
            birth=spawn_time,
            expansion_speed=radius / materialize_dur,
            max_radius=radius,
            lifespan=materialize_dur + death_dur,
            decay_tau=decay_tau,
            death_frac=death_dur / (materialize_dur + death_dur),
            life_kind="steady",
            death_kind=death_kind,
        )


@dataclass(frozen=True)
class Civ(Event):
    name: str
    kind: str                       # which placement strategy made it
    home: Vec                       # birth coordinates (a snapped star)
    life: Lifecycle
    genome: dict = field(default_factory=dict)

    def _d(self, p: Vec) -> float:
        return math.hypot(self.home[0] - p[0], self.home[1] - p[1])

    def contains(self, p: Vec, t: float) -> bool:
        """Inside the historical footprint AND still salient -- living,
        or ruins that haven't yet faded below the noise floor. Once
        salience drops below cutoff this is simply False: the Event is
        gone, not "there but nobody would ever notice." """
        d = self._d(p)
        if d > self.life.peak_radius_by(t):
            return False
        if self.is_living_at(p, t):
            return True
        return self.life.ruin_salience(d, t) >= SALIENCE_CUTOFF

    def is_living_at(self, p: Vec, t: float) -> bool:
        return (self.life.birth < t < self.life.death
               and self._d(p) <= self.life.radius(t))

    def ruin_age(self, p: Vec, t: float) -> float | None:
        return self.life.ruin_age(self._d(p), t)

    def ruin_salience(self, p: Vec, t: float) -> float:
        return self.life.ruin_salience(self._d(p), t)

    def manifest(self, p: Vec, t: float, sid: StarID | None = None) -> Manifestation | None:
        """Status is a property of the POINT, not the civ: during a
        collapse, a system in the receded annulus is already ruins even
        though the civ still lives at its core."""
        d = self._d(p)
        peak = max(self.life.peak_radius(), 1e-9)
        base: Manifestation = {"entity": self.name, "kind": self.kind,
                               "influence": round(max(0.0, 1.0 - d / peak), 2),
                               "genome": self.genome}
        if self.is_living_at(p, t):
            base["status"] = self.life.status(t)
            return base
        age = self.life.ruin_age(d, t)
        if age is None:
            return None
        salience = self.life.ruin_salience(d, t)
        if salience < SALIENCE_CUTOFF:
            return None
        base["status"] = ("RUINS (abandoned mid-collapse)"
                          if t < self.life.death else "RUINS")
        base["ruin_age"] = round(age)
        base["salience"] = round(salience, 2)
        return base


@dataclass(frozen=True)
class Ruin(Event):
    """A thing that already happened -- war debris, a failed colony,
    the wreckage of something -- with no living phase ever queryable, and
    no permanence either: like any ordinary Event, it genuinely fades
    away (see `contains()`). Deliberately NOT a `Civ`: it has no
    placement `kind` (it wasn't spawned by any of Tier 1's strategies)
    and no genome (it was never a going concern with traits). Just a
    name, a place, a `Lifecycle` (almost always built via
    `Lifecycle.instant_ruin`), and a free-text `cause` for flavor -- this
    mirrors how Tier 0's `Custodian`/`Lattice` are also their own classes
    rather than `Civ`s, despite being "things in spacetime" too.

    EXTENSION POINT: today these are only ever hand-authored (see
    `ruins.py`'s AUTHORED_RUINS). Once `overlap.py` grows a resolution
    layer, a war between two civs should be able to produce one of these
    at the encounter site -- nothing about this class or how the query
    layer handles it needs to change for that, only where instances come
    from."""

    name: str
    home: Vec
    life: Lifecycle
    cause: str = ""

    def _d(self, p: Vec) -> float:
        return math.hypot(self.home[0] - p[0], self.home[1] - p[1])

    def contains(self, p: Vec, t: float) -> bool:
        """Inside the footprint AND still salient. Never "living", so
        this is a pure salience gate once inside the geometry -- once
        faded below cutoff, the Ruin is simply gone."""
        d = self._d(p)
        if d > self.life.peak_radius_by(t):
            return False
        return self.life.ruin_salience(d, t) >= SALIENCE_CUTOFF

    def ruin_age(self, p: Vec, t: float) -> float | None:
        return self.life.ruin_age(self._d(p), t)

    def ruin_salience(self, p: Vec, t: float) -> float:
        return self.life.ruin_salience(self._d(p), t)

    def manifest(self, p: Vec, t: float, sid: StarID | None = None) -> Manifestation | None:
        """A Ruin has no living status -- ever. Just history, if it's
        still salient enough to detect."""
        d = self._d(p)
        age = self.life.ruin_age(d, t)
        if age is None:
            return None
        salience = self.life.ruin_salience(d, t)
        if salience < SALIENCE_CUTOFF:
            return None
        return {"entity": self.name, "kind": "ruin", "cause": self.cause,
               "status": "RUINS", "ruin_age": round(age), "salience": round(salience, 2)}
