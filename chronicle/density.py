"""Analytic stellar density field -- the shared 'biome map'.

Nothing ever counts actual stars. Star tiles, civ spawn rates, and biome
gates all read this function instead. Evaluable anywhere in O(1).

Currently a pure exponential disk; a spiral-arm modulation term can be
multiplied in later (1 + a*cos(N*theta - r/pitch)) and everything downstream
inherits it automatically.
"""

import math

from .config import R_SCALE

Vec = tuple[float, float]


def stellar_density(p: Vec) -> float:
    """Relative stellar density at point p. 1.0 at galactic center."""
    r = math.hypot(p[0], p[1])
    return math.exp(-r / R_SCALE)
