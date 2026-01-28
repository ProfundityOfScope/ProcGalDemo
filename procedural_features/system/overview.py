#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:26:42 2026

@author: sethbruzewski

System overview generation - creates hierarchical views of star systems.
"""
from dataclasses import dataclass
from ..core.coordinates import GalaxyCoordinate, FeatureCoordinate
from ..generators.celestial_generator import CelestialGenerator
from ..generators.feature_generator import FeatureGenerator
from typing import Any

@dataclass
class SystemEntity:
    """Represents any entity in the system for display"""
    coord: GalaxyCoordinate | FeatureCoordinate
    entity_type: str  # 'star', 'planet', 'feature'
    properties: dict[str, Any]
    children: list['SystemEntity'] | None = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

class SystemOverview:
    """Generate a complete hierarchical view of a star system"""
    
    @staticmethod
    def generate(star_coord: GalaxyCoordinate) -> SystemEntity:
        """
        Generate complete system overview for a star.
        Returns a tree structure with the star at root.
        """
        assert star_coord.level == 'star', "Must provide star-level coordinate"
        
        # Get star properties
        star_props = CelestialGenerator.get_star_properties(star_coord)
        
        # Create star entity
        star_entity = SystemEntity(
            coord=star_coord,
            entity_type='star',
            properties=star_props,
            children=[]
        )
        
        # Get star-level features (stations, asteroid belts, etc.)
        star_features = FeatureGenerator.get_features(star_coord, star_props)
        for feature in star_features:
            feature_props = FeatureGenerator.get_feature_properties(feature)
            star_entity.children.append(SystemEntity(
                coord=feature,
                entity_type='feature',
                properties=feature_props
            ))
        
        # Get all planets
        planet_count = CelestialGenerator.get_planet_count(star_coord)
        
        for planet_idx in range(planet_count):
            planet_coord = star_coord.child(planet_idx)
            planet_props = CelestialGenerator.get_planet_properties(planet_coord)
            
            planet_entity = SystemEntity(
                coord=planet_coord,
                entity_type='planet',
                properties=planet_props,
                children=[]
            )
            
            # Get planet features (cities, ruins, etc.)
            planet_features = FeatureGenerator.get_features(planet_coord, planet_props)
            for feature in planet_features:
                feature_props = FeatureGenerator.get_feature_properties(feature)
                planet_entity.children.append(SystemEntity(
                    coord=feature,
                    entity_type='feature',
                    properties=feature_props
                ))
            
            star_entity.children.append(planet_entity)
        
        return star_entity
    
    @staticmethod
    def to_dict(entity: SystemEntity) -> dict[str, Any]:
        """Convert system tree to nested dictionary for JSON/display"""
        return {
            'type': entity.entity_type,
            'coordinate': str(entity.coord),
            'properties': entity.properties,
            'children': [SystemOverview.to_dict(child) for child in entity.children]
        }
    
    @staticmethod
    def print_tree(entity: SystemEntity, indent: int = 0):
        """Pretty print the system hierarchy"""
        prefix = "  " * indent
        
        # Format based on entity type
        if entity.entity_type == 'star':
            name = f"⭐ Star (Class {entity.properties.get('spectral_class')})"
            details = f"Mass: {entity.properties.get('mass'):.2f} M☉"
        elif entity.entity_type == 'planet':
            name = f"🪐 Planet {entity.coord.planet_index}"
            ptype = entity.properties.get('type', 'unknown')
            details = f"Type: {ptype}, Radius: {entity.properties.get('orbital_radius', 0):.2f} AU"
            hab_str = '✅' if entity.properties.get('is_habitable', False) else '❌'
            details += f", Habitable: {hab_str}"
        else:  # feature
            ftype = entity.properties.get('type', 'unknown')
            fname = entity.properties.get('name', f'{ftype} {entity.coord.feature_index}')
            name = f"📍 {fname}"
            
            # Type-specific details
            if ftype == 'city':
                pop = entity.properties.get('population', 0)
                details = f"Population: {pop:,}"
            elif ftype == 'station':
                stype = entity.properties.get('station_type', 'unknown')
                details = f"Type: {stype}"
            elif ftype == 'asteroid_belt':
                comp = entity.properties.get('composition', 'unknown')
                details = f"Composition: {comp}"
            else:
                details = f"Type: {ftype}"
        
        print(f"{prefix}{name}")
        print(f"{prefix}  {details}")
        
        # Print children
        for child in entity.children:
            SystemOverview.print_tree(child, indent + 1)
    
    @staticmethod
    def get_summary(entity: SystemEntity) -> dict:
        """Get summary statistics for the system"""
        summary = {
            'total_planets': 0,
            'habitable_planets': 0,
            'total_features': 0,
            'features_by_type': {},
            'total_population': 0
        }
        
        def count_recursive(node: SystemEntity):
            if node.entity_type == 'planet':
                summary['total_planets'] += 1
                if node.properties.get('is_habitable'):
                    summary['habitable_planets'] += 1
            
            elif node.entity_type == 'feature':
                summary['total_features'] += 1
                ftype = node.properties.get('type', 'unknown')
                summary['features_by_type'][ftype] = summary['features_by_type'].get(ftype, 0) + 1
                
                # Add population if city
                if ftype == 'city':
                    summary['total_population'] += node.properties.get('population', 0)
            
            for child in node.children:
                count_recursive(child)
        
        count_recursive(entity)
        return summary
    
    @staticmethod
    def find_entities(entity: SystemEntity, entity_type: str = None, 
                     filter_fn = None) -> list[SystemEntity]:
        """Search the system tree for specific entities"""
        results = []
        
        def search_recursive(node: SystemEntity):
            # Check if this node matches
            matches = True
            if entity_type and node.entity_type != entity_type:
                matches = False
            if filter_fn and not filter_fn(node):
                matches = False
            
            if matches:
                results.append(node)
            
            # Search children
            for child in node.children:
                search_recursive(child)
        
        search_recursive(entity)
        return results