#!/usr/bin/env python3
"""Build a two-cell, full-scale lattice print coupon from the production model.

The coupon is cut from the completed slice, so it exercises the same skin,
windows, booleans and print pose as the release STL.  Output belongs under an
Analysis/build/<task>/ directory; this script deliberately refuses to write in
the release CAD and Print Files directories.
"""

import argparse
import importlib.util
import math
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE = ROOT / "CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py"


def arguments():
    p = argparse.ArgumentParser()
    p.add_argument("--scale", type=float, default=1.41,
                   help="model scale; 1.41 is the released CR-10 Pro model")
    p.add_argument("--first-cell", type=int, default=8,
                   help="first of two adjacent row cells (0-based); 8 selects "
                        "the upper-hull cells around the 48-degree junction")
    p.add_argument("--output", type=Path, required=True,
                   help="output stem, normally Analysis/build/<task>/lattice-coupon")
    return p.parse_args()


def load_model(scale):
    os.environ["OAS_VARIANT"] = "8T"
    os.environ["OAS_SIDE"] = "L"
    os.environ["OAS_SLICES"] = "8"
    os.environ["OAS_THRUSTER"] = "S"
    os.environ["OAS_SCALE"] = str(scale)
    os.environ["OAS_PIECES"] = "0"
    os.environ["OAS_RIB"] = "2.0"
    spec = importlib.util.spec_from_file_location("airship_slice_coupon", SOURCE)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    return model


def posed_point(model, point):
    """The two rotations in print_pose(), applied to one point."""
    h = math.radians(model.HALF)
    x = point.x * math.cos(h) - point.y * math.sin(h)
    y = point.x * math.sin(h) + point.y * math.cos(h)
    return (x, -point.z, y)


def cap_angle(model, p0, p1, side):
    """Angle of the straight upper cap side above the printer's build plane."""
    ring = model.oval_on_skin(p0, p1, side)
    apex = posed_point(model, ring[0][0])
    shoulder = posed_point(model, ring[len(ring) // 4][0])
    rise = abs(apex[2] - shoulder[2])
    run = math.hypot(apex[0] - shoulder[0], apex[1] - shoulder[1])
    return math.degrees(math.atan2(rise, run))


def main():
    args = arguments()
    out = args.output.resolve()
    forbidden = [ROOT / "CurrentModel/CAD Files", ROOT / "CurrentModel/Print Files"]
    if any(out == d.resolve() or d.resolve() in out.parents for d in forbidden):
        raise SystemExit("coupon output must not be placed in CAD Files or Print Files")
    out.parent.mkdir(parents=True, exist_ok=True)

    model = load_model(args.scale)
    rows = model.skin_ribs()
    k = args.first_cell
    if not 0 <= k < len(rows) - 2:
        raise SystemExit(f"--first-cell must be 0..{len(rows) - 3}")

    # The two raw cells meet across one full RIB.  Rounding the window inward can
    # only increase this value, so this is the conservative geometry measurement.
    lower = model.oval_on_skin(rows[k], rows[k + 1], -1)
    upper = model.oval_on_skin(rows[k + 1], rows[k + 2], -1)
    a = lower[len(lower) // 4][0]
    b = upper[3 * len(upper) // 4][0]
    measured_rib = (a - b).Length
    angles = [cap_angle(model, rows[j], rows[j + 1], -1) for j in (k, k + 1)]

    print(f"building production 8T slice at scale {args.scale:g}", flush=True)
    body = model.build()

    # Keep one complete azimuth column and exactly two adjacent row cells.  Both
    # crop boundaries follow the centres of production ribs: column(-1) follows
    # the seam/centre ribs, while the revolved sector follows rows k and k+2.
    # A flat XYZ box cuts curved neighbouring ribs into unsupported little
    # prongs, which would make the coupon reproduce the original failure for a
    # reason that does not exist in the production part.
    def far_on_row(psi):
        return (3.0 * model.A * math.cos(psi),
                3.0 * model.B * math.sin(psi))

    row_sector = model.wedge(
        [(0.0, 0.0), far_on_row(rows[k]), far_on_row(rows[k + 2])],
        half=model.HALF + 2.0)
    coupon = body.intersect(row_sector).intersect(model.column(-1))
    solids = [s for s in coupon.Solids() if s.Volume() > 1.0]
    if not solids:
        raise RuntimeError("coupon crop produced no printable solid")
    # The outer skin is the solid farthest from the axis if an unrelated intake
    # fragment is also caught by the crop.
    coupon = max(solids, key=lambda s: s.Center().x)
    coupon = model.print_pose(coupon)
    bb = coupon.BoundingBox()
    coupon = coupon.translate((0, 0, -bb.zmin))

    step = out.with_suffix(".step")
    stl = out.with_suffix(".stl")
    model.cq.exporters.export(coupon, str(step))
    model.cq.exporters.export(coupon, str(stl), tolerance=0.02,
                              angularTolerance=0.08)
    bb = coupon.BoundingBox()
    print(f"coupon: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, "
          f"{coupon.Volume() / 1000:.2f} cm3, {len(coupon.Solids())} solid, "
          f"valid {coupon.isValid()}")
    print(f"minimum row web: {measured_rib:.3f} mm "
          f"(design RIB {model.RIB:.3f} mm)")
    print(f"upper-cap angles above build plane: {min(angles):.1f}..{max(angles):.1f} deg")
    print(step)
    print(stl)


if __name__ == "__main__":
    main()
