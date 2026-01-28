#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:25:56 2026

@author: sethbruzewski

Demo script showing how to use the galaxy generator.
"""

from procedural_features import (
    GalaxyCoordinate,
    CelestialGenerator,
    SystemOverview,
    InteractiveSystemView
)


def explore(tx: int, ty: int, star_selection: int):
    print("=" * 60)
    print("PROCEDURAL GALAXY EXPLORER - DEMO")
    print("=" * 60)
    
    # User navigates to tile (5, 7)
    print("\n📍 Navigating to Tile (5, 7)...")
    tile_coord = GalaxyCoordinate(tx, ty)
    
    # Check how many stars in this tile
    star_count = CelestialGenerator.get_star_count(tile_coord)
    print(f"   Found {star_count} stars in this tile")
    
    # User clicks on star #42
    print(f"\n⭐ Examining Star #{star_selection}...")
    star_coord = tile_coord.child(star_selection)
    
    # Create interactive view
    system_view = InteractiveSystemView(star_coord)
    
    # Show the full system hierarchy
    print("\n" + "=" * 60)
    print("SYSTEM HIERARCHY")
    print("=" * 60)
    SystemOverview.print_tree(system_view.root)
    
    # Get summary statistics
    print("\n" + "=" * 60)
    print("SYSTEM SUMMARY")
    print("=" * 60)
    summary = SystemOverview.get_summary(system_view.root)
    print(f"Total Planets: {summary['total_planets']}")
    print(f"Habitable Planets: {summary['habitable_planets']}")
    print(f"Total Features: {summary['total_features']}")
    print(f"Total Population: {summary['total_population']:,}")
    if summary['features_by_type']:
        print("Feature Types:")
        for ftype, count in summary['features_by_type'].items():
            print(f"  - {ftype}: {count}")
    
    # Find all cities
    cities = SystemOverview.find_entities(
        system_view.root,
        filter_fn=lambda e: e.entity_type == 'feature' and 
                            e.properties.get('type') == 'city'
    )
    
    if cities:
        print(f"\n🏙️  Found {len(cities)} cities in system:")
        for city_entity in cities:
            props = city_entity.properties
            planet_idx = city_entity.coord.celestial.planet_index
            print(f"   - {props['name']} (Planet {planet_idx}): "
                  f"Pop {props['population']:,}, Tech Level {props['tech_level']}")
        
        # User clicks on first city
        first_city = cities[0]
        print(f"\n🔍 Examining {first_city.properties['name']} in detail...")
        detail = system_view.select(first_city.coord)
        print(f"   Type: {detail['type']}")
        print("   Properties:")
        for key, value in detail['properties'].items():
            if key != 'name':  # Already showed name
                print(f"      {key}: {value}")
    
    # Find stations
    stations = SystemOverview.find_entities(
        system_view.root,
        filter_fn=lambda e: e.entity_type == 'feature' and 
                            e.properties.get('type') == 'station'
    )
    
    if stations:
        print(f"\n🛰️  Found {len(stations)} orbital stations:")
        for station_entity in stations:
            props = station_entity.properties
            print(f"   - {props['name']}: {props['station_type']} station, "
                  f"Capacity {props['crew_capacity']}")
    
    # User wants to explore a specific planet
    if summary['total_planets'] > 0:
        planet_idx = 1 if summary['total_planets'] > 1 else 0
        planet_coord = star_coord.child(planet_idx)
        print(f"\n🪐 Examining Planet {planet_idx} in detail...")
        
        planet_entity = SystemOverview.find_entities(
            system_view.root,
            filter_fn=lambda e: e.entity_type == 'planet' and 
                                e.coord.planet_index == planet_idx
        )[0]
        
        props = planet_entity.properties
        print(f"   Type: {props['type']}")
        print(f"   Orbital Radius: {props['orbital_radius']:.2f} AU")
        print(f"   Mass: {props['mass']:.2f} M⊕")
        print(f"   Habitable: {'Yes' if props.get('is_habitable') else 'No'}")
        
        if planet_entity.children:
            print(f"   Features on this planet ({len(planet_entity.children)}):")
            for feature in planet_entity.children:
                fprops = feature.properties
                print(f"      - {fprops['name']} ({fprops['type']})")
    
    # Test navigation - go back to parent
    print("\n⬆️  Navigating back to star level...")
    parent = planet_coord.parent()
    print(f"   Current level: {parent.level}")
    print(f"   Coordinate: {parent}")
    
    # Show we can always come back to the same data
    print("\n" + "=" * 60)
    print("DETERMINISM TEST")
    print("=" * 60)
    print("Regenerating the same star system...")
    system_view_2 = InteractiveSystemView(star_coord)
    summary_2 = SystemOverview.get_summary(system_view_2.root)
    
    print(f"   First generation: {summary['total_planets']} planets, {summary['total_features']} features")
    print(f"   Second generation: {summary_2['total_planets']} planets, {summary_2['total_features']} features")
    print(f"   ✓ Identical: {summary == summary_2}")
    
    print("\n" + "=" * 60)
    print("EXPLORATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    explore(1, 1, 108)