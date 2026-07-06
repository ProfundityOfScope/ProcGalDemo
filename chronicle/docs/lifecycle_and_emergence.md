# Lifecycle segments, the Event abstraction, instant ruins, and overlap bones

This documents a rework of how `chronicle` civs live and die, a shared
`Event` contract that unifies everything queryable (civs, ruins, and now
the mythic tier too) under one interface, and groundwork for emergent
behavior (wars, mergers, layered ruins) without having to simulate
anyone's actual history.

## The problem this solves

The old `Lifecycle` was a single fixed trapezoid: linear rise, optional
plateau, linear decline, always monotonic, always the same shape. Every
civ told the same story at a different size. Two things were missing:

1. **Variety in the shape of a civ's life**, not just its scale — some
  civs should boom-and-bust cyclically, some should plateau for ages,
  some should die suddenly rather than recede gradually.
2. **A way to handle "instant" history** — debris, ruins, and other
  features that never had a living population, which the old model had
  no vocabulary for (everything was born, grew, and declined).

The guiding constraint throughout: the galaxy is meant to hold on the
order of 400 billion stars, and any point in spacetime has to be
queryable cheaply — O(1)-ish, no simulating a timeline, no iterating
over neighbors. Every change below was designed to preserve that.

## Package layout

```
chronicle/
  core/            foundational primitives -- no dependency on anything
                   else in the package
    config.py        all tunable knobs
    density.py        analytic stellar density field
    rng.py             deterministic RNG plumbing (needs numpy)
    stars.py            lazy star generation (needs numpy, via rng.py)
    era.py               the long-time civilization-rate curve
    event.py              the shared `Event` contract (see below)
  lifecycle/       the growth/life/death envelope specifically
    segments.py       growth/life/death curve catalog (pure math)
    envelope.py        Lifecycle, Civ, Ruin (implement Event)
    profiles.py         per-tier recipe weighting
  tiers/           placement strategies, each producing Events
    tier0.py          hand-authored mythics (Custodian, Lattice)
    tier1.py           procedural Great Powers / minor civs / leagues
  query.py         the point-in-spacetime query layer
  ruins.py         hand-authored instant ruins (AUTHORED_RUINS)
  overlap.py       overlap detection bones
  plot.py, observer.py, animate.py    rendering
```

This grew out of a structural question: `Event` used to live nested
inside `lifecycle/`, even though `tier0.py` depends on `Event` but not
on `Lifecycle`/the growth-life-death envelope at all -- the file layout
and the actual dependency direction were pointing opposite ways.
`core/` now holds everything genuinely foundational (nothing in it
depends on `lifecycle/` or `tiers/`); `lifecycle/` is scoped tightly to
the envelope; `tiers/` holds the placement strategies that produce
Events using whichever of `core`/`lifecycle` they actually need (Tier 0
needs only `Event` from `core`; Tier 1 needs `Lifecycle` from
`lifecycle` too). One nice side effect of doing this split: it became
visible in the import list, not just in prose, that Tier 0 never
depended on the envelope machinery at all.

`core/__init__.py` deliberately only re-exports the numpy-FREE half of
`core` (`Event`, `Manifestation`, `StarID`, `Vec`, `era_curve`) --
`sub_rng`/`nearest_star`/`stars_in_tile`/etc. need numpy (via `rng.py`),
so they're reached via `core.rng`/`core.stars` directly rather than
through the package root. That's what keeps `from .core import Event`
(and everything built only on `Event`/`Lifecycle`, i.e. most of
`lifecycle/`) importable without numpy, which is what makes the
standalone-script verification approach described below possible at
all.

## The core idea: segments

A civ's `radius(t)` is now three named phases stitched end to end:

```
growth (0 -> peak)  ->  life (peak -> r2)  ->  death (r2 -> 0)
```

Each phase picks a **named shape** from a small, reusable catalog
(`lifecycle/segments.py`) instead of hardcoding one curve:

- **Growth**: `steady_climb` (linear, the old default), `explosive`
  (fast early rise, leveling off), `slow_buildup` (slow start,
  accelerating late).
- **Life**: `steady` (flat plateau, the old implicit behavior),
  `expanding`/`contracting` (linear drift to a new target size),
  `oscillating` (a damped-looking wave of a few whole cycles around the
  peak — genuine boom-bust-boom without needing multiple discrete
  civs).
- **Death**: `inward_collapse` (linear recession, the old default),
  `outward_collapse` (fast initial recession, a small core lingers much
  longer), `sublimation` (nothing recedes until near the very end, then
  everything goes at once), `fracture` (recognized but not yet
  consequential — see [Known gaps](#known-gaps-left-as-extension-points)).

With every kind left at its default, the new model is numerically
**identical** to the old trapezoid — this was verified directly (see
[Verification](#verification)), not just asserted.

Picking *which* kind a civ gets is `lifecycle/profiles.py`'s job (see
[Per-tier variety](#per-tier-variety-and-the-minecraft-analogy)); the
segment catalog itself has no opinion about rarity or weighting.

### Why this stays cheap

Every shape is a closed-form function of a normalized local time `u ∈
[0, 1]`. Evaluating `radius(t)` is "which of 3 segments does t fall in,
then evaluate one small formula" — one more branch than the old
2-segment trapezoid, same O(1) complexity class. The recipe (which
kinds, what parameters) is rolled **once**, at construction, from the
same deterministic `sub_rng` stream every other lazy spawn in this
package already uses — nothing here adds a new source of randomness or
a new per-query cost.

### Ruin math had to generalize, and paid for itself

The old `abandoned_at(d)` inverted one linear decline formula. With
segments, `life` phases aren't always inert — a `contracting` life phase
permanently gives up ground *before* death even starts, and needs its
own (still closed-form) inversion. `abandoned_at` now checks, in order:
"was this abandoned during a contracting life phase" (only life kind
that permanently recedes), then falls through to inverting whichever
death shape the civ has. All three built-in death shapes
(`inward_collapse`, `outward_collapse`, `sublimation`) have exact
closed-form inverses — no numeric root-finding anywhere.

One nice side effect: `visible_ruin_radius` (the eroding ring drawn in
`plot.py`) simplified from a bespoke formula to a one-liner —
"wherever the living boundary *was*, `age_max` years ago" is just
`radius()` evaluated at an earlier time, for free, regardless of which
death shape is in play.

## Per-tier variety, and the Minecraft analogy

`Lifecycle`'s runtime cost doesn't depend on which recipe a civ rolled —
evaluating an elaborate `oscillating`/`fracture` civ costs the same as a
plain `steady_climb`/`inward_collapse` one. So "how much variety should
this tier get" isn't a performance question, it's a **narrative economy**
one, and it's handled by weighting, not by different machinery per tier
— exactly one `roll_recipe(rng, profile)` function, three different
`LifecycleProfile` weight tables (`lifecycle/profiles.py`):

- **`GREAT_POWER_PROFILE`** — the "stronghold" tier: rare enough that the
  full, most-varied catalog is affordable. Every death kind is equally
  likely, including `fracture`.
- **`CLUSTER_LEAGUE_PROFILE`** — the "village" tier: moderate frequency,
  biome-gated. Weighted toward `fracture` as its death kind specifically
  because *a league dissolving back into its member systems is what a
  league's death means* — this isn't an arbitrary weighting choice, it's
  a thematic fit.
- **`MINOR_CIV_PROFILE`** — the highest-volume tier, weighted heavily
  toward the plain `steady_climb`/`steady`/`inward_collapse` combo, so
  that the rare minor civ that rolls something exotic reads as a find
  rather than background noise.

This mirrors how Minecraft keeps common structures (mineshafts) simple
and rare ones (strongholds, ancient cities) elaborate — not because the
common ones *couldn't* be made complex, but because that contrast is
what makes rare things feel rare. Tier 0 (the hand-authored Custodian
and Lattice) intentionally sits outside this system entirely — they have
no lifecycle at all, which the Minecraft framing also validates: they're
the "ancient city," one-off and hand-placed, not proc-gen'd.

## The Event abstraction

Everything queryable — a civilization, a ruin, a relic network, and
eventually a gamma-ray burst or superweapon aftermath — shares one
contract, `Event` (`core/event.py`):

```python
class Event(ABC):
    def contains(self, p: Vec, t: float) -> bool: ...
    def manifest(self, p: Vec, t: float, sid: StarID | None = None) -> Manifestation | None: ...
```

`Event` is deliberately an interface only, with no shared data fields —
a disk-shaped, single-home thing (`Civ`, `Ruin`, `Custodian`) and a
multi-anchor graph (`Lattice`) don't share a natural data shape, only
the two questions above. This is what lets the query layer (and any
future overlap-rules layer, per the project owner's stated goal of
coding up specific rules for specific overlaps) treat every kind of
Event identically, with no type-specific dispatch — `query_point` is now
one loop over a flat list of candidates, not three separate code paths
for civs, ruins, and mythics (see [Verification](#verification) for how
much this simplified `query.py`).

**Ordinary Events genuinely expire.** This was a real correction, not
just a refactor: the previous model had `Civ.contains()` claim a
location *forever*, with only salience decaying separately underneath
it — a ruin was, by that model, always still "there," just eventually
undetectable. The project owner pushed back on this directly: ruins (and
everything else) should be "another temporal sort of thing," not
permanent-but-hidden. So `Event.contains()` now folds geometry and
salience into one check — once salience drops below the noise floor,
`contains()` returns `False`, full stop, and the Event is gone for query
purposes. The underlying `historical_peak`/`peak_radius_by` bookkeeping
still never shrinks (it's still needed to compute *where* the fade
happens, and to normalize "influence" by distance), but that's now an
internal implementation detail, not something `contains()` exposes as
permanence.

**Mythic permanence is the deliberate, rare exception, not the default.**
Tier 0's `Custodian` and `Lattice` are rebuilt as genuine `Event`
subclasses (they were previously bespoke classes with their own
`manifest(sid, p, t)` convention, now unified to `manifest(p, t, sid)`
matching everything else) — but they carry **no `Lifecycle` at all**.
No decay machinery was ever attached to begin with, rather than a
`Lifecycle` with enormous numbers standing in for "eternal" (which was
considered and rejected: representing "forever" via a very large
`lifespan`/`decay_tau` risks `inf`/`NaN` edge cases in the segment math,
and it obscures *why* these two are special). Their permanence is
architectural — they're the only Events with no fade mechanism — which
is exactly the "elevated version of an ordinary Event, but exceptionally
rare and from deep time" framing the project owner asked for: rarity is
what justifies never fading, not the other way around.

## Instant ruins, and `Ruin` as its own kind of thing

A first-class way to place something that **never had a living phase at
all** — war debris, a failed colonization attempt, anything that should
read as pure history. Rather than a special class of `Lifecycle`, it's a
degenerate *recipe*: `Lifecycle.instant_ruin(spawn_time, radius,
decay_tau, ...)` compresses growth into a near-instant
`materialize_dur` (default 100 years — invisible at civ timescales) with
zero life phase, so the object appears at full size almost immediately
and starts decaying right away — and, like any ordinary Event, its
`contains()` genuinely expires once salience fades (see [The Event
abstraction](#the-event-abstraction) above — this used to claim
permanence and no longer does).

That degenerate `Lifecycle` needed a home, though — and it doesn't
belong wrapped in a `Civ`. `Civ.kind` names a Tier 1 *placement
strategy* (`stronghold-style`/`mineshaft-style`/`dripstone-style`), which
a ruin was never spawned by, and `Civ.genome` implies traits a going
concern would have, which a ruin never was. So `Ruin`
(`lifecycle/envelope.py`) is its own small `Event` — `name`, `home`, a
`Lifecycle`, and a free-text `cause` — mirroring how Tier 0's
`Custodian`/`Lattice` are also their own classes rather than `Civ`s
despite being "things in spacetime" too. It implements `contains`/
`manifest` like every other Event, plus `ruin_age`/`ruin_salience` for
direct inspection, deliberately with no `is_living_at` — a `Ruin` was
never alive, full stop.

**These are wired in and actually exist now** — `ruins.py` holds
`AUTHORED_RUINS`, a hand-placed list (same pattern as Tier 0's
`AUTHORED`) with two examples: a failed colony and an unexplained debris
field. `query_point` includes them in its one flat Event list (no
special-casing needed), and `plot.py`/`observer.py` draw them through
the same `draw_civ` renderer `Civ`s use — `draw_civ` was loosened to
accept anything with `.home`/`.life` and fall back to a neutral ash-gray
(`DEFAULT_KIND_COLOR`) when there's no `.kind` to look up, rather than
requiring a `Civ` specifically.

Nothing currently *produces* new ruins automatically (see [Known
gaps](#known-gaps-left-as-extension-points)) — the two in
`AUTHORED_RUINS` are hand-placed, the same way Tier 0's Custodian and
Lattice are. Wiring `Ruin` production into an actual event (e.g. a war
between two overlapping civs) is future work; the class and its query/plot
integration are not.

## Overlap detection (bones only)

`overlap.py` answers exactly one question: *at time t, which civs'
living bubbles intersect?* `find_overlaps(civs, t)` does a pairwise
circle-intersection check over a candidate list and returns `Overlap`
records (which two civs, how much they interpenetrate). It does **not**
decide what an overlap means — no war rolls, no mergers, no consequence
of any kind. That resolution layer is deliberately not built.

This stays cheap for the same reason everything else does: `radius(t)`
is closed-form, so intersection is one distance comparison per pair, and
it's only ever meant to run over an already-local, already-bounded
candidate list (e.g. the output of `minor_civs_near`) — never "every civ
in the galaxy."

## Known gaps, left as extension points

These were deliberately scoped out, not overlooked — each is marked with
an `EXTENSION POINT` comment at its point of relevance in the code:

- **`fracture` has no consequence yet.** It's a real, selectable death
  kind (civs roll it, `status()` reports "fracturing"), but it currently
  reuses `sublimation`'s decay curve as a placeholder rather than
  spawning child civs at decline-start. Building that means giving
  `fracture` a hook that produces new `Civ` instances (seeded off
  `(parent_key, child_index)`, same pattern every lazy spawn in this
  package already uses) — a natural next step once `overlap.py`'s
  resolution layer exists, since fracture is really just "a civ making
  war on itself."
- **Overlap resolution isn't built.** The design sketch discussed
  alongside this change: hash `(a.name, b.name)` (sorted, so
  order-independent) into a deterministic roll for nothing / skirmish /
  war / merger, the same way every other lazy spawn in this codebase
  derives determinism from a key tuple. War outcomes would plausibly
  spawn a `Ruin` (via `Lifecycle.instant_ruin`) at the overlap's
  geometric centroid, appended to a registry the same way `AUTHORED_RUINS`
  is today, just lazily generated instead of hand-placed. A merger
  would plausibly introduce a third synthetic `Civ` that takes over
  reporting for `t ≥ t_merge`, without deleting or rewriting the two
  originals (so pre-merger history stays queryable — this is also the
  natural mechanism for "layered ruins from unrelated successive
  civilizations," which doesn't need any lifecycle changes at all, only
  query-side aggregation of multiple overlapping civs' salience).
- **Cross-tier encounters need an asymmetric outcome.** A Great Power's
  bubble overlapping a minor civ's isn't a peer merger — more like
  conquest or vassalage. The current `find_overlaps` doesn't distinguish
  same-tier from cross-tier pairs; a future resolution layer should.
- **Oscillating life-phase troughs aren't tracked as ruins.** If a point
  briefly falls outside an `oscillating` civ's radius mid-wave,
  `ruin_age` returns `None` (neither "living" nor "confirmed ruin")
  rather than guessing at a transient abandonment. This was a deliberate
  simplification: precisely tracking multiple abandon/re-occupy cycles
  within one civ's own oscillation was judged not worth the complexity
  for now, versus doing it via unrelated civs resettling the same area
  (already possible today, needs no code changes) or extending
  `abandoned_at` later if it turns out to matter.
- **The `historical_peak` for `oscillating` life is an approximation.**
  It assumes the wave's first crest is reached (true for any realistic
  `life_cycles`, since the first peak lands early in the phase), rather
  than exactly tracking when the crest occurs. Noted in code where it
  matters.
- **`Event` has no shared data fields, only the method contract.** This
  was a deliberate call, not an oversight — `Lattice` genuinely has no
  single `home` (it's a multi-anchor graph), so forcing one onto the
  base class would've been a fiction. If a future overlap-rules layer
  wants a uniform "representative position" for every Event (e.g. for
  distance-sorting candidates before running rules), that's a
  `home`-like helper worth adding *as an optional method with a default*,
  not a required field every subclass must fake.

## Adding new archetypes

To add a new growth/life/death shape: add one function (and, for a
death shape, its closed-form inverse) to the relevant catalog dict in
`lifecycle/segments.py`, and add the name to the matching `Literal` type
so type checkers catch typos. Nothing in `envelope.py` or `profiles.py`
needs to change — they look shapes up by name.

To add a new civ archetype or retune an existing tier: add or edit a
`LifecycleProfile` in `lifecycle/profiles.py`. Nothing outside that
module needs to change.

To add a wholly new kind of feature (a new "structure" in the Minecraft
sense) that reuses the growth/life/death envelope — a new civ-like
archetype: the pattern established here is a `LifecycleProfile` (or a
one-off recipe) plus a placement strategy — look at how Tier 1A/B/C
differ in `tier1.py` (guaranteed-per-epoch vs. lazy-per-cell vs.
density-gated) for the range of placement strategies already available
before inventing a new one.

To add a wholly new **kind** of Event that doesn't fit the growth/life/
death envelope at all (a gamma-ray burst: a brief flash with its own
falloff shape, not a civ's slow rise-and-fall; a superweapon's
aftermath: maybe permanent like the mythic tier, maybe not) — implement
`Event` directly (`contains`/`manifest`), the way `Custodian`/`Lattice`
do, rather than trying to force it through `Lifecycle`. That's exactly
what `Event` having no shared data fields buys: a new Event doesn't need
to pretend to have a `home`+`radius(t)` shape it doesn't actually have.

## Verification

`Lifecycle`/`Civ`/`Ruin`/`Event`/`overlap.find_overlaps` have zero
dependency on numpy or matplotlib — only the RNG-driven *rolling* of a
recipe (`profiles.roll_recipe`, used by `tier1.py`) and Tier 0's
per-star rolls (`tier0.py`, via `sub_rng`) need numpy. This meant the
core math could be verified directly with a standalone plain-Python
script (not checked into the package — this environment's `.venv` is
currently broken and lacks numpy/matplotlib entirely) covering:

- The new model reduces exactly to the old trapezoid at default kinds
  (growth duration, death duration, continuity at both phase
  boundaries).
- `peak_radius_by` is monotonic non-decreasing over a civ's whole
  lifetime.
- `abandoned_at` round-trips through `radius()` (i.e. `radius(abandoned_at(d))
  == d`) for every built-in death kind, and for a `contracting` life
  phase's mid-life recession.
- `expanding`/`contracting`/`oscillating` life phases hand off to death
  continuously, and `oscillating` with whole-number cycles returns
  exactly to its starting radius.
- The life-phase-duration-collapses-to-zero edge case (growth eats the
  whole pre-decline budget) doesn't leak a stale expand/contract/
  oscillate multiplier into `r2`/`historical_peak` — this was caught as
  a real bug during this pass, not hypothetical.
- `find_overlaps` detects an actually-overlapping pair and correctly
  ignores a distant one.
- `Civ`/`Ruin` are genuinely `Event` instances (`isinstance` check).
- **`Civ.contains()`/`Ruin.contains()` are `True` shortly after
  death/spawn (still salient) and `False` long after (genuinely gone) —
  this is the corrected behavior from [The Event
  abstraction](#the-event-abstraction); the first version of this test
  suite asserted the OLD "permanent" behavior and had to be updated once
  `contains()` was fixed to fold in salience, which is worth knowing if
  you're diffing test history rather than just trusting a single green
  run.
- `Civ.manifest()`/`Ruin.manifest()` (moved here from what used to be
  free functions in `query.py`) still produce the same shape of output
  as before: living status while alive, `"RUINS"` (or `"RUINS
  (abandoned mid-collapse)"`) plus `ruin_age`/`salience` once dead,
  `None` once faded past cutoff.

All of the above pass. `tier0.py`/`tier1.py`'s wiring (the numpy-dependent
half — Custodian/Lattice's per-star rolls, and per-tier recipe rolling)
was reviewed by hand and via `py_compile`, but not executed end-to-end —
whoever picks this up with a working environment should run the existing
`observer.py`/`animate.py` demos and eyeball a few civs across tiers to
sanity-check the *feel* (does Great Power variety actually read as more
interesting than minor civ variety, does cluster-league fracture look
right, does a ruin actually disappear from a query once it's faded,
etc.) — that's a taste judgment no amount of unit testing substitutes
for.
