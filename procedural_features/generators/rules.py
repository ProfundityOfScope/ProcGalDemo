#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generation rule system for complex interdependent procedural generation.

Rules allow you to modify generation based on context, enabling realistic
relationships between celestial bodies and features.

Example:
    >>> engine = create_default_rule_engine()
    >>> CelestialGenerator.set_rule_engine(engine)
    >>> # Now planets will respect habitable zones, old stars, etc.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class GenerationRule(ABC):
    """Base class for generation rules"""
    
    @abstractmethod
    def applies_to(self, context: Dict[str, Any]) -> bool:
        """Check if this rule applies to the current context"""
        pass
    
    @abstractmethod
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Modify properties based on the rule"""
        pass
    
    @property
    def priority(self) -> int:
        """Priority for rule application (higher = earlier). Default 0."""
        return 0


class HabitableZoneRule(GenerationRule):
    """
    Planets must be in habitable zone to be habitable.
    
    This is the most important rule for realistic planet generation.
    Too close to star = too hot, too far = too cold.
    """
    
    @property
    def priority(self) -> int:
        return 100  # High priority
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        return (context.get('entity_type') == 'planet' and 
                context.get('star_props') is not None and
                'orbital_radius' in context.get('properties', {}))
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        star_props = context['star_props']
        orbital_radius = properties['orbital_radius']
        
        # Calculate habitable zone based on star luminosity
        luminosity = self._calculate_luminosity(star_props)
        inner_hz = (luminosity / 1.1) ** 0.5
        outer_hz = (luminosity / 0.53) ** 0.5
        
        # Only rocky planets can be habitable
        if properties['type'] == 'rocky':
            in_hz = inner_hz <= orbital_radius <= outer_hz
            
            # If not in HZ, definitely not habitable
            if not in_hz:
                properties['is_habitable'] = False
                if orbital_radius < inner_hz:
                    properties['habitability_notes'] = 'Too hot - inside habitable zone'
                else:
                    properties['habitability_notes'] = 'Too cold - outside habitable zone'
            # If in HZ, keep existing habitability determination
            # (other factors like atmosphere can still make it uninhabitable)
        else:
            properties['is_habitable'] = False
        
        # Store HZ info for debugging/display
        properties['habitable_zone'] = {
            'inner': round(inner_hz, 2),
            'outer': round(outer_hz, 2),
            'in_zone': inner_hz <= orbital_radius <= outer_hz
        }
        
        return properties
    
    @staticmethod
    def _calculate_luminosity(star_props: Dict[str, Any]) -> float:
        """Calculate luminosity from spectral class and mass"""
        mass = star_props.get('mass', 1.0)
        
        # Mass-luminosity relation: L ∝ M^3.5 (approximation)
        # This is simplified; real relation varies by mass range
        if mass < 0.43:
            luminosity = 0.23 * (mass ** 2.3)
        elif mass < 2:
            luminosity = mass ** 4
        elif mass < 55:
            luminosity = 1.4 * (mass ** 3.5)
        else:
            luminosity = 32000 * mass
        
        return luminosity


class OldStarRule(GenerationRule):
    """
    Old stars (>10 Gyr) are less likely to have habitable planets.
    Stellar radiation over time can strip atmospheres.
    """
    
    @property
    def priority(self) -> int:
        return 50  # Medium priority, after HZ check
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        return (context.get('entity_type') == 'planet' and 
                context.get('star_props', {}).get('age', 0) > 10)
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        star_age = context['star_props'].get('age', 0)
        
        # Reduce habitability for old stars
        if properties.get('is_habitable'):
            rng = context.get('rng')
            if rng:
                # Probability increases with age
                uninhabitable_chance = min(0.8, (star_age - 10) * 0.1)
                
                if rng.random() < uninhabitable_chance:
                    properties['is_habitable'] = False
                    properties['habitability_notes'] = f'Star too old ({star_age:.1f} Gyr) - atmosphere stripped'
        
        return properties


class YoungStarRule(GenerationRule):
    """
    Very young stars (<0.5 Gyr) unlikely to have developed life.
    Planet formation may still be ongoing.
    """
    
    @property
    def priority(self) -> int:
        return 50
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        return (context.get('entity_type') == 'planet' and 
                context.get('star_props', {}).get('age', 0) < 0.5)
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if properties.get('is_habitable'):
            rng = context.get('rng')
            if rng and rng.random() < 0.7:  # 70% chance to be uninhabitable
                properties['is_habitable'] = False
                properties['habitability_notes'] = 'Star too young - planets still forming'
        
        return properties


class MetallicityRule(GenerationRule):
    """
    Higher metallicity stars = more rocky planets and resources.
    Lower metallicity = more gas giants.
    """
    
    @property
    def priority(self) -> int:
        return 80  # High priority, affects planet type
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        return context.get('entity_type') == 'planet'
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        star_props = context.get('star_props', {})
        metallicity = star_props.get('metallicity', 0)
        rng = context.get('rng')
        
        if not rng:
            return properties
        
        # High metallicity favors rocky planets
        if metallicity > 0.2 and properties['type'] == 'gas_giant':
            # Small chance to convert to rocky
            if rng.random() < 0.2:
                properties['type'] = 'rocky'
                properties['mass'] = rng.uniform(0.5, 10.0)  # Adjust mass
        
        # Low metallicity makes rocky planets less likely to be habitable
        if metallicity < -1.0 and properties.get('is_habitable'):
            if rng.random() < 0.3:
                properties['is_habitable'] = False
                properties['habitability_notes'] = 'Low metallicity - insufficient heavy elements'
        
        return properties


class GasGiantNeighborRule(GenerationRule):
    """
    Gas giants can protect inner rocky planets from asteroids (Jupiter effect).
    But very close gas giants can disrupt orbits.
    """
    
    @property
    def priority(self) -> int:
        return 30  # Lower priority
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        # Need to know about sibling planets - this is more complex
        # For now, just a placeholder
        return False
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Future: check if there's a gas giant in outer orbit
        # If yes, slightly increase habitability
        return properties


class HighMetallicityCitiesRule(GenerationRule):
    """
    Higher metallicity stars = more resources = higher tech civilizations.
    """
    
    @property
    def priority(self) -> int:
        return 10
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        return context.get('feature_type') == 'city'
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        star_props = context.get('star_props', {})
        metallicity = star_props.get('metallicity', 0)
        
        # Modify tech level based on metallicity
        current_tech = properties.get('tech_level', 5)
        
        if metallicity > 0.2:
            # High metallicity = +2 tech levels
            properties['tech_level'] = min(10, current_tech + 2)
        elif metallicity > 0.0:
            # Moderate metallicity = +1
            properties['tech_level'] = min(10, current_tech + 1)
        elif metallicity < -1.0:
            # Low metallicity = -2 tech levels
            properties['tech_level'] = max(1, current_tech - 2)
        
        return properties


class DenseSystemStationsRule(GenerationRule):
    """
    Systems with many planets are more likely to have stations.
    """
    
    @property
    def priority(self) -> int:
        return 10
    
    def applies_to(self, context: Dict[str, Any]) -> bool:
        return context.get('feature_type') == 'station'
    
    def apply(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # This would need planet count in context
        # Just a placeholder for now
        return properties


class RuleEngine:
    """
    Manages and applies generation rules in priority order.
    
    Example:
        >>> engine = RuleEngine()
        >>> engine.add_rule(HabitableZoneRule())
        >>> engine.add_rule(OldStarRule())
        >>> 
        >>> properties = {'type': 'rocky', 'is_habitable': True}
        >>> context = {'entity_type': 'planet', 'star_props': {...}}
        >>> properties = engine.apply_rules(properties, context)
    """
    
    def __init__(self):
        self.rules: List[GenerationRule] = []
    
    def add_rule(self, rule: GenerationRule):
        """Add a rule to the engine"""
        self.rules.append(rule)
        # Sort by priority (higher first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def apply_rules(self, properties: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all applicable rules to properties.
        
        Args:
            properties: The properties to modify
            context: Additional context (star props, coordinates, etc.)
        
        Returns:
            Modified properties dict
        """
        # Add properties to context so rules can see them
        context['properties'] = properties
        
        for rule in self.rules:
            try:
                if rule.applies_to(context):
                    properties = rule.apply(properties, context)
                    # Update context with new properties
                    context['properties'] = properties
            except Exception as e:
                logger.error(f"Error applying rule {rule.__class__.__name__}: {e}")
                # Continue with other rules
        
        return properties


def create_default_rule_engine() -> RuleEngine:
    """
    Create a rule engine with standard realistic rules.
    
    Returns:
        RuleEngine configured with default rules
    """
    engine = RuleEngine()
    
    # Add all standard rules
    engine.add_rule(HabitableZoneRule())
    engine.add_rule(OldStarRule())
    engine.add_rule(YoungStarRule())
    engine.add_rule(MetallicityRule())
    engine.add_rule(HighMetallicityCitiesRule())
    
    return engine


def create_minimal_rule_engine() -> RuleEngine:
    """
    Create a rule engine with only the most essential rules.
    Use this for better performance if you don't need full realism.
    """
    engine = RuleEngine()
    engine.add_rule(HabitableZoneRule())
    return engine


def create_hardcore_rule_engine() -> RuleEngine:
    """
    Create a rule engine with many strict rules for maximum realism.
    This will reduce the number of habitable planets significantly.
    """
    engine = create_default_rule_engine()
    
    # Could add more strict rules here
    # For example: binary star instability, high radiation zones, etc.
    
    return engine
