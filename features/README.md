# Procedural System/Feature Generator

A deterministic procedural generation system for creating explorable systems with consistent, reproducible content.

> [!WARNING]
> This version of the documentation was AI-generated based on code analysis and may not reflect all implementation details or recent changes. It will eventually be replaced with human-generated docs. Refer to the source code for authoritative information.

## What It Does

Generate entire star systems with planets, cities, stations, and points of interest—all from simple coordinates. No database needed.

```python
from procedural_features import GalaxyCoordinate, InteractiveSystemView

# Navigate to tile (5, 7), examine star #108
coord = GalaxyCoordinate(5, 7, 108)
system = InteractiveSystemView(coord)

# Get all cities in this system
cities = SystemOverview.find_entities(
    system.root,
    filter_fn=lambda e: e.properties.get('type') == 'city'
)
```

## Features

- **Hierarchical Coordinates**: Tiles → Stars → Planets → Features
- **Deterministic Generation**: Same input = same output, always
- **Realistic Rules**: Habitable zones, stellar evolution, metallicity effects
- **Extensible**: Easy to add new feature types or generation rules
- **Configurable**: Pre-built presets for different galaxy flavors

## Quick Start

```python
# Basic usage
coord = GalaxyCoordinate(1, 1, 42)  # Tile (1,1), star 42
star_props = CelestialGenerator.get_star_properties(coord)
planet_count = CelestialGenerator.get_planet_count(coord)

# Add realism rules
from generation_rules import create_default_rule_engine
CelestialGenerator.set_rule_engine(create_default_rule_engine())

# Change galaxy flavor
from generation_config import GenerationConfig, ConfigManager
ConfigManager.set_config(GenerationConfig.high_civilization())
```

## Structure

```
procedural_features/
├── core/                  # Coordinates & RNG
├── generators/            # Celestial & feature generation
├── features/              # Feature types (cities, stations, etc.)
├── system/                # System overview & navigation
└── rules/                 # Generation rules (habitable zones, etc.)
```

## Adding New Features

```python
from features.base import Feature

class SpaceWhale(Feature):
    FEATURE_TYPE = 'space_whale'
    PARENT_LEVEL = 'star'
    SPAWN_CHANCE = 0.01
    
    def generate_properties(self, rng):
        return {
            'type': self.FEATURE_TYPE,
            'name': self.generate_name(rng),
            'size': rng.choice(['small', 'enormous', 'incomprehensible']),
            'friendly': rng.random() > 0.5
        }
```

Register it in `features/registry.py` and you're done.

## Generation Rules

Rules let you add complex interdependencies:

```python
class NoMoonsAroundGasGiantsRule(GenerationRule):
    def applies_to(self, context):
        return context.get('parent_type') == 'gas_giant'
    
    def apply(self, properties, context):
        properties['has_moons'] = False
        return properties
```

## Galaxy Presets

- `GenerationConfig.default()` - Realistic distribution
- `GenerationConfig.high_civilization()` - Lots of cities and stations
- `GenerationConfig.harsh_galaxy()` - Rare habitable worlds
- `GenerationConfig.ancient_galaxy()` - Ruins everywhere
- `GenerationConfig.frontier()` - Mining operations and outposts

## Key Characteristics

**Infinite Scalability**: Deterministic generation allows for billions of unique star systems without persistence. Each coordinate consistently produces identical content across sessions.

**Performance**: Full star system generation, including all celestial bodies and features, completes in milliseconds.

**Platform Independence**: Pure Python implementation with minimal dependencies. The coordinate-based seeding approach ports cleanly to other languages while maintaining deterministic results.

## Example Output

```
⭐ Star (Class G)
  Mass: 1.02 M☉
  🪐 Planet 0
    Type: rocky, Radius: 0.87 AU, Habitable: ✅
    🏙️ New Colony
      Population: 2,547,891
    🏛️ Ancient Ruin 0
      Age: 245,678 years
  🪐 Planet 1
    Type: gas_giant, Radius: 5.23 AU, Habitable: ❌
  🛰️ Alpha Station
    Type: research
```

## Notes

- All generation is **lazy** - nothing computed until requested
- Thread-safe - uses coordinate-based seeding, no shared state
- Coordinates use tuples: `(tile_x, tile_y, star_index, planet_index)`
- Feature coordinates add `(feature_index, feature_type)`

## Future Ideas

- Trade route generation between cities
- Faction/government systems
- Resource deposits and mining
- Binary star systems
- Planet moons
- Stellar phenomena (black holes, pulsars)

---

A coordinate-based approach to procedural content generation.