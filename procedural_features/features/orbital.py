#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:24:02 2026

@author: sethbruzewski

Features that orbit stars or exist in orbital space.
Includes stations, asteroid belts, etc.
"""

from .base import Feature
from ..core.rng import RNG
from typing import Any

class OrbitalStation(Feature):
    """Space stations orbiting stars"""
    
    FEATURE_TYPE: str = 'station'
    DISPLAY_NAME = 'Orbital Station'
    PARENT_LEVEL = 'star'
    SPAWN_CHANCE: float = 0.40
    MIN_COUNT: int = 0
    MAX_COUNT: int = 4
    
    STELLAR_CLASS_FILTER = ['G', 'K', 'F']  # Only near suitable stars
    
    @classmethod
    def can_spawn_at(cls, parent_level: str, parent_props: dict[str, Any]) -> bool:
        if not super().can_spawn_at(parent_level, parent_props):
            return False
        
        stellar_class = parent_props.get('spectral_class', '')
        if stellar_class not in cls.STELLAR_CLASS_FILTER:
            return False
        
        return True
    
    def generate_properties(self, rng: RNG) -> dict[str, Any]:
        return {
            'type': self.FEATURE_TYPE,
            'display_name': self.DISPLAY_NAME,
            'name': self.generate_name(rng),
            'station_type': rng.choice(['mining', 'research', 'military', 'trade']),
            'orbital_radius': rng.uniform(0.5, 5.0),
            'crew_capacity': rng.randint(10, 1000),
        }
    
    def generate_name(self, rng: RNG) -> str:
        prefixes = ['Alpha', 'Beta', 'Gamma', 'Deep Space']
        suffixes = ['Station', 'Base', 'Outpost', 'Platform']
        return f"{rng.choice(prefixes)} {rng.choice(suffixes)}"

class AsteroidBelt(Feature):
    """Asteroid belts around stars"""
    
    FEATURE_TYPE: str = 'asteroid_belt'
    DISPLAY_NAME = 'Asteroid Belt'
    PARENT_LEVEL = 'star'
    SPAWN_CHANCE = 0.40
    MIN_COUNT = 0
    MAX_COUNT = 2
    
    def generate_properties(self, rng: RNG) -> dict[str, Any]:
        return {
            'type': self.FEATURE_TYPE,
            'display_name': self.DISPLAY_NAME,
            'name': f"Asteroid Belt {self.coordinate.feature_index}",
            'density': rng.choice(['sparse', 'moderate', 'dense']),
            'composition': rng.choice(['metallic', 'rocky', 'icy']),
            'inner_radius': rng.uniform(2.0, 3.0),
            'outer_radius': rng.uniform(3.5, 5.0),
        }
