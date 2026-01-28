#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:25:16 2026

@author: sethbruzewski

Central registry of all available feature types.
"""
from typing import List
from .planetary import City, AncientRuin, MiningOperation
from .orbital import OrbitalStation, AsteroidBelt
from .spatial import Nebula, SpaceAnomaly
from .base import Feature

class FeatureRegistry:
    """Registry of all feature types"""
    
    FEATURE_CLASSES: list[type[Feature]] = [
        # Planetary
        City,
        AncientRuin,
        MiningOperation,
        
        # Orbital
        OrbitalStation,
        AsteroidBelt,
        
        # Spatial
        Nebula,
        SpaceAnomaly,
    ]
    
    @classmethod
    def get_feature_class(cls, feature_type: str) -> type[Feature] | None:
        """Get the class for a feature type"""
        for feature_class in cls.FEATURE_CLASSES:
            if feature_class.FEATURE_TYPE == feature_type:
                return feature_class
        return None
    
    @classmethod
    def get_features_for_level(cls, parent_level: str) -> List[type[Feature]]:
        """Get all feature classes that can spawn at this level"""
        return [fc for fc in cls.FEATURE_CLASSES if fc.PARENT_LEVEL == parent_level]