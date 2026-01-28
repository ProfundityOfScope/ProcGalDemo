"""
dumb_quadtree_demo_rotated_viewport.py

Same dumb procedural quadtree demo, but the "screen"/viewport can be ROTATED.

- Quadtree cells are axis-aligned (AABB).
- Viewport is an oriented rectangle (OBB): center + half-sizes + angle.

We select cells at EXACTLY a given depth that either:
  - INTERSECT the rotated viewport   (contained=False)   [usually what you want]
  - are FULLY CONTAINED by it        (contained=True)

Visualization:
  - selected cells (white)
  - rotated viewport (yellow)

No interactivity. Edit constants at bottom and run.
"""

from dataclasses import dataclass, field
from typing import Callable
import math

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle
import matplotlib.animation as animation
import matplotlib.patheffects as path_effects

import myrand


GLOBAL_SEED = 8675309

# ----------------------------
# Star Stuff
# ----------------------------

@dataclass(frozen=True)
class StarStub:
    starID: int
    position: tuple[float, float]
    brightness: float  # This will generally be in the range 0-1, combined with depth
    
    @property
    def x(self): return self.position[0]
    @property
    def y(self): return self.position[1]
    @property
    def r(self): return self.x*self.x + self.y*self.y


# ----------------------------
# Axis-aligned rectangles (quadtree cells / world root)
# ----------------------------

@dataclass(frozen=True)
class Rect:
    cx: float
    cy: float
    hw: float
    hh: float

    @property
    def xmin(self): return self.cx - self.hw
    @property
    def xmax(self): return self.cx + self.hw
    @property
    def ymin(self): return self.cy - self.hh
    @property
    def ymax(self): return self.cy + self.hh
    @property
    def w(self): return 2 * self.hw
    @property
    def h(self): return 2 * self.hh

    def corners(self) -> list[tuple[float, float]]:
        return [
            (self.xmin, self.ymin),
            (self.xmin, self.ymax),
            (self.xmax, self.ymax),
            (self.xmax, self.ymin),
        ]

    def quadrants(self) -> tuple["Rect", "Rect", "Rect", "Rect"]:
        # NW, NE, SW, SE
        qhw, qhh = self.hw / 2, self.hh / 2
        return (
            Rect(self.cx - qhw, self.cy + qhh, qhw, qhh),
            Rect(self.cx + qhw, self.cy + qhh, qhw, qhh),
            Rect(self.cx - qhw, self.cy - qhh, qhw, qhh),
            Rect(self.cx + qhw, self.cy - qhh, qhw, qhh),
        )


# ----------------------------
# Oriented viewport rectangle (rotatable "screen")
# ----------------------------

@dataclass(frozen=True)
class OrientedRect:
    """
    Center (cx, cy), half sizes (hw, hh), rotation angle theta_rad (CCW).
    """
    cx: float
    cy: float
    hw: float
    hh: float
    theta_rad: float

    def _axes(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """
        Return unit vectors for the rectangle's local x-axis (u) and y-axis (v),
        expressed in world coordinates.
        """
        c = math.cos(self.theta_rad)
        s = math.sin(self.theta_rad)
        u = (c, s)      # local +x
        v = (-s, c)     # local +y
        return u, v

    def corners(self) -> list[tuple[float, float]]:
        """
        The 4 corners in CCW order.
        """
        u, v = self._axes()
        cx, cy = self.cx, self.cy

        def add(ax, ay, bx, by): return (ax + bx, ay + by)
        def mul(a, k): return (a[0] * k, a[1] * k)

        du = mul(u, self.hw)
        dv = mul(v, self.hh)

        # corners: c +/- du +/- dv
        c0 = add(cx, cy, -du[0] - dv[0], -du[1] - dv[1])
        c1 = add(cx, cy, -du[0] + dv[0], -du[1] + dv[1])
        c2 = add(cx, cy, +du[0] + dv[0], +du[1] + dv[1])
        c3 = add(cx, cy, +du[0] - dv[0], +du[1] - dv[1])
        return [c0, c1, c2, c3]
    
    def to_local(self, x: float, y: float) -> tuple[float, float]:
        # translate
        dx = x - self.cx
        dy = y - self.cy

        # rotate by -theta
        c = math.cos(self.theta_rad)
        s = math.sin(self.theta_rad)

        lx =  c * dx + s * dy
        ly = -s * dx + c * dy
        return lx, ly

    def to_world(self, lx: float, ly: float) -> tuple[float, float]:
        
        c = math.cos(self.theta_rad)
        s = math.sin(self.theta_rad)

        # rotate by +theta
        dx = c * lx - s * ly
        dy = s * lx + c * ly

        # translate back
        x = dx + self.cx
        y = dy + self.cy
        return x, y

    def aabb_bounds(self) -> Rect:
        """
        Axis-aligned bounding box of the rotated viewport (useful for plot limits).
        """
        cs = self.corners()
        xs = [p[0] for p in cs]
        ys = [p[1] for p in cs]
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        return Rect(cx=0.5 * (xmin + xmax), cy=0.5 * (ymin + ymax),
                    hw=0.5 * (xmax - xmin), hh=0.5 * (ymax - ymin))

    def contains_point(self, x: float, y: float) -> bool:
        """
        Point-in-OBB test:
        transform point into viewport local coords and check extents.
        """
        u, v = self._axes()
        dx, dy = x - self.cx, y - self.cy

        # local coords are dot products with u, v
        lx = dx * u[0] + dy * u[1]
        ly = dx * v[0] + dy * v[1]
        return (abs(lx) <= self.hw) and (abs(ly) <= self.hh)

    def contains_aabb(self, aabb: Rect) -> bool:
        """
        Fully contained if ALL aabb corners are inside the oriented viewport.
        """
        return all(self.contains_point(x, y) for (x, y) in aabb.corners())

    def intersects_aabb(self, aabb: Rect) -> bool:
        """
        OBB vs AABB intersection via Separating Axis Theorem (SAT).

        Axes to test for rectangle-rectangle in 2D:
          - AABB's axes: (1,0), (0,1)
          - OBB's axes: u, v
        If projections overlap on all axes -> intersect.
        """
        u, v = self._axes()
        axes = [(1.0, 0.0), (0.0, 1.0), u, v]

        # Helpers: project rectangle onto an axis and return [min, max] interval.
        def dot(ax, ay, bx, by): return ax * bx + ay * by

        def proj_aabb(axis, r: Rect) -> tuple[float, float]:
            ax, ay = axis
            # center projection
            c = dot(r.cx, r.cy, ax, ay)
            # radius projection: hw*|axis·(1,0)| + hh*|axis·(0,1)|
            rad = r.hw * abs(ax) + r.hh * abs(ay)
            return (c - rad, c + rad)

        def proj_obb(axis, r: OrientedRect) -> tuple[float, float]:
            ax, ay = axis
            # center projection
            c = dot(r.cx, r.cy, ax, ay)
            # radius: hw*|axis·u| + hh*|axis·v|
            ux, uy = u
            vx, vy = v
            rad = r.hw * abs(dot(ux, uy, ax, ay)) + r.hh * abs(dot(vx, vy, ax, ay))
            return (c - rad, c + rad)

        def overlap(i1, i2) -> bool:
            return not (i1[1] < i2[0] or i2[1] < i1[0])

        for axis in axes:
            if not overlap(proj_aabb(axis, aabb), proj_obb(axis, self)):
                return False
        return True


# ----------------------------
# Actual quadtree stuff I guess
# ----------------------------

StopPredicate = Callable[["QuadNode", "OrientedRect"], bool]

@dataclass
class QuadNode:
    rect: Rect
    depth: int
    path: tuple[int, ...] = ()
    
    children: tuple["QuadNode", "QuadNode", "QuadNode", "QuadNode"] | None = None
    stars: list[StarStub] | None = None
    
    # --- tree management ---
    
    def subdivide(self) -> None:
        if self.children is not None:
            return
        
        self.children = tuple(
            QuadNode(
                rect=child_rect,
                depth=self.depth+1,
                path=self.path+(i,),
            ) for i,child_rect in enumerate(self.rect.quadrants())
        )
        
    @property
    def tileID(self) -> int:
        return myrand.tile_key(GLOBAL_SEED, *self.node_key)
        
    @property
    def is_leaf(self) -> bool:
        return self.children is None
    
    @property
    def node_position(self) -> tuple[int, int]:
        # Simple method to convert path into grid coords
        x = y = 0
        for step in self.path:
            xb = step & 1
            yb = (step >> 1) & 1
            x = (x << 1) | xb
            y = (y << 1) | yb
            
        return (x, y)
    
    @property
    def node_key(self) -> tuple[int, int, int]:
        # Get a tile key we could hash
        return (self.depth, *self.node_position)
    
    @property
    def morton_code(self) -> int:
        # Uses node properties to derive Morton code
        x, y = self.node_position
        
        code = 0
        for i in range(self.depth):
            code |= ((x >> i) & 1) << (2 * i)
            code |= ((y >> i) & 1) << (2 * i + 1)
        return code
    
    # --- traversal ---
    
    def traverse(self, viewport: OrientedRect, *, 
                 stop: StopPredicate,
                 visited: list["QuadNode"] | None = None,
                 max_depth: int | None = None):
        
        # Prune entire branch if no intersection
        if not viewport.intersects_aabb(self.rect):
            self.children = None
            return
        
        # If we do intersect, record this one
        if visited is not None:
            visited.append(self)
        
        # Stopping behavior
        should_stop = stop(self, viewport)
        if max_depth is not None and self.depth >= max_depth:
            should_stop = True
            
        if should_stop:
            self.children = None
            return
        
        # Otherwise, recurse
        if self.children is None:
            self.subdivide()

        for child in self.children:
            child.traverse(
                viewport,
                stop=stop,
                visited=visited,
                max_depth=max_depth,
            )
            
    # --- randomness ---
    
    def generate_stars(self) -> list[StarStub]:
        
        if self.stars is None:
            # How many to draw
            n_expected = int(5**self.depth / 4**self.depth)
            variation = int((myrand.u01(self.tileID, 0xFADECAFE) - 0.5) * n_expected * 0.3)
            n = max(1, n_expected+variation) # TODO: We need a Poisson here eventually
            
            seed = self.tileID
            stars_local = [ 
                StarStub(
                    starID=myrand.star_id(seed, i),
                    position=(
                        self.rect.cx + (myrand.u01(seed, 2*i)-0.5) * self.rect.w,
                        self.rect.cy + (myrand.u01(seed, 2*i+1)-0.5) * self.rect.h
                    ),
                    brightness=myrand.u01(seed, i)
                ) for i in range(n) 
            ]
            # Cache those
            self.stars = stars_local
        
        return self.stars
        

@dataclass
class QuadTree:
    root: QuadNode

    # LOD knob: "aim for ~N cells across the smallest viewport dimension"
    cells_across: int 

    # Optional hard clamp so you don't go wild when zoomed way in/out.
    min_depth: int = 0
    max_depth: int = 20 # Roughly matches Google kind of

    # Star stuff
    TileCache: dict = field(default_factory=dict)

    @classmethod
    def from_center(cls, cx: float, cy: float, hw: float, hh: float, 
                    cells_across: int = 4) -> "QuadTree":
        rect = Rect(cx, cy, hw, hh)
        qnode = QuadNode(rect, depth=0)
        return cls(qnode, cells_across=cells_across)
    
    def update(self, viewport: OrientedRect, *,
               stop: StopPredicate | None = None) -> list[QuadNode]:
        
        # Figure out stop
        if stop is None:
            stop = self.default_stop_predicate(viewport)
        
        visited: list[QuadNode] = []
        
        # Do traversal
        self.root.traverse(
            viewport,
            stop=stop,
            visited=visited,
            max_depth=self.max_depth
        )
        
        return visited
    
    def pseudo_depth(self, viewport: OrientedRect) -> float:
        
        # Get viewport scale
        vmin = min(viewport.hw, viewport.hh) * 2
        
        # Get root scale
        root_size = max(self.root.rect.w, self.root.rect.h)
        
        ratio = (root_size * float(self.cells_across)) / max(1e-9, vmin)
        pdepth = math.log2(ratio)
        return pdepth
    
    def desired_depth(self, viewport: OrientedRect) -> int:
        
        pdepth_int = int(math.ceil(self.pseudo_depth(viewport)))
        d_clamp = max(self.min_depth, min(self.max_depth, pdepth_int))
        return d_clamp
    
    def default_stop_predicate(self, viewport: OrientedRect) -> StopPredicate:
        target_depth = self.desired_depth(viewport)
        
        def stop(node: QuadNode, _vp: OrientedRect) -> bool:
            return node.depth >= target_depth or node.depth >= self.max_depth
        
        return stop
    
    def pprint(self, max_depth: int | None = None) -> None:
        """
        Pretty-print the quadtree hierarchy.

        max_depth:
            Optional cutoff so you don't explode the terminal.
        """

        def rec(node: QuadNode, indent: int) -> None:
            if max_depth is not None and node.depth > max_depth:
                return

            pad = "  " * indent
            print(f"{pad}- depth={node.depth}, path={node.path}")

            if node.children is not None:
                for child in node.children:
                    rec(child, indent + 1)

        rec(self.root, 0)
        
    def debug(self, max_depth: int | None = None) -> str:
        
        def rec(node: QuadNode, tracker: dict) -> None:
            if max_depth is not None and node.depth > max_depth:
                return
            
            if node.depth not in tracker:
                tracker[node.depth] = 0
            tracker[node.depth] += 1
            
            if node.children is not None:
                for child in node.children:
                    rec(child, tracker)
            
        debug = {}
        rec(self.root, debug)
        return debug


# ----------------------------
# Matplotlib visualization
# ----------------------------

def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def draw_aabb(ax, r: Rect, *, color="k", lw=1.0, alpha=1.0):
    ax.add_patch(Rectangle((r.xmin, r.ymin), r.w, r.h,
                           fill=False, edgecolor=color, linewidth=lw, alpha=alpha))
    
def draw_aabb_in_camera(ax, r: Rect, viewport: OrientedRect, *, color="k", lw=1.0, alpha=1.0):
    # Transform all corners to viewport local coords
    corners_world = r.corners()
    corners_local = [viewport.to_local(x, y) for x, y in corners_world]

    # Draw as polygon in camera space
    ax.add_patch(Polygon(corners_local, closed=True, fill=False,
                         edgecolor=color, linewidth=lw, alpha=alpha))

def draw_obb(ax, r: OrientedRect, *, color="yellow", lw=1, alpha=1.0):
    ax.add_patch(Polygon(r.corners(), closed=True, fill=False,
                         edgecolor=color, linewidth=lw, alpha=alpha))
    
def draw_stars(ax, tree: QuadTree, viewport: OrientedRect,
               visited: list, for_camera: bool = False, base_star_scale=500):
    
    base_scale = tree.root.rect.hw / viewport.hw if for_camera else 1
    pdepth = tree.pseudo_depth(viewport)
    cmap = plt.get_cmap('tab10')
    
    xy, size, rgba = [], [], []
    sorted_nodes = sorted(visited, key=lambda node: node.depth, reverse=True)
    for node in sorted_nodes:
        
        # Handles LOD loading visuals
        scaling = smoothstep((pdepth-node.depth)/1.5)
        node_alpha = scaling if for_camera else 1
        node_size = base_scale * base_star_scale
        node_size *= scaling if for_camera else 1
        
        r,g,b,_ = cmap(node.depth % cmap.N)
        node_rgba = (r, g, b, node_alpha if for_camera else 1)
        
        stars = node.generate_stars()
        for star in stars:
            if star.r < tree.root.rect.hw**2:
                pos = star.position
                xy.append(viewport.to_local(*pos) if for_camera else pos)
                
                star_size = node_size * math.exp(-(node.depth+star.brightness))
                size.append(star_size)
                rgba.append(node_rgba)
    
    sc = ax.scatter([], [])
    sc.set_offsets(xy)
    sc.set_sizes(size)
    sc.set_facecolors(rgba)
    sc.set_edgecolors('none')
    
def draw_world(ax, tree, viewport, visited, debug=True):
    
    root = tree.root.rect
    ax.set_aspect("equal", adjustable="box")
    
    root = tree.root.rect
    ax.add_patch(Circle((root.cx, root.cy), root.hw, fill=None))

    for node in visited:
        draw_aabb(ax, node.rect, color="gray", lw=0.8, alpha=1)
    draw_stars(ax, tree, viewport, visited)

    draw_obb(ax, viewport, color="C0", lw=3, alpha=1)

    # Set limits to the viewport's AABB (so you see the "screen" region)
    ax.set_xlim(root.xmin, root.xmax)
    ax.set_ylim(root.ymin, root.ymax)

    ax.set_xticks([])
    ax.set_yticks([])
    
    if debug:
        debug_info = tree.debug()
        max_depth = max(debug_info)
        dstr = ''
        for depth in range(max_depth):
            tile_num = debug_info.get(depth, 0)
            dstr += f'L{depth:02d} = {tile_num:>3d}\n'
        ax.text(root.xmin*0.98, root.ymax*0.98, dstr, ha='left', va='top')
        
def draw_camera(ax, tree, viewport, visited, base_star_scale=500):
    
    ax.set_aspect('equal', adjustable='box')
    
    root = tree.root.rect
    circle_cnt = viewport.to_local(root.cx, root.cy)
    ax.add_patch(Circle(circle_cnt, root.hw, fill=None))
    
    draw_stars(ax, tree, viewport, visited, True, base_star_scale=base_star_scale)
    
    ax.set_xlim(-viewport.hw, viewport.hw)
    ax.set_ylim(-viewport.hh, viewport.hh)
    
    ax.set_xticks([])
    ax.set_yticks([])

def plot(tree: QuadTree, viewport: OrientedRect):
    
    visited = tree.update(viewport)
    pd = tree.pseudo_depth(viewport)
    print('Visited', len(visited), 'nodes, down to depth', pd)
    
    # Set up our figures
    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, viewport.hw / viewport.hh])
    ax_world = fig.add_subplot(gs[0, 0])
    ax_cam = fig.add_subplot(gs[0, 1])
    
    draw_world(ax_world, tree, viewport, visited)
    draw_camera(ax_cam, tree, viewport, visited)
    
    # Save it
    plt.savefig('/Users/sethbruzewski/Documents/Projects/Coding/Python/GalaxyQuad/quad.png')
    plt.show()

# ----------------------------
# Make a little movie
# ----------------------------   

def make_zoom_movie(tree: QuadTree, viewport0: OrientedRect, *,
                    zoom_start: float = 0.1,
                    zoom_end: float = 100.0,
                    n_frames: int = 7200,
                    fps: int = 60,
                    resolution: tuple = (2560, 1440),
                    dpi: int = 100,
                    bitrate: int = 25_000,
                    out_path: str = "zoom.mp4"):

    import numpy as np
    t = np.linspace(0, 2*np.pi, n_frames)
    log_start = np.log10(zoom_start)
    log_end = np.log10(zoom_end)
    log_zoom = log_start + 0.5 * (1-np.cos(t)) * (log_end-log_start)
    zooms = 10**log_zoom

    width_inches = resolution[0] / dpi
    height_inches = resolution[1] / dpi
    
    # Build figure ONCE (same layout you already use)
    fig = plt.figure(figsize=(width_inches, height_inches))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, viewport0.hw / viewport0.hh])
    ax_world = fig.add_subplot(gs[0, 0])
    ax_cam = fig.add_subplot(gs[0, 1])

    # If you want a tight layout without constrained_layout fighting aspect:
    fig.subplots_adjust(left=0.03, right=0.97, top=0.92, bottom=0.05, wspace=0.08)

    def frame(i: int):
        z = float(zooms[i])

        vp = OrientedRect(
            cx=viewport0.cx,
            cy=viewport0.cy,
            hw=viewport0.hw / z,
            hh=viewport0.hh / z,
            theta_rad=viewport0.theta_rad,
        )

        visited = tree.update(vp)

        # Clear and redraw using YOUR existing drawing functions
        ax_world.cla()
        ax_cam.cla()

        draw_world(ax_world, tree, vp, visited)
        draw_camera(ax_cam, tree, vp, visited)

        # Returning artists is optional if blit=False (we’ll set blit=False)
        return []

    ani = animation.FuncAnimation(fig, frame, frames=n_frames, interval=1000 / fps, blit=False)

    # Save
    writer = animation.FFMpegWriter(
        fps=fps,
        bitrate=bitrate,
        codec='libx264'
    )
    ani.save(out_path, writer=writer, progress_callback=lambda i, n: print(f"\rFrame {i+1}/{n}", end=""))

    plt.close(fig)
    print()
    print(f"Wrote {out_path}")
    
def make_thumbnail(tree: QuadTree, viewport: OrientedRect,
                   resolution=(2460, 1440), dpi=100, out_path='zoom.png'):
    
    set_zoom = 100
    rotated_viewport = OrientedRect(
        cx=viewport.cx, 
        cy=viewport.cy, 
        hw=viewport.hh/set_zoom, 
        hh=viewport.hw/set_zoom, 
        theta_rad=viewport.theta_rad-math.pi/2
    )
    visited = tree.update(rotated_viewport)
    
    # Set up our figures

    width_inches = resolution[0] / dpi
    height_inches = resolution[1] / dpi
    
    # Build figure ONCE (same layout you already use)
    fig = plt.figure(figsize=(width_inches, height_inches))
    ax = fig.add_subplot()

    # If you want a tight layout without constrained_layout fighting aspect:
    fig.subplots_adjust(left=0.03, right=0.97, top=0.92, bottom=0.05, wspace=0.08)
    
    
    for node in visited:
        draw_aabb_in_camera(ax, node.rect, rotated_viewport, alpha=0.05)
    draw_camera(ax, tree, rotated_viewport, visited, base_star_scale=20_000)
    
    text = ax.text(-1.2, 0, 'Zoom\nForever', color='white', size=250, va='center', ha='left', font='DejaVu Sans')
    text.set_path_effects([
        path_effects.Stroke(linewidth=20, foreground='black'),
        path_effects.Normal()
    ])
    
    # Save it
    plt.savefig(out_path, bbox_inches='tight')
    plt.show()

# ----------------------------
# Main: edit these values
# ----------------------------

if __name__ == "__main__":

    # Rotated "screen" / viewport in world coords
    zoom = 1
    VIEWPORT = OrientedRect(
        cx=10.0,
        cy=96.0,
        hw=90.0/zoom,
        hh=160.0/zoom,
        theta_rad=math.radians(30.0),  # <-- rotate your screen here
    )

    # Testing new behavior
    TREE = QuadTree.from_center(cx=0.0, cy=0.0, hw=512.0, hh=512.0)
    
    plot(TREE, VIEWPORT)
    
    #make_zoom_movie(TREE, VIEWPORT, out_path='quadzoom.mp4')
    make_thumbnail(TREE, VIEWPORT)