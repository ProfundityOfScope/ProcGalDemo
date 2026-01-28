#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration system for procedural generation.

Provides centralized control over generation parameters, allowing
for different galaxy "flavors" or difficulty settings.
"""

from dataclasses import dataclass, field


@dataclass
class GenerationConfig:
    """
    Central configuration for generation parameters.
    
    Use this to customize the characteristics of your generated galaxy.
    
    Example:
        >>> config = GenerationConfig.high_civilization()
        >>> config.feature_spawn_multipliers['city']
        2.0
    """
    
    # Tile settings
    stars_per_tile_range: tuple[int, int] = (50, 200)
    
    # Star settings
    spectral_class_weights: dict[str, float] = field(default_factory=lambda: {
        'O': 0.00003,  # Very rare, hot blue supergiants
        'B': 0.13,     # Rare, blue-white stars
        'A': 0.6,      # White stars (Sirius, Vega)
        'F': 3.0,      # Yellow-white stars
        'G': 7.6,      # Yellow stars (our Sun)
        'K': 12.1,     # Orange stars
        'M': 76.45     # Red dwarfs (most common)
    })
    
    # Planet settings
    planets_per_star_range: tuple[int, int] = (0, 12)
    habitable_zone_strictness: float = 1.0  # Higher = stricter HZ requirements
    
    # Planet type distribution weights
    planet_type_weights: dict[str, float] = field(default_factory=lambda: {
        'rocky': 0.35,
        'gas_giant': 0.30,
        'ice_giant': 0.20,
        'dwarf': 0.15,
    })
    
    # Feature spawn rates (multipliers on base rates)
    feature_spawn_multipliers: dict[str, float] = field(default_factory=dict[str, float])
    
    # Habitability settings
    base_habitability_chance: float = 0.3  # For rocky planets in HZ
    old_star_penalty: float = 0.1  # Per billion years over 10
    young_star_penalty: float = 0.7  # Chance to be uninhabitable if < 0.5 Gyr
    
    # Civilization settings
    min_civilization_age: float = 0.5  # Billion years before civilizations appear
    metallicity_tech_bonus: bool = True  # Higher metallicity = higher tech
    
    # Naming
    name_style: str = 'mixed'  # 'mixed', 'systematic', 'creative'
    
    @classmethod
    def default(cls) -> 'GenerationConfig':
        """Standard realistic galaxy"""
        return cls()
    
    @classmethod
    def high_civilization(cls) -> 'GenerationConfig':
        """
        More cities, stations, and advanced civilizations.
        Good for a populated, "Star Trek" style galaxy.
        """
        config = cls()
        config.feature_spawn_multipliers = {
            'city': 2.0,
            'station': 1.5,
            'mining_site': 1.3,
        }
        config.base_habitability_chance = 0.4
        config.min_civilization_age = 0.3
        return config
    
    @classmethod
    def ancient_galaxy(cls) -> 'GenerationConfig':
        """
        More ruins and ancient sites, fewer active settlements.
        Good for an archaeological/exploration focused game.
        """
        config = cls()
        config.feature_spawn_multipliers = {
            'ancient_ruin': 3.0,
            'city': 0.5,
            'station': 0.7,
        }
        config.old_star_penalty = 0.05  # Old stars less penalized
        return config
    
    @classmethod
    def young_galaxy(cls) -> 'GenerationConfig':
        """
        Fewer old stars, more active systems, ongoing planet formation.
        """
        config = cls()
        config.spectral_class_weights = {
            'O': 0.001,   # More hot young stars
            'B': 0.5,
            'A': 2.0,
            'F': 5.0,
            'G': 10.0,
            'K': 15.0,
            'M': 67.5
        }
        config.feature_spawn_multipliers = {
            'nebula': 2.0,
            'asteroid_belt': 1.5,
        }
        return config
    
    @classmethod
    def harsh_galaxy(cls) -> 'GenerationConfig':
        """
        Very few habitable worlds, rare civilizations.
        Good for hard sci-fi or survival games.
        """
        config = cls()
        config.base_habitability_chance = 0.1
        config.habitable_zone_strictness = 1.5
        config.feature_spawn_multipliers = {
            'city': 0.3,
            'station': 0.5,
        }
        config.old_star_penalty = 0.2
        config.young_star_penalty = 0.9
        return config
    
    @classmethod
    def garden_galaxy(cls) -> 'GenerationConfig':
        """
        Many habitable worlds, lush and diverse.
        Good for exploration-focused gameplay.
        """
        config = cls()
        config.base_habitability_chance = 0.6
        config.planet_type_weights = {
            'rocky': 0.50,  # More rocky planets
            'gas_giant': 0.25,
            'ice_giant': 0.15,
            'dwarf': 0.10,
        }
        config.feature_spawn_multipliers = {
            'city': 1.5,
        }
        return config
    
    @classmethod
    def frontier(cls) -> 'GenerationConfig':
        """
        Mix of settled and unsettled systems.
        Mining operations and stations, fewer cities.
        """
        config = cls()
        config.feature_spawn_multipliers = {
            'mining_site': 2.0,
            'station': 1.5,
            'city': 0.7,
        }
        return config
    
    @classmethod
    def post_apocalyptic(cls) -> 'GenerationConfig':
        """
        Many ruins, few active settlements.
        Good for a fallen civilization scenario.
        """
        config = cls()
        config.feature_spawn_multipliers = {
            'ancient_ruin': 4.0,
            'city': 0.2,
            'station': 0.3,
        }
        return config
    
    def get_feature_spawn_chance(self, feature_type: str, base_chance: float) -> float:
        """
        Get modified spawn chance for a feature type.
        
        Args:
            feature_type: Type of feature (e.g., 'city')
            base_chance: Base spawn chance from feature class
        
        Returns:
            Modified spawn chance
        """
        multiplier = self.feature_spawn_multipliers.get(feature_type, 1.0)
        return min(1.0, base_chance * multiplier)


@dataclass
class VisualizationConfig:
    """Configuration for visualization/UI elements"""
    
    # Color schemes for different spectral classes
    spectral_colors: dict[str, str] = field(default_factory=lambda: {
        'O': '#9bb0ff',  # Blue
        'B': '#aabfff',  # Blue-white
        'A': '#cad7ff',  # White
        'F': '#f8f7ff',  # Yellow-white
        'G': '#fff4ea',  # Yellow
        'K': '#ffd2a1',  # Orange
        'M': '#ffcc6f',  # Red
    })
    
    # Planet type colors
    planet_colors: dict[str, str] = field(default_factory=lambda: {
        'rocky': '#8b7355',
        'gas_giant': '#d4a574',
        'ice_giant': '#87ceeb',
        'dwarf': '#696969',
    })
    
    # Icon/emoji mapping
    icons: dict[str, str] = field(default_factory=lambda: {
        'star': '⭐',
        'rocky': '🪐',
        'gas_giant': '🌍',
        'ice_giant': '❄️',
        'dwarf': '🌑',
        'city': '🏙️',
        'station': '🛰️',
        'asteroid_belt': '☄️',
        'ancient_ruin': '🏛️',
        'mining_site': '⛏️',
        'nebula': '🌌',
        'anomaly': '❓',
    })


class ConfigManager:
    """
    Manages the current configuration.
    
    Use this to set and retrieve the active configuration.
    """
    
    _current_config: GenerationConfig | None = None
    _visual_config: VisualizationConfig | None = None
    
    @classmethod
    def set_config(cls, config: GenerationConfig):
        """Set the active generation configuration"""
        cls._current_config = config
    
    @classmethod
    def get_config(cls) -> GenerationConfig:
        """Get the active configuration (or default if not set)"""
        if cls._current_config is None:
            cls._current_config = GenerationConfig.default()
        return cls._current_config
    
    @classmethod
    def set_visual_config(cls, config: VisualizationConfig):
        """Set the visualization configuration"""
        cls._visual_config = config
    
    @classmethod
    def get_visual_config(cls) -> VisualizationConfig:
        """Get the visualization configuration (or default)"""
        if cls._visual_config is None:
            cls._visual_config = VisualizationConfig()
        return cls._visual_config
    
    @classmethod
    def reset(cls):
        """Reset to default configuration"""
        cls._current_config = GenerationConfig.default()
        cls._visual_config = VisualizationConfig()


# Example usage
if __name__ == "__main__":
    # Set up a high civilization galaxy
    config = GenerationConfig.high_civilization()
    ConfigManager.set_config(config)
    
    # Later in code:
    current = ConfigManager.get_config()
    city_spawn_chance = current.get_feature_spawn_chance('city', 0.3)
    print(f"Modified city spawn chance: {city_spawn_chance}")  # 0.6 (0.3 * 2.0)
