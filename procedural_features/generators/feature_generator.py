#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:25:56 2026

@author: sethbruzewski

Spawning and property generation for features.
Coordinates between feature classes and the generation system.
"""

from ..core.coordinates import GalaxyCoordinate, FeatureCoordinate
from ..core.rng import DeterministicRNG
from ..features.registry import FeatureRegistry
from ..features.base import Feature
from typing import Any

# Updated spawner and generator
class FeatureSpawner:
    """Handles spawn logic"""
    
    @staticmethod
    def get_features(celestial: GalaxyCoordinate, 
                     celestial_properties: dict[str, Any] | None = None) -> list[FeatureCoordinate]:
        """Determine which features spawn"""
        features: list[FeatureCoordinate] = []
        celestial_properties = celestial_properties or {}
        
        # Get applicable feature classes
        applicable = FeatureRegistry.get_features_for_level(celestial.level)
        
        for feature_class in applicable:
            if FeatureSpawner._should_spawn(celestial, feature_class, celestial_properties):
                count = FeatureSpawner._get_spawn_count(celestial, feature_class)
                
                for i in range(count):
                    feature = FeatureCoordinate(
                        celestial=celestial,
                        feature_index=i,
                        feature_type=feature_class.FEATURE_TYPE
                    )
                    features.append(feature)
        
        return features
    
    @staticmethod
    def _should_spawn(celestial: GalaxyCoordinate, 
                     feature_class: type[Feature],
                     celestial_properties: dict[str, Any]) -> bool:
        """Roll dice to see if feature spawns"""
        rng = DeterministicRNG.seeded_random(
            "feature_spawn", *celestial.tile_coord(),
            celestial.star_index, celestial.planet_index,
            feature_class.FEATURE_TYPE
        )
        
        # Basic spawn chance
        if rng.random() > feature_class.SPAWN_CHANCE:
            return False
        
        # Check class-specific conditions
        return feature_class.can_spawn_at(celestial.level, celestial_properties)
    
    @staticmethod
    def _get_spawn_count(celestial: GalaxyCoordinate, feature_class: type[Feature]) -> int:
        """How many of this feature type?"""
        rng = DeterministicRNG.seeded_random(
            "feature_count", *celestial.tile_coord(),
            celestial.star_index, celestial.planet_index,
            feature_class.FEATURE_TYPE
        )
        return rng.randint(feature_class.MIN_COUNT, feature_class.MAX_COUNT)


class FeaturePropertyGenerator:
    """Generates properties for feature instances"""
    
    @staticmethod
    def generate(feature: FeatureCoordinate) -> dict[str, Any]:
        """Generate all properties for a feature"""
        rng = DeterministicRNG.seeded_random("feature_props", *feature.coord_tuple())
        
        # Get the feature class
        feature_class = FeatureRegistry.get_feature_class(feature.feature_type)
        if not feature_class:
            return {'type': feature.feature_type, 'name': 'Unknown'}
        
        # Instantiate and generate
        feature_instance = feature_class(feature)
        return feature_instance.generate_properties(rng)


# Facade stays the same
class FeatureGenerator:
    """Facade for feature generation"""
    
    @staticmethod
    def get_features(celestial: GalaxyCoordinate, 
                     celestial_properties: dict[str, Any] | None = None) -> list[FeatureCoordinate]:
        return FeatureSpawner.get_features(celestial, celestial_properties)
    
    @staticmethod
    def get_feature_properties(feature: FeatureCoordinate) -> dict[str, Any]:
        return FeaturePropertyGenerator.generate(feature)