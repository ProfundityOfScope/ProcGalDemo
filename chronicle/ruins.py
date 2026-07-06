"""Hand-authored instant ruins: things that already happened, with no
living phase anyone could ever have queried. Same AUTHORED-list pattern
as tier0.py, but these aren't mythic/permanent singletons like the
Custodian or Lattice -- they're ordinary history that decays like
anything else (their salience fades same as any civ's ruins), they just
never had a "living" status at all.

EXTENSION POINT: once overlap.py grows a resolution layer, wars/failed
mergers between civs should be able to produce Ruin instances at the
encounter site -- append to a list here, or (better, once there could be
many) generate them lazily the same way tier1 lazily spawns civs.
Nothing about `Ruin` or how `query.py` handles it needs to change for
that, only where the instances come from.
"""

from .core.stars import nearest_star
from .lifecycle import Lifecycle, Ruin

_, _ashfall_home = nearest_star((-18_000.0, 9_500.0))
_, _lance_home = nearest_star((26_500.0, -31_000.0))

AUTHORED_RUINS: list[Ruin] = [
    Ruin(
        name="The Ashfall Colony",
        home=_ashfall_home,
        life=Lifecycle.instant_ruin(
            spawn_time=6_500_000_000.0, radius=350.0, decay_tau=45_000.0,
            death_kind="sublimation",
        ),
        cause="failed colonization attempt",
    ),
    Ruin(
        name="The Lance Wreck",
        home=_lance_home,
        life=Lifecycle.instant_ruin(
            spawn_time=11_200_000_000.0, radius=120.0, decay_tau=15_000.0,
            death_kind="outward_collapse",
        ),
        cause="debris field, origin unknown",
    ),
]
