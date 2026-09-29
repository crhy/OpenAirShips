"""Geometry numbers for the float budget, for the hull variant set in the
environment (OAS_VARIANT, OAS_SCALE). Prints one JSON line. Run by
float_budget.py; needs the STEP files that airship_slice.py and propulsion.py
write."""
import json
import math
import os
import sys

import cadquery as cq
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "CAD Files")
sys.path.insert(0, os.path.join(CAD, "SimplifiedSlice"))
sys.path.insert(0, os.path.join(CAD, "Propulsion"))
import airship_slice as h   # noqa: E402
import propulsion as p      # noqa: E402


def mesh_cm3(shape):
    """Volume from a fine tessellation (the kernel's own volume is unreliable
    on these lattice solids)."""
    v, t = shape.tessellate(0.05, 0.1)
    m = trimesh.Trimesh(np.array([q.toTuple() for q in v]), np.array(t))
    return abs(m.volume) / 1000


def load(path):
    return cq.importers.importStep(path).val()


def rev(pts):
    """Full 360 deg solid from an (r, z) polygon."""
    return h.wedge(pts, half=180.0)


sides = h.slice_sides()
vol = {sd: mesh_cm3(load(os.path.join(CAD, "SimplifiedSlice", h.slice_name(sd) + ".step")))
       for sd in sorted(set(sides))}
slices = [vol[sd] for sd in sorted(vol)]
hull_cm3 = sum(vol[sd] for sd in sides)
tubes_cm3 = sum(mesh_cm3(t_) for t_ in h.tube_segments()) if h.PIECES else 0.0

parts = {}
for n in ("impeller", "fan_hatch", "servo_mount", "stem", "stem_gear", "servo_gear", "thruster_ring") + (
        ("avionics_tray",) if h.PIECES else ()):
    parts[n] = mesh_cm3(load(os.path.join(p.OUT_DIR, n + ".step")))

# free interior: inside the skin, minus the shaft core, the fan housing, the
# ducts and the printed material itself
Ai, Bi = h.A - h.T, h.B - h.T
inner = rev([(0, -Bi)] + [(Ai * math.cos(t), Bi * math.sin(t))
                          for t in [-math.pi / 2 + math.pi * i / 200 for i in range(1, 200)]] + [(0, Bi)])
v_inner = 4 / 3 * math.pi * Ai ** 2 * Bi / 1e6
core = rev([(0, -h.B - 1), (h.SHAFT_R + h.T, -h.B - 1), (h.SHAFT_R + h.T, h.B + 1), (0, h.B + 1)])
zk = -(h.B - h.T) * math.sqrt(1 - (h.PLENUM_KEEL_R / (h.A - h.T)) ** 2)
house = rev([(0, -h.B - 1), (h.PLENUM_KEEL_R + 1, -h.B - 1), (h.PLENUM_KEEL_R + 1, zk)]
            + [(r, z + h.T) for r, z in reversed(h.shroud_curve()[1:-1])] + [(0, h.nozzle_top())])
v_core = core.intersect(inner).Volume() / 1e6
v_house = house.cut(core).intersect(inner).Volume() / 1e6
walls, bore = h.duct_solids()
n_thr = 4 if h.FOUR else 8
duct = walls.fuse(bore).cut(house).intersect(inner)
v_ducts = n_thr * duct.Volume() / 1e6
v_free = v_inner - v_core - v_house - v_ducts - hull_cm3 / 1000
# ellipsoid surface (oblate), for the gas-cell film estimate
e = math.sqrt(1 - (h.B / h.A) ** 2)
surf = 2 * math.pi * h.A ** 2 * (1 + (1 - e * e) / e * math.atanh(e)) / 1e6

path = h.duct_path()
duct_l = sum((b - a).Length for a, b in zip(path, path[1:])) / 1000
ribs = h.skin_ribs()
meridian = h.ellipse_arc(-math.pi / 2, ribs[-1]) / 1000        # seam length, keel to intake
cuts = 0.0
if h.PIECES:                                                   # piece cut lines, round the ship
    c = h.cut_ribs()
    cuts = 2 * math.pi * (2 * h.skin_point(c["z_hi"], 0)[0] + 2 * h.skin_point(c["r_hi"], 0)[0]) / 1000
print(json.dumps(dict(variant=h.VARIANT, scale=h.SCALE, A=h.A, B=h.B, slices=slices, hull_cm3=hull_cm3,
                      n_slices=h.N, pieces=h.PIECES, tubes_cm3=tubes_cm3, meridian=meridian, cuts=cuts,
                      parts=parts, v_inner=v_inner, v_core=v_core, v_house=v_house, v_ducts=v_ducts,
                      v_free=v_free, surface_m2=surf, duct_l=duct_l, n_thr=n_thr,
                      duct_d=h.DUCT_BORE, stem_id=p.STEM_ID, slot=p.SLOT, slot_r=p.RT + p.RC - 1.0)))
