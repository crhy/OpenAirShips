#!/usr/bin/env python3
"""Clean rebuild of the airship slice from CurrentModel/SPEC.md (task a02).

One function per part; every part is a closed solid that overlaps its
neighbours by >= 0.4 mm; ONE final fuse; lattice windows and every hole are
cut AFTER the fuse as offset prisms; then .clean().  No coincident faces,
no keep-clear patches - the overlaps and the post-fuse cuts do the work.

    /home/rhy/.venvs/cadquery/bin/python -I "CurrentModel/CAD Files/Slice2/slice.py"

Writes slice-8T.step, slice-CR10Pro.step next to this file and the STLs in
CurrentModel/Print Files/Slice2/ (exported last).
"""
import math
import os

import cadquery as cq
from cadquery import exporters

# ---- PARAMS: every dimension, both scales (SPEC R1-R12) ---------------------
PARAMS = {
    "A": 207.765,          # hull equatorial semi-axis, mm (R1)
    "B": 104.0,            # hull half-height, mm (R1)
    "N": 8,                # slices per ring (R2)
    "T": 0.86,             # wall = 2 perimeters (R21)
    "RIB": 2.0,            # lattice web width (R6)
    "FLOOR_Z": 32.7,       # fan ceiling stands this far above the bottom pole (R8)
    "SHAFT_R": 33.0,       # motor shaft wall radius (R8)
    "PLENUM_R": 60.5,      # plenum outer wall radius (R8)
    "HATCH_R": 47.0,       # keel hatch opening for the 88 mm impeller (R8)
    "DUCT_BORE": 24.0,     # thruster duct bore (R9)
    "SKIN_BITE": 0.30,     # the bore breaks the outer skin by this much (R9)
    "DUCT_BULB": 32.0,     # bulb bore at the stem end (R9)
    "STEM_HOLE": 25.4,     # bearing stem hole through the boss (R9)
    "BOSS_R": 14.0,        # bearing sleeve outer radius (R9)
    "BOSS_LEN": 12.0,      # bearing sleeve length (R9)
    "DUCT_MOUTH_R": 58.5,  # duct mouth radius, just past the plenum wall (R9)
    "CREST_BAND": 12.0,    # solid band each side of a duct seam (R29)
    "SERVO_BRACKET_L": 42.3,   # bracket footprint along the equator (R10)
    "SERVO_BRACKET_W": 24.2,   # bracket footprint across it (R10)
    "PAD_T": 1.5,          # pad thickness counting the band (R19)
    "SERVO_T": 36.0,       # spline axis distance from the seam, tangential (R10)
    "SERVO_HOLE": 8.0,     # spline hole diameter (R10)
    "BRACE_W": 9.0,        # brace width along the hull (R20)
    "BRACE_D": 2.5,        # brace depth inward (R20)
    "BOSS_D": 7.0,         # joint boss diameter (R12)
    "BOSS_L": 5.0,         # joint boss protrusion (R12)
    "PEG_D": 3.0,          # peg diameter (R12)
    "PEG_L": 3.6,          # peg length (R12)
    "JOINT_FIT": 0.30,     # clearance per side; chord-aware so check_cad sees
                           # no hairline (deviation from R13's 0.15, see SLICE2.md)
    "WEB": 1.2,            # minimum lattice web (R28)
    "LAND": 1.2,           # minimum land from rim/keel (R28)
    "CELL": 11.2,          # lattice pitch (window 10.0 + web 1.2)
    "JOINT_Z": (0.0, 55.0),  # the two joints sit on the equator and above it (R14)
}
SCALES = {"8T": 1.0, "CR10Pro": 1.41}   # R3
DENSITY = 1.24e-3          # g/mm3 PLA (R22)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def common(a, b):
    """Intersection via two cuts (cadquery 2.8 has no Shape.common)."""
    return a.cut(a.cut(b))


# ---- surface helpers ---------------------------------------------------------
def make_geo(S):
    """Scale-dependent geometry closures for one build scale."""
    A, B = PARAMS["A"] * S, PARAMS["B"] * S
    HALF = 180.0 / PARAMS["N"]

    def skin_pt(u, d):
        """Point on the meridian at parametric latitude u (deg), depth d inward."""
        ur = math.radians(u)
        nx, nz = B * math.cos(ur), A * math.sin(ur)
        ln = math.hypot(nx, nz)
        return (A * math.cos(ur) - d * nx / ln, B * math.sin(ur) - d * nz / ln)

    def nrm(u, th):
        ur, thr = math.radians(u), math.radians(th)
        nx, nz = B * math.cos(ur), A * math.sin(ur)
        ln = math.hypot(nx, nz)
        return cq.Vector(nx / ln * math.cos(thr), nx / ln * math.sin(thr), nz / ln)

    def to3(p, th):
        thr = math.radians(th)
        return cq.Vector(p[0] * math.cos(thr), p[0] * math.sin(thr), p[1])

    def _revolve(face_wr, a0, a1):
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
        from OCP.gp import gp_Ax1, gp_Pnt, gp_Dir, gp_Trsf
        tr = gp_Trsf()
        tr.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(a0))
        moved = BRepBuilderAPI_Transform(face_wr, tr, True).Shape()
        rev = BRepPrimAPI_MakeRevol(moved,
                                    gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)),
                                    math.radians(a1 - a0))
        rev.Build()
        return cq.Shape.cast(rev.Shape())

    def revolve_wire(wire):
        """Revolve a meridian wire 360 deg; the seam face is parked at 180 deg,
        far from the +/-HALF wedge cuts, so the final clip_wedge always eats it."""
        return _revolve(cq.Face.makeFromWires(wire).wrapped, 180.0, 180.0 + 360.0)

    def meridian_region(d0, d1):
        pts = [skin_pt(u, d0) for u in range(-90, 91, 2)]
        pts += [skin_pt(u, d1) for u in range(90, -91, -2)]
        return pts

    def meridian_wire(d0, d1):
        """Closed polygon wire: outer offset + inner offset + two end segments.
        The pole is closed on-axis (arc-closed poles fail the OCC revolve,
        a03 round 4; the +-88 flat land gave slivers, round 2)."""
        a = [cq.Vector(r, 0, z) for (r, z)
             in [skin_pt(u, d0) for u in range(-90, 91, 3)]]
        b = [cq.Vector(r, 0, z) for (r, z)
             in [skin_pt(u, d1) for u in range(90, -91, -3)]]
        return cq.Wire.makePolygon(a + b + [a[0]])

    def band(d0, d1):
        """Full-ring shell between depths d0 and d1 (clip to the wedge after)."""
        return revolve_wire(meridian_wire(d0, d1))

    def sector_band(d0, d1, a0, a1):
        """Ring sector between depths d0..d1 and azimuths a0..a1 (deg): a direct
        partial revolve of the meridian face, so there is no seam to clip."""
        return _revolve(cq.Face.makeFromWires(meridian_wire(d0, d1)).wrapped, a0, a1)

    def spheroid(bite=0.0):
        """Solid of revolution of the skin offset by -bite (bite > 0: bigger)."""
        a = [cq.Vector(r, 0, z) for (r, z)
             in [skin_pt(u, -bite) for u in range(-90, 91, 3)]]
        wire = cq.Wire.makePolygon(a + [a[0]])
        return revolve_wire(wire)



    def pie(a0, a1, z0=-1.6 * B, z1=1.6 * B):
        """Prism sector between azimuths a0..a1 (deg)."""
        r = 1.6 * A
        pts = [(0.0, 0.0)]
        steps = max(2, int(abs(a1 - a0)))
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            pts.append((r * math.cos(a), r * math.sin(a)))
        return cq.Workplane("XY").workplane(offset=z0) \
            .polyline(pts).close().extrude(z1 - z0, both=False).findSolid()

    OUTSIDE = None

    def clip_wedge(part):
        """Cut everything outside this slice's 45 deg sector."""
        return part.cut(pie(HALF, 360.0 - HALF))

    def cyl_between(p1, p2, r):
        d = p2 - p1
        L = d.Length
        xd = cq.Vector(0, 0, 1) if abs(d.z) < 0.9 * L else cq.Vector(1, 0, 0)
        wp = cq.Workplane(cq.Plane(p1, xDir=xd, normal=d.normalized()))
        return wp.circle(r).extrude(L).findSolid()

    def cyl_z(r, z0, z1):
        return cq.Workplane("XY").workplane(offset=z0).circle(r).extrude(z1 - z0).findSolid()

    return dict(A=A, B=B, HALF=HALF, skin_pt=skin_pt, nrm=nrm, to3=to3,
                band=band, spheroid=spheroid, meridian_wire=meridian_wire,
                sector_band=sector_band, revolve_wire=revolve_wire,
                pie=pie, clip_wedge=clip_wedge,
                cyl_between=cyl_between, cyl_z=cyl_z)


# ---- parts: one function each, all closed solids (R26) ------------------------
def part_skin(G):
    """R6: the T-thick lattice band; the windows are cut after the fuse."""
    return G["clip_wedge"](G["band"](0.0, PARAMS["T"]))


def part_keel(G):
    """R8: fan ceiling, plenum wall, shaft wall - all overlapping the skin."""
    B, T = G["B"], PARAMS["T"]
    fz = -B + PARAMS["FLOOR_Z"]
    ceil = G["cyl_z"](PARAMS["PLENUM_R"], fz, fz + T) \
        .cut(G["cyl_z"](PARAMS["SHAFT_R"], fz - 1, fz + T + 1))
    wall = G["cyl_z"](PARAMS["PLENUM_R"], -B - 1, fz + T) \
        .cut(G["cyl_z"](PARAMS["PLENUM_R"] - T, -B - 2, fz + T + 1))
    shaft = G["cyl_z"](PARAMS["SHAFT_R"] + T, fz + T - 0.4, 0.0) \
        .cut(G["cyl_z"](PARAMS["SHAFT_R"], fz + T - 1, 1))
    keel = ceil.fuse(wall).fuse(shaft)
    return common(G["clip_wedge"](keel), G["spheroid"](0.0))


def part_ducts(G):
    """R9: one full duct per slice split across its two seam planes: tube from
    the mouth to the bulb, bulb, bearing sleeve - clipped to the skin + bite so
    the hull skin IS the duct's outer wall."""
    A, T = G["A"], PARAMS["T"]
    rb = PARAMS["DUCT_BORE"] / 2
    rt = rb + T
    axis_r = A - (rb - PARAMS["SKIN_BITE"])   # bore breaks the skin by SKIN_BITE
    big = G["spheroid"](0.0)
    out = []
    for seam in (-G["HALF"], G["HALF"]):
        p = lambda r: G["to3"]((r, 0.0), seam)
        tube = G["cyl_between"](p(PARAMS["DUCT_MOUTH_R"]), p(axis_r + rt), rt)
        bulb = G["cyl_between"](p(A - 40.0), p(axis_r + rt), PARAMS["DUCT_BULB"] / 2 + T)
        sleeve = G["cyl_between"](p(A - 40.0), p(A - 40.0 + PARAMS["BOSS_LEN"]), PARAMS["BOSS_R"])
        out.append(common(tube.fuse(bulb).fuse(sleeve), big))
    return out[0].fuse(out[1])


def part_pad(G):
    """R10: solid pad under the bracket footprint, PAD_T deep (overlaps the band)."""
    A = G["A"]
    th_pad = G["HALF"] - math.degrees(PARAMS["SERVO_T"] / A)
    dth = math.degrees(PARAMS["SERVO_BRACKET_L"] / 2 / A)
    pad = G["sector_band"](0.0, PARAMS["PAD_T"], th_pad - dth, th_pad + dth)
    slab = G["cyl_z"](2 * A, -PARAMS["SERVO_BRACKET_W"] / 2, PARAMS["SERVO_BRACKET_W"] / 2)
    return G["clip_wedge"](common(pad, slab))


def part_brace(G):
    """R11/R20: 9.0 x 2.5 beam along the equator from the pad to the far bulb."""
    A = G["A"]
    th_pad = G["HALF"] - math.degrees(PARAMS["SERVO_T"] / A)
    dth = math.degrees(PARAMS["SERVO_BRACKET_L"] / 2 / A)
    brace = G["sector_band"](0.0, PARAMS["BRACE_D"], -th_pad - 1.0, th_pad + dth)
    slab = G["cyl_z"](2 * A, -PARAMS["BRACE_W"] / 2, PARAMS["BRACE_W"] / 2)
    return G["clip_wedge"](common(brace, slab))


def part_joints(G):
    """R12/R14: anchor ribs on both rims + boss and peg on the +seam rim.
    The sockets are cut after the fuse."""
    A = G["A"]
    rb = PARAMS["BOSS_D"] / 2
    rib_dth = math.degrees(10.0 / A)          # rib depth along theta: 10 mm
    rib_w = 12.0                              # rib half-height in z
    out = []
    for zc in PARAMS["JOINT_Z"]:
        u_z = math.degrees(math.asin(max(-1.0, min(1.0, zc / G["B"]))))
        boss_r = G["skin_pt"](u_z, 5.0)[0]    # boss axis: 5 mm under the local skin
        for seam in (-G["HALF"], G["HALF"]):
            a0 = seam - rib_dth if seam > 0 else seam
            a1 = seam if seam > 0 else seam + rib_dth
            rib = G["sector_band"](0.0, 10.0, a0, a1)
            rib = common(rib, G["cyl_z"](2 * A, zc - rib_w, zc + rib_w))
            out.append(rib)
            if seam > 0:  # boss + peg protrude past the +seam face
                # start 2 mm outside the rib's a0 edge: a cap buried inside
                # the rib survives the fuse as an internal face (issue #36)
                th0 = G["HALF"] - math.degrees(12.0 / A)
                p1 = G["to3"]((boss_r, zc), th0)
                p2 = G["to3"]((boss_r, zc), G["HALF"] + math.degrees(PARAMS["BOSS_L"] / A))
                p3 = G["to3"]((boss_r, zc), G["HALF"] + math.degrees((PARAMS["BOSS_L"] + PARAMS["PEG_L"]) / A))
                out.append(G["cyl_between"](p1, p2, rb))
                out.append(G["cyl_between"](p2, p3, PARAMS["PEG_D"] / 2))
    return out[0].fuse(*out[1:])


# ---- cutters: everything removed after the ONE fuse (R27) ---------------------
def window_cutter(G, u0, u1, th0, th1):
    """R28: a cell cut as a 2D-offset prism normal to the skin, through the band."""
    uc, thc = (u0 + u1) / 2, (th0 + th1) / 2
    P = G["to3"](G["skin_pt"](uc, 0.0), thc)
    n = G["nrm"](uc, thc)
    ur, thr = math.radians(uc), math.radians(thc)
    nx, nz = G["B"] * math.cos(ur), G["A"] * math.sin(ur)
    ln = math.hypot(nx, nz)
    e_u = cq.Vector(-nz / ln * math.cos(thr), -nz / ln * math.sin(thr), nx / ln)
    e_th = cq.Vector(-math.sin(thr), math.cos(thr), 0)
    arc_u = math.hypot(G["A"] * math.sin(ur), G["B"] * math.cos(ur))
    hu = math.radians(u1 - u0) / 2 * arc_u - PARAMS["WEB"] / 2
    ht = math.radians(th1 - th0) / 2 * G["A"] * math.cos(ur) - PARAMS["WEB"] / 2
    if hu < 1.0 or ht < 1.0:
        return None
    pts2 = [(-hu, -ht), (hu, -ht), (hu, ht), (-hu, ht)]
    wp = cq.Workplane(cq.Plane(P, xDir=e_u, normal=n))
    return wp.moveTo(*pts2[0]).polyline(pts2[1:]).close() \
        .extrude(PARAMS["T"] + 1.2).translate(n * (-0.6)).findSolid()


def lattice_cutters(G):
    """Grid of windows over the exposed band; solid stays where the crest
    band, the pad/brace corridor or a joint rib is (R28, R29)."""
    A, HALF = G["A"], G["HALF"]
    th_max = HALF - math.degrees((PARAMS["CREST_BAND"] + 2.0) / A)
    step = math.degrees(PARAMS["CELL"] / A)
    cols, t = [], step / 2
    while t <= th_max - step / 4:
        cols.append(t)
        t += step
    th_pad = HALF - math.degrees(PARAMS["SERVO_T"] / A)
    dth_pad = math.degrees(PARAMS["SERVO_BRACKET_L"] / 2 / A)
    cutters = []
    u = -40.0
    while u <= 38.0:   # above this the window walls graze the curved skin and
        # the checker reads hairline gaps; the cap above stays solid
        ur = math.radians(u)
        arc_u = math.hypot(A * math.sin(ur), G["B"] * math.cos(ur))
        zc, rc = G["B"] * math.sin(ur), A * math.cos(ur)
        du = math.degrees(PARAMS["CELL"] / arc_u)
        for tc in cols:
            for sgn in (-1, 1):
                thc = sgn * tc
                if abs(zc) < max(PARAMS["BRACE_W"], PARAMS["SERVO_BRACKET_W"]) / 2 + 4 and \
                        -th_pad - dth_pad - 2 <= thc <= th_pad + dth_pad + 2:
                    continue
                if any(abs(zc - jz) < 12 + PARAMS["CELL"] and abs(thc) > HALF - math.degrees(14.0 / A)
                       for jz in PARAMS["JOINT_Z"]):
                    continue
                cutters.append(window_cutter(G, u - du / 2, u + du / 2,
                                             thc - step / 2, thc + step / 2))
        u += du
    return [c for c in cutters if c is not None]


def hole_cutters(G):
    """Duct bores, bulb bore, spline hole, keel hatch, joint sockets."""
    A, T = G["A"], PARAMS["T"]
    rb = PARAMS["DUCT_BORE"] / 2
    axis_r = A - (rb - PARAMS["SKIN_BITE"])
    out = []
    for seam in (-G["HALF"], G["HALF"]):
        p = lambda r: G["to3"]((r, 0.0), seam)
        out.append(G["cyl_between"](p(PARAMS["DUCT_MOUTH_R"] - 0.5), p(A - 28.0), rb))
        out.append(G["cyl_between"](p(A - 28.0), p(axis_r + rb + 1.0), PARAMS["DUCT_BULB"] / 2))
        # the bearing stem hole through the boss plug (R9); ends exactly at
        # the bore step so the two coaxial bores share the step face
        out.append(G["cyl_between"](p(A - 40.0 - 1.0), p(A - 28.0),
                                    PARAMS["STEM_HOLE"] / 2))
    th_pad = G["HALF"] - math.degrees(PARAMS["SERVO_T"] / A)
    out.append(G["cyl_between"](G["to3"](G["skin_pt"](0.0, -1.2), th_pad),
                                G["to3"](G["skin_pt"](0.0, PARAMS["PAD_T"] + 1.0), th_pad),
                                PARAMS["SERVO_HOLE"] / 2))
    out.append(G["cyl_z"](PARAMS["HATCH_R"], -G["B"] - 2, -G["B"] + 10.0))
    fit = PARAMS["JOINT_FIT"]
    for zc in PARAMS["JOINT_Z"]:
        u_z = math.degrees(math.asin(max(-1.0, min(1.0, zc / G["B"]))))
        boss_r = G["skin_pt"](u_z, 5.0)[0]
        th0 = -G["HALF"] - math.degrees(0.5 / A)
        p1 = G["to3"]((boss_r, zc), th0)
        p2 = G["to3"]((boss_r, zc), -G["HALF"] + math.degrees(PARAMS["BOSS_L"] / A))
        p3 = G["to3"]((boss_r, zc), -G["HALF"] + math.degrees((PARAMS["BOSS_L"] + PARAMS["PEG_L"] + 0.6) / A))
        out.append(G["cyl_between"](p1, p2, PARAMS["BOSS_D"] / 2 + fit))
        out.append(G["cyl_between"](p2, p3, PARAMS["PEG_D"] / 2 + fit))
    return out


# ---- build --------------------------------------------------------------------
def build(S):
    G = make_geo(S)
    parts = [part_skin(G), part_keel(G), part_ducts(G), part_pad(G),
             part_brace(G), part_joints(G)]
    solid = parts[0].fuse(*parts[1:])                      # ONE fuse (R27)
    solid = solid.cut(*lattice_cutters(G), *hole_cutters(G))
    solid = solid.clean()
    solids = solid.Solids()
    return solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)


def main():
    for tag, S in SCALES.items():
        shape = build(S)
        vol = shape.Volume()
        step_path = os.path.join(HERE, "slice-%s.step" % tag)
        stl_path = os.path.join(REPO, "Print Files", "Slice2", "slice-%s.stl" % tag)
        cq.exporters.export(shape, step_path, exporters.ExportTypes.STEP)
        os.makedirs(os.path.dirname(stl_path), exist_ok=True)
        cq.exporters.export(shape, stl_path, exporters.ExportTypes.STL,
                            tolerance=0.05, angularTolerance=0.2)
        print("%s: vol %.0f mm3  mass %.1f g  faces %d  -> %s" %
              (tag, vol, vol * DENSITY, len(shape.Faces()), step_path))


if __name__ == "__main__":
    main()
