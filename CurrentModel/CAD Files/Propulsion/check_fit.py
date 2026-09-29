"""Fit checks for the propulsion parts against the 926 slice (run after propulsion.py)."""
import math, os, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import propulsion as p
from propulsion import hull

SL = os.path.join(HERE, "..", "SimplifiedSlice")
types = {sd: cq.importers.importStep(os.path.join(SL, hull.slice_name(sd) + ".step")).val()
         for sd in set(hull.slice_sides())}
ship = cq.Compound.makeCompound([types[sd].rotate((0, 0, 0), (0, 0, 1), 360.0 / hull.N * k)
                                 for k, sd in enumerate(hull.slice_sides())]
                                + (hull.tube_segments() if hull.PIECES else []))
motor = cq.Solid.makeCylinder(p.MOTOR_D / 2, p.MOTOR_L, cq.Vector(0, 0, p.PED_TOP))
nut = cq.Solid.makeCylinder(4.5, 5.8, cq.Vector(0, 0, p.BELL_TOP + p.CUP_TOP_T))   # M5 nylock
def clash(a, b_, name, tol=0.05):
    try:
        v = a.intersect(b_).Volume()
    except ValueError:
        # The kernel can fail where a part only touches the hull (a glued
        # mount on the skin). Check slice by slice; where that fails too,
        # take the smallest overlap over 0.01 mm nudges (touching, not a clash).
        v = 0.0
        for s_ in (b_.Solids() if hasattr(b_, "Solids") else [b_]):
            try:
                v += a.intersect(s_).Volume()
            except ValueError:
                vals = []
                for d in ((-0.01, 0, 0), (0.01, 0, 0), (0, -0.01, 0), (0, 0.01, 0), (0, 0, -0.01), (0, 0, 0.01)):
                    try:
                        vals.append(a.translate(d).intersect(s_).Volume())
                    except ValueError:
                        pass
                v += min(vals) if vals else float("inf")
    print(f"{name:40} {'OK' if v < tol else 'CLASH %.2f mm3' % v}")
    return v

imp, hatch, hatch_in = p.impeller(), p.fan_hatch(), p.fan_hatch(locked=False)
clash(imp, ship, "impeller vs hull (under the shroud)")
clash(hatch, ship, "hatch locked vs hull")
clash(hatch_in, ship, "hatch at insert angle vs hull")
clash(motor, ship, "motor vs hull")
clash(motor, hatch, "motor vs hatch")
clash(imp, motor, "impeller vs motor")
clash(imp, hatch, "impeller vs hatch")
clash(nut, ship, "prop nut vs hull")
top_, base_ = p.impeller_z()
path = cq.Solid.makeCylinder(p.IMP_R2 + 0.05, base_ + hull.B + 10, cq.Vector(0, 0, -hull.B - 10))
clash(path, ship, "impeller path up through the hatch opening")
for dz in (5, 10, 15):
    clash(hatch_in.translate((0, 0, -dz)), ship, f"hatch {dz} mm below seated, insert angle")
gap = imp.intersect(ship.translate((0, 0, -(hull.SHROUD_GAP - 0.3)))).Volume()
print(f"{'shroud gap >= %.1f mm' % (hull.SHROUD_GAP - 0.3):40} {'OK' if gap < 0.05 else 'TOO TIGHT %.2f mm3' % gap}")
top, base = p.impeller_z()
print("impeller top z %.1f (shaft mouth %.1f), bottom z %.1f, keel inside at axis %.1f"
      % (top, hull.FLOOR_Z, base, -(hull.B - hull.T)))
stem, mount, servo = p.stem(), p.servo_mount(), p.servo_dummy()
outside = [("stem", stem), ("servo", servo), ("servo mount", mount),
           ("stem gear", p.stem_gear()), ("servo gear", p.servo_gear())]
for name, part in outside:
    clash(p.at_seam(part), ship, f"{name} vs hull")
clash(servo, mount, "servo vs its mount")
clash(p.servo_gear(), servo, "servo gear vs servo body")
if hull.PIECES:
    tray = p.avionics_tray()
    clash(tray, ship, "avionics tray vs hull and tube")
    clash(tray, imp.fuse(motor), "avionics tray vs fan")
for ang in (-90, -45, 0, 45, 90):
    ring = p.thruster_ring_placed(ang)
    clash(p.at_seam(ring), ship, f"ring at {ang:+} deg vs hull")
    clash(ring, p.servo_gear().fuse(p.stem_gear()), f"ring at {ang:+} deg vs gears")
    clash(p.at_seam(ring), p.at_seam(p.thruster_ring_placed(-ang), 1), f"ring at {ang:+} vs next thruster")
