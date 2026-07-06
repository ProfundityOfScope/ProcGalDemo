"""The Lightcone layer: what a ship actually SEES, versus what IS.

The whole relativistic observation mechanic is one line:

    apparent_state(p) = state(p, t - |p - ship| / c)

Every point in the sky is sampled at its own retarded time -- near things
are nearly 'now', the rim is deep past. Because the Chronicle is a pure
function of (seed, time), asking about the past costs the same as asking
about the present. No history is stored; it is re-derived on demand.

Run from the repo root:
    python -m chronicle.observer

Things to tweak at the bottom: SHIP frac/angle, OBS_TIME, the era of the
comparison. The demo auto-places the ship far from the Lattice's failure
origin so the disagreement between panels is dramatic.

Simplification worth knowing about: each civ is evaluated at the retarded
time of its HOME star (a 'rigid body' approximation). Strictly, every
point of an extended envelope has its own retarded time, so a fast-
collapsing empire should look subtly warped -- its near edge older news
than its far edge... wait, the reverse: near edge seen more recently.
Doing that per-point is a fun exercise (fixed-point solve on the radius);
for envelopes this small relative to galaxy scale the error is tiny.
"""

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .core import Vec
from .core.config import GALAXY_R, T_PRESENT
from .core.stars import stars_in_tile, tile_range
from .plot import draw_civ, iter_civs_via_cells
from .query import tier0_registry
from .ruins import AUTHORED_RUINS
from .tiers.tier0 import AUTHORED, Custodian, Lattice

C: float = 1.0   # ly / yr. The constant the whole game is about.


# ----------------------------------------------------------------- core
def _dist(p: Vec, q: Vec) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


def retarded_time(p: Vec, ship: Vec, t: float) -> float:
    """The moment of p's history whose light reaches the ship at time t."""
    return t - _dist(p, ship) / C


# ----------------------------------------------------------- drawing bits
def _draw_stars(ax: plt.Axes) -> None:
    xs: list[float] = []
    ys: list[float] = []
    for tx in tile_range():
        for ty in tile_range():
            for _, (x, y) in stars_in_tile(tx, ty):
                xs.append(x)
                ys.append(y)
    ax.scatter(xs, ys, s=2, c="#8892a6", alpha=0.5, lw=0)


def _draw_lattice(ax: plt.Axes, lat: Lattice, node_time) -> None:
    """node_time(pos) -> the time at which to evaluate that node.
    God view passes a constant; the lightcone passes retarded time."""
    pts = [q for _, q in lat.anchors]
    for i, j in lat.edges:
        alive = (node_time(pts[i]) < lat.dark_time(pts[i])
                 and node_time(pts[j]) < lat.dark_time(pts[j]))
        ax.plot([pts[i][0], pts[j][0]], [pts[i][1], pts[j][1]],
                c="#59ffb0" if alive else "#3a4152",
                lw=1.5 if alive else 0.9, alpha=0.95 if alive else 0.7)
    for pt in pts:
        alive = node_time(pt) < lat.dark_time(pt)
        ax.scatter(*pt, s=42, marker="D",
                   c="#59ffb0" if alive else "#3a4152", zorder=5)


def _frame(ax: plt.Axes, title: str) -> None:
    ax.set_title(title, color="#e6e6e6", fontsize=12)
    lim = GALAXY_R * 1.05
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("#0b0e14")


# ----------------------------------------------------------- the two views
def plot_chronicle(ax: plt.Axes, t: float, tier0: list,
                   inflate: float = 8.0) -> None:
    """God view: everything evaluated at the same coordinate time t.
    (Same idea as plot_era; repeated here so this file is self-contained
    to tweak.)"""
    _frame(ax, f"THE CHRONICLE — what IS at t = {t:,.0f}")
    _draw_stars(ax)
    for e in tier0:
        if isinstance(e, Custodian):
            ax.add_patch(plt.Circle(e.center, e.radius, fill=False,
                                    ec="#b06fff", ls=":", lw=1.6, alpha=0.9))
        elif isinstance(e, Lattice):
            _draw_lattice(ax, e, node_time=lambda p: t)
    for c in iter_civs_via_cells(t):
        draw_civ(ax, c, t, inflate)
    for r in AUTHORED_RUINS:
        draw_civ(ax, r, t, inflate)


def plot_lightcone(ax: plt.Axes, ship: Vec, t: float, tier0: list,
                   inflate: float = 8.0) -> None:
    """The ship's sky: every entity evaluated at ITS OWN retarded time."""
    delay_edge = _dist(ship, (GALAXY_R, 0.0))   # just for the title
    _frame(ax, f"THE LIGHTCONE — as seen from the ship at t = {t:,.0f}")
    _draw_stars(ax)
    for e in tier0:
        if isinstance(e, Custodian):
            ax.add_patch(plt.Circle(e.center, e.radius, fill=False,
                                    ec="#b06fff", ls=":", lw=1.6, alpha=0.9))
        elif isinstance(e, Lattice):
            _draw_lattice(ax, e, node_time=lambda p: retarded_time(p, ship, t))
            
    max_delay = 150_000 # manually set obviously
    for c in iter_civs_via_cells(t, extra_lookback=max_delay):
        draw_civ(ax, c, retarded_time(c.home, ship, t), inflate)
    for r in AUTHORED_RUINS:
        draw_civ(ax, r, retarded_time(r.home, ship, t), inflate)

    # lookback rings: everything on a ring is seen at the same moment
    for frac in (0.25, 0.5, 0.75, 1.0):
        r = frac * 1.6 * GALAXY_R
        ax.add_patch(plt.Circle(ship, r, fill=False, ec="#ffffff",
                                ls=(0, (2, 6)), lw=0.6, alpha=0.35))
        ax.annotate(f"−{r / C:,.0f} yr", (ship[0], ship[1] + r),
                    color="#ffffff", alpha=0.55, fontsize=7.5,
                    ha="center", va="bottom")
    # the ship
    ax.scatter(*ship, marker="^", s=130, c="#ffffff", ec="#0b0e14",
               zorder=10)
    ax.annotate("ship", ship, color="#ffffff", fontsize=9,
                xytext=(8, -14), textcoords="offset points")


# ----------------------------------------------------------------- figure
def compare_figure(ship: Vec, t: float, out_path: str,
                   inflate: float = 8.0) -> None:
    tier0 = tier0_registry()
    fig, axes = plt.subplots(1, 2, figsize=(15, 7.6), facecolor="#0b0e14")
    plot_chronicle(axes[0], t, tier0, inflate)
    plot_lightcone(axes[1], ship, t, tier0, inflate)
    fig.suptitle("Same seed, same moment — two truths "
                 f"(civ radii ×{inflate:g} for visibility)",
                 color="#ffffff", fontsize=14, y=0.99)
    fig.tight_layout(rect=(0, 0.01, 1, 0.94))
    fig.savefig(out_path, dpi=140, facecolor=fig.get_facecolor())
    print(f"Saved figure -> {out_path}")


def print_disagreements(ship: Vec, t: float) -> None:
    """Where the god view and the ship's sky disagree, entity by entity."""
    lat = next(e for e in AUTHORED if isinstance(e, Lattice))
    print(f"Ship at ({ship[0]:,.0f}, {ship[1]:,.0f}), t = {t:,.0f}")
    print(f"{'relay':>8} {'dist (ly)':>10} {'sees yr':>12} "
          f"{'IS':>6} {'APPEARS':>8}")
    for k, (sid, p) in enumerate(lat.anchors):
        d = _dist(p, ship)
        t_ret = retarded_time(p, ship, t)
        actual = "dark" if t >= lat.dark_time(p) else "alive"
        appears = "dark" if t_ret >= lat.dark_time(p) else "ALIVE"
        flag = "  <-- ghost signal" if actual == "dark" and appears == "ALIVE" else ""
        print(f"{k:>8} {d:>10,.0f} {t_ret:>12,.0f} {actual:>6} {appears:>8}{flag}")

    civ_ghosts = sum(
        1 for c in iter_civs_via_cells(t, extra_lookback=150_000)
        if t >= c.life.death > retarded_time(c.home, ship, t) > c.life.birth
    )
    print(f"\nCivs already dead whose light still shows them alive: {civ_ghosts}")


# ----------------------------------------------------------------- main
if __name__ == "__main__":
    # Ship placement: far side of the disk from the Lattice failure origin,
    # to maximize how out-of-date its news about the collapse is. Tweak me.
    lat = next(e for e in AUTHORED if isinstance(e, Lattice))
    ox, oy = lat.fail_origin
    norm = math.hypot(ox, oy)
    SHIP: Vec = (-ox / norm * 0.8 * GALAXY_R, -oy / norm * 0.8 * GALAXY_R)

    OBS_TIME: float = T_PRESENT + 3e5

    print_disagreements(SHIP, OBS_TIME)
    compare_figure(SHIP, OBS_TIME,
                   "outputs/lightcone_vs_chronicle.png")