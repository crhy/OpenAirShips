"""Propulsion parts for the 926 pie-slice airship (tethered bench demo), rev E.

Air path: the impeller at the bottom of the central shaft pulls air down the
shaft and throws it outward into the plenum between the floor and the keel.
From there it enters the 8 thrust ducts, which run inside the skin to the
equator. The hull's outside stays smooth. At each seam, a rotating stem
passes through a round hole in the skin, with its flange behind a bearing
boss inside the duct, and carries a printed air-multiplier ring. An MG90S
servo inside the hull turns it through a 1:1 gear pair just outside the
skin. The swivel axis is radial, so each thruster points its jet anywhere in
the plane made of "up" and the tangential direction.

Parts (all in mm; each is exported already posed for printing):
  impeller        open, backward-curved, 88 mm; a cup over the motor bell clamps on its shaft
  fan_hatch       removable keel hatch (bayonet); the 2207 stands on it, bell up
  servo_mount     glued inside the skin; holds the MG90S, spline out
  stem            rotating swivel tube; its flange sits behind the duct's bearing boss
  stem_gear       36T m1, D-bore, glued on the stem
  servo_gear      36T m1, hub through the skin onto the MG90S spline
  thruster_ring   air multiplier: Coanda lip, 1.6 mm slot, 64 mm OD

Run: python3 propulsion.py      -> <part>.step (model coordinates) + print/<part>.step
     freecadcmd make_fcstd.py     -> propulsion 926.FCStd + print/<part>.stl
     python3 check_fit.py         -> clash checks against the hull
"""
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "SimplifiedSlice"))
import airship_slice as hull  # noqa: E402

# ---- motor: 2207 1750KV racing outrunner on 4S (see Analysis/AIRFLOW.md), ~32 g
MOTOR_D = 28.0             # bell diameter
MOTOR_L = 20.0             # mount face to bell top
MOUNT_SQUARE = 16.0        # M3 holes on a 16 x 16 mm square (the usual 2207 pattern)
HUB_BORE = 5.2             # M5 motor shaft

# ---- fan hatch: the keel under the fan, removable; the motor stands on it
# The impeller's cup sits on the bell top and is clamped by the prop nut, so
# the bell top sets the impeller height: the blade tips run SHROUD_GAP under
# the housing's shroud.
CUP_TOP_T = 2.0            # cup top disc (clamped between bell and nut)
CUP_R = 15.5               # cup wall inner radius (bell is 14)
IMP_B2 = 12.5                  # blade height at the tip (from the airflow analysis); the
                               # inlet edge is taller, following the housing's shroud
IMP_PLATE_TOP = hull.FLOOR_Z - hull.SHROUD_GAP - IMP_B2
BELL_TOP = IMP_PLATE_TOP + 5.2   # the nut sits in the eye, under the contraction
PED_TOP = BELL_TOP - MOTOR_L
PED_R = 20.0               # motor pedestal drum on the hatch
PED_PLATE = 2.0
HATCH_CLR = 0.2            # hatch dish to keel opening, per side
FLANGE_Z = (hull.LUG_Z[1] + 0.2, hull.LUG_Z[1] + 1.7)   # bayonet tabs ride on the lugs
TAB_HALF = 14.0            # 8 tabs, 28 deg wide, centred on the seams when inserted
LOCK_TURN = 11.5           # degrees clockwise (from above) from insert to locked
WIRE_HOLE = (25.0, 3.0)    # phase-wire hole through the dish: radius, hole radius

# ---- impeller ---------------------------------------------------------------
IMP_R1, IMP_R2 = 33.0, 44.0    # eye (blade inlet) / tip radius (OD 88 passes the Ø94 keel hatch opening)
IMP_BLADES = 7
IMP_PLATE = 0.8                # backplate: 4 layers; the blades stiffen it
IMP_T = 0.86                   # blade thickness (2 lines)
IMP_BETA = 40.0                # backward sweep of the blade, degrees
IMP_SCALLOP_MARGIN = 2.0       # backplate kept this far beyond each blade face
IMP_SCALLOP_R = 38.0           # scallops start here (the eye and inner passages keep a full floor)

# ---- swivel and servo (outlet frame: X = radial along the seam, Z = up) ----
# The hull stays smooth: only the stem (on the seam) and the servo's gear hub
# (SERVO_Y to the side) pass through round holes in the skin. The stem's
# flange sits behind the bearing boss inside the duct; the servo hangs inside
# the hull on a mount glued to the skin; the gear pair runs just outside.
OUT_Z = hull.OUT_Z         # swivel axis height
X_SKIN = hull.hull_r(OUT_Z)                 # skin at the stem, on the seam
X_BOSS = X_SKIN - hull.BOSS_LEN             # inner face of the bearing boss
FOUR = hull.FOUR           # OAS_VARIANT=4T: 4 thrusters sized for twice the flow each
STEM_OD, STEM_ID = (34.0, 31.0) if FOUR else (25.0, 22.0)   # bore: see Analysis/AIRFLOW*.md
FLANGE_D, FLANGE_T = STEM_OD + 3.0, 1.8    # sits in the duct's end bulb, behind the bearing sleeve
D_FLAT = 0.7               # depth of the stem's D-flat that keys the gear
GEAR_M, GEAR_Z, GEAR_T = 1.0, (44 if FOUR else 36), 4.0   # 4T: 44T to clear the Ø34 stem
GEAR_X = X_SKIN + 1.235    # hull-side face of both gears, just outside the skin
SERVO_Y = hull.SERVO_T     # 1:1 pair: centre distance = pitch diameter
assert abs(SERVO_Y - GEAR_M * GEAR_Z) < 1e-6
MG90S = dict(body=(22.8, 12.2), tabs=32.3, hole_pitch=27.8, shaft_offset=5.4,
             below_tabs=16.0, above_tabs=4.5, spline_tip=11.5, spline_d=4.8)
TAB_X = X_SKIN - 15.265    # servo tab plane: the body top clears the curved skin
MOUNT_T = 3.0

# ---- air multiplier ring ----------------------------------------------------
RT, RO = (24.0, 36.0) if FOUR else (20.0, 32.0)   # throat radius at the slot, outer radius
HD = 42.0 if FOUR else 32.0   # diffuser height (exit at a = 0, slot near the top); tall enough for the stem feed
TAPER = 15.0               # diffuser half-angle
RC = 4.0 if FOUR else 3.0  # Coanda lip radius
SLOT = 2.0 if FOUR else 1.6   # from the airflow analysis (shrouded fan)
RING_W = 0.86              # 2 perimeters
STEM_IN = RO + 12.0        # stem socket length from the ring axis


# ---- helpers ----------------------------------------------------------------
def revolve(pts, arcs=()):
    """Revolve a closed (radius, z) polyline 360 deg about Z."""
    w = cq.Workplane("XZ").polyline(pts).close()
    return w.revolve(360, (0, 0, 0), (0, 1, 0)).val()


def spur_gear(z, m, t, bore=None, hub_r=10.0):
    """Involute spur gear, flat on XY, `t` thick."""
    rp, ra, rf = m * z / 2, m * z / 2 + m, m * z / 2 - 1.25 * m
    rb = rp * math.cos(math.radians(20))

    def inv(r):
        a = math.acos(min(1.0, rb / r))
        return math.tan(a) - a

    half = math.pi / (2 * z) + inv(rp)          # half tooth angle at base circle
    pts = []
    for i in range(z):
        c = 2 * math.pi * i / z
        flank = [max(rb, rf) + (ra - max(rb, rf)) * k / 6 for k in range(7)]
        left = [(r, c - half + inv(r)) for r in flank]
        right = [(r, c + half - inv(r)) for r in reversed(flank)]
        root = [(rf, c - half - 0.6 * math.pi / z * 0.5)]
        for r, a in root + left + right:
            pts.append((r * math.cos(a), r * math.sin(a)))
    g = cq.Workplane("XY").polyline(pts).close().extrude(t)
    if bore:
        g = g.cut(bore)
    if rf - 2 - hub_r >= 3.0:                           # room for lightening holes?
        for k in range(6):
            a = 2 * math.pi * k / 6
            rr = (rf - 2 + hub_r) / 2                   # between hub and root
            g = g.cut(cq.Workplane("XY").center(rr * math.cos(a), rr * math.sin(a))
                        .circle((rf - 2 - hub_r) / 2).extrude(t))
    return g.val()


def d_bore(d, flat, t):
    c = cq.Workplane("XY").circle(d / 2).extrude(t)
    return c.cut(cq.Workplane("XY").center(d / 2 + d / 2 - flat, 0)
                  .rect(d, d).extrude(t)).val()


def hull_envelope(margin=0.0):
    """The whole hull, as a solid, optionally grown by `margin`."""
    a = hull.arc(hull.A + margin, hull.B + margin, -math.pi / 2, math.pi / 2)
    wire = cq.Wire.assembleEdges(hull.parts_to_edges([a]))
    return cq.Solid.revolve(cq.Face.makeFromWires(wire), 360,
                            cq.Vector(), cq.Vector(0, 0, 1))


# ---- impeller and motor pedestal (hull coordinates, axis = Z) ---------------
def keel_cap(margin=0.0, r_max=70.0, height=60.0):
    """The bottom of the hull (grown by `margin`) out to r_max, as a solid of
    revolution. Unlike the whole ellipsoid, it has no degenerate top pole."""
    a, b = hull.A + margin, hull.B + margin
    p1 = -math.acos(r_max / a)
    return hull.wedge_edges(hull.arc(a, b, -math.pi / 2, p1),
                            (r_max, -hull.B + height), (0, -hull.B + height), half=180.0)


def fan_hatch(locked=True):
    """The keel under the fan: a dish flush with the hull, a spigot wall and 8
    bayonet tabs, and the motor pedestal. Insert it with the tabs on the seams,
    push up, and turn it LOCK_TURN clockwise (from above) onto the lugs until
    the tabs hit the stop posts. The motor's reaction torque (the impeller
    turns counter-clockwise) holds it against the posts; the housing pressure
    holds the tabs down on the lugs. Tape the outside seam for the air seal."""
    r_d = hull.HATCH_R - HATCH_CLR
    shell = keel_cap(0).cut(keel_cap(-hull.T))
    dish = shell.intersect(cq.Solid.makeCylinder(r_d, 20, cq.Vector(0, 0, -hull.B - 5)))
    inside = keel_cap(-hull.T / 2)
    spigot = cq.Solid.makeCylinder(hull.LUG_R - 0.2, FLANGE_Z[1] + hull.B + 1,
                                   cq.Vector(0, 0, -hull.B - 1)).cut(
        cq.Solid.makeCylinder(hull.LUG_R - 0.2 - hull.T, 30, cq.Vector(0, 0, -hull.B - 1))).intersect(inside)
    ring = cq.Solid.makeCylinder(hull.HATCH_R - 0.4, FLANGE_Z[1] - FLANGE_Z[0],
                                 cq.Vector(0, 0, FLANGE_Z[0])).cut(
        cq.Solid.makeCylinder(hull.LUG_R - 0.4, 10, cq.Vector(0, 0, FLANGE_Z[0] - 5)))
    tabs = None
    for k in range(8):
        sector = hull.wedge([(0, FLANGE_Z[0] - 1), (60, FLANGE_Z[0] - 1), (60, FLANGE_Z[1] + 1),
                             (0, FLANGE_Z[1] + 1)], half=TAB_HALF).rotate(
            (0, 0, 0), (0, 0, 1), hull.HALF + 45 * k)
        t_ = ring.intersect(sector)
        tabs = t_ if tabs is None else tabs.fuse(t_)
    drum = cq.Solid.makeCylinder(PED_R, PED_TOP + hull.B + 1, cq.Vector(0, 0, -hull.B - 1)).intersect(inside)
    drum = drum.cut(cq.Solid.makeCylinder(PED_R - hull.T, PED_TOP - PED_PLATE + hull.B + 1,
                                          cq.Vector(0, 0, -hull.B - 1)))
    body = dish.fuse(spigot, tabs, drum)
    body = body.cut(cq.Solid.makeCylinder(4.5, 10, cq.Vector(0, 0, PED_TOP - 5)))   # circlip
    for k in range(4):
        a = math.radians(45 + 90 * k)
        c = MOUNT_SQUARE / math.sqrt(2)
        body = body.cut(cq.Solid.makeCylinder(1.7, 10, cq.Vector(c * math.cos(a), c * math.sin(a),
                                                                 PED_TOP - 5)))
    body = body.cut(cq.Solid.makeCylinder(WIRE_HOLE[1], 20, cq.Vector(WIRE_HOLE[0], 0, -hull.B - 5)))
    body = body.clean()
    return body.rotate((0, 0, 0), (0, 0, 1), -LOCK_TURN) if locked else body


def impeller_z():
    """Top of the blades, and the backplate underside, in hull z."""
    base = IMP_PLATE_TOP - IMP_PLATE
    return blade_top(IMP_R1), base


def blade_top(r):
    """Blade top edge: the housing's shroud curve, SHROUD_GAP below it (normal to it)."""
    zc = hull.FLOOR_Z + hull.SHROUD_RC                 # centre of the shroud turn
    rc = hull.EYE_R + hull.SHROUD_RC
    if r >= rc:
        return hull.FLOOR_Z - hull.SHROUD_GAP
    R = hull.SHROUD_RC + hull.SHROUD_GAP
    return zc - math.sqrt(max(R * R - (rc - r) ** 2, 0.0))


def impeller():
    top, base = impeller_z()
    plate = cq.Solid.makeCylinder(IMP_R2, IMP_PLATE, cq.Vector(0, 0, base))
    # scalloped rim: the backplate is cut away between neighbouring blades from
    # IMP_SCALLOP_R out to the rim, keeping a strip under each blade
    sweep = math.radians(IMP_BETA)
    ang = lambda k, r: (2 * math.pi * k / IMP_BLADES
                        - sweep * (min(max(r, IMP_R1), IMP_R2) - IMP_R1) ** 1.3
                        / (IMP_R2 - IMP_R1) ** 1.3)
    keep = IMP_T / 2 + IMP_SCALLOP_MARGIN
    rs = [IMP_SCALLOP_R + (IMP_R2 + 2 - IMP_SCALLOP_R) * i / 12 for i in range(13)]
    for k in range(IMP_BLADES):
        lead = [(r * math.cos(ang(k, r) + keep / r), r * math.sin(ang(k, r) + keep / r)) for r in rs]
        trail = [(r * math.cos(ang(k + 1, r) - keep / r), r * math.sin(ang(k + 1, r) - keep / r))
                 for r in reversed(rs)]
        def arc_(r, a0, a1, n=10):                   # the scallop's ends follow circles
            return [(r * math.cos(a0 + (a1 - a0) * j / n), r * math.sin(a0 + (a1 - a0) * j / n))
                    for j in range(1, n)]
        r_out, r_in = rs[-1], rs[0]
        outer = arc_(r_out, ang(k, r_out) + keep / r_out, ang(k + 1, r_out) - keep / r_out)
        inner = arc_(r_in, ang(k + 1, r_in) - keep / r_in, ang(k, r_in) + keep / r_in)
        scallop = (cq.Workplane("XY").workplane(offset=base - 0.5)
                     .polyline(lead + outer + trail + inner).close().extrude(IMP_PLATE + 1).val())
        plate = plate.cut(scallop)
    # cup over the motor bell: the backplate opens inside it, and its top disc
    # sits on the bell and is clamped by the prop nut
    plate = plate.cut(cq.Solid.makeCylinder(CUP_R, 5, cq.Vector(0, 0, base - 1)))
    cup = cq.Solid.makeCylinder(CUP_R + IMP_T, BELL_TOP + CUP_TOP_T - base, cq.Vector(0, 0, base)).cut(
        cq.Solid.makeCylinder(CUP_R, BELL_TOP - base, cq.Vector(0, 0, base)))
    body = plate.fuse(cup)
    # the blade tops follow the housing's shroud, SHROUD_GAP below it
    prof = [(IMP_R1 - 3 + (IMP_R2 + 8 - IMP_R1) * i / 40, 0) for i in range(41)]
    prof = [(r, blade_top(r)) for r, _ in prof]
    cutter = cq.Workplane("XZ").polyline(
        prof + [(prof[-1][0], top + 20), (prof[0][0], top + 20)]).close() \
        .revolve(360, (0, 0, 0), (0, 1, 0)).val()
    # blade: circular arc from r1 to r2, swept back by IMP_BETA
    for k in range(IMP_BLADES):
        a0 = 2 * math.pi * k / IMP_BLADES
        mid = [(IMP_R1 + (IMP_R2 - IMP_R1) * i / 8,
                a0 - sweep * (i / 8) ** 1.3) for i in range(9)]
        side = []
        for sgn in (1, -1):
            for r, a in (mid if sgn > 0 else reversed(mid)):
                da = sgn * IMP_T / 2 / r
                side.append((r * math.cos(a + da), r * math.sin(a + da)))
        blade = (cq.Workplane("XY").workplane(offset=base + IMP_PLATE)
                   .polyline(side).close().extrude(top - base + 5).val())
        body = body.fuse(blade.cut(cutter))
    body = body.cut(cq.Solid.makeCylinder(HUB_BORE / 2, 30, cq.Vector(0, 0, base - 5)))
    return body.clean()


# ---- thruster outlet: local frame, X = radial along the seam, Z = up -------
def servo_mount():
    """Cradle glued to the inside of the skin; the MG90S hangs in it, spline out.

    The servo drops in from the hull side and is held by two M2 screws driven
    from inside the hull through the plate into its tabs.
    """
    b, w = MG90S["body"]
    cz = OUT_Z + MG90S["shaft_offset"]              # body centre (spline is off-centre)
    inside = hull_envelope(-hull.T)
    shell = cq.Solid.makeBox(20, w + 12, MG90S["tabs"] + 10,
                             cq.Vector(TAB_X - MOUNT_T, SERVO_Y - w / 2 - 6, cz - MG90S["tabs"] / 2 - 5))
    hollow = cq.Solid.makeBox(20, w + 8, MG90S["tabs"] + 6,
                              cq.Vector(TAB_X, SERVO_Y - w / 2 - 4, cz - MG90S["tabs"] / 2 - 3))
    body = shell.intersect(inside).cut(hollow)
    body = body.cut(cq.Solid.makeBox(10, w + 0.4, b + 0.4,
                                     cq.Vector(TAB_X - 8, SERVO_Y - w / 2 - 0.2, cz - b / 2 - 0.2)))
    for s_ in (1, -1):
        body = body.cut(cq.Solid.makeCylinder(0.8, 10, cq.Vector(TAB_X - 8, SERVO_Y,
                        cz + s_ * MG90S["hole_pitch"] / 2), cq.Vector(1, 0, 0)))
    # windows in the side walls let glue squeeze out and save a little weight
    return body.clean()


def servo_dummy():
    """MG90S envelope, for fit checks."""
    b, w = MG90S["body"]
    cz = OUT_Z + MG90S["shaft_offset"]
    body = cq.Solid.makeBox(MG90S["below_tabs"] + MG90S["above_tabs"], w, b,
                            cq.Vector(TAB_X - MG90S["below_tabs"], SERVO_Y - w / 2, cz - b / 2))
    tabs = cq.Solid.makeBox(2.5, w, MG90S["tabs"], cq.Vector(TAB_X, SERVO_Y - w / 2, cz - MG90S["tabs"] / 2))
    spline = cq.Solid.makeCylinder(MG90S["spline_d"] / 2, MG90S["spline_tip"] - MG90S["above_tabs"],
                                   cq.Vector(TAB_X + MG90S["above_tabs"], SERVO_Y, OUT_Z), cq.Vector(1, 0, 0))
    return body.fuse(tabs, spline)


def stem():
    """Rotating swivel tube; its flange sits behind the bearing boss in the duct."""
    x0 = X_BOSS - FLANGE_T - 0.3
    length = (GEAR_X + GEAR_T + 3) - x0 + 8          # into the ring socket by 8
    ax = cq.Vector(1, 0, 0)
    tube = cq.Solid.makeCylinder(STEM_OD / 2, length, cq.Vector(x0, 0, OUT_Z), ax)
    flange = cq.Solid.makeCylinder(FLANGE_D / 2, FLANGE_T, cq.Vector(x0, 0, OUT_Z), ax)
    body = tube.fuse(flange)
    flat = cq.Solid.makeBox(GEAR_T + 2, 2 * STEM_OD, 3,
                            cq.Vector(GEAR_X - 1, -STEM_OD, OUT_Z + STEM_OD / 2 - D_FLAT))
    body = body.cut(flat)
    return body.cut(cq.Solid.makeCylinder(STEM_ID / 2, length + 2,
                                          cq.Vector(x0 - 1, 0, OUT_Z), ax)).clean()


def on_axis(g, y):
    """Gear built flat on XY (thickness +Z) -> hull-side face at GEAR_X, axis X."""
    return g.rotate((0, 0, 0), (0, 1, 0), 90).translate((GEAR_X, y, OUT_Z))


def stem_gear():
    bore = d_bore(STEM_OD + 0.2, D_FLAT + 0.1, GEAR_T)
    return on_axis(spur_gear(GEAR_Z, GEAR_M, GEAR_T, bore, hub_r=STEM_OD / 2 + 1.5), 0)


def servo_gear():
    """36T gear with a hub that reaches through the skin onto the MG90S spline.

    Press it on the spline and fix it with the servo's M2 horn screw from outside.
    """
    hub_len = GEAR_X - (TAB_X + MG90S["spline_tip"] - 3.0)   # 3 mm on the spline
    g = spur_gear(GEAR_Z, GEAR_M, GEAR_T)
    hub = cq.Solid.makeCylinder(3.7, hub_len, cq.Vector(0, 0, -hub_len))
    g = g.fuse(hub)
    g = g.cut(cq.Solid.makeCylinder(MG90S["spline_d"] / 2, 3.0, cq.Vector(0, 0, -hub_len)))  # slip fit + glue
    g = g.cut(cq.Solid.makeCylinder(1.1, hub_len + GEAR_T, cq.Vector(0, 0, -hub_len)))
    g = g.cut(cq.Solid.makeCylinder(2.2, 2.0, cq.Vector(0, 0, GEAR_T - 2.0)))  # screw head
    return on_axis(g, SERVO_Y)


def thruster_ring():
    """Air multiplier (printed exit-down, axis vertical), with the stem socket.

    Section, in (radius, height): a diffuser cone from the exit (a = 0) up to
    the throat, a Coanda lip of radius RC over its top, and a plenum around it
    closed by a 45-degree roof whose tip hangs SLOT above the lip. Every
    surface faces up or overhangs at most 45 degrees.
    """
    r_exit = RT + HD * math.tan(math.radians(TAPER))
    tip_r, tip_a = RT + RC - 1.0, HD + RC + SLOT
    wall_a = tip_a - (RO - tip_r)
    n = 8
    lip = [(RT + RC - RC * math.cos(math.pi / 2 * i / n), HD + RC * math.sin(math.pi / 2 * i / n))
           for i in range(n + 1)]                              # (RT, HD) -> (RT+RC, HD+RC)
    lip_in = [(RT + RC - (RC - RING_W) * math.cos(math.pi / 2 * i / n),
               HD + (RC - RING_W) * math.sin(math.pi / 2 * i / n)) for i in range(n, -1, -1)]
    inner = ([(r_exit, 0)] + lip + [(RT + RC, HD + RC - RING_W)] + lip_in[1:]
             + [(r_exit + RING_W, 0)])
    k = RING_W * math.sqrt(2)                       # roof thickness, measured vertically
    housing = [(r_exit + RING_W / 2, 0), (RO, 0), (RO, wall_a + k), (tip_r, tip_a + k),
               (tip_r, tip_a), (RO - RING_W, tip_a - (RO - RING_W - tip_r)),
               (RO - RING_W, RING_W), (r_exit + RING_W / 2, RING_W)]
    ring = revolve(inner).fuse(revolve(housing))
    # stem socket on the outer wall, axis along -X (towards the hull)
    sa = RING_W + STEM_OD / 2 + 0.4
    ax = cq.Vector(-1, 0, 0)
    boss = cq.Solid.makeCylinder(STEM_OD / 2 + 2.4, STEM_IN - RO + 1, cq.Vector(-RO + 1, 0, sa), ax)
    boss = boss.intersect(cq.Solid.makeBox(200, 200, 100, cq.Vector(-100, -100, 0)))
    ring = ring.fuse(boss)
    ring = ring.cut(cq.Solid.makeCylinder(STEM_OD / 2 + 0.1, 9, cq.Vector(-STEM_IN - 0.01, 0, sa),
                                          cq.Vector(1, 0, 0)))
    ring = ring.cut(cq.Solid.makeCylinder(STEM_ID / 2 - 0.5, STEM_IN - RO + 4,
                                          cq.Vector(-STEM_IN + 8, 0, sa), cq.Vector(1, 0, 0)))
    return ring.clean(), sa


def thruster_ring_placed(angle=0.0):
    """Ring on the stem end; angle 0 = jet straight down (lift up)."""
    ring, sa = thruster_ring()
    stem_end = GEAR_X + GEAR_T + 3 + 8
    r = ring.translate((stem_end - 8 + STEM_IN, 0, OUT_Z - sa))   # socket faces the hull
    return r.rotate((0, 0, OUT_Z), (1, 0, OUT_Z), angle)


# ---- export -----------------------------------------------------------------
def at_seam(shape, k=0):
    """Outlet-frame part -> hull coordinates on thruster seam k (8T: every seam,
    between slice k and k+1; 4T: every other seam, between left slice 2k and
    right slice 2k+1)."""
    return shape.rotate((0, 0, 0), (0, 0, 1), hull.HALF + (90 if FOUR else 45) * k)


OUT_DIR = os.path.join(HERE, "4T") if FOUR else HERE   # the 4-thruster parts live in 4T/
if hull.SCALE != 1:
    OUT_DIR = os.path.join(OUT_DIR, f"x{hull.SCALE:g}")


def export(name, shape, pose):
    """STEP in model coordinates, plus the print pose for make_fcstd.py."""
    cq.exporters.export(shape, os.path.join(OUT_DIR, name + ".step"))
    os.makedirs(os.path.join(OUT_DIR, "print"), exist_ok=True)
    cq.exporters.export(pose(shape), os.path.join(OUT_DIR, "print", name + ".step"))
    print(f"{name:14} {shape.Volume() / 1000:6.2f} cm3  valid {shape.isValid()}")


def flat(shape):
    b = shape.BoundingBox()
    return shape.translate((-b.center.x, -b.center.y, -b.zmin))


def axis_x_up(shape):
    return flat(shape.rotate((0, 0, 0), (0, 1, 0), -90))


if __name__ == "__main__":
    parts = {
        "impeller": (impeller(), flat),
        "fan_hatch": (fan_hatch(locked=False), flat),
        "servo_mount": (servo_mount(), axis_x_up),
        "stem": (stem(), lambda s: flat(s.rotate((0, 0, 0), (0, 1, 0), 90))),
        "stem_gear": (stem_gear(), lambda s: flat(s.rotate((0, 0, 0), (0, 1, 0), 90))),
        "servo_gear": (servo_gear(), lambda s: flat(s.rotate((0, 0, 0), (0, 1, 0), 90))),
        "thruster_ring": (thruster_ring()[0], flat),
    }
    for name, (shape, pose) in parts.items():
        export(name, shape, pose)
