"""Fit checks for the propulsion parts against the 926 slice (run after propulsion.py)."""
import math, os, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import propulsion as p
from propulsion import hull

sl = cq.importers.importStep(os.path.join(HERE, "..", "SimplifiedSlice", "airship pie slice 926.step")).val()
ship = cq.Compound.makeCompound([sl.rotate((0, 0, 0), (0, 0, 1), 45 * k) for k in range(8)])
motor = cq.Solid.makeCylinder(p.MOTOR_D / 2, p.MOTOR_L, cq.Vector(0, 0, p.PED_TOP))
nut = cq.Solid.makeCylinder(4.5, 5.8, cq.Vector(0, 0, p.BELL_TOP + p.CUP_TOP_T))   # M5 nylock
def clash(a, b_, name, tol=0.05):
    v = a.intersect(b_).Volume()
    print(f"{name:40} {'OK' if v < tol else 'CLASH %.2f mm3' % v}")
    return v

imp, ped = p.impeller(), p.motor_pedestal()
clash(imp, ship, "impeller vs hull")
clash(ped, ship, "pedestal vs hull (in its keel socket)")
clash(motor, ship, "motor vs hull")
clash(imp, motor, "impeller vs motor")
clash(imp, ped, "impeller vs pedestal")
clash(nut, ship, "prop nut vs hull")
shaft_bore = cq.Solid.makeCylinder(hull.SHAFT_R - 0.01, 200, cq.Vector(0, 0, hull.FLOOR_Z))
print("parts in the intake shaft above the floor: %.2f mm3 (must be 0)"
      % imp.fuse(motor, ped).intersect(shaft_bore).Volume())
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
for ang in (-90, -45, 0, 45, 90):
    ring = p.thruster_ring_placed(ang)
    clash(p.at_seam(ring), ship, f"ring at {ang:+} deg vs hull")
    clash(ring, p.servo_gear().fuse(p.stem_gear()), f"ring at {ang:+} deg vs gears")
    clash(p.at_seam(ring), p.at_seam(p.thruster_ring_placed(-ang), 1), f"ring at {ang:+} vs next thruster")
