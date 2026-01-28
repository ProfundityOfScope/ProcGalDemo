#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:29:27 2026

@author: sethbruzewski

Adapts system data for UI display.
Converts raw game data into UI-friendly formats.
"""

from dataclasses import dataclass
from typing import Any
from .overview import SystemEntity

@dataclass
class SystemDisplayNode:
    """Simplified display-friendly format"""
    id: str  # Unique identifier
    name: str
    type: str
    icon: str  # emoji or icon name
    details: list[tuple[str, str]]  # [(label, value), ...]
    children: list['SystemDisplayNode']
    coordinate: Any  # Store for click handling
    
class SystemUIAdapter:
    """Convert system tree to UI-friendly format"""
    
    @staticmethod
    def to_display_tree(entity: SystemEntity) -> SystemDisplayNode:
        """Convert to display format"""
        
        if entity.entity_type == 'star':
            return SystemDisplayNode(
                id=str(entity.coord),
                name="Star System",
                type='star',
                icon='⭐',
                details=[
                    ('Class', entity.properties.get('spectral_class')),
                    ('Mass', f"{entity.properties.get('mass'):.2f} M☉"),
                    ('Age', f"{entity.properties.get('age'):.1f} Gyr"),
                ],
                children=[SystemUIAdapter.to_display_tree(c) for c in entity.children],
                coordinate=entity.coord
            )
        
        elif entity.entity_type == 'planet':
            props = entity.properties
            return SystemDisplayNode(
                id=str(entity.coord),
                name=f"Planet {entity.coord.planet_index + 1}",
                type=props.get('type', 'unknown'),
                icon='🪐' if props.get('type') != 'gas_giant' else '🌍',
                details=[
                    ('Type', props.get('type')),
                    ('Orbit', f"{props.get('orbital_radius'):.2f} AU"),
                    ('Mass', f"{props.get('mass'):.2f} M⊕"),
                    ('Habitable', 'Yes' if props.get('is_habitable') else 'No'),
                ],
                children=[SystemUIAdapter.to_display_tree(c) for c in entity.children],
                coordinate=entity.coord
            )
        
        else:  # feature
            props = entity.properties
            ftype = props.get('type')
            
            icons = {
                'city': '🏙️',
                'station': '🛰️',
                'asteroid_belt': '☄️',
                'ancient_ruin': '🏛️',
                'mining_site': '⛏️',
                'nebula': '🌌',
                'anomaly': '❓'
            }
            
            details = [('Type', ftype)]
            if ftype == 'city':
                details.extend([
                    ('Population', f"{props.get('population'):,}"),
                    ('Tech Level', str(props.get('tech_level'))),
                ])
            elif ftype == 'station':
                details.extend([
                    ('Station Type', props.get('station_type')),
                    ('Capacity', str(props.get('crew_capacity'))),
                ])
            
            return SystemDisplayNode(
                id=str(entity.coord),
                name=props.get('name', f'{ftype} {entity.coord.feature_index}'),
                type=ftype,
                icon=icons.get(ftype, '📍'),
                details=details,
                children=[],
                coordinate=entity.coord
            )