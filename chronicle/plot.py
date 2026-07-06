"""Plotting. plot_era(ax, t) draws one moment in history; the three-panel
figure just calls it three times.

Discipline check: this module sees the world ONLY through the same lazy
accessors the game would use (stars_in_tile, minor_civs_in_cell, ...).
No secret global list exists for it to read.

Honesty note: at 100 kly, real civ radii are invisible dots. The
`inflate` factor scales Tier 1 radii FOR DISPLAY ONLY -- the data
underneath stays honest.
"""

import math

import matplotlib.pyplot as plt

from .core.config import CIV_CELL, CLUSTER_CELL, GALAXY_R, SALIENCE_CUTOFF, CIV_LOOKBACK, CLUSTER_LOOKBACK, GP_LOOKBACK
from .core.stars import stars_in_tile, tile_range
from .lifecycle import Civ, Ruin
from .ruins import AUTHORED_RUINS
from .tiers.tier0 import Custodian, Lattice
from .tiers.tier1 import cluster_leagues_in_cell, great_powers_in_cell, minor_civs_in_cell, epoch_window

KIND_COLOR: dict[str, str] = {
    "stronghold-style": "#ff5f5f",
    "mineshaft-style": "#5fb0ff",
    "dripstone-style": "#ffd75f",
}
DEFAULT_KIND_COLOR = "#c8c8c8"  # fallback for kinds not in the table above
                                # (instant ruins, and anything else added later)


def draw_civ(ax: plt.Axes, c: "Civ | Ruin", t_eval: float, inflate: float = 8.0) -> None:
    """The one civ (and Ruin) renderer, shared by the Chronicle and the
    Lightcone (callers differ only in what time they pass: coordinate or
    retarded). Works for anything exposing `.home`/`.life` -- a `Ruin`
    has no `.kind`, so it just falls through to DEFAULT_KIND_COLOR,
    which reads as a fitting ash-gray for "history, not a going concern".

    Living envelope: filled circle at radius(t).
    Ruins: dashed ring at visible_ruin_radius(t) -- the erosion frontier.
    The frontier was abandoned first, so ruins fade OUTSIDE-IN: the ring
    shrinks and dims until the footprint sinks below the noise floor.
    During a collapse both are visible at once: a shrinking living core
    inside a growing-then-eroding ring of abandonment."""
    r_live = c.life.radius(t_eval)
    if r_live > 0:
        kind = getattr(c, "kind", None)
        color = DEFAULT_KIND_COLOR if kind is None else KIND_COLOR.get(kind, DEFAULT_KIND_COLOR)
        ax.add_patch(plt.Circle(c.home, r_live * inflate, fill=True,
                                alpha=0.10, fc=color))
        ax.add_patch(plt.Circle(c.home, r_live * inflate, fill=False,
                                lw=1.1, ec=color, alpha=0.9))
    r_vis = c.life.visible_ruin_radius(t_eval, SALIENCE_CUTOFF)
    if r_vis > r_live:
        mid_d = 0.5 * (r_live + r_vis)
        sal = c.life.ruin_salience(mid_d, t_eval)
        ax.add_patch(plt.Circle(c.home, r_vis * inflate, fill=False,
                                lw=0.7, ls="--", ec="#666f80",
                                alpha=0.15 + 0.55 * sal))


def _all_cells(cell: float) -> list[tuple[int, int]]:
    n = int(math.ceil(GALAXY_R / cell))
    return [(cx, cy) for cx in range(-n, n) for cy in range(-n, n)]


def iter_civs_via_cells(t: float, extra_lookback: float = 0.0) -> list[Civ]:
    """Enumerate every civ the lazy cells can produce (for plots/stats).
    Still goes through the lazy accessors -- the 'god view' is just a loop
    over the same functions the game calls."""
    
    civs: list[Civ] = []
    for e in epoch_window(t, GP_LOOKBACK):
        civs.extend(great_powers_in_cell(e))
        
    for cx, cy in _all_cells(CIV_CELL):
        for e in epoch_window(t, CIV_LOOKBACK):
            civs.extend(minor_civs_in_cell(cx, cy, e))
            
    for cx, cy in _all_cells(CLUSTER_CELL):
        for e in epoch_window(t, CLUSTER_LOOKBACK):
            civs.extend(cluster_leagues_in_cell(cx, cy, e))
            
    rel_civs = [c for c in civs if 
                c.life.is_relevant_between(t - extra_lookback, t,
                                           SALIENCE_CUTOFF)]
    return rel_civs


def plot_era(ax: plt.Axes, t: float, tier0: list, inflate: float = 8.0) -> None:
    """Draw the galaxy at coordinate time t onto an axes. Reuse freely."""
    ax.set_facecolor("#0b0e14")

    # stars, via lazy tiles
    xs: list[float] = []
    ys: list[float] = []
    for tx in tile_range():
        for ty in tile_range():
            for _, (x, y) in stars_in_tile(tx, ty):
                xs.append(x)
                ys.append(y)
    ax.scatter(xs, ys, s=2, c="#8892a6", alpha=0.5, lw=0)

    # tier 0
    for entity in tier0:
        if isinstance(entity, Custodian):
            ax.add_patch(plt.Circle(entity.center, entity.radius, fill=False,
                                    ec="#b06fff", ls=":", lw=1.6, alpha=0.9))
        elif isinstance(entity, Lattice):
            pts = [q for _, q in entity.anchors]
            for i, j in entity.edges:
                alive = (t < entity.dark_time(pts[i])
                         and t < entity.dark_time(pts[j]))
                ax.plot([pts[i][0], pts[j][0]], [pts[i][1], pts[j][1]],
                        c="#59ffb0" if alive else "#3a4152",
                        lw=1.5 if alive else 0.9,
                        alpha=0.95 if alive else 0.7)
            for pt in pts:
                alive = t < entity.dark_time(pt)
                ax.scatter(*pt, s=42, marker="D",
                           c="#59ffb0" if alive else "#3a4152", zorder=5)

    # tier 1 (radii inflated for display only)
    for c in iter_civs_via_cells(t):
        draw_civ(ax, c, t, inflate)

    # authored instant ruins (no living phase, ever -- see ruins.py)
    for r in AUTHORED_RUINS:
        draw_civ(ax, r, t, inflate)

    ax.set_title(f"t = {t:,.0f} yr", color="#e6e6e6", fontsize=13)
    lim = GALAXY_R * 1.05
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.axis("off")


def three_era_figure(times: tuple[float, float, float], tier0: list,
                     out_path: str, inflate: float = 8.0) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(19, 6.6), facecolor="#0b0e14")
    for ax, t in zip(axes, times):
        plot_era(ax, t, tier0, inflate=inflate)
    handles = [
        plt.Line2D([], [], c="#b06fff", ls=":", label="Tier 0: Custodian footprint (active)"),
        plt.Line2D([], [], c="#59ffb0", marker="D", ls="-", label="Tier 0: Lattice (live relays)"),
        plt.Line2D([], [], c="#3a4152", marker="D", ls="-", label="Tier 0: Lattice (dead relays)"),
        plt.Line2D([], [], c="#ff5f5f", label="Tier 1A: Great Powers (stronghold-style)"),
        plt.Line2D([], [], c="#5fb0ff", label="Tier 1B: minor civs (mineshaft-style)"),
        plt.Line2D([], [], c="#ffd75f", label="Tier 1C: cluster leagues (dripstone-style)"),
        plt.Line2D([], [], c="#666f80", ls="--", label="ruins (eroding, fading)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
               labelcolor="#e6e6e6", fontsize=9.5)
    fig.suptitle(
        f"Tiered Procedural Galaxy, 100 kly across — civ radii ×{inflate:g} for visibility",
        color="#ffffff", fontsize=15, y=0.98)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(out_path, dpi=140, facecolor=fig.get_facecolor())