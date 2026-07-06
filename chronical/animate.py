# -*- coding: utf-8 -*-
"""Render the galaxy's history as an mp4 (or gif fallback).

Run from the directory containing galaxy/:
    python -m galaxy.animate

How it works: FuncAnimation calls update(i) once per frame; update clears
the axes and redraws that moment with the same plot_era you've been using.
Because every generator in the package is lru_cached, the WORLD is only
computed once (during frame 0) -- all later frames pay only matplotlib
drawing cost.

mp4 needs ffmpeg on your PATH (macOS: brew install ffmpeg). If it's
missing we fall back to a gif via Pillow so you still get output.
"""

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation

from .config import T_PRESENT
from .plot import plot_era
from .query import tier0_registry

# ------------------------------------------------------------------ knobs
N_FRAMES: int = 300     # 300 @ 30fps = 10s. At 100 frames, short-lived minor
                        # civs (5-40 kyr) blink in/out in 1-2 frames; ~300+
                        # frames over 2 Myr makes their rise/fall readable.
FPS: int = 30
DPI: int = 110
T_START: float = T_PRESENT - 5e5
T_END: float = T_PRESENT + 5e5
INFLATE: float = 8.0
OUT_STEM: str = "outputs/galaxy_history"


def make_animation(n_frames: int = N_FRAMES,
                   t_start: float = T_START,
                   t_end: float = T_END) -> tuple[plt.Figure, animation.FuncAnimation]:
    tier0 = tier0_registry()
    times = np.linspace(t_start, t_end, n_frames)

    fig, ax = plt.subplots(figsize=(9, 9), facecolor="#0b0e14")

    def update(i: int) -> list:
        ax.clear()                      # wipes titles/limits too;
        plot_era(ax, float(times[i]), tier0, inflate=INFLATE)   # ...plot_era resets all of it
        return []

    anim = animation.FuncAnimation(fig, update, frames=n_frames, interval=1000 / FPS)
    return fig, anim


def save(anim: animation.FuncAnimation, fig: plt.Figure, stem: str = OUT_STEM) -> str:
    """Try mp4 (ffmpeg), fall back to gif (Pillow)."""
    kwargs = dict(dpi=DPI, savefig_kwargs={"facecolor": fig.get_facecolor()})
    if animation.FFMpegWriter.isAvailable():
        path = f"{stem}.mp4"
        writer = animation.FFMpegWriter(fps=FPS, bitrate=3500,
                                        metadata={"title": "Tiered Procedural Galaxy"})
        anim.save(path, writer=writer, **kwargs)
    else:
        path = f"{stem}.gif"
        anim.save(path, writer=animation.PillowWriter(fps=FPS), **kwargs)
        print("ffmpeg not found -- wrote gif instead. `brew install ffmpeg` for mp4.")
    return path


if __name__ == "__main__":
    fig, anim = make_animation()
    out = save(anim, fig)
    print(f"Saved -> {out}")