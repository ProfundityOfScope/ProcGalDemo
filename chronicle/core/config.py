"""All tunable knobs in one place. Distances in light-years, times in years."""
import math

MASTER_SEED: int = 20260702

# ---------------------------------------------------------------- galaxy
GALAXY_R: float = 50_000.0        # disk RADIUS (100 kly across)
R_SCALE: float = GALAXY_R / 3.0   # exponential disk scale length
N_STARS_TARGET: int = 1_100       # expected star count ("pretend it's a lot")
EPOCH_LEN: float = 1_000_000.0    # spacetime-cell duration, years
T_PRESENT: float = 13.0e9         # cosmic age of "the present"

# ---------------------------------------------------------------- galaxy evolution
METALLICITY_FLOOR: float = 2.0e9
RISE_SCALE: float = 3.0e9
DECLINE_SCALE: float = 8e9
PEAK_TIME: float = 9e9

# ---------------------------------------------------------------- tiles
TILE: float = 12_500.0            # star-tile edge length

# ---------------------------------------------------------------- tier 1A: great powers
# (radius_fraction_of_GALAXY_R, count) per placement annulus -- Minecraft-style
GP_RINGS: tuple[float, float, float] = (0.25, 0.55, 0.85)
GP_RATE_PER_EPOCH: float = 2.0 # TODO: come back to this
GP_R_MAX: float = 0.06 * GALAXY_R
GP_LIFESPAN: tuple[float, float] = (50_000.0, 400_000.0)
GP_SPEED: tuple[float, float] = (0.01, 0.03)          # ly/yr (fraction of c)

# ---------------------------------------------------------------- tier 1B: minor civs
CIV_CELL: float = 12_500.0        # spawn-cell edge length
CIV_RATE_PER_EPOCH: float = 6.0            # Poisson mean per cell at density 1.0 (whole history)
CIV_R_MAX: float = 1_500.0        # hard cap on any minor civ's reach
CIV_LIFESPAN: tuple[float, float] = (5_000.0, 40_000.0)
CIV_SPEED: tuple[float, float] = (0.005, 0.02)

# ---------------------------------------------------------------- tier 1C: cluster leagues
CLUSTER_CELL: float = 25_000.0    # coarser spawn cells
CLUSTER_RATE_PER_EPOCH: float = 20.0         # Poisson mean per qualifying cell
CLUSTER_DENSITY_GATE: float = 0.30   # 'biome' requirement on stellar_density
CLUSTER_R_PER_DENSITY: float = 2_000.0   # max_radius = density * this
CLUSTER_R_MAX: float = 2_000.0
CLUSTER_LIFESPAN: tuple[float, float] = (20_000.0, 60_000.0)
CLUSTER_SPEED: tuple[float, float] = (0.005, 0.015)

# ---------------------------------------------------------------- ruin decay
# Salience: how detectable/visible a ruin is, decaying as exp(-age / tau).
# Tau differs by what was built: flimsy habitats fade fast, great-power
# cores linger. (Tier 0 has NO tau -- not decaying is what makes it mythic.)
GP_DECAY_TAU: float = 300_000.0
CIV_DECAY_TAU: float = 40_000.0
CLUSTER_DECAY_TAU: float = 80_000.0
SALIENCE_CUTOFF: float = 0.05     # below this, a ruin sinks beneath the noise floor

# ---------------------------------------------------------------- tier 0
CUSTODIAN_CENTER_R: tuple[float, float] = (0.2 * GALAXY_R, 0.6 * GALAXY_R)
CUSTODIAN_RADIUS: tuple[float, float] = (0.12 * GALAXY_R, 0.22 * GALAXY_R)

LATTICE_BAND: tuple[float, float] = (0.30 * GALAXY_R, 0.80 * GALAXY_R)
LATTICE_NODES: int = 12
LATTICE_SPACING: float = 0.08 * GALAXY_R   # min anchor separation
LATTICE_FAIL_TIME: float = T_PRESENT     # first node goes dark
LATTICE_FAIL_SPEED: float = 0.1            # collapse wave, ly/yr

# ---------------------------------------------------------------- lookbacks
def _lookback(lifespan_max: float, tau: float) -> float:
    return lifespan_max + tau * math.log(1.0/SALIENCE_CUTOFF)

CIV_LOOKBACK: float = _lookback(CIV_LIFESPAN[1], CIV_DECAY_TAU)
CLUSTER_LOOKBACK: float = _lookback(CLUSTER_LIFESPAN[1], CLUSTER_DECAY_TAU)
GP_LOOKBACK: float = _lookback(GP_LIFESPAN[1], GP_DECAY_TAU)