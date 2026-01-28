#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:22:30 2026

@author: sethbruzewski

Features that exist on planetary surfaces.
Includes cities, ruins, mining operations, etc.
"""

from .base import Feature
from ..core.rng import RNG
from typing import Any
        
class City(Feature):
    """Cities on habitable planets"""
    
    FEATURE_TYPE = 'city'
    DISPLAY_NAME = 'City'
    PARENT_LEVEL = 'planet'
    SPAWN_CHANCE = 0.3
    MIN_COUNT = 1
    MAX_COUNT = 20
    
    @classmethod
    def can_spawn_at(cls, parent_level: str, parent_props: dict[str, Any]) -> bool:
        """Cities only on habitable planets with mature stars"""
        if not super().can_spawn_at(parent_level, parent_props):
            return False
        
        if not parent_props.get('is_habitable', False):
            return False
        
        return True
    
    def generate_properties(self, rng: RNG) -> dict[str, Any]:
        """Generate city-specific properties"""
        return {
            'type': self.FEATURE_TYPE,
            'display_name': self.DISPLAY_NAME,
            'name': self.generate_name(rng),
            'population': rng.randint(10_000, 10_000_000),
            'latitude': rng.uniform(-90, 90),
            'longitude': rng.uniform(-180, 180),
            'tech_level': rng.randint(1, 10),
        }
    
    def generate_name(self, rng: RNG) -> str:
        """Generate city name"""
        prefixes = ['New', 'Old', 'Alpha', 'Beta', 'Gamma', 'Delta', 'Prime']
        suffixes = ['City', 'Haven', 'Colony', 'Settlement', 'Outpost']
        return f"{rng.choice(prefixes)} {rng.choice(suffixes)}"

class AncientRuin(Feature):
    """Archaeological sites on planets"""
    
    FEATURE_TYPE = 'ancient_ruin'
    DISPLAY_NAME = 'Ancient Ruin'
    PARENT_LEVEL = 'planet'
    SPAWN_CHANCE = 0.15
    MIN_COUNT = 0
    MAX_COUNT = 5
    
    def generate_properties(self, rng: RNG) -> dict[str, Any]:
        return {
            'type': self.FEATURE_TYPE,
            'display_name': self.DISPLAY_NAME,
            'name': f"Ancient Ruin {self.coordinate.feature_index}",
            'age': rng.uniform(1_000, 1_000_000),  # years
            'condition': rng.choice(['pristine', 'deteriorated', 'ruins']),
            'artifact_count': rng.randint(0, 10),
        }


class MiningOperation(Feature):
    """Mining operations on planets"""
    
    FEATURE_TYPE = 'mining_site'
    DISPLAY_NAME = 'Mining Operation'
    PARENT_LEVEL = 'planet'
    SPAWN_CHANCE = 0.30
    MIN_COUNT = 0
    MAX_COUNT = 8
    
    def generate_properties(self, rng: RNG) -> dict[str, Any]:
        """Generate mining operation properties"""
        resource_types = [
            'iron', 'copper', 'gold', 'platinum', 'uranium',
            'titanium', 'lithium', 'rare_earth', 'diamonds', 'helium-3'
        ]
        
        operation_types = ['surface', 'deep_core', 'strip_mine', 'automated']
        
        is_active = rng.choice([True, False])
        
        return {
            'type': self.FEATURE_TYPE,
            'display_name': self.DISPLAY_NAME,
            'name': self.generate_name(rng),
            'resource_type': rng.choice(resource_types),
            'operation_type': rng.choice(operation_types),
            'yield_rate': rng.uniform(0.1, 10.0),  # tons per day
            'ore_quality': rng.uniform(0.1, 1.0),  # 0-100% purity
            'active': is_active,
            'workforce': rng.randint(10, 5000) if is_active else 0,
            'depth': rng.uniform(0.1, 50.0),  # kilometers
            'latitude': rng.uniform(-90, 90),
            'longitude': rng.uniform(-180, 180),
        }
    
    def generate_name(self, rng: RNG) -> str:
        """Generate mining operation name"""
        prefixes = ['Site', 'Dig', 'Quarry', 'Mine', 'Extraction Point']
        suffixes = ['Alpha', 'Beta', 'Gamma', 'Prime', 'One', 'Central']
        
        return f"{rng.choice(prefixes)} {rng.choice(suffixes)}"