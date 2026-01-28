# Procedural Galaxy Generator - Code Review & Suggestions

## Executive Summary

Your procedural generation system has a solid foundation with excellent architectural choices:
- ✅ Hierarchical coordinate system
- ✅ Deterministic RNG with proper seeding
- ✅ Clean separation of concerns
- ✅ Extensible feature registry pattern

However, there are opportunities to improve maintainability, add complex generation rules, and fix some issues.

---

## Critical Issues

### 1. **Incomplete SpaceAnomaly Class**
**File:** `spatial.py`
**Issue:** The `SpaceAnomaly` class is cut off with just a comment `# ...`

**Fix:**
```python
class SpaceAnomaly(Feature):
    """Strange phenomena in space"""
    
    FEATURE_TYPE = 'anomaly'
    DISPLAY_NAME = 'Space Anomaly'
    PARENT_LEVEL = 'tile'
    SPAWN_CHANCE = 0.02
    MIN_COUNT = 0
    MAX_COUNT = 1
    
    def generate_properties(self, rng) -> dict:
        return {
            'type': self.FEATURE_TYPE,
            'display_name': self.DISPLAY_NAME,
            'name': self.generate_name(rng),
            'anomaly_type': rng.choice(['temporal', 'gravitational', 'energy', 'wormhole']),
            'danger_level': rng.randint(1, 10),
            'size': rng.uniform(0.1, 5.0),  # AU
        }
    
    def generate_name(self, rng) -> str:
        prefixes = ['Anomaly', 'Distortion', 'Rift', 'Phenomenon']
        suffixes = ['Alpha', 'Beta', 'Gamma', 'Delta']
        return f"{rng.choice(prefixes)} {rng.choice(suffixes)}"
```

### 2. **Type Annotation Syntax Error**
**File:** `feature_generator.py` line 30
**Issue:** `list[FeatureCoordinate]` should be `List[FeatureCoordinate]` for Python < 3.9 compatibility

**Fix:**
```python
from typing import List

def get_features(celestial: GalaxyCoordinate, 
                 celestial_properties: dict = None) -> List[FeatureCoordinate]:
```

### 3. **Missing Star Properties in Planet Generation**
**File:** `celestial_generator.py`
**Issue:** Habitability calculation doesn't consider star properties (temperature, radiation)

**Current:**
```python
if planet_type == 'rocky':
    habitability = rng.random()
    if habitability > 0.3:
        is_habitable = True
```

**Should be:**
```python
# Need to pass star properties
def get_planet_properties(coord: GalaxyCoordinate, star_props: dict = None) -> dict:
    # ... existing code ...
    
    is_habitable = False
    if planet_type == 'rocky' and star_props:
        # Check if in habitable zone
        habitable_zone = CelestialGenerator._calculate_habitable_zone(star_props)
        if habitable_zone[0] <= orbital_radius <= habitable_zone[1]:
            # Fine-tune with additional factors
            habitability = rng.random()
            if habitability > 0.3:
                is_habitable = True
```

---

## Architecture Improvements

### 1. **Add Configuration System**

Create a centralized configuration for generation parameters:

```python
# config/generation_config.py
from dataclasses import dataclass, field
from typing import Dict, Tuple

@dataclass
class GenerationConfig:
    """Central configuration for generation parameters"""
    
    # Tile settings
    stars_per_tile_range: Tuple[int, int] = (50, 200)
    
    # Star settings
    spectral_class_weights: Dict[str, float] = field(default_factory=lambda: {
        'O': 0.00003,  # Very rare
        'B': 0.13,
        'A': 0.6,
        'F': 3.0,
        'G': 7.6,      # Like our sun
        'K': 12.1,
        'M': 76.45     # Most common
    })
    
    # Planet settings
    planets_per_star_range: Tuple[int, int] = (0, 12)
    habitable_zone_multiplier: float = 1.0
    
    # Feature spawn rates (can override per-feature)
    feature_spawn_multipliers: Dict[str, float] = field(default_factory=dict)
    
    @classmethod
    def default(cls):
        return cls()
    
    @classmethod
    def high_civilization(cls):
        """More cities and stations"""
        config = cls()
        config.feature_spawn_multipliers = {
            'city': 2.0,
            'station': 1.5,
        }
        return config
    
    @classmethod
    def ancient_galaxy(cls):
        """More ruins, fewer active settlements"""
        config = cls()
        config.feature_spawn_multipliers = {
            'ancient_ruin': 3.0,
            'city': 0.5,
        }
        return config
```

### 2. **Add Rule System for Complex Generation**

Create a rule-based system for interdependent generation:

```python
# generators/rules.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class GenerationRule(ABC):
    """Base class for generation rules"""
    
    @abstractmethod
    def applies_to(self, context: Dict[str, Any]) -> bool:
        """Check if this rule applies to the current context"""
        pass
    
    @abstractmethod
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Modify properties based on the rule"""
        pass


class HabitableZoneRule(GenerationRule):
    """Planets must be in habitable zone to be habitable"""
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        return context.get('entity_type') == 'planet' and context.get('star_props') is not None
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        star_props = context['star_props']
        orbital_radius = properties['orbital_radius']
        
        # Calculate habitable zone based on star luminosity
        luminosity = self._calculate_luminosity(star_props)
        inner_hz = (luminosity / 1.1) ** 0.5
        outer_hz = (luminosity / 0.53) ** 0.5
        
        if properties['type'] == 'rocky':
            in_hz = inner_hz <= orbital_radius <= outer_hz
            properties['is_habitable'] = in_hz and properties.get('is_habitable', False)
        
        return properties
    
    @staticmethod
    def _calculate_luminosity(star_props: Dict[str, Any]) -> float:
        """Calculate luminosity from spectral class and mass"""
        spectral_class = star_props.get('spectral_class', 'G')
        mass = star_props.get('mass', 1.0)
        
        # Rough approximation: L ∝ M^3.5
        return mass ** 3.5


class OldStarNoHabitableRule(GenerationRule):
    """Old stars (>10 Gyr) less likely to have habitable planets"""
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        return (context.get('entity_type') == 'planet' and 
                context.get('star_props', {}).get('age', 0) > 10)
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Reduce habitability for old stars
        if properties.get('is_habitable'):
            # 50% chance to make uninhabitable
            rng = context.get('rng')
            if rng and rng.random() < 0.5:
                properties['is_habitable'] = False
                properties['habitability_notes'] = 'Star too old - radiation stripped atmosphere'
        
        return properties


class HighMetallicityCitiesRule(GenerationRule):
    """Higher metallicity stars = more advanced civilizations"""
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        return context.get('feature_type') == 'city'
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        star_props = context.get('star_props', {})
        metallicity = star_props.get('metallicity', 0)
        
        # Higher metallicity = more resources = higher tech
        if metallicity > 0.2:
            properties['tech_level'] = min(10, properties['tech_level'] + 2)
        elif metallicity < -1.0:
            properties['tech_level'] = max(1, properties['tech_level'] - 2)
        
        return properties


class RuleEngine:
    """Manages and applies generation rules"""
    
    def __init__(self):
        self.rules: List[GenerationRule] = []
    
    def add_rule(self, rule: GenerationRule):
        self.rules.append(rule)
    
    def apply_rules(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all applicable rules to properties"""
        for rule in self.rules:
            if rule.applies_to(context):
                properties = rule.apply(properties, context)
        
        return properties


# Default rule engine
def create_default_rule_engine() -> RuleEngine:
    engine = RuleEngine()
    engine.add_rule(HabitableZoneRule())
    engine.add_rule(OldStarNoHabitableRule())
    engine.add_rule(HighMetallicityCitiesRule())
    return engine
```

### 3. **Enhance CelestialGenerator with Rules**

```python
# Updated celestial_generator.py
class CelestialGenerator:
    """Generate stars deterministically for a tile"""
    
    # Add class-level rule engine
    rule_engine = None
    
    @classmethod
    def set_rule_engine(cls, engine):
        cls.rule_engine = engine
    
    @staticmethod
    def get_planet_properties(coord: GalaxyCoordinate, star_props: dict = None) -> dict:
        """Get properties for a specific planet"""
        rng = DeterministicRNG.seeded_random("planet", *coord.planet_coord())
        
        planet_type = rng.choice(['rocky', 'gas_giant', 'ice_giant', 'dwarf'])
        orbital_radius = rng.uniform(0.1, 50.0)
        mass = rng.uniform(0.01, 300.0)
        
        # Initial habitability (will be refined by rules)
        is_habitable = False
        if planet_type == 'rocky':
            habitability = rng.random()
            if habitability > 0.3:
                is_habitable = True
        
        properties = {
            'type': planet_type,
            'orbital_radius': orbital_radius,
            'mass': mass,
            'is_habitable': is_habitable
        }
        
        # Apply rules if engine is configured
        if CelestialGenerator.rule_engine and star_props:
            context = {
                'entity_type': 'planet',
                'star_props': star_props,
                'rng': rng,
                'coord': coord
            }
            properties = CelestialGenerator.rule_engine.apply_rules(properties, context)
        
        return properties
    
    @staticmethod
    def _calculate_habitable_zone(star_props: dict) -> tuple[float, float]:
        """Calculate habitable zone for a star"""
        spectral_class = star_props.get('spectral_class', 'G')
        mass = star_props.get('mass', 1.0)
        
        # Luminosity approximation
        luminosity = mass ** 3.5
        
        # Habitable zone calculation
        inner = (luminosity / 1.1) ** 0.5
        outer = (luminosity / 0.53) ** 0.5
        
        return (inner, outer)
```

---

## Maintainability Improvements

### 1. **Add Validation and Error Handling**

```python
# core/validation.py
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Raised when generation produces invalid data"""
    pass


class PropertyValidator:
    """Validates generated properties"""
    
    @staticmethod
    def validate_planet(properties: Dict[str, Any]) -> bool:
        """Validate planet properties"""
        required = ['type', 'orbital_radius', 'mass', 'is_habitable']
        
        for field in required:
            if field not in properties:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate ranges
        if properties['orbital_radius'] <= 0:
            logger.error(f"Invalid orbital_radius: {properties['orbital_radius']}")
            return False
        
        if properties['mass'] <= 0:
            logger.error(f"Invalid mass: {properties['mass']}")
            return False
        
        return True
    
    @staticmethod
    def validate_feature(properties: Dict[str, Any], feature_type: str) -> bool:
        """Validate feature properties"""
        if 'type' not in properties:
            logger.error("Feature missing type field")
            return False
        
        if 'name' not in properties:
            logger.error("Feature missing name field")
            return False
        
        # Type-specific validation
        if feature_type == 'city':
            if 'population' not in properties or properties['population'] < 0:
                logger.error(f"Invalid city population: {properties.get('population')}")
                return False
        
        return True
```

### 2. **Add Caching Layer**

For performance optimization when repeatedly accessing the same coordinates:

```python
# core/cache.py
from functools import lru_cache
from typing import Dict, Any

class GenerationCache:
    """Cache for generated properties"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
    
    def get(self, key: str) -> Any:
        return self._cache.get(key)
    
    def set(self, key: str, value: Any):
        if len(self._cache) >= self.max_size:
            # Simple FIFO eviction
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value
    
    def clear(self):
        self._cache.clear()


# Usage in generators
class CelestialGenerator:
    _cache = GenerationCache()
    
    @staticmethod
    def get_star_properties(coord: GalaxyCoordinate) -> dict:
        cache_key = f"star_{coord.star_coord()}"
        
        cached = CelestialGenerator._cache.get(cache_key)
        if cached:
            return cached
        
        # ... existing generation code ...
        
        result = {
            'position': (pos_x, pos_y, pos_z),
            # ... rest of properties
        }
        
        CelestialGenerator._cache.set(cache_key, result)
        return result
```

### 3. **Better Naming Generation**

Replace simple random choice with Markov chains or syllable-based generation:

```python
# utils/name_generator.py
import random
from typing import List

class NameGenerator:
    """Generate more interesting names using syllables"""
    
    PREFIXES = {
        'city': ['Neo', 'Nova', 'Port', 'New', 'Old', 'Fort', 'Terra'],
        'station': ['Alpha', 'Beta', 'Gamma', 'Deep Space', 'Orbital'],
        'planet': ['Kepler', 'Gliese', 'Proxima', 'Tau', 'Epsilon'],
    }
    
    ROOTS = {
        'city': ['Angeles', 'York', 'Tokyo', 'London', 'Paris', 'Berlin'],
        'station': ['One', 'Prime', 'Nexus', 'Hub', 'Outpost'],
    }
    
    SUFFIXES = {
        'city': ['City', 'Haven', 'Colony', 'Settlement', 'Prime', 'Major', 'Minor'],
        'station': ['Station', 'Base', 'Outpost', 'Platform', 'Array'],
    }
    
    SYLLABLES = [
        'ka', 'ri', 'na', 'to', 'ma', 'shi', 'ra', 'mi', 'ko', 'sa',
        'zen', 'dor', 'val', 'rex', 'tor', 'vex', 'nox', 'zar', 'kir'
    ]
    
    @classmethod
    def generate_city_name(cls, rng: random.Random, culture: str = 'generic') -> str:
        """Generate city name with optional culture flavor"""
        if rng.random() < 0.7:  # 70% use prefix-suffix pattern
            prefix = rng.choice(cls.PREFIXES['city'])
            suffix = rng.choice(cls.SUFFIXES['city'])
            
            # Sometimes add a root
            if rng.random() < 0.3:
                root = rng.choice(cls.ROOTS['city'])
                return f"{prefix} {root} {suffix}"
            return f"{prefix} {suffix}"
        else:  # 30% use syllable-based
            syllable_count = rng.randint(2, 4)
            syllables = [rng.choice(cls.SYLLABLES) for _ in range(syllable_count)]
            name = ''.join(syllables).capitalize()
            return f"{name} City"
    
    @classmethod
    def generate_station_name(cls, rng: random.Random) -> str:
        """Generate station name"""
        prefix = rng.choice(cls.PREFIXES['station'])
        suffix = rng.choice(cls.SUFFIXES['station'])
        
        # Sometimes add a number
        if rng.random() < 0.4:
            num = rng.randint(1, 99)
            return f"{prefix} {suffix} {num}"
        
        return f"{prefix} {suffix}"
    
    @classmethod
    def generate_planet_designation(cls, rng: random.Random, star_name: str, planet_index: int) -> str:
        """Generate planet designation (like Kepler-452b)"""
        # Use star coordinate as "catalog number"
        letter = chr(ord('b') + planet_index)  # b, c, d, etc.
        return f"{star_name}-{letter}"
```

---

## Additional Features to Consider

### 1. **Trade Routes Between Cities**

```python
# features/trade.py
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class TradeRoute:
    """Connection between two cities"""
    origin: FeatureCoordinate
    destination: FeatureCoordinate
    trade_volume: float
    goods: List[str]
    
class TradeNetwork:
    """Generate trade networks within a system"""
    
    @staticmethod
    def generate_routes(cities: List[FeatureCoordinate], star_coord: GalaxyCoordinate) -> List[TradeRoute]:
        """Generate trade routes between cities"""
        rng = DeterministicRNG.seeded_random("trade", *star_coord.star_coord())
        
        routes = []
        for i, city1 in enumerate(cities):
            for city2 in cities[i+1:]:
                # Probability based on distance (same planet = higher)
                if city1.celestial == city2.celestial:
                    prob = 0.8
                else:
                    prob = 0.2
                
                if rng.random() < prob:
                    routes.append(TradeRoute(
                        origin=city1,
                        destination=city2,
                        trade_volume=rng.uniform(100, 10000),
                        goods=rng.sample(['food', 'tech', 'minerals', 'fuel'], k=rng.randint(1, 3))
                    ))
        
        return routes
```

### 2. **Faction/Government System**

```python
# features/factions.py
from enum import Enum
from typing import Dict, List

class GovernmentType(Enum):
    DEMOCRACY = "democracy"
    AUTOCRACY = "autocracy"
    CORPORATE = "corporate"
    THEOCRACY = "theocracy"
    ANARCHY = "anarchy"

class Faction:
    """Political faction controlling cities/systems"""
    
    def __init__(self, name: str, government: GovernmentType, tech_level: int):
        self.name = name
        self.government = government
        self.tech_level = tech_level
        self.controlled_cities: List[FeatureCoordinate] = []
    
class FactionGenerator:
    """Generate factions for star systems"""
    
    @staticmethod
    def generate_system_factions(star_coord: GalaxyCoordinate, cities: List) -> Dict[str, Faction]:
        """Generate factions that control cities in this system"""
        rng = DeterministicRNG.seeded_random("factions", *star_coord.star_coord())
        
        # Number of factions based on city count
        faction_count = min(len(cities), rng.randint(1, 3))
        
        factions = {}
        for i in range(faction_count):
            faction = Faction(
                name=f"Faction {chr(65 + i)}",  # A, B, C...
                government=rng.choice(list(GovernmentType)),
                tech_level=rng.randint(1, 10)
            )
            factions[faction.name] = faction
        
        # Assign cities to factions
        for city in cities:
            faction = rng.choice(list(factions.values()))
            faction.controlled_cities.append(city)
        
        return factions
```

### 3. **Resource System**

```python
# features/resources.py
from enum import Enum
from typing import Dict

class ResourceType(Enum):
    IRON = "iron"
    COPPER = "copper"
    GOLD = "gold"
    URANIUM = "uranium"
    HELIUM3 = "helium-3"
    WATER = "water"
    RARE_EARTH = "rare_earth"

class ResourceDeposit:
    """Resource deposits on planets"""
    
    def __init__(self, resource: ResourceType, abundance: float, quality: float):
        self.resource = resource
        self.abundance = abundance  # 0-1
        self.quality = quality  # 0-1
    
class PlanetaryResources:
    """Generate resources for planets"""
    
    @staticmethod
    def generate(planet_coord: GalaxyCoordinate, planet_props: dict) -> Dict[ResourceType, ResourceDeposit]:
        """Generate resources based on planet type"""
        rng = DeterministicRNG.seeded_random("resources", *planet_coord.planet_coord())
        
        resources = {}
        planet_type = planet_props.get('type', 'rocky')
        
        # Different planet types have different resource profiles
        if planet_type == 'rocky':
            possible = [ResourceType.IRON, ResourceType.COPPER, ResourceType.URANIUM, 
                       ResourceType.RARE_EARTH, ResourceType.WATER]
        elif planet_type == 'gas_giant':
            possible = [ResourceType.HELIUM3]
        elif planet_type == 'ice_giant':
            possible = [ResourceType.WATER, ResourceType.HELIUM3]
        else:
            possible = []
        
        # Spawn some resources
        for resource in possible:
            if rng.random() < 0.4:  # 40% chance
                resources[resource] = ResourceDeposit(
                    resource=resource,
                    abundance=rng.random(),
                    quality=rng.random()
                )
        
        return resources
```

---

## Testing Recommendations

### 1. **Determinism Tests**

```python
# tests/test_determinism.py
import unittest
from procedural_features import GalaxyCoordinate, CelestialGenerator

class TestDeterminism(unittest.TestCase):
    
    def test_star_properties_deterministic(self):
        """Same coordinate should always produce same star"""
        coord = GalaxyCoordinate(1, 1, 42)
        
        props1 = CelestialGenerator.get_star_properties(coord)
        props2 = CelestialGenerator.get_star_properties(coord)
        
        self.assertEqual(props1, props2)
    
    def test_different_coords_different_properties(self):
        """Different coordinates should produce different results"""
        coord1 = GalaxyCoordinate(1, 1, 42)
        coord2 = GalaxyCoordinate(1, 1, 43)
        
        props1 = CelestialGenerator.get_star_properties(coord1)
        props2 = CelestialGenerator.get_star_properties(coord2)
        
        self.assertNotEqual(props1, props2)
    
    def test_planet_count_deterministic(self):
        """Planet count should be deterministic"""
        coord = GalaxyCoordinate(5, 7, 108)
        
        count1 = CelestialGenerator.get_planet_count(coord)
        count2 = CelestialGenerator.get_planet_count(coord)
        
        self.assertEqual(count1, count2)
```

### 2. **Property Validation Tests**

```python
# tests/test_validation.py
import unittest
from procedural_features import CelestialGenerator, GalaxyCoordinate

class TestPropertyValidation(unittest.TestCase):
    
    def test_planet_properties_valid(self):
        """All planet properties should be in valid ranges"""
        coord = GalaxyCoordinate(1, 1, 0, 0)
        props = CelestialGenerator.get_planet_properties(coord)
        
        self.assertIn('type', props)
        self.assertIn('orbital_radius', props)
        self.assertIn('mass', props)
        
        self.assertGreater(props['orbital_radius'], 0)
        self.assertGreater(props['mass'], 0)
        self.assertIn(props['type'], ['rocky', 'gas_giant', 'ice_giant', 'dwarf'])
    
    def test_habitable_zone_logic(self):
        """Habitable planets should generally be rocky and in good orbits"""
        # Run many times to check distribution
        habitable_count = 0
        total = 100
        
        for i in range(total):
            coord = GalaxyCoordinate(1, 1, 0, i)
            props = CelestialGenerator.get_planet_properties(coord)
            
            if props.get('is_habitable'):
                # Must be rocky
                self.assertEqual(props['type'], 'rocky')
                habitable_count += 1
        
        # Should have some habitable planets but not too many
        self.assertGreater(habitable_count, 0)
        self.assertLess(habitable_count, total)
```

---

## Documentation Improvements

Add comprehensive docstrings:

```python
class CelestialGenerator:
    """
    Generate stars and planets deterministically for galaxy tiles.
    
    This generator uses coordinate-based seeding to ensure the same
    coordinates always produce identical results. This allows for
    infinite galaxy exploration without storing every star.
    
    Example:
        >>> coord = GalaxyCoordinate(5, 7, 42)  # Tile (5,7), star 42
        >>> props = CelestialGenerator.get_star_properties(coord)
        >>> print(props['spectral_class'])
        'G'
    
    Thread Safety:
        All methods are thread-safe as they use coordinate-based
        seeding rather than shared state.
    
    Performance:
        Generation is lazy - properties are only computed when requested.
        For frequently accessed coordinates, consider caching results.
    """
```

---

## Summary of Recommendations

### High Priority
1. ✅ Fix the incomplete `SpaceAnomaly` class
2. ✅ Fix type annotation compatibility issues
3. ✅ Add rule system for complex interdependent generation
4. ✅ Pass star properties to planet generation
5. ✅ Add proper validation and error handling

### Medium Priority
1. ✅ Implement configuration system
2. ✅ Add caching layer for performance
3. ✅ Improve name generation
4. ✅ Add comprehensive tests
5. ✅ Better documentation

### Nice to Have
1. Trade route system
2. Faction/government system
3. Resource deposits
4. Star naming/catalog system
5. Visual debugging tools

Your architecture is solid - these improvements will make it more maintainable and ready for complex rule additions!
