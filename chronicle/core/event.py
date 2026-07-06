"""Event: the shared contract for anything with temporal + spatial
extent that a point-in-spacetime query can discover -- a civilization, a
ruin, a relic network, a burst, a superweapon's aftermath, whatever gets
added later. The query layer (and any future overlap-rules layer) can
treat every kind of Event identically, without type-specific dispatch.

Deliberately an interface only, with no shared data fields: a
disk-shaped, single-home thing (a civ, a ruin, the Custodian) and a
multi-anchor graph (the Lattice) don't share a natural data shape, only
a contract. Each concrete Event picks whatever fields make sense for it.

Ordinary Events fade: past some point they are simply GONE --
`contains` returns False, full stop, not "still technically there but
nobody would ever notice." Mythic-tier Events are the deliberate, rare
exception: built with no decay machinery at all, so permanence is an
explicit choice for a handful of hand-authored entities ("deep time"),
not a default every Event gets for free. See
docs/lifecycle_and_emergence.md for the reasoning.
"""

from abc import ABC, abstractmethod

from .density import Vec

# Duplicated from stars.py rather than imported, deliberately: stars.py
# pulls in rng.py -> numpy, and this package's core math (segments,
# envelope, this file) has no numpy dependency, which is what lets it be
# verified with a plain-Python script when numpy isn't installed. It's
# just a type alias -- keeping it in sync is a non-issue.
StarID = tuple[int, int, int]

Manifestation = dict[str, object]


class Event(ABC):
    """Interface only. `name` is expected on every concrete Event but
    isn't enforced here (dataclass fields already provide it at
    runtime); only the two methods below are actually abstract."""

    name: str

    @abstractmethod
    def contains(self, p: Vec, t: float) -> bool:
        """Is this Event still a thing, here, now? For anything that can
        fade, this folds geometry AND salience together -- once salience
        has dropped below the noise floor, this returns False. Mythic
        Events (no decay) return True for as long as they're within
        their static spatial claim, forever."""

    @abstractmethod
    def manifest(self, p: Vec, t: float, sid: StarID | None = None) -> Manifestation | None:
        """What this Event reports at (p, t), or None if there's nothing
        to report. `sid` is only meaningful to star-keyed Events (so far
        only the mythic tier, for per-star rolls / anchor identity);
        everything else ignores it."""
