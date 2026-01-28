# Procedural Galaxy

Spatial indexing system for efficiently rendering large-scale galaxy maps with dynamic level-of-detail.

> **Note**: This version of the documentation was AI-generated based on code analysis and may not reflect all implementation details or recent changes. It will eventually be replaced with human-generated docs. Refer to the source code for authoritative information.

## What It Does

Uses a quadtree structure to partition galaxy space and render only visible regions at appropriate detail levels. Supports rotated viewports and seamless zoom from galaxy-wide views down to individual star systems.

```python
# Create a quadtree covering galaxy space
tree = QuadTree.from_center(cx=0.0, cy=0.0, hw=512.0, hh=512.0)

# Define a rotated viewport
viewport = OrientedRect(
    cx=10.0, cy=96.0,
    hw=90.0, hh=160.0,
    theta_rad=math.radians(30.0)
)

# Query visible nodes at current zoom level
visited = tree.update(viewport)
```

## Features

- **Adaptive Level-of-Detail**: Automatically selects appropriate quadtree depth based on viewport zoom
- **Rotatable Viewports**: Oriented bounding box (OBB) intersection tests for arbitrary camera rotation
- **Procedural Stars**: Deterministic star generation per quadtree cell using coordinate-based seeding
- **Efficient Culling**: SAT-based intersection tests minimize rendered geometry

## Core Components

**QuadTree**: Hierarchical spatial partition with lazy node expansion
**OrientedRect**: Rotatable viewport with OBB-AABB intersection
**StarStub**: Minimal star representation for rendering (position, brightness, ID)

## Visualization

Dual-view rendering system:
- **World view**: Shows quadtree structure and viewport bounds in galaxy coordinates
- **Camera view**: Renders stars as they appear in the rotated viewport

## Performance

Nodes are generated on-demand and cached. Star data is procedurally generated per cell using deterministic seeding, eliminating storage requirements while maintaining consistency across frames.

## Technical Notes

- AABB cells for quadtree structure (axis-aligned)
- OBB viewport for rotation support (oriented)
- Separating Axis Theorem for intersection tests
- Smoothstep interpolation for LOD transitions

---

Spatial indexing for procedural galaxy rendering.