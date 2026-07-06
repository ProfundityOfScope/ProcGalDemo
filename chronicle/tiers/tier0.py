"""Tier 0: the mythic registry. A handful of entities generated straight
from the master seed, resident forever (a few KB). These are the only
things allowed to break the locality budget."""

import math
from dataclasses import dataclass

from .config import (CUSTODIAN_CENTER_R, CUSTODIAN_RADIUS, LATTICE_BAND,
                     LATTICE_FAIL_SPEED, LATTICE_FAIL_TIME, LATTICE_NODES,
                     LATTICE_SPACING, T_PRESENT, TIER0_BLOCK,
                     TIER0_RATE_PER_GYR)
from .density import Vec
from .era import era_curve
from .rng import sub_rng
from .stars import StarID, nearest_star

Manifestation = dict[str, object]

AUTHORED = []

def _dist(p: Vec, q: Vec) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


@dataclass
class Custodian:
    """Active dormant machine intelligence. Huge circular footprint.
    Manifestation grammar: sparse monoliths, probability rising toward
    center; everywhere else in the footprint, just the feeling of being
    watched. Per-star rolls are keyed on the STABLE star ID."""

    name: str = "The Custodian"
    center: Vec = (0.0, 0.0)
    radius: float = 0.0

    def __post_init__(self) -> None:
        rng = sub_rng("tier0", "custodian")
        ang = rng.random() * 2 * math.pi
        rad = rng.uniform(*CUSTODIAN_CENTER_R)
        self.center = (rad * math.cos(ang), rad * math.sin(ang))
        self.radius = rng.uniform(*CUSTODIAN_RADIUS)

    def manifest(self, sid: StarID, p: Vec, t: float) -> Manifestation | None:
        d = _dist(self.center, p)
        if d > self.radius:
            return None
        roll = float(sub_rng("tier0", "custodian", sid).random())
        strength = 1.0 - d / self.radius
        trace = ("silent monolith" if roll < 0.08 + 0.20 * strength
                 else "sensor ghosts / watched feeling")
        return {"entity": self.name, "trace": trace,
                "active": True, "proximity": round(strength, 2)}


@dataclass
class Lattice:
    """Dead precursor relay network. Anchors sampled in a radial band and
    snapped to real stars, linked by a relative-neighborhood graph. Shut
    down in a collapse wave propagating from the failure origin at 0.1c --
    when any relay went dark is a pure function of its position."""

    name: str = "The Lattice"
    anchors: list[tuple[StarID, Vec]] = None   # type: ignore[assignment]
    edges: list[tuple[int, int]] = None        # type: ignore[assignment]
    fail_origin: Vec = (0.0, 0.0)

    def __post_init__(self) -> None:
        rng = sub_rng("tier0", "lattice")
        anchors: list[tuple[StarID, Vec]] = []
        attempts = 0
        while len(anchors) < LATTICE_NODES and attempts < 500:
            attempts += 1
            ang = rng.random() * 2 * math.pi
            rad = rng.uniform(*LATTICE_BAND)
            candidate: Vec = (rad * math.cos(ang), rad * math.sin(ang))
            sid, pos = nearest_star(candidate)
            if any(sid == a_sid for a_sid, _ in anchors):
                continue
            if any(_dist(pos, q) < LATTICE_SPACING for _, q in anchors):
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

    def manifest(self, sid: StarID, p: Vec, t: float) -> Manifestation | None:
        if not any(sid == a_sid for a_sid, _ in self.anchors):
            return None
        dark = self.dark_time(p)
        if t < dark:
            return {"entity": self.name, "active": True,
                    "trace": "RELAY ACTIVE (beacon broadcasting)",
                    "goes_dark_at": round(dark)}
        return {"entity": self.name, "active": False,
                "trace": f"dead relay hulk (dark for {t - dark:,.0f} yr)",
                "went_dark_at": round(dark)}

def spawn_mythic(rng, b, i):
    # TODO: figure out what this should do?
    return rng.choice([Lattice(), Custodian()])

def build_tier0() -> list:
    """The whole mythic registry. Called once; a few KB, resident forever."""
    entities = []
    for b in range(int(T_PRESENT / TIER0_BLOCK) + 1):
        rng = sub_rng("tier0", "block", b)
        block_mid = (b + 0.5) * TIER0_BLOCK
        lam = TIER0_RATE_PER_GYR * (TIER0_BLOCK / 1e9) * era_curve(block_mid)
        for i in range(int(rng.poisson(lam))):
            entities.append(spawn_mythic(rng, b, i))
    entities += AUTHORED
    return entities
