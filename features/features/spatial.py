#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:24:44 2026

@author: sethbruzewski

Features that exist in open space at the tile level.
Includes nebulae, anomalies, etc.
"""

from .base import Feature
from ..core.rng import RNG
from typing import Any

class Nebula(Feature):
    """Space nebulae in tiles"""
    
    FEATURE_TYPE = 'nebula'
    DISPLAY_NAME = 'Nebula'
    PARENT_LEVEL = 'tile'
    SPAWN_CHANCE = 0.05
    MIN_COUNT = 0
    MAX_COUNT = 1
    
    def generate_properties(self, rng: RNG) -> dict[str, Any]:
        return {
            'type': self.FEATURE_TYPE,
            'display_name': self.DISPLAY_NAME,
            'name': self.generate_name(rng),
            'nebula_type': rng.choice(['emission', 'reflection', 'dark', 'planetary']),
            'color': rng.choice(['red', 'blue', 'green', 'purple', 'orange', 'pink']),
            'size': rng.uniform(1.0, 10.0),  # light years
            'density': rng.choice(['sparse', 'moderate', 'dense']),
            'ionization': rng.uniform(0.0, 1.0),
        }
    
    def generate_name(self, rng: RNG) -> str:
        """Generate nebula name"""
        prefixes = ['The', 'Great', 'Little', 'Dark', 'Bright']
        names = ['Eagle', 'Horsehead', 'Crab', 'Ring', 'Helix', 'Orion', 
                'Carina', 'Tarantula', 'Veil', 'Rosette']
        suffixes = ['Nebula', 'Cloud', 'Complex']
        
        if rng.random() < 0.3:
            return f"{rng.choice(names)} {rng.choice(suffixes)}"
        else:
            return f"{rng.choice(prefixes)} {rng.choice(names)} {rng.choice(suffixes)}"


class SpaceAnomaly(Feature):
    """Strange phenomena in space"""
    
    FEATURE_TYPE = 'anomaly'
    DISPLAY_NAME = 'Space Anomaly'
    PARENT_LEVEL = 'tile'
    SPAWN_CHANCE = 0.02
    MIN_COUNT = 0
    MAX_COUNT = 1
    
    def generate_properties(self, rng: RNG) -> dict[str, Any]:
        anomaly_type = rng.choice(['temporal', 'gravitational', 'energy', 
                                  'wormhole', 'quantum', 'dimensional'])
        
        # Different properties based on type
        props: dict[str, Any] = {
            'type': self.FEATURE_TYPE,
            'display_name': self.DISPLAY_NAME,
            'name': self.generate_name(rng, anomaly_type),
            'anomaly_type': anomaly_type,
            'danger_level': rng.randint(1, 10),
            'size': rng.uniform(0.1, 5.0),  # AU
            'stability': rng.choice(['stable', 'fluctuating', 'unstable', 'critical']),
        }
        
        # Type-specific properties
        if anomaly_type == 'wormhole':
            props['destination_known'] = rng.choice([True, False])
            props['traversable'] = rng.choice([True, False])
        elif anomaly_type == 'temporal':
            props['time_dilation_factor'] = rng.uniform(0.5, 2.0)
        elif anomaly_type == 'gravitational':
            props['gravity_multiplier'] = rng.uniform(0.1, 10.0)
        
        return props
    
    def generate_name(self, rng: RNG, anomaly_type: str | None = None) -> str:
        """Generate anomaly name based on type"""
        type_prefixes = {
            'temporal': ['Temporal', 'Chrono', 'Time'],
            'gravitational': ['Gravity', 'Mass', 'Singularity'],
            'energy': ['Energy', 'Plasma', 'Radiation'],
            'wormhole': ['Wormhole', 'Gateway', 'Portal'],
            'quantum': ['Quantum', 'Probability', 'Superposition'],
            'dimensional': ['Dimensional', 'Rift', 'Tear'],
        }
        
        suffixes = ['Anomaly', 'Distortion', 'Phenomenon', 'Rift', 'Field']
        
        if anomaly_type and anomaly_type in type_prefixes:
            prefix = rng.choice(type_prefixes[anomaly_type])
        else:
            prefix = rng.choice(['Unknown', 'Strange', 'Mysterious'])
        
        # Sometimes add a designation
        if rng.random() < 0.5:
            designation = rng.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon'])
            return f"{prefix} {rng.choice(suffixes)} {designation}"
        
        return f"{prefix} {rng.choice(suffixes)}"
