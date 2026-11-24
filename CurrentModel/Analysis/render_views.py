#!/usr/bin/env python3
"""Fixed-view renders of an airship STEP — issue #36, task c02.

    /home/rhy/.venvs/cadquery/bin/python -I CurrentModel/Analysis/render_views.py \
        "<step file>" <out dir>

Exports six fixed views with CadQuery's SVG exporter (hidden lines off) and
converts each to a 1200 px wide PNG with rsvg-convert:

    iso-front.png  iso-back.png  top.png  side.png  servo-mount.png  bulb.png

The two close-up boxes come from the servo-mount and bulb constants in
airship_slice.py (OAS_VARIANT / OAS_SCALE / OAS_THRUSTER are its env names; the
CR10Pro STEP is 8T at 1.41), so the views always look at the same named
features of the model. The CAD itself is never modified.
"""
import argparse
import importlib.util
import math
import os
import subprocess
import sys

import cadquery as cq
from cadquery.occ_impl.exporters.svg import getSVG
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.TopTools import TopTools_ListOfShape
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN
from OCP.gp import gp_Pnt


def load_slice(env):
    """Import airship_slice.py (constants + placement maths, build() is guarded
    by __main__) with the env that names the build."""
    for k, v in env.items():
        os.environ[k] = v
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "CAD Files", "SimplifiedSlice", "airship_slice.py")
    spec = importlib.util.spec_from_file_location("airship_slice_gen", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rot_z(v, deg):
    a = math.radians(deg)
    return cq.Vector(v.x * math.cos(a) - v.y * math.sin(a),
                     v.x * math.sin(a) + v.y * math.cos(a), v.z)


def inside(shape, p):
    cls = BRepClass3d_SolidClassifier(shape.Solids()[0].wrapped)
    cls.Perform(gp_Pnt(p.x, p.y, p.z), 1e-6)
    return cls.State() == TopAbs_IN


def closeup_angle(shape, probe_candidates):
    """The seam rotation (+/- HALF) whose probe point actually sits in material;
    fall back to the first."""
    for a, p in probe_candidates:
        if inside(shape, p):
            return a
    return probe_candidates[0][0]


def crop(shape, centre, half):
    """Clip the shape to the close-up box: keep the faces whose bbox touches it,
    then boolean-common them with the box so the view ends exactly at the box.
    Geometry only, the STEP is untouched."""
    box = cq.Solid.makeBox(2 * half, 2 * half, 2 * half,
                           cq.Vector(centre.x - half, centre.y - half,
                                     centre.z - half))
    keep = []
    for f in shape.Faces():
        bb = f.BoundingBox()
        if (bb.xmax >= centre.x - half and bb.xmin <= centre.x + half
                and bb.ymax >= centre.y - half and bb.ymin <= centre.y + half
                and bb.zmax >= centre.z - half and bb.zmin <= centre.z + half):
            keep.append(f)
    comp = cq.Compound.makeCompound(keep)
    algo = BRepAlgoAPI_Common()
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(comp.wrapped)
    tools.Append(box.wrapped)
    algo.SetArguments(args)
    algo.SetTools(tools)
    algo.Build()
    if not algo.IsDone():
        return comp
    return cq.Shape.cast(algo.Shape())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step")
    ap.add_argument("outdir")
    ap.add_argument("--variant", default="8T")
    ap.add_argument("--scale", default="1.41")
    ap.add_argument("--thruster", default=None, help="L or S (default: the variant's)")
    ap.add_argument("--only", default=None,
                    help="comma-separated view names to render (default: all six)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    ws = cq.importers.importStep(args.step)
    vals = ws.vals() if isinstance(ws, cq.Workplane) else [ws]
    shape = cq.Compound.makeCompound(vals)
    print("# loaded %s: %d solids, %d faces" % (args.step, len(shape.Solids()),
                                                len(shape.Faces())))

    mod = load_slice({"OAS_VARIANT": args.variant, "OAS_SCALE": args.scale,
                      "OAS_THRUSTER": args.thruster or
                      ("L" if args.variant == "4T" else "S"),
                      "OAS_TAG": "c02-render"})
    half_angle = mod.HALF

    # the bulb: centre of the duct end's dome, on this slice's seam, a point in
    # its wall band for the probe
    C = mod.duct_bulb_centre()
    to_end = mod.duct_path()[-1].sub(C).normalized()
    wall = (mod.DUCT_BULB / 2 + mod.bulb_wall_r()) / 2
    bulb_probe = C.add(to_end.multiply(wall))
    bulb_a = closeup_angle(shape, [(a_, rot_z(bulb_probe, a_)) for a_ in
                                   (half_angle, -half_angle)])
    bulb_c = rot_z(C, bulb_a)
    bulb_half = mod.DUCT_BULB / 2 + 8.0

    # the servo mount: centre of the Ø SERVO_HOLE spline hole bore, radial out
    # of it into the skin band for the probe
    hc = cq.Vector(mod.A - 17.765 + 15.0, mod.SERVO_T, getattr(mod, "OUT_Z", 0.0))
    # the hole axis is radial, so probe along z: SERVO_HOLE/2 + SERVO_WALL/2 off
    # the axis, still in the skin band (the band is too thin for a radial probe)
    servo_probe = hc.add(cq.Vector(0.0, 0.0,
                                   mod.SERVO_HOLE / 2 + mod.SERVO_WALL / 2))
    a = closeup_angle(shape, [(a_, rot_z(servo_probe, a_)) for a_ in
                              (half_angle, -half_angle)])
    servo_c = rot_z(hc, a)
    servo_half = max(mod.SERVO_BRACKET_L, mod.SERVO_BRACKET_W) / 2 + 8.0
    print("# servo close-up at x=%.1f y=%.1f z=%.1f (box %.0f mm)"
          % (servo_c.x, servo_c.y, servo_c.z, 2 * servo_half))
    print("# bulb close-up at x=%.1f y=%.1f z=%.1f (box %.0f mm)"
          % (bulb_c.x, bulb_c.y, bulb_c.z, 2 * bulb_half))

    # view direction: along it at the shape, gp_Ax2 style
    # the bulb: look along its seam's tangent so the duct's profile shows
    bulb_dir = (math.sin(math.radians(bulb_a)),
                -math.cos(math.radians(bulb_a)), 0.4)
    views = [
        ("iso-front", (-1, -1, 1), shape, None),
        ("iso-back", (1, 1, -1), shape, None),
        ("top", (0, 0, -1), shape, None),
        ("side", (-1, 0, 0), shape, None),
        ("servo-mount", (-1, -1, 1), shape, (servo_c, servo_half)),
        ("bulb", bulb_dir, shape, (bulb_c, bulb_half)),
    ]

    for name, direction, subj, box in views:
        if args.only and name not in args.only.split(","):
            continue
        target = subj
        if box:
            target = crop(subj, box[0], box[1])
        svg = os.path.join(args.outdir, name + ".svg")
        png = os.path.join(args.outdir, name + ".png")
        opts = {"projectionDir": tuple(direction), "showHidden": False,
                "showAxes": False, "width": 1200, "height": None,
                "marginLeft": 20.0, "marginTop": 20.0}
        with open(svg, "w") as fh:
            fh.write(getSVG(target, opts))
        subprocess.run(["rsvg-convert", "-w", "1200", svg, "-o", png],
                       check=True)
        print("# wrote %s" % png)


if __name__ == "__main__":
    sys.exit(main())
