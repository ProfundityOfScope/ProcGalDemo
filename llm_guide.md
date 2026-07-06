# Procedural Galaxy Generation: Architecture & Implementation Guide

## Project Codename: *Lightward* (working title)

A comprehensive reference for building a relativistic exploration game featuring fully procedural galaxy generation, temporal evolution, and emergent civilization dynamics.

---

# Part I: Foundational Concepts

## 1.1 Design Philosophy

This project sits at the intersection of three design goals that often conflict:

1. **Generative Purity**: The universe is a deterministic function of seeds. Given the same inputs, you get the same outputs—always, everywhere, on any device.

2. **Relational Richness**: Entities have meaningful relationships that span hierarchy boundaries—civilizations that span systems, supernovae that sterilize neighbors, ancient networks that connect distant ruins.

3. **Temporal Depth**: The universe evolves. Stars die, civilizations rise and fall, and the player moves through time as much as space.

The architecture described in this document—**SeedGraph + Overlays**—resolves these tensions through careful separation of concerns. The base universe is a pure function; cross-cutting relationships live in scoped overlays; time is a query parameter, not simulated state.

### The Core Insight

> **An entity's address is its identity. Its state is a function of that address, its ancestors' context, applicable overlays, and the query time T.**

```
EntityState = f(Address, AncestorContext, OverlayManifest, T)
```

This single equation governs everything.

---

## 1.2 Scale & Constraints

### Target Scale

| Dimension | Value | Notes |
|-----------|-------|-------|
| Total stars | 100–400 billion | Only addressable, never fully instantiated |
| Galaxy diameter | ~100,000 ly | 2D projection acceptable |
| Typical journey | Decades to centuries (coordinate time) | Proper time much shorter at relativistic speeds |
| Maximum journey | ~100,000 years (coordinate time) | Full galaxy crossing |
| Civilization bubble | Tens to hundreds of light-years | Local, not galaxy-spanning |
| Civilization lifespan | Thousands to millions of years | Varies by archetype |
| POI density | Every system has *something*; truly interesting is rarer | Emergent from rules |

### Technical Constraints

| Constraint | Target | Rationale |
|------------|--------|-----------|
| Generation latency | <100ms for system Spec | Player approaches gradually; Spec needed for scanning |
| Full system generation | <500ms | Acceptable as player enters |
| Memory footprint | <100MB active entities | iOS device limits |
| Persistence | Player state + event outcomes only | Galaxy regenerates from seed |
| Platform | iOS (iPhone), modern devices | Swift/SwiftUI, can use latest APIs |

---

## 1.3 Glossary

| Term | Definition |
|------|------------|
| **Address** | Hierarchical identifier for an entity, permanent across all time. Also the seed source. |
| **Spec** | Cheap, stable properties derivable in O(1) from parent context + address. Available for overlay selection. |
| **Derived** | Expensive generated properties requiring full generation. |
| **Overlay** | Cross-cutting data (fields, graphs, directives) layered over the base generation. |
| **Signal Layer** | Continuous function over space (and optionally time) that entities sample. |
| **Lifecycle Function** | Deterministic function mapping (Spec, T) → state for physics-driven evolution. |
| **Event Timeline** | Sparse list of discrete events generated from seed, queryable by time. |
| **Claim Record** | Stable binding between an overlay feature and a selected entity address. |
| **Proper Time** | Time experienced by the player/ship. |
| **Coordinate Time** | Galaxy-wide reference time (T). |
| **Reference Epoch (T₀)** | The time at which addresses are assigned. Fixed per universe seed. |

---

# Part II: Architecture

## 2.1 The Address System

### CosmicAddress

Every entity in the universe has a unique, permanent address encoding its position in the hierarchy. The address is:

- **Hierarchical**: Galaxy → Sector → System → Body → Region → POI
- **Stable**: Assigned at reference epoch T₀, never changes
- **Seed-bearing**: The address deterministically derives the entity's seed

```
Address format:
  Galaxy(seed=X)
  └── Sector(i, j)           // 2D grid, e.g., 1000x1000 sectors
      └── System(k)          // Index within sector
          └── Body(n)        // Star=0, planets=1+, sorted by orbit
              └── Region(r)  // Surface subdivision
                  └── POI(p) // Point of interest index
```

#### Implementation Notes

```swift
struct CosmicAddress: Hashable, Codable {
    let components: [AddressComponent]
    
    enum AddressComponent: Hashable, Codable {
        case galaxy(seed: UInt64)
        case sector(i: Int, j: Int)
        case system(index: Int)
        case body(index: Int)
        case region(index: Int)
        case poi(index: Int)
    }
    
    var seed: UInt64 {
        // Cascaded hash of all components
        components.reduce(0) { hash($0, $1) }
    }
    
    var parent: CosmicAddress? {
        guard components.count > 1 else { return nil }
        return CosmicAddress(components: Array(components.dropLast()))
    }
    
    func child(_ component: AddressComponent) -> CosmicAddress {
        CosmicAddress(components: components + [component])
    }
}
```

### Seed Mixing

All randomness derives from deterministic seed mixing:

```swift
func mixSeed(_ base: UInt64, _ domain: String, _ index: Int) -> UInt64 {
    // Use a high-quality hash like xxHash or SipHash
    var hasher = XXHasher(seed: base)
    hasher.combine(domain)
    hasher.combine(index)
    return hasher.finalize()
}
```

**Domain separation** prevents correlation between different generation aspects:

```swift
let starTypeSeed = mixSeed(systemSeed, "star_type", 0)
let planetCountSeed = mixSeed(systemSeed, "planet_count", 0)
let civilizationSeed = mixSeed(systemSeed, "civilization", 0)
```

---

## 2.2 The Generation Pipeline

### Spec vs. Derived

Every entity type defines two data tiers:

| Tier | Characteristics | Use |
|------|-----------------|-----|
| **Spec** | O(1) to compute, stable, parent-dependent only | Overlay selection, scanning, cheap queries |
| **Derived** | Expensive, may require child enumeration | Full entity state, rendering, interaction |

#### Spec/Derived by Entity Type

| Entity | Spec (Cheap) | Derived (Expensive) |
|--------|--------------|---------------------|
| **Sector** | Star density band, dominant stellar population, overlay flags | Actual star list, sector-level POIs |
| **System** | Star class(es), metallicity, planet count, binary flag, has_civ flag | Full orbital layout, specific planets |
| **Star** | Mass, spectral type, age, lifecycle phase | Luminosity curve, exact radius, activity |
| **Planet** | Orbit slot, mass class, atmosphere type, hydrosphere flag, moon count, habitable flag | Surface biomes, tectonics, specific moons |
| **Moon** | Mass class, atmosphere flag, tidal lock flag | Surface features, geology |
| **Region** | Biome type, elevation band, has_water flag | POI list, terrain details |
| **POI** | Category, size class, age, civilization_tag | Full description, events, interaction options |
| **Civilization** | Archetype, tech level, expansion phase | Territory details, history, relationships |

### The GenerationContext

Context flows strictly downward through the hierarchy. A child generator receives:

```swift
struct GenerationContext {
    let address: CosmicAddress
    let seed: UInt64
    let parentSpec: (any EntitySpec)?
    let overlayManifest: OverlayManifest
    let queryTime: Double  // T
    
    // Convenience accessors for common parent properties
    var stellarMetallicity: Double? { ... }
    var stellarLuminosity: Double? { ... }
    var habitableZoneBounds: ClosedRange<Double>? { ... }
    var civilizationInfluence: CivilizationTag? { ... }
}
```

**Critical rule**: Children never query siblings. A planet doesn't ask "what are the other planets in this system?" It receives all necessary information through context.

### Generator Registry

Generators are stateless functions registered by entity type:

```swift
protocol EntityGenerator {
    associatedtype SpecType: EntitySpec
    associatedtype DerivedType: EntityDerived
    
    static func generateSpec(context: GenerationContext) -> SpecType
    static func generateDerived(context: GenerationContext, spec: SpecType) -> DerivedType
}

class GeneratorRegistry {
    static func spec<T: EntityGenerator>(for address: CosmicAddress, context: GenerationContext) -> T.SpecType
    static func derived<T: EntityGenerator>(for address: CosmicAddress, context: GenerationContext) -> T.DerivedType
}
```

### Generation Flow

```
User approaches System S at time T
         │
         ▼
    ┌────────────────┐
    │ Address: S     │
    │ Query time: T  │
    └───────┬────────┘
            │
            ▼
    ┌─────────────────────────┐
    │ Ensure parent chain     │
    │ (Sector Spec exists)    │
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │ Build GenerationContext │
    │ - Parent Spec           │
    │ - Overlay manifest      │
    │ - Query time T          │
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │ SystemGenerator.spec()  │ ← O(1), fast
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │ Apply lifecycle(T)      │ ← Star phase, etc.
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │ Cache Spec              │
    └───────────┬─────────────┘
                │
     (Later, if player enters)
                │
                ▼
    ┌─────────────────────────┐
    │ SystemGenerator.derived │ ← Enumerate planets, etc.
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │ For each planet:        │
    │   PlanetGenerator.spec()│
    └─────────────────────────┘
```

---

## 2.3 The Overlay System

Overlays handle cross-cutting concerns that pure hierarchical generation cannot express: faction territories, archaeological networks, trade routes, supernova sterilization zones.

### OverlayManifest

Each scope (sector, arm, galaxy) can produce an overlay manifest containing three types of content:

```swift
struct OverlayManifest {
    let signalLayers: [SignalLayerID: SignalLayer]
    let sparseGraphs: [GraphID: SparseGraph]
    let directives: [Directive]
    let claims: [ClaimRecord]
}
```

#### 1. Signal Layers (Fields)

Continuous functions over space (and optionally time) that entities sample:

```swift
protocol SignalLayer {
    func sample(position: Position2D, time: Double) -> Double
}

// Examples:
struct CivilizationInfluenceLayer: SignalLayer {
    // Returns 0.0–1.0 influence strength at position
}

struct NebulaeDensityLayer: SignalLayer {
    // Returns gas density for visual/generation effects
}

struct MetallicityGradientLayer: SignalLayer {
    // Galactic metallicity gradient (higher toward center)
}
```

Signal layers solve "membership is the generated property" problems. A system doesn't need to know which civilization it belongs to; it samples `CivilizationInfluenceLayer(position, T)` and gets an answer.

#### 2. Sparse Graphs

For discrete N-ary relationships that can't be expressed as fields:

```swift
struct SparseGraph {
    let nodes: [CosmicAddress: NodeData]
    let edges: [(from: CosmicAddress, to: CosmicAddress, label: EdgeLabel)]
    
    struct NodeData {
        let role: String
        let validFrom: Double
        let validUntil: Double?
    }
    
    enum EdgeLabel {
        case partOf
        case references
        case tradeRoute
        case causalLink
    }
}
```

Use cases:
- Archaeological networks (ruin A references ruin B)
- Trade routes between systems
- Civilization causality graphs (civ X spawned from colony of civ Y)

#### 3. Directives

Surgical overrides into reserved generator slots:

```swift
enum Directive {
    case reserveMoonArchetype(system: CosmicAddress, archetype: MoonArchetype)
    case reservePOISlot(planet: CosmicAddress, poiType: POIType)
    case forceHabitable(planet: CosmicAddress)
}
```

Directives are rare and capped (2–3 reserved slots per generator, one claim per overlay feature per scope).

#### 4. Claim Records

Stable bindings between overlay features and selected entities:

```swift
struct ClaimRecord: Codable {
    let featureID: String  // e.g., "precursor_network_node_7"
    let targetAddress: CosmicAddress
    let claimedAt: Date  // Real-world time, for debugging
}
```

Claims are write-once. Once an overlay feature selects an entity, that binding is permanent for the save file.

### Overlay Selection Algorithm

When an overlay needs to place something (e.g., "the Prime Relic on a barren airless moon"):

```swift
func selectEntity(
    predicate: (EntitySpec) -> Bool,
    scope: CosmicAddress,
    featureID: String
) -> CosmicAddress {
    
    // Check for existing claim
    if let claim = claims[featureID] {
        return claim.targetAddress
    }
    
    // Enumerate candidates (cheap: Spec only)
    let candidates = enumerateCandidates(in: scope)
        .filter { predicate(generateSpec(for: $0)) }
    
    if let best = candidates.min(by: { scoreHash($0, featureID) }) {
        // Record claim
        claims[featureID] = ClaimRecord(featureID: featureID, targetAddress: best)
        return best
    }
    
    // Fallback: escalate scope or use directive
    return escalateOrInject(predicate, scope.parent, featureID)
}
```

### Overlay Scope Visibility Rule

**Entities may only read overlay manifests for scopes on their ancestor chain.**

A planet can read:
- Galaxy overlay
- Arm overlay (if applicable)
- Sector overlay
- System overlay

A planet **cannot** query:
- Other sectors' overlays
- Sibling systems' overlays
- Other planets' state (except through parent context)

This firewall prevents accidental global coupling.

---

## 2.4 Temporal System

Time is a first-class query parameter. Generation becomes `f(address, context, T) → EntityState`.

### Reference Epoch

All addresses are assigned at reference epoch **T₀ = 0** (the "present" when the player starts). Entities that existed before T₀ have negative birth times; entities born after have positive birth times.

The player's coordinate time advances as they travel. When they query an entity at time T, they get that entity's state at T.

### Lifecycle Functions

For physics-driven evolution, define pure functions:

```swift
protocol LifecycleFunction {
    associatedtype SpecType: EntitySpec
    associatedtype StateType
    
    static func evaluate(spec: SpecType, time: Double) -> StateType
}

// Example: Stellar lifecycle
struct StellarLifecycle: LifecycleFunction {
    struct State {
        let phase: StellarPhase
        let luminosity: Double
        let radius: Double
        let temperature: Double
        let exists: Bool  // False if exploded/collapsed
    }
    
    static func evaluate(spec: StarSpec, time: Double) -> State {
        let age = time - spec.birthTime
        let mainSequenceLifespan = calculateMSLifespan(mass: spec.mass)
        
        if age < 0 {
            return .protostar(age: age, mass: spec.mass)
        } else if age < mainSequenceLifespan {
            return .mainSequence(age: age, mass: spec.mass)
        } else if age < mainSequenceLifespan * 1.1 {
            return .giantPhase(age: age, mass: spec.mass)
        } else {
            return .remnant(mass: spec.mass)  // WD, NS, or BH
        }
    }
}
```

Lifecycle functions are **O(1)**—no simulation, just math from initial conditions.

#### Lifecycle Functions to Implement

| Entity | Lifecycle Aspects |
|--------|-------------------|
| **Star** | Phase (protostar → MS → giant → remnant), luminosity, radius |
| **Planet atmosphere** | Composition evolution, pressure changes, stripping if star brightens |
| **Planet surface** | Geological activity decay, crater accumulation |
| **Moon orbit** | Tidal decay (rare, very long timescales) |
| **Civilization** | Rise/fall phase (from event timeline, not continuous function) |

### Event Timelines

For discrete, stochastic events, generate a sparse timeline:

```swift
struct EventTimeline {
    let events: [(time: Double, event: Event)]
    
    func state(at time: Double) -> [Event] {
        events.filter { $0.time <= time }.map(\.event)
    }
    
    func nextEvent(after time: Double) -> (time: Double, event: Event)? {
        events.first { $0.time > time }
    }
}

enum Event {
    case civilizationFounded(homeworld: CosmicAddress)
    case civilizationCollapse(cause: CollapseCause)
    case civilizationExpansion(newTerritory: [CosmicAddress])
    case impactEvent(impactorSize: Double)
    case technologicalSingularity
    case schism(newFaction: FactionID)
}
```

Timeline generation:

```swift
func generateCivilizationTimeline(seed: UInt64, archetype: CivArchetype) -> EventTimeline {
    var rng = SeededRNG(seed: seed)
    var events: [(Double, Event)] = []
    var time: Double = rng.next(in: -1_000_000 ... 0)  // Founded sometime in the past
    
    events.append((time, .civilizationFounded(...)))
    
    while true {
        let nextEventDelay = archetype.eventInterval.sample(&rng)
        time += nextEventDelay
        
        let eventType = archetype.eventDistribution.sample(&rng)
        events.append((time, eventType))
        
        if eventType == .collapse || time > 10_000_000 {
            break
        }
    }
    
    return EventTimeline(events: events)
}
```

### Time-Indexed Signal Layers

Faction territory evolves over time:

```swift
struct CivilizationTerritoryLayer: SignalLayer {
    let timeline: EventTimeline
    let homeworld: Position2D
    let expansionRate: Double
    
    func sample(position: Position2D, time: Double) -> Double {
        let events = timeline.state(at: time)
        
        // Find current territorial extent based on expansion events
        let currentRadius = computeRadius(from: events, at: time)
        let distance = position.distance(to: homeworld)
        
        // Smooth falloff at edges
        return max(0, 1 - (distance / currentRadius))
    }
}
```

### Supernova Sterilization

When generating a planet's habitability at time T:

```swift
func checkSterilization(systemPosition: Position2D, planetBirthTime: Double, queryTime: Double) -> SterilizationEvent? {
    let nearbyStars = enumerateStarsWithin(radius: 50.ly, of: systemPosition)
    
    for star in nearbyStars {
        let starSpec = generateSpec(for: star.address)
        let lifecycle = StellarLifecycle.evaluate(spec: starSpec, time: queryTime)
        
        // Did this star go supernova between planet formation and now?
        if let supernovaTime = lifecycle.supernovaTime,
           supernovaTime > planetBirthTime,
           supernovaTime < queryTime {
            let distance = star.position.distance(to: systemPosition)
            let intensity = supernovaIntensity(at: distance)
            
            if intensity > sterilizationThreshold {
                return SterilizationEvent(source: star.address, time: supernovaTime, intensity: intensity)
            }
        }
    }
    
    return nil
}
```

This is O(nearby stars), which is manageable given stellar density.

---

## 2.5 The Light Cone System

This is the novel mechanic that makes relativistic travel meaningful: **information propagates at the speed of light**.

### Player State

```swift
struct PlayerState {
    var position: Position2D
    var coordinateTime: Double  // T, galaxy-wide reference
    var properTime: Double      // τ, player's experienced time
    var velocity: Vector2D      // For relativistic calculations
    
    // What the player "knows" about the universe
    var lightConeCache: [CosmicAddress: ObservationRecord]
}

struct ObservationRecord {
    let address: CosmicAddress
    let observedState: EntityState
    let observationTime: Double  // When the light left the source
    let receivedTime: Double     // When the player received it (player's T)
}
```

### What the Player Can See

At any moment, the player can observe the past light cone—events whose light has had time to reach them:

```swift
func observableState(of address: CosmicAddress, from player: PlayerState) -> EntityState? {
    let targetPosition = positionOf(address)
    let distance = player.position.distance(to: targetPosition)
    let lightTravelTime = distance / c  // In years if distance is in light-years
    
    let observableTime = player.coordinateTime - lightTravelTime
    
    if observableTime < 0 {
        // Light hasn't reached player yet (target too far, universe too young)
        return nil
    }
    
    // Generate entity state at the time light left
    return generateState(for: address, at: observableTime)
}
```

### Implications for Gameplay

1. **Scanning distant systems shows their past.** A system 1000 ly away appears as it was 1000 years ago.

2. **Returning to a system reveals what happened.** You left at T=5000, traveled for 500 years proper (5000 coordinate), arrive at T=10000. Everything that happened between T=5000 and T=10000 is now visible.

3. **Waiting reveals news.** If you wait at a location, light from increasingly distant (and thus older) events reaches you. After 1000 years, you can see what was happening 1000 ly away, 1000 years ago.

4. **Information asymmetry creates mystery.** You see a civilization's territory 500 years ago. Are they still there? You won't know until you get closer or wait for newer light.

### Observation Cache

To avoid regenerating distant systems repeatedly:

```swift
class LightConeCache {
    private var observations: [CosmicAddress: ObservationRecord] = [:]
    
    func observe(address: CosmicAddress, player: PlayerState) -> ObservationRecord? {
        let observableTime = calculateObservableTime(address, player)
        
        // If we have a cached observation from this time or later, use it
        if let cached = observations[address], cached.observationTime >= observableTime {
            return cached
        }
        
        // Generate new observation
        guard let state = generateState(for: address, at: observableTime) else {
            return nil
        }
        
        let record = ObservationRecord(
            address: address,
            observedState: state,
            observationTime: observableTime,
            receivedTime: player.coordinateTime
        )
        
        observations[address] = record
        return record
    }
}
```

---

## 2.6 Player Interactions & Persistence

The universe is mostly read-only, but player actions can have persistent effects.

### Event Interaction System

```swift
struct InteractableEvent {
    let id: String
    let address: CosmicAddress
    let windowStart: Double  // T when event becomes interactable
    let windowEnd: Double    // T when window closes
    let options: [InteractionOption]
}

struct InteractionOption {
    let id: String
    let description: String
    let outcome: InteractionOutcome
}

enum InteractionOutcome {
    case modifyTimeline(entityAddress: CosmicAddress, modification: TimelineModification)
    case spawnEntity(address: CosmicAddress, spec: EntitySpec)
    case grantResource(resource: Resource)
    case nothing
}
```

### Persistent Modifications

Player choices are stored as sparse overrides:

```swift
struct PlayerModifications: Codable {
    var timelineOverrides: [CosmicAddress: [TimelineModification]]
    var spawnedEntities: [CosmicAddress: EntitySpec]
    var discoveryLog: [DiscoveryRecord]
}

struct TimelineModification: Codable {
    let appliedAt: Double  // Coordinate time when player acted
    let originalEvent: Event?
    let replacementEvent: Event?
}
```

When generating an entity's timeline, check for overrides:

```swift
func generateTimeline(for address: CosmicAddress, baseTimeline: EventTimeline) -> EventTimeline {
    guard let mods = playerModifications.timelineOverrides[address] else {
        return baseTimeline
    }
    
    var events = baseTimeline.events
    for mod in mods {
        if let original = mod.originalEvent {
            events.removeAll { $0.event == original }
        }
        if let replacement = mod.replacementEvent {
            events.append((mod.appliedAt, replacement))
        }
    }
    
    return EventTimeline(events: events.sorted(by: \.time))
}
```

### Example: The Research Outpost

```swift
// At T=5000, player finds a struggling research outpost
let outpostEvent = InteractableEvent(
    id: "outpost_crisis_\(address.seed)",
    address: address,
    windowStart: 4900,
    windowEnd: 5200,
    options: [
        InteractionOption(
            id: "rescue",
            description: "Provide supplies and technical assistance",
            outcome: .modifyTimeline(
                entityAddress: address,
                modification: TimelineModification(
                    appliedAt: 5000,
                    originalEvent: .collapse(cause: .resourceDepletion),
                    replacementEvent: .expansion(newTerritory: [...])
                )
            )
        ),
        InteractionOption(
            id: "ignore",
            description: "Continue on your journey",
            outcome: .nothing
        )
    ]
)

// If player rescues: 1000 years later, it's a thriving city
// If player ignores: 1000 years later, it's ruins
```

---

# Part III: Entity Specifications

## 3.1 Sector

The galaxy is divided into a 2D grid of sectors. Sectors are the coarsest granularity and the scope for many overlay features.

### Sector Spec

```swift
struct SectorSpec: EntitySpec {
    let address: CosmicAddress
    let position: Position2D  // Center of sector in galactic coordinates
    
    // Derived from galactic position
    let stellarDensity: StellarDensityBand  // core, disk, halo, arm
    let dominantPopulation: StellarPopulation  // Population I, II, III
    let metallicityBand: MetallicityBand
    
    // From overlays
    let civilizationPresence: Bool  // Is there any civ activity in this sector?
    let majorFeatures: [SectorFeature]  // Nebula, star cluster, void, etc.
}

enum StellarDensityBand {
    case core       // ~10,000 stars per cubic ly
    case innerDisk  // ~1 star per cubic ly
    case outerDisk  // ~0.1 stars per cubic ly
    case arm        // ~2x local disk density
    case halo       // ~0.001 stars per cubic ly
}
```

### Sector Derived

```swift
struct SectorDerived: EntityDerived {
    let starCount: Int
    let systemAddresses: [CosmicAddress]  // Enumerable but not yet generated
    let nebulaRegions: [NebulaRegion]
    let civilizationOverlay: CivilizationSectorManifest?
}
```

### Sector Generation

```swift
struct SectorGenerator: EntityGenerator {
    static func generateSpec(context: GenerationContext) -> SectorSpec {
        let galaxyCenter = Position2D(x: 0, y: 0)
        let distanceFromCenter = context.position.distance(to: galaxyCenter)
        
        let densityBand = StellarDensityBand.from(galacticRadius: distanceFromCenter)
        let metallicity = MetallicityBand.from(galacticRadius: distanceFromCenter)
        
        // Check spiral arm overlay
        let inArm = context.overlayManifest.signalLayers["spiral_arms"]?
            .sample(position: context.position, time: context.queryTime) ?? 0 > 0.5
        
        return SectorSpec(
            address: context.address,
            position: context.position,
            stellarDensity: inArm ? densityBand.boosted : densityBand,
            ...
        )
    }
}
```

---

## 3.2 System

A star system containing one or more stars and their orbiting bodies.

### System Spec

```swift
struct SystemSpec: EntitySpec {
    let address: CosmicAddress
    let position: Position2D  // Within sector
    
    // Star properties
    let starCount: Int  // 1 for single, 2 for binary, rarely 3+
    let primaryStarClass: SpectralClass
    let primaryMass: Double  // Solar masses
    let primaryBirthTime: Double  // T when star formed
    
    // System properties
    let metallicity: Double  // Affects planet composition
    let planetCount: Int
    let hasBelt: Bool
    let habitableZoneInner: Double  // AU
    let habitableZoneOuter: Double  // AU
    
    // From overlays
    let civilizationTag: CivilizationTag?
    let isArchaeologicalSite: Bool
}

enum SpectralClass: CaseIterable {
    case O, B, A, F, G, K, M
    // Plus special: WD (white dwarf), NS (neutron star), BH (black hole)
    case WD, NS, BH
    
    var mainSequenceLifespan: Double { ... }  // In years
    var luminosity: Double { ... }
    var color: Color { ... }
}
```

### System Derived

```swift
struct SystemDerived: EntityDerived {
    let stars: [StarState]  // Full stellar data including lifecycle state
    let planets: [PlanetSpec]  // Specs only; Derived on demand
    let asteroidBelts: [BeltSpec]
    let stations: [StationSpec]  // If civilized
    let anomalies: [AnomalySpec]  // Unusual features
}
```

### System Generation

```swift
struct SystemGenerator: EntityGenerator {
    static func generateSpec(context: GenerationContext) -> SystemSpec {
        var rng = SeededRNG(seed: context.seed)
        
        let sectorSpec = context.parentSpec as! SectorSpec
        
        // Star class distribution depends on stellar population
        let starClass = sectorSpec.dominantPopulation.sampleStarClass(&rng)
        let mass = starClass.sampleMass(&rng)
        
        // Birth time: older in halo/bulge, younger in arms
        let birthTime = sectorSpec.stellarDensity.sampleBirthTime(&rng)
        
        // Metallicity affects planet count
        let metallicity = sectorSpec.metallicityBand.sample(&rng)
        let basePlanetCount = Int(rng.next(in: 0...12))
        let adjustedPlanetCount = Int(Double(basePlanetCount) * metallicity.planetMultiplier)
        
        // Check civilization overlay
        let civTag = context.overlayManifest.signalLayers["civilization_influence"]?
            .sampleTag(position: context.position, time: context.queryTime)
        
        return SystemSpec(
            starCount: rng.next() < 0.3 ? 2 : 1,
            primaryStarClass: starClass,
            primaryMass: mass,
            primaryBirthTime: birthTime,
            metallicity: metallicity,
            planetCount: adjustedPlanetCount,
            ...
        )
    }
}
```

---

## 3.3 Star

The star itself, with lifecycle-dependent properties.

### Star Spec

```swift
struct StarSpec: EntitySpec {
    let address: CosmicAddress
    let spectralClass: SpectralClass
    let mass: Double
    let birthTime: Double
    let metallicity: Double
}
```

### Star State (Time-Dependent)

```swift
struct StarState {
    let spec: StarSpec
    let phase: StellarPhase
    let age: Double
    let luminosity: Double
    let radius: Double
    let temperature: Double
    let exists: Bool  // False if collapsed to remnant
    
    static func at(spec: StarSpec, time: Double) -> StarState {
        StellarLifecycle.evaluate(spec: spec, time: time)
    }
}

enum StellarPhase {
    case protostar
    case mainSequence
    case subgiant
    case redGiant
    case horizontalBranch
    case asymptoticGiantBranch
    case planetaryNebula
    case whiteD warm
    case supergiant
    case supernova
    case neutronStar
    case blackHole
}
```

### Stellar Lifecycle Implementation

```swift
struct StellarLifecycle {
    static func evaluate(spec: StarSpec, time: Double) -> StarState {
        let age = time - spec.birthTime
        
        guard age >= 0 else {
            // Pre-birth: protostellar disk
            return StarState(
                spec: spec,
                phase: .protostar,
                age: age,
                luminosity: 0.1,
                ...
            )
        }
        
        let msLifespan = mainSequenceLifespan(mass: spec.mass)
        
        if spec.mass > 8 {
            // Massive star: MS → supergiant → supernova → NS/BH
            return massiveStarEvolution(spec: spec, age: age, msLifespan: msLifespan)
        } else if spec.mass > 0.5 {
            // Sun-like: MS → red giant → planetary nebula → WD
            return solarTypeEvolution(spec: spec, age: age, msLifespan: msLifespan)
        } else {
            // Red dwarf: MS for trillions of years
            return redDwarfEvolution(spec: spec, age: age)
        }
    }
    
    static func mainSequenceLifespan(mass: Double) -> Double {
        // Rough approximation: t_MS ≈ 10^10 * (M/M☉)^(-2.5) years
        return 1e10 * pow(mass, -2.5)
    }
}
```

---

## 3.4 Planet

Planetary bodies with atmospheric and surface properties.

### Planet Spec

```swift
struct PlanetSpec: EntitySpec {
    let address: CosmicAddress
    let orbitSlot: Int
    let orbitalRadius: Double  // AU
    
    // Physical properties
    let massClass: PlanetMassClass
    let mass: Double  // Earth masses
    let radius: Double  // Earth radii
    let density: Double
    let hasAtmosphere: Bool
    let atmosphereType: AtmosphereType?
    let hasHydrosphere: Bool
    let tidallyLocked: Bool
    
    // Derived from star
    let inHabitableZone: Bool
    let surfaceTemperature: Double  // Equilibrium temperature
    
    // Moons
    let moonCount: Int
    
    // From overlays
    let civilizationPresence: CivilizationPresenceType?
    let isArchaeologicalSite: Bool
}

enum PlanetMassClass {
    case mercurian  // < 0.1 Earth mass
    case subterran  // 0.1 - 0.5
    case terran     // 0.5 - 2
    case superterran // 2 - 10
    case neptunian  // 10 - 50
    case jovian     // > 50
}

enum AtmosphereType {
    case none
    case thin(composition: AtmosphericComposition)
    case moderate(composition: AtmosphericComposition)
    case thick(composition: AtmosphericComposition)
    case crushing(composition: AtmosphericComposition)
}

enum CivilizationPresenceType {
    case uninhabited
    case ruins
    case preSpaceflight
    case spacefaring
    case homeworld
}
```

### Planet Derived

```swift
struct PlanetDerived: EntityDerived {
    let regions: [RegionSpec]  // Surface subdivisions
    let moons: [MoonSpec]
    let stations: [StationSpec]
    let rings: RingSystem?
    let atmosphereDetail: AtmosphereDetail
    let tectonicActivity: TectonicActivity
    let biosphere: BiosphereType
}
```

### Planet Lifecycle

Planets evolve based on their star's lifecycle:

```swift
struct PlanetaryLifecycle {
    static func evaluate(spec: PlanetSpec, starState: StarState, time: Double) -> PlanetState {
        var state = PlanetState(spec: spec)
        
        // Atmospheric evolution based on star luminosity history
        if spec.hasAtmosphere {
            let luminosityHistory = integratedLuminosity(star: starState.spec, upTo: time)
            state.atmosphereState = atmosphereEvolution(
                initial: spec.atmosphereType,
                luminosityHistory: luminosityHistory,
                planetMass: spec.mass
            )
        }
        
        // Sterilization check
        if let sterilization = checkSterilization(
            systemPosition: spec.position,
            planetBirthTime: spec.birthTime,
            queryTime: time
        ) {
            state.sterilizationEvent = sterilization
            state.biosphere = .sterilized(at: sterilization.time)
        }
        
        // Geological activity decreases over time
        state.tectonicActivity = geologicalDecay(
            initialActivity: spec.baseActivity,
            age: time - spec.birthTime
        )
        
        return state
    }
}
```

---

## 3.5 Surface Region

Abstract surface subdivisions containing POIs.

### Region Spec

```swift
struct RegionSpec: EntitySpec {
    let address: CosmicAddress
    let regionIndex: Int
    
    let biome: BiomeType
    let elevationBand: ElevationBand
    let hasWater: Bool
    let geologicalFeature: GeologicalFeature?
    
    let poiCount: Int
}

enum BiomeType {
    case barren
    case volcanic
    case icy
    case desert
    case oceanic
    case continental
    case toxic
    case exotic(description: String)
}

enum GeologicalFeature {
    case mountainRange
    case canyon
    case impactCrater(age: Double, diameter: Double)
    case volcano(active: Bool)
    case lavaFields
    case glacier
}
```

### Region Derived

```swift
struct RegionDerived: EntityDerived {
    let pois: [POISpec]
    let visualDescription: String  // Generated flavor text
}
```

---

## 3.6 Point of Interest (POI)

The atomic unit of interaction.

### POI Spec

```swift
struct POISpec: EntitySpec {
    let address: CosmicAddress
    let category: POICategory
    let sizeClass: POISizeClass
    let age: Double  // When it appeared/was built
    
    // Tags for procedural detail
    let tags: Set<POITag>
    
    // From overlays
    let civilizationOrigin: CivilizationTag?
    let networkMembership: [NetworkID]  // Archaeological networks, etc.
}

enum POICategory {
    // Natural
    case geologicalFormation
    case uniqueLifeform
    case anomaly
    
    // Artificial - Active
    case settlement(type: SettlementType)
    case station
    case megastructure
    
    // Artificial - Abandoned
    case ruins(type: RuinType)
    case artifact
    case derelict
}

enum POITag: String, Codable {
    // Physical
    case underground, floating, submerged, orbital
    
    // Condition
    case pristine, damaged, decaying, hazardous
    
    // Content
    case technological, biological, archaeological, resource
    case dataCache, powerSource, manufactury
    
    // Narrative
    case mysterious, ominous, beautiful, horrifying
    case referencesOther  // Points to another POI
}

enum POISizeClass {
    case tiny      // Single object, artifact
    case small     // Building, small site
    case medium    // Complex, small settlement
    case large     // City, major installation
    case massive   // Megastructure, continental feature
}
```

### POI Derived

```swift
struct POIDerived: EntityDerived {
    let description: String
    let scanResults: [ScanResult]
    let interactableEvents: [InteractableEvent]
    let resources: [Resource]
    let connections: [POIConnection]  // References to other POIs
}
```

### POI Generation

```swift
struct POIGenerator: EntityGenerator {
    static func generateSpec(context: GenerationContext) -> POISpec {
        var rng = SeededRNG(seed: context.seed)
        let regionSpec = context.parentSpec as! RegionSpec
        let planetSpec = context.grandparentSpec as! PlanetSpec
        
        // Determine category based on context
        let category: POICategory
        
        if let civPresence = planetSpec.civilizationPresence {
            category = civilizationDrivenCategory(&rng, presence: civPresence)
        } else if let geo = regionSpec.geologicalFeature {
            category = geologyDrivenCategory(&rng, feature: geo)
        } else {
            category = naturalCategory(&rng, biome: regionSpec.biome)
        }
        
        // Generate tags
        var tags: Set<POITag> = []
        tags.insert(conditionTag(&rng))
        if rng.next() < 0.3 { tags.insert(.referencesOther) }
        
        // Check overlay for network membership
        let networks = context.overlayManifest.sparseGraphs
            .compactMap { (id, graph) in
                graph.nodes[context.address] != nil ? id : nil
            }
        
        return POISpec(
            address: context.address,
            category: category,
            sizeClass: categorySizeDistribution(category).sample(&rng),
            age: determineAge(&rng, category: category, planetAge: planetSpec.age),
            tags: tags,
            civilizationOrigin: planetSpec.civilizationTag,
            networkMembership: networks
        )
    }
}
```

---

## 3.7 Civilization

Civilizations are overlay entities with temporal dynamics.

### Civilization Spec

```swift
struct CivilizationSpec: EntitySpec {
    let id: CivilizationID
    let archetype: CivilizationArchetype
    let homeworld: CosmicAddress
    let foundingTime: Double
    let seed: UInt64
    
    // Base characteristics
    let techTrajectory: TechTrajectory
    let expansionTendency: ExpansionTendency
    let lifespan: LifespanClass
}

enum CivilizationArchetype {
    case slowBurn      // Long-lived, slow expansion, stable
    case expansionist  // Rapid growth, often burns out
    case isolationist  // Small territory, long-lived
    case cyclical      // Rise and fall repeatedly
    case transcendent  // Short biological phase, then ???
}

enum TechTrajectory {
    case stagnant
    case steady
    case accelerating
    case collapsed
}

enum LifespanClass {
    case brief(thousands: ClosedRange<Int>)      // 1,000 - 10,000 years
    case moderate(tens_of_thousands: ClosedRange<Int>)  // 10,000 - 100,000
    case enduring(hundreds_of_thousands: ClosedRange<Int>)  // 100,000 - 1,000,000
    case ancient(millions: ClosedRange<Int>)     // 1,000,000+
}
```

### Civilization State

```swift
struct CivilizationState {
    let spec: CivilizationSpec
    let timeline: EventTimeline
    let currentPhase: CivilizationPhase
    let territory: TerritoryState
    let techLevel: TechLevel
}

enum CivilizationPhase {
    case preHistory           // Before founding
    case founding
    case expansion
    case goldenAge
    case stagnation
    case decline
    case collapse
    case postCollapse(ruinsAge: Double)
    case transcendence
}

struct TerritoryState {
    let homeworld: CosmicAddress
    let colonies: [CosmicAddress]
    let influenceRadius: Double  // Light-years
    
    func contains(position: Position2D) -> Bool
    func influence(at position: Position2D) -> Double  // 0-1
}
```

### Civilization Timeline Generation

```swift
func generateCivilizationTimeline(spec: CivilizationSpec) -> EventTimeline {
    var rng = SeededRNG(seed: spec.seed)
    var events: [(Double, CivEvent)] = []
    var time = spec.foundingTime
    
    events.append((time, .founded(homeworld: spec.homeworld)))
    
    let baseLifespan = spec.lifespan.sample(&rng)
    
    switch spec.archetype {
    case .slowBurn:
        // Gradual expansion punctuated by consolidation
        var expansionPhases = Int.random(in: 3...7, using: &rng)
        let phaseLength = baseLifespan / Double(expansionPhases * 2)
        
        for i in 0..<expansionPhases {
            time += phaseLength
            events.append((time, .expansion(newSystems: rng.next(in: 2...10))))
            time += phaseLength
            events.append((time, .consolidation))
        }
        time += phaseLength
        events.append((time, .decline(cause: .entropy)))
        
    case .expansionist:
        // Rapid growth, then collapse
        let peakTime = spec.foundingTime + baseLifespan * 0.3
        events.append((peakTime * 0.5, .expansion(newSystems: 50)))
        events.append((peakTime * 0.7, .expansion(newSystems: 100)))
        events.append((peakTime, .goldenAge))
        events.append((peakTime * 1.2, .overextension))
        events.append((peakTime * 1.5, .collapse(cause: .overextension)))
        
    // ... other archetypes
    }
    
    return EventTimeline(events: events)
}
```

### Civilization Signal Layer

```swift
struct CivilizationInfluenceLayer: SignalLayer {
    let civilizations: [CivilizationSpec]
    
    func sample(position: Position2D, time: Double) -> CivilizationSample {
        var dominantCiv: CivilizationID? = nil
        var maxInfluence: Double = 0
        
        for civ in civilizations {
            let state = CivilizationState.at(spec: civ, time: time)
            let influence = state.territory.influence(at: position)
            
            if influence > maxInfluence {
                maxInfluence = influence
                dominantCiv = civ.id
            }
        }
        
        return CivilizationSample(
            dominantCivilization: dominantCiv,
            influenceStrength: maxInfluence
        )
    }
}
```

---

# Part IV: Implementation Roadmap

## 4.1 Phase 0: Foundation (Week 1-2)

**Goal**: Core infrastructure that everything else builds on.

### Deliverables

1. **CosmicAddress implementation**
   - Address construction, parsing, hashing
   - Seed derivation
   - Parent/child navigation

2. **Seeded RNG**
   - Deterministic RNG seeded from address
   - Domain separation (mixSeed)
   - Distribution sampling (uniform, normal, weighted)

3. **Basic Entity Protocol**
   ```swift
   protocol EntitySpec: Codable, Hashable {}
   protocol EntityDerived {}
   protocol EntityGenerator {
       associatedtype Spec: EntitySpec
       associatedtype Derived: EntityDerived
       static func generateSpec(context: GenerationContext) -> Spec
       static func generateDerived(context: GenerationContext, spec: Spec) -> Derived
   }
   ```

4. **GenerationContext**
   - Parent spec access
   - Seed and address
   - Query time T (placeholder for now)

5. **Simple Cache**
   - LRU cache for Specs
   - Keyed by (Address, T) — even if T is unused initially

### Validation

- Generate 1000 random addresses, verify deterministic output
- Benchmark: Spec generation should be <1ms

---

## 4.2 Phase 1: Static Galaxy (Week 3-4)

**Goal**: Generate a navigable galaxy with stars and basic planets, no time evolution yet.

### Deliverables

1. **Galaxy structure**
   - 2D coordinate system (galactic plane)
   - Sector grid (e.g., 1000×1000 sectors)
   - Position ↔ sector mapping

2. **SectorGenerator**
   - Stellar density based on galactic position
   - Spiral arm overlay (simple signal layer)
   - Star count per sector

3. **SystemGenerator**
   - Star spectral class, mass, metallicity
   - Planet count
   - Position within sector

4. **BasicPlanetGenerator**
   - Mass class, orbit slot
   - Atmosphere (yes/no), hydrosphere (yes/no)
   - Habitable zone calculation

5. **Spatial queries**
   - "Stars within radius R of position P"
   - Efficient sector enumeration

### Validation

- Total star count extrapolates to ~100 billion
- Visual: sector map with star density variation
- Drill-down: click sector → see systems → see planets

---

## 4.3 Phase 2: Temporal Foundation (Week 5-6)

**Goal**: Add time as a query parameter, implement stellar lifecycle.

### Deliverables

1. **StellarLifecycle**
   - Evaluate(StarSpec, T) → StarState
   - Main sequence, giant, remnant phases
   - Supernova timing for massive stars

2. **Time-dependent queries**
   - All generators accept T parameter
   - Star state varies with T

3. **PlayerState basics**
   - Coordinate time T
   - Proper time τ
   - Position

4. **Simple travel model**
   - Given destination and velocity, calculate T_arrival
   - Time dilation (γ factor)

### Validation

- Query same star at T=0 vs T=1 billion years, see evolution
- Travel from A to B, verify time passes correctly
- Find a supernova: query star before/after explosion

---

## 4.4 Phase 3: Light Cone System (Week 7-8)

**Goal**: Implement relativistic information propagation.

### Deliverables

1. **ObservableState function**
   - Given player position and T, what can they see?
   - Light travel time calculation

2. **LightConeCache**
   - Store observations
   - Update as player moves/waits

3. **Scanning UI concept**
   - Scan distant system: see its past
   - Display "observed at T=X (Y years ago)"

4. **Waiting mechanic**
   - Player can wait, advancing T
   - New information arrives from more distant sources

### Validation

- Observe star 1000 ly away, confirm seeing T-1000 state
- Wait 500 years, observe same star, now seeing T-500 state
- Watch supernova "happen" from safe distance as light arrives

---

## 4.5 Phase 4: Overlays - Civilizations (Week 9-11)

**Goal**: Add civilization overlay with temporal dynamics.

### Deliverables

1. **OverlayManifest structure**
   - Signal layers
   - Sparse graphs
   - Directives
   - Claims

2. **CivilizationSpec & CivilizationState**
   - Archetypes
   - Timeline generation

3. **CivilizationInfluenceLayer**
   - Sample(position, T) → civilization presence
   - Integrate into SystemGenerator

4. **Civilization-dependent POIs**
   - Settlements, ruins based on civ state
   - Match civ aesthetic/tech level

5. **Civilization timeline events**
   - Expansion, decline, collapse
   - Observable through POIs

### Validation

- System in civ territory has appropriate POIs
- Same system before civ founding has no civ POIs
- Observe civ collapse over time

---

## 4.6 Phase 5: POIs & Interaction (Week 12-14)

**Goal**: Full POI system with player interaction.

### Deliverables

1. **Full POI taxonomy**
   - All categories and tags
   - Generation based on context

2. **InteractableEvent system**
   - Event windows
   - Options and outcomes

3. **PlayerModifications**
   - Persistence layer
   - Timeline override injection

4. **POI connections**
   - References to other POIs
   - Archaeological network overlay

### Validation

- Interact with POI, choice persists
- Return later, see consequence
- Find ruin that references another ruin, visit it

---

## 4.7 Phase 6: Polish & Completeness (Week 15-16)

**Goal**: Fill gaps, handle edge cases, optimize.

### Deliverables

1. **Supernova sterilization**
   - Check nearby star deaths
   - Affect planet habitability/biosphere

2. **Atmospheric evolution**
   - Based on star luminosity history
   - Runaway greenhouse, stripping

3. **Planetary surface detail**
   - Region generation
   - Visual procedural map (abstract)

4. **Performance optimization**
   - Profile generation pipeline
   - Cache tuning
   - Background generation

5. **Edge cases**
   - Binary stars
   - Rogue planets (optional)
   - Neutron star systems

### Validation

- Find sterilized system (nearby supernova)
- Watch planet atmosphere evolve
- Smooth performance on target device

---

## 4.8 Phase 7: Gameplay Loop (Week 17+)

**Goal**: Turn the generation system into a game.

### Deliverables

1. **Travel gameplay**
   - Course plotting
   - In-transit events
   - Time acceleration (sleep pods)

2. **Scanning gameplay**
   - Probe systems
   - Gather information
   - Discover POIs

3. **Interaction gameplay**
   - Visit POIs
   - Make choices
   - Collect resources/knowledge

4. **Discovery log**
   - Track what player has seen
   - Timeline of journey

5. **Ship systems (optional)**
   - Fuel, maintenance
   - Upgrades
   - Crew/passengers (narrative flavor)

---

# Part V: Critical Implementation Details

## 5.1 Star Enumeration at Scale

With 100 billion stars, you cannot enumerate all of them. Use hierarchical spatial hashing.

### Sector-Based Enumeration

```swift
func starsWithin(radius: Double, of position: Position2D) -> LazySequence<SystemSpec> {
    // Determine which sectors could contain stars within radius
    let sectorSize: Double = 100  // ly
    let searchRadiusSectors = Int(ceil(radius / sectorSize)) + 1
    let centerSector = sectorFor(position)
    
    return (centerSector.i - searchRadiusSectors ... centerSector.i + searchRadiusSectors)
        .lazy
        .flatMap { i in
            (centerSector.j - searchRadiusSectors ... centerSector.j + searchRadiusSectors)
                .lazy
                .map { j in (i, j) }
        }
        .flatMap { (i, j) in
            systemsInSector(i: i, j: j)
        }
        .filter { system in
            system.position.distance(to: position) <= radius
        }
}
```

### Star Count per Sector

Calibrate star counts so total extrapolates correctly:

```swift
func starCountForSector(spec: SectorSpec) -> Int {
    // Galaxy: ~100 billion stars
    // Sectors: 1000 x 1000 = 1 million sectors
    // Average: 100,000 stars per sector
    // But varies by density band:
    
    let baseCount: Int
    switch spec.stellarDensity {
    case .core:      baseCount = 500_000
    case .innerDisk: baseCount = 150_000
    case .outerDisk: baseCount = 50_000
    case .arm:       baseCount = 200_000
    case .halo:      baseCount = 1_000
    }
    
    // Add some per-sector variation
    var rng = SeededRNG(seed: spec.address.seed)
    let variation = rng.next(in: 0.7...1.3)
    
    return Int(Double(baseCount) * variation)
}
```

### Lazy System Address Generation

Don't generate all 100,000 systems in a sector. Generate deterministic addresses on demand:

```swift
func systemAddress(sector: CosmicAddress, index: Int) -> CosmicAddress {
    sector.child(.system(index: index))
}

func systemPosition(address: CosmicAddress, sectorSpec: SectorSpec) -> Position2D {
    var rng = SeededRNG(seed: address.seed)
    
    // Uniform distribution within sector bounds
    let x = sectorSpec.bounds.minX + rng.next() * sectorSpec.bounds.width
    let y = sectorSpec.bounds.minY + rng.next() * sectorSpec.bounds.height
    
    return Position2D(x: x, y: y)
}
```

---

## 5.2 Determinism Guarantees

### Rule 1: Same Inputs → Same Outputs

Every generator must be a pure function of (Address, Context, T). No ambient state.

```swift
// GOOD
static func generateSpec(context: GenerationContext) -> SystemSpec {
    var rng = SeededRNG(seed: context.seed)  // Deterministic
    ...
}

// BAD
static func generateSpec(context: GenerationContext) -> SystemSpec {
    let random = Double.random(in: 0...1)  // Non-deterministic!
    ...
}
```

### Rule 2: RNG Stream Isolation

Each generation aspect uses its own RNG stream:

```swift
static func generateSpec(context: GenerationContext) -> SystemSpec {
    var starRNG = SeededRNG(seed: mixSeed(context.seed, "star", 0))
    var planetRNG = SeededRNG(seed: mixSeed(context.seed, "planets", 0))
    var civRNG = SeededRNG(seed: mixSeed(context.seed, "civilization", 0))
    
    let starClass = sampleStarClass(&starRNG)
    let planetCount = samplePlanetCount(&planetRNG)
    // If we add a new star property later, it doesn't affect planet generation
}
```

### Rule 3: Monotonic Spec Refinement

If a Spec is generated, derived data cannot contradict it:

```swift
// In PlanetSpec
let hasAtmosphere: Bool

// In PlanetDerived - must be consistent
let atmosphereDetail: AtmosphereDetail?  // nil if hasAtmosphere == false
```

---

## 5.3 Civilization Scoping

Civilizations are local. This is both a design choice and a tractability constraint.

### Maximum Civilization Radius

```swift
let maxCivilizationRadius: Double = 500  // light-years
```

At 500 ly radius, a civilization covers ~π×500² ≈ 785,000 square light-years. With ~0.004 stars per square light-year (disk average), that's ~3,000 stars—a reasonable empire.

### Civilization Density

Target: ~1000 concurrent civilizations galaxy-wide at any given T.

With a galaxy ~100,000 ly across and ~1000 civs, average spacing is ~3,000 ly between civ centers. Most of the galaxy is wilderness.

### Civilization Generation Scope

Civilizations are generated at **sector scope**, not galaxy scope:

```swift
func civilizationsInSector(sectorSpec: SectorSpec, time: Double) -> [CivilizationSpec] {
    var rng = SeededRNG(seed: mixSeed(sectorSpec.address.seed, "civilizations", 0))
    
    // How many civ "seeds" in this sector's history?
    let civSeedCount = poissonSample(lambda: 0.1, rng: &rng)  // ~0.1 civs per sector on average
    
    var civs: [CivilizationSpec] = []
    for i in 0..<civSeedCount {
        let civ = generateCivilizationSpec(
            seed: mixSeed(sectorSpec.address.seed, "civ", i),
            sectorSpec: sectorSpec
        )
        
        // Only include if active at query time
        let state = CivilizationState.at(spec: civ, time: time)
        if state.isActiveOrHasRuins {
            civs.append(civ)
        }
    }
    
    return civs
}
```

### Cross-Sector Civilizations

Some civilizations span multiple sectors. Handle via claims:

```swift
// If a civilization's homeworld is in Sector A but territory extends to Sector B,
// Sector B's overlay references the civilization by ID, not by regenerating it.

struct SectorOverlayManifest {
    let localCivilizations: [CivilizationSpec]
    let foreignInfluence: [CivilizationID: InfluenceRegion]
}
```

---

## 5.4 Supernova Sterilization Implementation

### Which Stars Go Supernova?

```swift
extension StarSpec {
    var willSupernova: Bool {
        mass > 8.0  // Solar masses
    }
    
    var supernovaTime: Double? {
        guard willSupernova else { return nil }
        return birthTime + StellarLifecycle.mainSequenceLifespan(mass: mass)
    }
}
```

### Sterilization Check (Optimized)

```swift
func checkSterilization(
    forPlanet planetAddress: CosmicAddress,
    inSystem systemSpec: SystemSpec,
    fromTime planetBirth: Double,
    toTime queryTime: Double
) -> SterilizationEvent? {
    
    let sterilizationRadius: Double = 50  // ly - approximate "kill radius" for supernova
    
    // Get nearby sectors
    let nearbySectors = sectorsWithin(radius: sterilizationRadius + 10, of: systemSpec.position)
    
    for sector in nearbySectors {
        // Only check massive stars (O, B class) - they're rare
        let massiveStars = systemsInSector(sector)
            .lazy
            .map { generateSpec(for: $0) }
            .filter { $0.primaryStarClass == .O || $0.primaryStarClass == .B }
        
        for star in massiveStars {
            guard let supernovaTime = star.supernovaTime else { continue }
            
            // Did it go off in the relevant time window?
            guard supernovaTime > planetBirth && supernovaTime < queryTime else { continue }
            
            // Was it close enough?
            let distance = star.position.distance(to: systemSpec.position)
            guard distance < sterilizationRadius else { continue }
            
            return SterilizationEvent(
                source: star.address,
                time: supernovaTime,
                distance: distance,
                intensity: supernovaIntensity(at: distance)
            )
        }
    }
    
    return nil
}
```

### Performance Note

This is O(nearby massive stars), which is small because:
- O/B stars are ~0.1% of all stars
- 50 ly radius contains ~500 stars on average
- So ~0.5 massive stars to check per query

Cache results per system since they're time-range queries.

---

## 5.5 The Idle Game Time Model

Your vision of an idle game where you "open it occasionally and fire off probes" suggests time should pass even when the app is closed.

### Real-Time vs. Game-Time Mapping

```swift
struct TimeModel {
    let realTimeStart: Date  // When this save began
    let gameTimeStart: Double  // Game T at that moment
    let timeAcceleration: Double  // Game years per real second (while app closed)
    
    var isInTransit: Bool
    var transitStartRealTime: Date?
    var transitStartGameTime: Double?
    var transitEndGameTime: Double?
    
    func currentGameTime() -> Double {
        if isInTransit {
            // During transit, time advances based on journey
            let realElapsed = Date().timeIntervalSince(transitStartRealTime!)
            let transitDuration = transitEndGameTime! - transitStartGameTime!
            let transitRealDuration: TimeInterval = transitDuration / 1000  // 1000 years per real second?
            
            let progress = min(1, realElapsed / transitRealDuration)
            return transitStartGameTime! + transitDuration * progress
        } else {
            // While stationary, time passes slowly
            let realElapsed = Date().timeIntervalSince(realTimeStart)
            return gameTimeStart + realElapsed * timeAcceleration
        }
    }
}
```

### Sleep Pods

Sleep pods accelerate the player's perception of time:

```swift
enum SleepPodQuality {
    case basic      // 10x acceleration (1 real hour = 10 game years while in system)
    case standard   // 100x
    case advanced   // 1000x
    case stasis     // 10000x (rare, expensive)
}

func enterSleepPod(quality: SleepPodQuality, duration: Double) {
    // duration is in game years
    timeModel.timeAcceleration = quality.accelerationFactor
    // When player "wakes," they're duration years in the future
}
```

### Events That Wake You

```swift
struct WakeEvent {
    let triggerTime: Double
    let type: WakeEventType
    let description: String
}

enum WakeEventType {
    case arrival  // Reached destination
    case collision  // Debris impact
    case signal  // Received transmission
    case proximity  // Something approaching
    case systemFailure  // Ship problem
    case scheduled  // Player-set alarm
}
```

When computing current game time, check for wake events:

```swift
func checkForWakeEvents(upTo time: Double) -> WakeEvent? {
    return scheduledEvents
        .filter { $0.triggerTime <= time }
        .min(by: { $0.triggerTime < $1.triggerTime })
}
```

---

## 5.6 Probe System

Probes extend the player's information-gathering capability.

### Probe Spec

```swift
struct Probe: Codable {
    let id: UUID
    let launchTime: Double  // Game T when launched
    let launchPosition: Position2D
    let target: CosmicAddress
    let velocity: Double  // Fraction of c
    let scanCapability: ScanCapability
}

enum ScanCapability {
    case basic       // System Spec only
    case detailed    // System Derived
    case deep        // POI Specs
}
```

### Probe Data Return

Probes send data back at light speed:

```swift
func probeDataArrival(probe: Probe, playerPosition: Position2D, playerTime: Double) -> ProbeData? {
    let targetPosition = positionOf(probe.target)
    let travelDistance = probe.launchPosition.distance(to: targetPosition)
    let travelTime = travelDistance / probe.velocity
    
    let arrivalAtTarget = probe.launchTime + travelTime
    let dataReturnDistance = targetPosition.distance(to: playerPosition)
    let dataReturnTime = dataReturnDistance / c
    
    let dataArrivalTime = arrivalAtTarget + dataReturnTime
    
    guard dataArrivalTime <= playerTime else {
        return nil  // Data hasn't arrived yet
    }
    
    // Generate what the probe observed
    let observedState = generateState(for: probe.target, at: arrivalAtTarget)
    
    return ProbeData(
        probe: probe,
        observedAt: arrivalAtTarget,
        receivedAt: dataArrivalTime,
        data: observedState
    )
}
```

---

# Part VI: Testing & Validation Strategy

## 6.1 Determinism Tests

```swift
func testDeterminism() {
    let address = CosmicAddress.random()
    let context = GenerationContext(address: address, time: 1000)
    
    let spec1 = SystemGenerator.generateSpec(context: context)
    let spec2 = SystemGenerator.generateSpec(context: context)
    
    XCTAssertEqual(spec1, spec2, "Same inputs must produce same outputs")
}

func testCrossSessionDeterminism() {
    // Generate, persist address, restart app, regenerate
    // Results must match
}
```

## 6.2 Statistical Validation

```swift
func testStarClassDistribution() {
    let specs = (0..<10000).map { i in
        let address = CosmicAddress.testAddress(index: i)
        return SystemGenerator.generateSpec(context: context(for: address))
    }
    
    let mDwarfFraction = specs.filter { $0.primaryStarClass == .M }.count / 10000
    
    // M dwarfs should be ~75% of all stars
    XCTAssertTrue((0.70...0.80).contains(mDwarfFraction))
}

func testGalacticStarCount() {
    // Sample sectors, extrapolate total
    let sampleSectors = (0..<1000).map { _ in randomSector() }
    let avgStarsPerSector = sampleSectors.map { $0.starCount }.average()
    let totalSectors = 1_000_000
    let estimatedTotalStars = avgStarsPerSector * Double(totalSectors)
    
    XCTAssertTrue((50_000_000_000...200_000_000_000).contains(estimatedTotalStars))
}
```

## 6.3 Temporal Consistency Tests

```swift
func testStellarEvolution() {
    let starSpec = StarSpec(mass: 10, birthTime: -1_000_000)
    
    // Should be main sequence at T=0
    let earlyState = StellarLifecycle.evaluate(spec: starSpec, time: 0)
    XCTAssertEqual(earlyState.phase, .mainSequence)
    
    // Should be dead at T = 100 million years
    let lateState = StellarLifecycle.evaluate(spec: starSpec, time: 100_000_000)
    XCTAssertTrue([.neutronStar, .blackHole].contains(lateState.phase))
}

func testMonotonicSpec() {
    let planetSpec = PlanetGenerator.generateSpec(context: someContext)
    let planetDerived = PlanetGenerator.generateDerived(context: someContext, spec: planetSpec)
    
    // Derived cannot contradict Spec
    if !planetSpec.hasAtmosphere {
        XCTAssertNil(planetDerived.atmosphereDetail)
    }
}
```

## 6.4 Performance Benchmarks

```swift
func benchmarkSystemSpecGeneration() {
    measure {
        for _ in 0..<1000 {
            let _ = SystemGenerator.generateSpec(context: randomContext())
        }
    }
    // Target: <1ms per spec (<1 second for 1000)
}

func benchmarkSterilizationCheck() {
    measure {
        for _ in 0..<100 {
            let _ = checkSterilization(forPlanet: randomPlanet(), ...)
        }
    }
    // Target: <10ms per check
}
```

---

# Part VII: Appendices

## Appendix A: Stellar Data

### Main Sequence Lifetimes (Approximate)

| Spectral Class | Mass (M☉) | MS Lifetime (years) |
|----------------|-----------|---------------------|
| O | 30 | 3 million |
| B | 10 | 30 million |
| A | 2 | 1 billion |
| F | 1.3 | 4 billion |
| G | 1.0 | 10 billion |
| K | 0.7 | 30 billion |
| M | 0.3 | 100+ billion |

### Stellar Class Frequencies (Milky Way)

| Class | Frequency |
|-------|-----------|
| M | 76% |
| K | 12% |
| G | 8% |
| F | 3% |
| A | 0.6% |
| B | 0.1% |
| O | 0.00003% |

## Appendix B: Habitable Zone Calculations

```swift
func habitableZone(luminosity: Double) -> ClosedRange<Double> {
    // Inner edge: ~0.95 * sqrt(L) AU
    // Outer edge: ~1.37 * sqrt(L) AU
    let sqrtL = sqrt(luminosity)
    return (0.95 * sqrtL)...(1.37 * sqrtL)
}
```

## Appendix C: Time Dilation Reference

For velocity v as fraction of c:

```swift
func lorentzFactor(v: Double) -> Double {
    1 / sqrt(1 - v * v)
}

// At 0.9c: γ ≈ 2.3 (10 years journey = 23 years elapsed)
// At 0.99c: γ ≈ 7.1 (10 years journey = 71 years elapsed)
// At 0.999c: γ ≈ 22.4 (10 years journey = 224 years elapsed)
```

## Appendix D: Recommended Libraries (Swift)

| Purpose | Library | Notes |
|---------|---------|-------|
| Fast hashing | xxHash-Swift | For seed mixing |
| Noise functions | FastNoise-Swift | For signal layers |
| Spatial indexing | R-tree implementation | For "stars within radius" |
| JSON persistence | Codable (built-in) | For player state |

## Appendix E: Glossary Quick Reference

| Term | One-Line Definition |
|------|---------------------|
| Address | Permanent hierarchical entity identifier |
| Spec | Cheap, O(1) entity properties |
| Derived | Expensive, fully-generated entity state |
| Signal Layer | Continuous function sampled by entities |
| Overlay | Cross-cutting data (fields, graphs, directives) |
| Claim | Stable binding between overlay feature and entity |
| Lifecycle | Deterministic time-dependent state function |
| Timeline | Sparse list of discrete events |
| Proper Time | Player's experienced time (τ) |
| Coordinate Time | Galaxy reference time (T) |
| Light Cone | Set of observable past events |

---

# Part VIII: Final Notes

## What This Document Is

A comprehensive architectural reference for building a procedural galaxy with temporal evolution, relativistic information propagation, and emergent civilization dynamics. It synthesizes discussions with multiple AI systems and your design requirements into a coherent implementation plan.

## What This Document Is Not

- A Swift tutorial
- A game design document (narrative, UI, moment-to-moment gameplay)
- A complete specification (many details intentionally left for implementation)

## Where to Start

1. **Phase 0**: Get CosmicAddress and deterministic generation working. This is the foundation.
2. **Test early**: Write determinism tests before you write generators.
3. **Visualize early**: Even a text-based printout of "here are the stars in this sector" validates that generation works.
4. **Time is hard**: Don't rush Phase 2. The temporal model affects everything downstream.

## When Stuck

- **Determinism broken?** Check RNG stream isolation.
- **Performance bad?** Check Spec vs. Derived boundary—are you generating Derived when you only need Spec?
- **Civilizations weird?** Check overlay scope visibility—is something querying across scope boundaries?
- **Light cone confusing?** Draw spacetime diagrams. Seriously.

## The Most Important Thing

The architecture serves the experience. If a "pure" solution makes the game worse, break the rules thoughtfully. Document why, and localize the impurity.

Good luck. This is going to be a fantastic project.

---

*Document version: 1.0*
*Architecture: SeedGraph + Overlays*
*Generated: January 2025*
