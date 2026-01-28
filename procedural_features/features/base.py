#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:21:40 2026

@author: sethbruzewski

Abstract base class for all feature types.
Defines the interface that all features must implement.
"""

from abc import ABC, abstractmethod
from ..core.coordinates import FeatureCoordinate
from ..core.rng import RNG
from typing import Any


class Feature(ABC):
    """Base class for all feature types"""
    
    FEATURE_TYPE: str
    DISPLAY_NAME: str | None = None
    PARENT_LEVEL: str | None = None
    SPAWN_CHANCE: float = 0.0
    MIN_COUNT: int = 0
    MAX_COUNT: int = 1
    
    def __init__(self, coordinate: FeatureCoordinate):
        self.coordinate = coordinate
    
    @classmethod
    def can_spawn_at(cls, parent_level: str, parent_props: dict[str, Any]) -> bool:
        """Check if this feature can spawn at this location"""
        return parent_level == cls.PARENT_LEVEL
    
    @abstractmethod
    def generate_properties(self, rng: RNG) -> dict[str, Any]:
        """Generate type-specific properties"""
        pass
    
    def generate_name(self, rng: RNG) -> str:
        """Default name generation"""
        ft = self.FEATURE_TYPE
        assert ft is not None, "Subclass must define FEATURE_TYPE"
        return f"{ft.replace('_', ' ').title()} {self.coordinate.feature_index}"

