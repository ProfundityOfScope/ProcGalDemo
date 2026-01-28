#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:30:31 2026

@author: sethbruzewski

Interactive system view for user navigation and selection.
"""

from ..core.coordinates import GalaxyCoordinate, FeatureCoordinate
from .overview import SystemOverview, SystemEntity
from typing import Any
        
class InteractiveSystemView:
    """Handle user interaction with system view"""
    
    def __init__(self, star_coord: GalaxyCoordinate):
        self.root = SystemOverview.generate(star_coord)
        self.current_selection = self.root
    
    def select(self, coordinate: GalaxyCoordinate | FeatureCoordinate):
        """Find and select an entity by coordinate"""
        found = SystemOverview.find_entities(
            self.root,
            filter_fn=lambda e: str(e.coord) == str(coordinate)
        )
        if found:
            self.current_selection = found[0]
            return self.get_detail_view()
        return None
    
    def get_detail_view(self) -> dict[str, Any]:
        """Get detailed view of currently selected entity"""
        entity = self.current_selection
        return {
            'coordinate': entity.coord,
            'type': entity.entity_type,
            'properties': entity.properties,
            'has_children': len(entity.children) > 0,
            'child_count': len(entity.children),
            'parent': entity.coord.parent() if hasattr(entity.coord, 'parent') else None
        }
    
    def get_siblings(self):
        """Get entities at the same level as current selection"""
        # Implementation depends on how you track parent relationships
        pass