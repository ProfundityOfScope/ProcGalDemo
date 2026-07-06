"""Lazy star generation.

There is no global star array. Stars exist only as answers to
stars_in_tile(tx, ty), which is a pure function of the master seed
(lru_cache just makes repeated asks free). A star's identity is its
stable ID (tx, ty, i) -- never its rounded coordinates.

Temportal note: stars are effectively timeless over the lifespan of the sim,
in that a "star" here is more about the mass being budgeted, and the later
generation can decide what happened to that mass (proto->MS->giant->remnant)
"""

import math
from functools import lru_cache

from .config import GALAXY_R, N_STARS_TARGET, TILE
from .density import stellar_density, Vec
from .rng import sub_rng

StarID = tuple[int, int, int]   # (tile_x, tile_y, index_within_tile)


def tile_of(p: Vec) -> tuple[int, int]:
    """Which tile contains point p."""
    return int(math.floor(p[0] / TILE)), int(math.floor(p[1] / TILE))


def tile_center(tx: int, ty: int) -> Vec:
    return ((tx + 0.5) * TILE, (ty + 0.5) * TILE)


def tile_range() -> range:
    """Index range covering the disk along each axis."""
    n = int(math.ceil(GALAXY_R / TILE))
    return range(-n, n)


@lru_cache(maxsize=1)
def _density_norm() -> float:
    """Calibration constant K so expected total star count ~= N_STARS_TARGET.

    Computed once by summing the density field over all tile centers
    (a few hundred evaluations -- independent of star count).
    """
    total = sum(
        stellar_density(tile_center(tx, ty)) * TILE**2
        for tx in tile_range()
        for ty in tile_range()
    )
    return N_STARS_TARGET / total


@lru_cache(maxsize=None)
def stars_in_tile(tx: int, ty: int) -> list[tuple[StarID, Vec]]:
    """All stars in a tile: Poisson count from the density field,
    uniform positions, stars outside the disk rejected."""
    rng = sub_rng("tile", tx, ty)
    lam = _density_norm() * stellar_density(tile_center(tx, ty)) * TILE**2
    n = int(rng.poisson(lam))
    out: list[tuple[StarID, Vec]] = []
    for i in range(n):
        p: Vec = ((tx + rng.random()) * TILE, (ty + rng.random()) * TILE)
        if math.hypot(p[0], p[1]) <= GALAXY_R:
            out.append(((tx, ty, i), p))
    return out


def star_position(sid: StarID) -> Vec:
    """Resolve a stable ID back to coordinates (regenerates its tile)."""
    tx, ty, i = sid
    for candidate_id, p in stars_in_tile(tx, ty):
        if candidate_id == sid:
            return p
    raise KeyError(f"No such star: {sid}")


def nearest_star(p: Vec) -> tuple[StarID, Vec]:
    """Nearest star to p: expanding ring search over tiles.

    O(nearby tiles), independent of galaxy size. After the first hit we
    search one extra ring, since a star in the next ring can be closer
    than one found in the current ring's corner.
    """
    tx0, ty0 = tile_of(p)
    best: tuple[StarID, Vec] | None = None
    best_d = math.inf
    ring = 0
    found_ring: int | None = None
    while True:
        for tx in range(tx0 - ring, tx0 + ring + 1):
            for ty in range(ty0 - ring, ty0 + ring + 1):
                if max(abs(tx - tx0), abs(ty - ty0)) != ring:
                    continue   # only the ring's shell
                for sid, q in stars_in_tile(tx, ty):
                    d = math.hypot(p[0] - q[0], p[1] - q[1])
                    if d < best_d:
                        best, best_d = (sid, q), d
        if best is not None and found_ring is None:
            found_ring = ring
        if found_ring is not None and ring >= found_ring + 1:
            return best   # type: ignore[return-value]
        ring += 1
        if ring > len(tile_range()):   # pathological: empty galaxy
            raise RuntimeError("No stars found anywhere near point")
