#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:16:11 2026

@author: sethbruzewski

Coordinate systems for navigating the procedural galaxy.
Handles hierarchical addressing from tiles down to individual features.
"""

from dataclasses import dataclass

@dataclass
class GalaxyCoordinate:
    """Hierarchical addressing system"""
    tile_x: int
    tile_y: int
    star_index: int | None = None
    planet_index: int | None = None
    
    def __post_init__(self):
        """Validate coordinate"""
        # Cant have planet without star
        if self.has_planet and not self.has_star:
            raise ValueError(
                f"planet_index={self.planet_index} requires star_index"
            )
    
    # Validation methods
    @property
    def has_star(self) -> bool:
        return self.star_index is not None
    
    @property
    def has_planet(self) -> bool:
        return self.planet_index is not None
    
    # Heirarchy helpers
    @property
    def level(self) -> str:
        match (self.has_star, self.has_planet):
            case (False, False): return 'tile'
            case (True, False): return 'star'
            case (True, True): return 'planet'
            case (False, True): raise ValueError # TODO: what do we do here?
    
    def parent(self) -> "GalaxyCoordinate | None":
        match self.level:
            case 'planet': return GalaxyCoordinate(*self.star_coord())
            case 'star': return GalaxyCoordinate(*self.tile_coord())
            case 'tile': return None
            case _: return None # TODO: what do we do here?
    
    def child(self, index: int) -> "GalaxyCoordinate | None":
        match self.level:
            case 'planet': return None
            case 'star': return GalaxyCoordinate(*self.star_coord(), index)
            case 'tile': return GalaxyCoordinate(*self.tile_coord(), index)
            case _: return None # TODO: what do we do here?
    
    # Coord helpers
    def tile_coord(self) -> tuple[int, int]:
        return (self.tile_x, self.tile_y)
    
    def star_coord(self) -> tuple[int, int, int]:
        if self.star_index is None:
            raise ValueError(f"star_coord() called on {self.level}-level coordinate")
        return self.tile_coord() + (self.star_index,)
    
    def planet_coord(self) -> tuple[int, int, int, int]:
        if self.planet_index is None:
            raise ValueError(f"planet_coord() called on {self.level}-level coordinate")
        return self.star_coord() + (self.planet_index,)
    
@dataclass
class FeatureCoordinate:
    """Feature on a celestial object"""
    celestial: GalaxyCoordinate
    feature_index: int
    feature_type: str
    
    # Define what can be where
    _VALID_PARENTS = {
        'city': 'planet',
        'surface_feature': 'planet',
        'station': 'star',
        'asteroid_belt': 'star',
        'nebula': 'tile',
        'anomaly': 'tile'
    }
    
    def __post_init__(self):
        expected_level = self._VALID_PARENTS.get(self.feature_type)
        if expected_level and self.celestial.level != expected_level:
            raise ValueError(
                f"{self.feature_type} must be on {expected_level}, "
                f"not {self.celestial.level}"
            )
    
    def coord_tuple(self) -> tuple[int, ...]:
        """Full coordinate for seeding"""
        if self.celestial.level == 'planet':
            return (*self.celestial.planet_coord(), self.feature_index)
        elif self.celestial.level == 'star':
            return (*self.celestial.star_coord(), self.feature_index)
        else:  # tile
            return (*self.celestial.tile_coord(), self.feature_index)