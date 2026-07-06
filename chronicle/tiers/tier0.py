"""Tier 0: the mythic registry. A handful of hand-authored Events,
resident forever (a few KB). Mythic permanence -- no decay machinery at
all -- is a deliberate, rare exception (see core/event.py); these
are the only things allowed to break the locality budget or claim to
exist "forever, from deep time"."""

import math
from dataclasses import dataclass

from ..core import Event, Manifestation, StarID, Vec
from ..core.config import (CUSTODIAN_CENTER_R, CUSTODIAN_RADIUS, LATTICE_BAND,
                           LATTICE_FAIL_SPEED, LATTICE_FAIL_TIME, LATTICE_NODES,
                           LATTICE_SPACING)
from ..core.rng import sub_rng
from ..core.stars import nearest_star

def _dist(p: Vec, q: Vec) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


@dataclass
class Custodian(Event):
    """Active dormant machine intelligence. Huge circular footprint.
    Manifestation grammar: sparse monoliths, probability rising toward
    center; everywhere else in the footprint, just the feeling of being
    watched. Per-star rolls are keyed on the STABLE star ID. No
    `Lifecycle`, no decay -- eternal by deliberate design, not a huge
    number plugged into the normal envelope math."""

    name: str = "The Custodian"
    key: tuple = ("mega",)
    radius_r: tuple[float, float] = CUSTODIAN_RADIUS
    center: Vec = (0.0, 0.0)
    radius: float = 0.0

    def __post_init__(self) -> None:
        rng = sub_rng("tier0", "custodian", *self.key)
        ang = rng.random() * 2 * math.pi
        rad = rng.uniform(*CUSTODIAN_CENTER_R)
        self.center = (rad * math.cos(ang), rad * math.sin(ang))
        self.radius = rng.uniform(*self.radius_r)

    def contains(self, p: Vec, t: float) -> bool:
        return _dist(self.center, p) <= self.radius

    def manifest(self, p: Vec, t: float, sid: StarID | None = None) -> Manifestation | None:
        if sid is None:
            return None
        d = _dist(self.center, p)
        if d > self.radius:
            return None
        roll = float(sub_rng("tier0", "custodian", *self.key, sid).random())
        strength = 1.0 - d / self.radius
        trace = ("silent monolith" if roll < 0.08 + 0.20 * strength
                 else "sensor ghosts / watched feeling")
        return {"entity": self.name, "trace": trace,
                "active": True, "proximity": round(strength, 2)}


@dataclass
class Lattice(Event):
    """Dead precursor relay network. Anchors sampled and snapped to real
    stars, linked by a relative-neighborhood graph. Shut down in a
    collapse wave propagating from the failure origin at 0.1c -- when any
    relay went dark is a pure function of its position. No `Lifecycle`
    either: a relay's ANCHOR never stops being one (that's the mythic
    permanence), only whether it's currently broadcasting changes.

    By default anchors scatter across a full annulus around the galaxy
    origin (`band`). Set `local_center` (with `local_spread`) to instead
    cluster the anchors in one hand-picked corner of the galaxy."""

    name: str = "The Lattice"
    key: tuple = ("mega",)
    nodes: int = LATTICE_NODES
    spacing: float = LATTICE_SPACING
    band: tuple[float, float] = LATTICE_BAND
    local_center: Vec | None = None    # set => cluster around this point instead
    local_spread: float | None = None  # radius of that local cluster
    anchors: list[tuple[StarID, Vec]] = None   # type: ignore[assignment]
    edges: list[tuple[int, int]] = None        # type: ignore[assignment]
    fail_origin: Vec = (0.0, 0.0)

    def __post_init__(self) -> None:
        rng = sub_rng("tier0", "lattice", *self.key)

        anchors: list[tuple[StarID, Vec]] = []
        attempts = 0
        while len(anchors) < self.nodes and attempts < 500:
            attempts += 1
            if self.local_center is not None:
                ang = rng.random() * 2 * math.pi
                rad = rng.uniform(0.0, self.local_spread)
                candidate: Vec = (self.local_center[0] + rad * math.cos(ang),
                                  self.local_center[1] + rad * math.sin(ang))
            else:
                ang = rng.random() * 2 * math.pi
                rad = rng.uniform(*self.band)
                candidate = (rad * math.cos(ang), rad * math.sin(ang))
            sid, pos = nearest_star(candidate)
            if any(sid == a_sid for a_sid, _ in anchors):
                continue
            if any(_dist(pos, q) < self.spacing for _, q in anchors):
                continue
            anchors.append((sid, pos))
        self.anchors = anchors

        # relative-neighborhood graph: link i,j unless some k is closer to both
        pts = [q for _, q in anchors]
        edges: list[tuple[int, int]] = []
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                dij = _dist(pts[i], pts[j])
                if not any(
                    max(_dist(pts[i], pts[k]), _dist(pts[j], pts[k])) < dij
                    for k in range(len(pts)) if k not in (i, j)
                ):
                    edges.append((i, j))
        self.edges = edges
        self.fail_origin = pts[int(rng.integers(len(pts)))]

    def dark_time(self, p: Vec) -> float:
        """When the relay at p went (or will go) silent."""
        return LATTICE_FAIL_TIME + _dist(self.fail_origin, p) / LATTICE_FAIL_SPEED

    def contains(self, p: Vec, t: float) -> bool:
        """The relay HULK is still there whether it's alive or dark --
        that's the point of it being mythic. `p` is expected to be an
        exact star position (as returned by `nearest_star`/
        `star_position`), so exact equality is reliable here, not an
        approximation."""
        return any(p == q for _, q in self.anchors)

    def manifest(self, p: Vec, t: float, sid: StarID | None = None) -> Manifestation | None:
        if sid is None or not any(sid == a_sid for a_sid, _ in self.anchors):
            return None
        dark = self.dark_time(p)
        if t < dark:
            return {"entity": self.name, "active": True,
                    "trace": "RELAY ACTIVE (beacon broadcasting)",
                    "goes_dark_at": round(dark)}
        return {"entity": self.name, "active": False,
                "trace": f"dead relay hulk (dark for {t - dark:,.0f} yr)",
                "went_dark_at": round(dark)}


AUTHORED: list = [
    Custodian(key=("mega",)),
    Lattice(key=("mega",)),
]


def build_tier0() -> list:
    """The whole mythic registry: hand-authored only. Called once; a few
    KB, resident forever."""
    return list(AUTHORED)
