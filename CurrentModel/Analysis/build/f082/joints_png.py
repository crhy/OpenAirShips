#!/usr/bin/env python
"""f082: a top-down picture of each seam face, with the joints marked.

The seam face is the flat side of the wedge, so it is drawn in its own true
shape: r (out from the axis, measured in the seam plane) across, z up. The
material comes from the built STEP - the planar faces whose normal is the seam
normal - so the picture cannot drift from what the generator wrote out.

Over that, from the joint map the same build wrote: every peg/hole pair at its
(r, z) with the boss (ØBOSS_D) and the hole (ØHOLE_D) to scale, and the keep-clear
outlines (the fan housing, the plenum air, the impeller's swept volume, the duct
bore, the bulb's bore) that Analysis/check_outputs.py measures against.

  /home/rhy/.venvs/cadquery/bin/python CurrentModel/Analysis/build/f082/joints_png.py

Writes CurrentModel/Analysis/build/joints-8T-seam-<hole|peg>.png. Scratch: not
committed, like everything else under build/.
"""
import json
import math
import os
import sys

import cadquery as cq
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402

HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SLICE_DIR = os.path.join(HERE, "CurrentModel", "CAD Files", "SimplifiedSlice")
BUILD = os.path.join(HERE, "CurrentModel", "Analysis", "build")
sys.path.insert(0, SLICE_DIR)
import airship_slice as h   # noqa: E402

STEP = os.path.join(SLICE_DIR, "airship pie slice 1026.step")
MAP = os.path.join(SLICE_DIR, "airship pie slice 1026.joints.json")

shape = cq.importers.importStep(STEP).val()
jm = json.load(open(MAP))


def seam_face(phi_deg):
    """The seam face at azimuth phi, as (r, z) polygons: the first polygon of
    each group is a planar face's outer wire, the rest are its holes."""
    phi = math.radians(phi_deg)
    nx, ny = math.cos(phi), math.sin(phi)
    groups = []
    for f in shape.Faces():
        try:
            pl = f.normalAt()
        except Exception:
            continue
        if abs(pl.x * ny - pl.y * nx) > 1e-6 or abs(pl.z) > 1e-6:
            continue                       # not parallel to this seam plane
        c = f.Center()
        if c.x * nx + c.y * ny < 1e-6:     # the plane through the origin's other side
            continue
        polys = []
        for w in [f.outerWire()] + list(f.innerWires()):
            pts = []
            for e in w.Edges():
                n = max(2, int(e.Length() / 0.5))
                vs = []
                for i in range(n + 1):
                    v = e.positionAt(i / n)
                    vs.append((math.hypot(v.x, v.y), v.z))
                pts += vs if not pts else vs[1:]
            if len(pts) > 2:
                polys.append(pts)
        if polys:
            groups.append(polys)
    return groups


def draw(phi_deg, path, title):
    fig, ax = plt.subplots(figsize=(13.5, 8.0))
    for polys in seam_face(phi_deg):
        for k, pts in enumerate(polys):
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            ax.fill(xs, ys, color="#9fb6c9" if k == 0 else "white",
                    edgecolor="#33475b", linewidth=0.6, zorder=2 if k == 0 else 3)
    for c in jm["keep_clear"]:
        prof = c["profile"]
        xs = [p[0] for p in prof] + [prof[0][0]]
        ys = [p[1] for p in prof] + [prof[0][1]]
        ax.plot(xs, ys, linestyle="--" if c["kind"] == "air2d" else ":",
                color="#b4451f", linewidth=1.1, zorder=4)
        ax.text(xs[len(xs) // 4], ys[len(ys) // 4], c["name"], fontsize=7,
                color="#b4451f", zorder=4)
    th = np.linspace(0, 2 * math.pi, 72)
    for j in jm["joints"]:
        r, z = j["r"], j["z"]
        for rad, col in ((j["boss_d"] / 2.0, "#c8860a"), (j["hole_d"] / 2.0, "#7a1fa2")):
            ax.plot(r + rad * np.cos(th), z + rad * np.sin(th),
                    color=col, linewidth=1.6, zorder=6)
        ax.plot([r], [z], marker="+", color="black", markersize=9, zorder=7)
        ax.annotate("%s  r=%.1f z=%.1f\nfused: %s" % (j["name"], r, z,
                                                      " + ".join(j["fused_to"])),
                    (r, z), xytext=(r + 12, z - 30), fontsize=8, color="black",
                    zorder=8, arrowprops=dict(arrowstyle="->", color="black",
                                              linewidth=0.8))
    ax.set_title("%s  (seam face at %+.1f deg, drawn in r, z)" % (title, phi_deg),
                 fontsize=11)
    ax.set_xlabel("r  mm out from the axis, in the seam plane")
    ax.set_ylabel("z  mm")
    ax.set_xlim(0, h.A + 8)
    ax.set_ylim(-h.B - 8, h.B + 8)
    ax.set_aspect("equal")
    ax.grid(True, linewidth=0.2, alpha=0.4)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    g = seam_face(phi_deg)
    print("wrote %s  %d face groups, areas %s mm2, holes %s"
          % (os.path.basename(path), len(g),
             [round(abs(sum((p_[0][0] * p_[1][1] - p_[1][0] * p_[0][1]) for p_ in zip(q, q[1:] + q[:1]))
                         / 2.0)) for q in [grp[0] for grp in g]],
             [len(grp) - 1 for grp in g]))


draw(-h.HALF, os.path.join(BUILD, "joints-8T-seam-hole.png"),
     "8T slice, hole seam: the holes the neighbouring slice's pegs come through")
draw(+h.HALF, os.path.join(BUILD, "joints-8T-seam-peg.png"),
     "8T slice, peg seam: two pegs, both fused into the duct wall")
