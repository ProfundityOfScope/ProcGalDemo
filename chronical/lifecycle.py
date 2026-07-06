"""Civ lifecycle envelope. All times in ABSOLUTE years.

The envelope is a trapezoid: linear rise to a peak, plateau, linear
collapse to zero. Ruins appear where the LIVING envelope has receded --
during collapse that's a growing annulus of abandonment chasing the
shrinking frontier inward; at death it completes into a disk. Nothing
pops into existence.

Every system's ruins have their own age: abandoned_at(d) inverts the
decline curve, so the frontier (abandoned first) always carries older
ruins than the core. Salience -- how detectable a ruin still is --
decays as exp(-age / decay_tau). Vacuum preserves matter; what decays
is SIGNAL. Old ruins don't vanish, they sink below the noise floor.
"""

import math
from dataclasses import dataclass, field

from .density import Vec


@dataclass(frozen=True)
class Lifecycle:
    """Influence radius as a pure function of time, plus the post-mortem
    salience curve. Rise, plateau, collapse, fade."""

    birth: float
    expansion_speed: float          # ly / year (well below c)
    max_radius: float
    lifespan: float                 # years, birth -> final silence
    decline_frac: float = 0.25      # final fraction of life spent collapsing
    decay_tau: float = 50_000.0     # ruin salience e-folding time (years)

    @property
    def death(self) -> float:
        return self.birth + self.lifespan

    @property
    def _decline_start(self) -> float:
        return self.death - self.lifespan * self.decline_frac

    @property
    def _decline_dur(self) -> float:
        return self.lifespan * self.decline_frac

    # ------------------------------------------------------- the envelope
    def peak_radius(self) -> float:
        return min(self.max_radius,
                   (self._decline_start - self.birth) * self.expansion_speed)

    def radius(self, t: float) -> float:
        """Living envelope. Trapezoid: the decline is linear FROM THE PEAK
        (the old growth*decay product was a parabola for speed-limited
        civs, which made the recede time ambiguous)."""
        if t <= self.birth or t >= self.death:
            return 0.0
        if t <= self._decline_start:
            return min(self.max_radius, (t - self.birth) * self.expansion_speed)
        return self.peak_radius() * (self.death - t) / self._decline_dur

    def peak_radius_by(self, t: float) -> float:
        """Max radius achieved UP TO time t -- the historical footprint.
        This replaces the old 'frozen peak circle at death'."""
        if t <= self.birth:
            return 0.0
        reach_t = min(t, self._decline_start)
        return min(self.max_radius, (reach_t - self.birth) * self.expansion_speed)

    # ------------------------------------------------------- abandonment
    def abandoned_at(self, d: float) -> float | None:
        """When the living envelope receded past distance d from home.
        Inverts the linear decline: d = peak -> decline start (frontier
        abandoned FIRST), d = 0 -> death. None if never covered."""
        peak = self.peak_radius()
        if d > peak:
            return None
        if peak <= 0.0:
            return self.death
        return self.death - self._decline_dur * (max(d, 0.0) / peak)

    def ruin_age(self, d: float, t: float) -> float | None:
        """Age of the ruins at distance d, at time t. None if that spot is
        still living, was never covered, or hasn't been reached yet."""
        if d > self.peak_radius_by(t):
            return None                     # envelope never got there (yet)
        t_ab = self.abandoned_at(d)
        if t_ab is None or t < t_ab:
            return None                     # still living there
        return t - t_ab

    def ruin_salience(self, d: float, t: float) -> float:
        """Detectability of the ruins at distance d: 1.0 fresh -> 0.0 gone."""
        age = self.ruin_age(d, t)
        return 0.0 if age is None else math.exp(-age / self.decay_tau)

    def visible_ruin_radius(self, t: float, cutoff: float) -> float:
        """Outermost distance whose ruins still clear the salience cutoff.
        Since the frontier was abandoned first, ruins ERODE INWARD -- this
        radius shrinks over time until the whole footprint fades."""
        peak = self.peak_radius()
        if peak <= 0.0 or t <= self._decline_start:
            return 0.0
        age_max = -self.decay_tau * math.log(cutoff)
        d = (age_max - (t - self.death)) * peak / self._decline_dur
        return min(max(d, 0.0), peak)

    # ------------------------------------------------------- status
    def status(self, t: float) -> str:
        if t < self.birth:
            return "not yet"
        if t >= self.death:
            return "RUINS"
        if t > self._decline_start:
            return "collapsing"
        if self.radius(t) >= self.peak_radius() * 0.95:
            return "peak"
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


@dataclass(frozen=True)
class Civ:
    name: str
    kind: str                       # which placement strategy made it
    home: Vec                       # birth coordinates (a snapped star)
    life: Lifecycle
    genome: dict = field(default_factory=dict)

    def _d(self, p: Vec) -> float:
        return math.hypot(self.home[0] - p[0], self.home[1] - p[1])

    def contains(self, p: Vec, t: float) -> bool:
        """Inside the historical footprint (living OR abandoned). Geometric
        only -- salience filtering is the query layer's job, because even a
        fully-faded ruin still physically exists for a deliberate survey."""
        return self._d(p) <= self.life.peak_radius_by(t)

    def is_living_at(self, p: Vec, t: float) -> bool:
        return (self.life.birth < t < self.life.death
                and self._d(p) <= self.life.radius(t))

    def ruin_age(self, p: Vec, t: float) -> float | None:
        return self.life.ruin_age(self._d(p), t)

    def ruin_salience(self, p: Vec, t: float) -> float:
        return self.life.ruin_salience(self._d(p), t)