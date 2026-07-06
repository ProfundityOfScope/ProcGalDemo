"""The long-time era curve that dictates how the galaxy booms and busts

Temporal counterpart to density.py
"""

import math

from .config import METALLICITY_FLOOR, RISE_SCALE, DECLINE_SCALE, PEAK_TIME

Vec = tuple[float, float]


def era_curve(t: float) -> float:
    """Relative civilization-generation rate at cosmic time t.
    I do think this is in need of some serious edits down the road"""
    if t < METALLICITY_FLOOR:
        return 0.0
    x = (t - METALLICITY_FLOOR) / RISE_SCALE
    rise = 1.0 - math.exp(-x)
    fade = math.exp(-max(0.0, t-PEAK_TIME) / DECLINE_SCALE)
    return rise * fade