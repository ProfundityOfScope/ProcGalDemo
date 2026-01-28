#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:18:51 2026

@author: sethbruzewski

Generate stars and their properties within tiles.
"""

from ..core.coordinates import GalaxyCoordinate
from ..core.rng import DeterministicRNG, RNG
from .rules import RuleEngine
from typing import Any

class CelestialGenerator:
    """
    Generate stars deterministically for a tile.
    
    This generator uses coordinate-based seeding to ensure the same
    coordinates always produce identical results. This allows for
    infinite galaxy exploration without storing every star.
    
    Example:
        >>> coord = GalaxyCoordinate(5, 7, 42)  # Tile (5,7), star 42
        >>> props = CelestialGenerator.get_star_properties(coord)
        >>> print(props['spectral_class'])
        'G'
    
    Rule System:
        You can add a rule engine to apply complex generation logic:
        >>> from generation_rules import create_default_rule_engine
        >>> engine = create_default_rule_engine()
        >>> CelestialGenerator.set_rule_engine(engine)
    """

    # Class-level rule engine (optional)
    rule_engine = None
    
    # Spectral class weights (realistic distribution)
    SPECTRAL_CLASS_WEIGHTS = {
        'O': 0.00003,   # Very rare, hot blue stars
        'B': 0.13,      # Rare, blue-white stars
        'A': 0.6,       # White stars
        'F': 3.0,       # Yellow-white stars
        'G': 7.6,       # Yellow stars (like our Sun)
        'K': 12.1,      # Orange stars
        'M': 76.45      # Red dwarfs (most common)
    }

    @classmethod
    def set_rule_engine(cls, engine: RuleEngine):
        """
        Set a rule engine for complex generation logic.
        
        Args:
            engine: RuleEngine instance or None to disable
        """
        cls.rule_engine = engine
    
    @staticmethod
    def get_star_count(coord: GalaxyCoordinate) -> int:
        """
        How many stars in this tile?
        
        Args:
            coord: GalaxyCoordinate at tile level
        
        Returns:
            Number of stars in the tile (50-200)
        """
        assert coord.level == 'tile', f"Expected tile coordinate, got {coord.level}"
        rng = DeterministicRNG.seeded_random("star_count", *coord.tile_coord())
        return rng.randint(50, 200)
    
    @staticmethod
    def get_star_properties(coord: GalaxyCoordinate) -> dict[str, Any]:
        """
        Get all properties for a specific star.
        
        Args:
            coord: GalaxyCoordinate at star level
        
        Returns:
            Dict with star properties including:
                - position: (x, y, z) normalized 0-1 within tile
                - spectral_class: O, B, A, F, G, K, or M
                - brightness: relative brightness (0.1-10.0)
                - mass: solar masses
                - age: billion years
                - metallicity: [Fe/H] ratio
        """
        assert coord.level == 'star', f"Expected star coordinate, got {coord.level}"
        
        # Use hierarchical seeding
        rng = DeterministicRNG.seeded_random("star", *coord.star_coord())
        
        # Position within tile (normalized 0-1)
        pos_x = rng.random()
        pos_y = rng.random()
        pos_z = rng.random()
        
        # Spectral class using realistic distribution
        spectral_class = CelestialGenerator._weighted_choice(
            rng, 
            CelestialGenerator.SPECTRAL_CLASS_WEIGHTS
        )
        
        # Mass based on spectral class
        mass = CelestialGenerator._mass_for_spectral_class(rng, spectral_class)
        
        # Age (0.1 to 13 billion years)
        # Older stars are slightly more common (galaxy is ~13.8 Gyr old)
        age = rng.triangular(0.1, 13.0, 8.0)
        
        # Metallicity [Fe/H] - newer stars tend to be more metal-rich
        # Correlate with age: younger = higher metallicity
        base_metallicity = -2.0 + (age / 13.0) * 2.5
        metallicity = rng.gauss(base_metallicity, 0.3)
        metallicity = max(-2.5, min(0.5, metallicity))  # Clamp
        
        # Brightness (relative, for display purposes)
        brightness = CelestialGenerator._brightness_for_mass(mass)
        brightness *= rng.uniform(0.8, 1.2)  # Add some variation
        
        return {
            'position': (pos_x, pos_y, pos_z),
            'spectral_class': spectral_class,
            'brightness': brightness,
            'mass': mass,
            'age': age,
            'metallicity': metallicity,
        }
    
    @staticmethod
    def get_planet_count(coord: GalaxyCoordinate) -> int:
        """How many planets orbit this star?"""
        rng = DeterministicRNG.seeded_random("planet_count", *coord.star_coord())
        return rng.randint(0, 12)
    
    @staticmethod
    def get_planet_properties(coord: GalaxyCoordinate) -> dict[str, Any]:
        """Get properties for a specific planet"""
        rng = DeterministicRNG.seeded_random("planet", *coord.planet_coord())
        
        planet_type = rng.choice(['rocky', 'gas_giant', 'ice_giant', 'dwarf'])
        orbital_radius = rng.uniform(0.1, 50.0)  # AU
        mass = rng.uniform(0.01, 300.0)  # Earth masses
        
        # Cities only on habitable rocky planets
        is_habitable = False
        if planet_type == 'rocky':
            habitability = rng.random()
            if habitability > 0.3:
                is_habitable = True
        
        return {
            'type': planet_type,
            'orbital_radius': orbital_radius,
            'mass': mass,
            'is_habitable': is_habitable
        }

    # Helper methods
    
    @staticmethod
    def _weighted_choice(rng: RNG, weights: dict[str, float]) -> str:
        """Choose item based on weights"""
        items = list(weights.keys())
        weight_values = list(weights.values())
        return rng.choices(items, weights=weight_values)[0]
    
    @staticmethod
    def _mass_for_spectral_class(rng: RNG, spectral_class: str) -> float:
        """Get appropriate mass for spectral class"""
        mass_ranges = {
            'O': (16.0, 50.0),
            'B': (2.1, 16.0),
            'A': (1.4, 2.1),
            'F': (1.04, 1.4),
            'G': (0.8, 1.04),
            'K': (0.45, 0.8),
            'M': (0.08, 0.45),
        }
        
        min_mass, max_mass = mass_ranges.get(spectral_class, (0.5, 1.5))
        return rng.uniform(min_mass, max_mass)
    
    @staticmethod
    def _brightness_for_mass(mass: float) -> float:
        """Calculate relative brightness from mass"""
        # Very rough approximation
        if mass < 0.43:
            return 0.23 * (mass ** 2.3)
        elif mass < 2:
            return mass ** 4
        else:
            return 1.4 * (mass ** 3.5)