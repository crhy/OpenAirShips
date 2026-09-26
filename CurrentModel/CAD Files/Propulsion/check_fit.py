"""Fit checks for the propulsion parts against the 926 slice (run after propulsion.py)."""
import math, os, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import propulsion as p
from propulsion import hull

sl = cq.importers.importStep(os.path.join(HERE, "..", "SimplifiedSlice", "airship pie slice 926.step")).val()
ship = cq.Compound.makeCompound([sl.rotate((0, 0, 0), (0, 0, 1), 45 * k) for k in range(8)])
motor = cq.Solid.makeCylinder(p.MOTOR_D / 2, p.MOTOR_L, cq.Vector(0, 0, hull.LEDGE_Z - p.MOTOR_L))
b, w = p.MG90S["body"]
servo = cq.Solid.makeBox(p.MG90S["depth"] + 12, w, b,
                         cq.Vector(p.SERVO_PLATE_X - p.MG90S["depth"], p.SERVO_Y - w / 2,
                                   p.OUT_Z + p.MG90S["shaft_offset"] - b / 2))

def clash(a, b_, name, tol=0.05):
    v = a.intersect(b_).Volume()
    print(f"{name:40} {'OK' if v < tol else 'CLASH %.2f mm3' % v}")
    return v

imp, spi = p.impeller(), p.motor_spider()
clash(imp, ship, "impeller vs hull")
clash(spi, ship, "spider vs hull (resting on ledge)")
clash(motor, ship, "motor vs hull")
clash(imp, motor, "impeller vs motor")
top, base = p.impeller_z()
print("impeller top z %.1f (shaft mouth %.1f), bottom z %.1f, keel inside at axis %.1f"
      % (top, hull.FLOOR_Z, base, -(hull.B - hull.T)))
hood, stem = p.outlet_hood(), p.stem()
for name, part in (("hood", hood), ("stem", stem), ("servo", servo),
                   ("stem gear", p.stem_gear()), ("servo gear", p.servo_gear())):
    clash(p.at_seam(part), ship, f"{name} vs hull")
clash(stem, hood, "stem vs hood")
for ang in (-90, -45, 0, 45, 90):
    ring = p.thruster_ring_placed(ang)
    clash(p.at_seam(ring), ship, f"ring at {ang:+} deg vs hull")
    clash(ring, servo.fuse(hood), f"ring at {ang:+} deg vs servo/hood")
    clash(p.at_seam(ring), p.at_seam(p.thruster_ring_placed(-ang), 1), f"ring at {ang:+} vs next thruster")
