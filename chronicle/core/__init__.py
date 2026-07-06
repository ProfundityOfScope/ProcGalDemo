"""Foundational primitives shared across chronicle: config constants,
the deterministic RNG plumbing, the analytic density field, star
generation, the long-time era curve, and the `Event` contract every
queryable thing implements.

Re-exports only the numpy-FREE symbols (`Event`/`Manifestation`/`StarID`
from event.py, `Vec` from density.py, `era_curve` from era.py) for
convenient `from .core import X` access. `sub_rng`/`nearest_star`/
`star_position`/`stars_in_tile`/etc. need numpy (via rng.py), so they're
deliberately NOT re-exported here -- that's what lets `from .core import
Event` (and anything built only on Event, like the pure-math half of
`lifecycle/`) stay importable without numpy installed, which is what let
this package's core math be verified with a standalone script in an
environment where numpy wasn't available. Import those via
`.core.rng`/`.core.stars` directly. Config's many numeric constants are
the other deliberate omission -- config.py stays the single source of
truth, imported by name via `.core.config` rather than duplicated in a
second re-export list here.
"""

from .density import Vec
from .era import era_curve
from .event import Event, Manifestation, StarID

__all__ = [
    "Vec",
    "era_curve",
    "Event",
    "Manifestation",
    "StarID",
]
