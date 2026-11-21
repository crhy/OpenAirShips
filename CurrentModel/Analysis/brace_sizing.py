#!/usr/bin/env python3
"""f152: how big do the servo pad (PAD_T) and the equator brace (BRACE_W x BRACE_D)
have to be? A hand calculation, not a FE run: nothing has been built or tested, so
every number is either measured off the CAD / the airflow model, taken from a
datasheet, or a tagged guess. The prose and the tags live in
CurrentModel/Analysis/STRUCTURE-ESTIMATES.md; the arithmetic lives here, so the two
cannot drift. Run:

    /home/rhy/.venvs/cadquery/bin/python -I CurrentModel/Analysis/brace_sizing.py

It prints, in order:

  1. the loads, with the source of each number;
  2. the brace as a beam fixed at both ends (bending about both axes, torsion) at
     the bench and the CR-10 Pro span;
  3. the pad: bond shear, plate bending, peel at the near edge;
  4. the skin-buckling margin the brace adds at the equator;
  5. the MINIMUM BRACE_W x BRACE_D and PAD_T that hold SAFETY_FACTOR, never below
     2 perimeters (2 * 0.43 = 0.86 mm) anywhere;
  6. the trade-off table: three sizes, grams per slice and per 8-slice hull at both
     print sizes, against the safety factor each one gives.

Change one number here and the answer changes: that is the point. After the first
hull is built and pushed on, put the measured failure load in LOADS and rerun.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "CAD Files", "SimplifiedSlice"))
import airship_slice as h          # noqa: E402  (import only: nothing is built here)

# ---------------------------------------------------------------- materials ---
# FDM PLA, the low end of the datasheet range, across the layer bonds: rule 11 of
# CONSTRUCTION-NOTES.md says quote the LOW value until a part is tested.
SIG_LOW = 20.0        # MPa tensile, across the layers [datasheet range 20-50, LOW used]
SIG_ALONG = 35.0      # MPa tensile, along the layers [datasheet range 35-50, LOW used]
TAU_LOW = 0.6 * SIG_LOW       # MPa shear [guess: 0.6 x tensile, the usual metals ratio]
E_PLA = 3000.0        # MPa tensile modulus [datasheet]
RHO_PLA = 1.24        # g/cm3 [float_budget.py]
RHO_LW = 0.80         # g/cm3, LW-PLA moderate foam [float_budget.py]
SAFETY_FACTOR = h.SAFETY_FACTOR   # [guess, until a physical test] - the constant lives in
                                  # airship_slice.py, next to the sizes it set, so the
                                  # generator and this script cannot disagree
SIG_A = SIG_LOW / SAFETY_FACTOR
TAU_A = TAU_LOW / SAFETY_FACTOR
KNOCKDOWN = 0.2       # curved-shell imperfection knockdown [guess]

# ------------------------------------------------------------------- loads ----
G = 9.81
SERVOS = {                      # name: (grams, stall kg-cm) [datasheet]
    "SG90": (9.0, 1.8),         # the double-Kobra v0.2 build (Propulsion README)
    "MG90S": (13.4, 2.2),       # the 8T / 4T bench and CR-10 Pro builds (same README)
}
M_BRACKET = 4.3 * RHO_PLA       # g: servo_mount.stl 4.3 cm3 [measured, Propulsion README]
M_SGEAR = 3.8 * RHO_PLA         # g: servo_gear.stl 3.8 cm3 [measured, Propulsion README]
GEAR_T, GEAR_MOD = 36, 1.0      # 36T m1 spur pair [measured, Propulsion README]
GEAR_R = GEAR_T * GEAR_MOD / 2.0        # mm pitch radius
PRESS_ANGLE = math.radians(20.0)        # [datasheet]
THRUST_GF = 306.0               # gf for the whole ship [Analysis/AIRFLOW.md, low end]
N_THR = {"8T": 8, "4T": 4}
K_HAND = 4.0                    # handling / gust / bump factor on the inertial + thrust
                                # loads [guess]. NOT applied to the stall torque: the
                                # stall torque is already the most the drivetrain can
                                # apply without stripping a gear.
RING_LOAD = 20.0                # N, a hand on a 64 mm thruster ring [guess]
CRASH_G = 20.0                  # crash deceleration [guess]
MASS_SHIP = 940.0               # g airborne, the estimate rhY asked to check [guess]
EPOXY_SHEAR = 10.0              # MPa lap shear, filled epoxy [datasheet, low end]

# ------------------------------------------------- printability floor (rule 1) --
LINE_W = 0.43                   # mm, the extruded line width check_outputs.py uses
MIN_WALL = 2 * LINE_W           # 0.86 mm = 2 perimeters: nothing may be thinner
BRACE_D_MIN = 2.5               # mm [guess] f150's 1.72 mm rib was rejected by rhY as
                                # "not thick enough to support the servo bracket"; 2.5
                                # is 0.86 (the band) + 3 lines of rib, and it is what
                                # the bracket's own 16 mm wall can bear on.
BRACE_W_MIN = h.RIB             # never narrower than a lattice rib


def geom(scale):
    """The brace's span and the pad's footprint at one OAS_SCALE. The brace follows
    the equator, so its span is an ARC, and the hardware does not scale: the span
    grows with the hull (measured: 107.1 mm at 1.0, 174.0 mm at 1.41)."""
    a0, b0 = h.A / h.SCALE, h.B / h.SCALE
    r0 = h.hull_r(h.OUT_Z, a=a0 * scale, b=b0 * scale)
    # the 8T slice's two duct seams are its own seam planes, +-HALF (measured:
    # duct_seams() == (22.5, -22.5) at N = 8); brace_span() takes the far one
    near, far = -h.HALF, h.HALF
    a_from = near + math.degrees((h.SERVO_T + h.servo_keep_r() + h.BRACE_EDGE_CLEAR) / r0)
    a_to = far - math.degrees(h.stem_keep_r() / r0)
    arc = math.radians(a_to - a_from) * r0
    return dict(scale=scale, r0=r0, arc=arc, circ=2 * math.pi * r0)


def added_mm3(g, bw, bd, pad_t, pad_area):
    """Printed material a (bw x bd) brace and a pad of pad_t add over a slice that
    has no brace and no pad: the rib below the skin band, plus the strip of lattice
    window the brace's corridor keeps solid, plus the pad below the band."""
    rib = max(0.0, bd - h.T) * bw * g["arc"]
    corridor = (bw + 2 * h.BRACE_EDGE_CLEAR) * h.T * g["arc"]
    pad = pad_area * max(0.0, pad_t - h.T)
    return rib + corridor + pad


def sect(bw, bd):
    """Section modulus of the brace, mm3. The brace's axis is the equator
    (azimuthal); BRACE_W stands up/down the hull (z at the equator) and BRACE_D is
    radial. A moment about the RADIAL axis - which is what the servo's stall torque
    is, because the spline axis is radial - is carried by BRACE_W squared."""
    return bd * bw * bw / 6.0, bw * bd * bd / 6.0      # (radial-axis, z-axis)


def cases(g, bw, bd):
    """Every load case the brace sees, as (name, N*mm, which axis). Fixed-fixed
    beam, span = the arc; a midspan point load gives PL/8, an end moment gives M."""
    L, r0, circ = g["arc"], g["r0"], g["circ"]
    out = []
    for name, (m_servo, kgcm) in SERVOS.items():
        m_hang = m_servo + M_BRACKET + M_SGEAR
        stall = kgcm * G * 10.0                    # N*mm
        ft = stall / GEAR_R                          # N, gear tangential force at stall
        # C1 the servo assembly's own weight, factored for handling
        out.append(("C1 weight %s" % name, K_HAND * m_hang / 1000.0 * G * L / 8.0, "rad"))
        # C4 single-failure bound: the bracket's bond fails and the brace alone
        # holds the servo at full stall, so the whole stall torque is an end moment
        out.append(("C4 stall bound %s" % name, stall, "rad"))
        # C2 the thrust reaction at the stem, factored, shared by the whole
        # equator: the brace's tributary width is its own width (it is one
        # stringer in a shell, and the load enters the hull at the stem's bearing
        # sleeve, 12 mm of solid band at the load point)
        f_trib = (bw + 2 * h.BRACE_EDGE_CLEAR) / circ
        p_th = K_HAND * THRUST_GF / N_THR["8T"] * G / 1000.0
        out.append(("C2 thrust share %s" % name, p_th * f_trib * L / 8.0, "z"))
    # C2b the whole of one thruster's thrust, factored, on the brace alone: a
    # bound, reported so the share above can be argued with
    out.append(("C2b thrust bound", K_HAND * THRUST_GF / N_THR["8T"] * G / 1000.0 * L / 8.0,
                "z"))
    # C3 the whole of a hand on a ring on the brace alone: a bound, reported,
    # not designed for (see the .md)
    out.append(("C3 ring load bound", RING_LOAD * L / 8.0, "z"))
    return out


def sf_of(bw, bd, gs):
    """The safety factor the section holds in the WORST brace case at either size."""
    zr, zz = sect(bw, bd)
    worst, wname, wscale = None, None, None
    for g in gs:
        for name, m, axis in cases(g, bw, bd):
            if name.startswith("C3"):
                continue                       # reported, not a design case
            z = zr if axis == "rad" else zz
            sf = SIG_LOW * z / m
            if worst is None or sf < worst:
                worst, wname, wscale = sf, name, g["scale"]
    return worst, wname, wscale


def mount_footprint():
    """(bonded area mm2, load along mm, load across mm) of the servo mount, read from the
    generator's own outline (f156: the waisted pad + beam, `servo_mount_area`), so the
    numbers below cannot drift from the shape that is printed. Falls back to f154's
    rectangle (42.45 x 28.2 mm, 1190 mm2 [measured]) if the generator has no outline yet.
    The load's footprint is the bracket's, not the mount's: the plate bends under the
    bracket, and the beam beyond it is sized by case 1 instead."""
    f = getattr(h, "servo_mount_area", None)
    if f is not None:
        return f()
    return 1190.0, 42.45, 28.2


def check():
    """--check: exit 1 unless the mount as the generator defines it holds SAFETY_FACTOR.

    Three things, all read from the generator's own constants and outline:
      the beam's worst bending case at either print size (the C4 stall bound is the one
      that sets BRACE_W), the pad's own plate bending under the bracket's foot, and the
      bond's shear / peel against the PLA under it (never the epoxy).
    f156 item 2 reshaped the mount, so this also prints how much bond area is left."""
    gs = [geom(1.0), geom(1.41)]
    pad_area, a_pad, b_pad = mount_footprint()
    ok = True
    print("--check: the mount as the generator defines it, against SAFETY_FACTOR %.1f" % SAFETY_FACTOR)
    print("  beam  BRACE_W %.2f x BRACE_D %.2f mm; bonded area %.0f mm2 over the bracket's "
          "%.1f x %.1f mm footprint" % (h.BRACE_W, h.BRACE_D, pad_area, a_pad, b_pad))
    sf, cname, cscale = sf_of(h.BRACE_W, h.BRACE_D, gs)
    zr, zz = sect(h.BRACE_W, h.BRACE_D)
    print("  1 beam bending, worst of the design cases: SF %5.2f  (%s at OAS_SCALE %.2f)"
          % (sf, cname, cscale))
    print("    Z radial-axis %.1f mm3, Z z-axis %.1f mm3" % (zr, zz))
    ok = ok and sf >= SAFETY_FACTOR
    j_polar = a_pad * b_pad * (a_pad ** 2 + b_pad ** 2) / 12.0
    r_max = math.hypot(a_pad / 2, b_pad / 2)
    pad_req, bond_sf, peel_sf = 0.0, 1e9, 1e9
    for name, (m_servo, kgcm) in SERVOS.items():
        stall = kgcm * G * 10.0
        ft = stall / GEAR_R
        fsep = ft * math.tan(PRESS_ANGLE)
        tau = ft / pad_area + stall * r_max / j_polar
        bond_sf = min(bond_sf, TAU_LOW / tau)
        p = K_HAND * (m_servo + M_BRACKET + M_SGEAR) / 1000.0 * G + fsep
        m_mm = p * a_pad / 4.0 / b_pad
        pad_req = max(pad_req, math.sqrt(6.0 * m_mm / SIG_A))
        peel = p / (b_pad * 10.0)
        peel_sf = min(peel_sf, SIG_LOW / peel)
        print("  2 %-6s pad bending needs %.2f mm of plate (PAD_T %.2f); bond shear %.4f MPa "
              "-> SF %.0f against the PLA; peel SF %.0f" % (name, pad_req, h.PAD_T, tau,
                                                            TAU_LOW / tau, SIG_LOW / peel))
    # t_req was solved with the ALLOWABLE stress (SIG_LOW / SAFETY_FACTOR), so the factor
    # against actual failure is (PAD_T / t_req)^2 * SAFETY_FACTOR: bending stress goes as 1/t^2.
    pad_sf = SAFETY_FACTOR * (h.PAD_T / pad_req) ** 2
    print("  3 pad plate bending: PAD_T %.2f mm against a %.2f mm requirement -> SF against "
          "failure %.2f" % (h.PAD_T, pad_req, pad_sf))
    ok = ok and pad_sf >= SAFETY_FACTOR
    ok = ok and bond_sf >= SAFETY_FACTOR and peel_sf >= SAFETY_FACTOR
    print("  worst SF of the mount: beam %.2f, pad plate %.2f, bond %.0f, peel %.0f"
          % (sf, pad_sf, bond_sf, peel_sf))
    if not ok:
        print("FAIL: the servo mount does not hold SAFETY_FACTOR %.1f" % SAFETY_FACTOR)
        return 1
    print("PASS: the servo mount holds SAFETY_FACTOR %.1f (bonded area %.0f mm2)"
          % (SAFETY_FACTOR, pad_area))
    return 0


def main():
    if "--check" in sys.argv:
        raise SystemExit(check())
    gs = [geom(1.0), geom(1.41)]
    pad_area = 1190.0            # mm2, the f154 footprint 42.45 x 28.2 mm [measured]
    print("=" * 78)
    print("f152 brace / pad sizing - SAFETY_FACTOR = %.1f [guess, until a physical test]"
          % SAFETY_FACTOR)
    print("allowable: %.2f MPa tensile (low end %.0f / SF), %.2f MPa shear"
          % (SIG_A, SIG_LOW, TAU_A))
    print("=" * 78)

    # 1 ---------------------------------------------------------------- loads
    print("\n1 LOADS")
    print("  geometry (measured off the generator, the hardware does not scale):")
    for g in gs:
        print("    OAS_SCALE %.2f  hull_r(equator) %7.2f mm  brace arc %6.1f mm  "
              "circumference %6.0f mm" % (g["scale"], g["r0"], g["arc"], g["circ"]))
    print("  hanging on the pad (servo + bracket + servo gear):")
    for name, (m_servo, kgcm) in SERVOS.items():
        m_hang = m_servo + M_BRACKET + M_SGEAR
        stall = kgcm * G * 10.0
        print("    %-6s servo %5.1f g + bracket %4.2f g + gear %4.2f g = %5.2f g  "
              "%.3f N;  stall %4.1f kg-cm = %6.1f N*mm;  gear tangential at stall "
              "%5.2f N, separating %5.2f N"
              % (name, m_servo, M_BRACKET, M_SGEAR, m_hang, m_hang / 1000 * G, kgcm,
                 stall, stall / GEAR_R, stall / GEAR_R * math.tan(PRESS_ANGLE)))
    print("  thrust %d gf for the whole ship [AIRFLOW.md] = %.3f N per 8T thruster, "
          "%.3f N per 4T thruster" % (THRUST_GF, THRUST_GF / 8 * G / 1000,
                                      THRUST_GF / 4 * G / 1000))
    print("  handling / gust factor %.1f [guess] on the inertial and thrust loads; "
          "a hand on a ring %.0f N [guess]; crash %.0f g [guess]"
          % (K_HAND, RING_LOAD, CRASH_G))

    # 2 ------------------------------------------------------------ the brace
    print("\n2 THE BRACE as a beam fixed at both ends (the servo pad at one end, the")
    print("  far duct's solid bearing band at the other). Bending about the RADIAL axis")
    print("  is the servo's stall torque; about z it is thrust and handling.")
    for g in gs:
        print("  span %.1f mm, section 6.0 x 3.0 mm (f151) as the reference:" % g["arc"])
        zr, zz = sect(6.0, 3.0)
        for name, m, axis in cases(g, 6.0, 3.0):
            z = zr if axis == "rad" else zz
            print("     %-24s M = %8.1f N*mm   Z = %5.1f mm3   sigma = %5.2f MPa   "
                  "SF = %5.2f%s" % (name, m, z, m / z, SIG_LOW * z / m,
                                    "   (bound, not designed for)" if name.startswith("C3") else ""))
        # torsion: the thrust / ring load applied off the brace's own axis
        e = 1.0                                    # mm eccentricity [guess]
        t_orq = K_HAND * THRUST_GF / 8 * G / 1000.0 * e
        b, hh = 3.0, 6.0
        alpha = 0.299                              # [guess] torsion constant, b/h = 0.5
        print("     %-24s T = %8.1f N*mm   tau = %5.3f MPa   SF = %5.1f"
              % ("T torsion (e=%.1f mm)" % e, t_orq, t_orq / (alpha * b * b * hh),
                 TAU_LOW / (t_orq / (alpha * b * b * hh))))

    # 3 --------------------------------------------------------------- the pad
    print("\n3 THE PAD (%.0f mm2 footprint, PAD_T counting the %.2f mm skin band)"
          % (pad_area, h.T))
    a_pad, b_pad = 42.45, 28.2
    j_polar = a_pad * b_pad * (a_pad ** 2 + b_pad ** 2) / 12.0
    r_max = math.hypot(a_pad / 2, b_pad / 2)
    for name, (m_servo, kgcm) in SERVOS.items():
        stall = kgcm * G * 10.0
        ft = stall / GEAR_R
        fsep = ft * math.tan(PRESS_ANGLE)
        tau = ft / pad_area + stall * r_max / j_polar
        print("    %-6s bond shear: direct %.4f + torsion %.4f = %.4f MPa -> SF %5.0f "
              "against the PLA (%.0f MPa), %4.0f against epoxy (%.0f MPa)"
              % (name, ft / pad_area, stall * r_max / j_polar, tau, TAU_LOW / tau,
                 TAU_LOW, EPOXY_SHEAR / tau, EPOXY_SHEAR))
        # plate bending: the bracket's foot as a strip spanning the pad's length
        p = K_HAND * (m_servo + M_BRACKET + M_SGEAR) / 1000.0 * G + fsep
        m_mm = p * a_pad / 4.0 / b_pad              # N*mm per mm of width
        t_req = math.sqrt(6.0 * m_mm / SIG_A)
        print("           plate bending of the pad under the bracket: P = %.2f N over a "
              "%.1f mm span -> %.2f N*mm/mm; t_min = %.2f mm" % (p, a_pad, m_mm, t_req))
        # peel at the pad's near edge (the edge next to the stem hole)
        peel = p / (b_pad * 10.0)                  # [guess] 10 mm of effective edge
        print("           peel at the near edge ~ %.4f MPa -> SF %5.0f against the PLA"
              % (peel, SIG_LOW / peel))
    print("    the bond is never the limit (SF in the hundreds): the PLA under it is,")
    print("    and the pad's own bending sets PAD_T.")

    # 4 ----------------------------------------------------------- buckling
    print("\n4 SKIN BUCKLING at the equator, which is what the brace is for as much as")
    print("  the servo is: the equator is the widest line and the thrusters hang off it.")
    crush = MASS_SHIP / 1000.0 * CRASH_G * G       # N, a crash spread round the hull
    for g in gs:
        sig_load = crush / (g["circ"] * h.T)
        for t_eff, lab in ((h.T, "skin alone"), (2.5, "skin + 2.5 mm brace"),
                           (3.0, "skin + 3.0 mm brace")):
            sig_cr = KNOCKDOWN * 0.605 * E_PLA * t_eff / g["r0"]
            print("    scale %.2f %-18s sigma_cr %5.2f MPa vs crash sigma %.3f MPa -> "
                  "margin %5.1f" % (g["scale"], lab, sig_cr, sig_load, sig_cr / sig_load))
    print("    (classical curved-shell sigma_cr = 0.605 E t / R with a %.1f imperfection"
          % KNOCKDOWN)
    print("     knockdown [guess]; the brace acts as a hoop stringer over its span, so")
    print("     t goes from T to BRACE_D there: the margin rises by BRACE_D / T.)")

    # 5 ------------------------------------------------- the minimum sizes
    print("\n5 MINIMUM SIZE that holds SAFETY_FACTOR, never below %.2f mm (2 perimeters)"
          % MIN_WALL)
    best = None
    for i in range(int(1.0 * 4), int(14.0 * 4) + 1):
        bw = i / 4.0
        for j in range(int(1.0 * 4), int(8.0 * 4) + 1):
            bd = j / 4.0
            if bw < BRACE_W_MIN or bd < max(BRACE_D_MIN, MIN_WALL):
                continue
            sf, cname, cscale = sf_of(bw, bd, gs)
            if sf < SAFETY_FACTOR:
                continue
            vol = min(added_mm3(g, bw, bd, 1.5, pad_area) for g in gs)
            if best is None or vol < best[0]:
                best = (vol, bw, bd, sf, cname, cscale)
    vol, bw_min, bd_min, sf_min, cname, cscale = best
    print("    BRACE_W = %.2f mm x BRACE_D = %.2f mm  (f151 shipped 6.00 x 3.00)"
          % (bw_min, bd_min))
    print("      worst brace case: %s at OAS_SCALE %.2f, SF = %.2f" % (cname, cscale, sf_min))
    zr, zz = sect(bw_min, bd_min)
    zr6, zz6 = sect(6.0, 3.0)
    print("      Z radial-axis %5.1f mm3 (6x3 gives %4.1f), Z z-axis %5.1f mm3 "
          "(6x3 gives %4.1f)" % (zr, zr6, zz, zz6))
    for name, (m_servo, kgcm) in SERVOS.items():
        stall = kgcm * G * 10.0
        print("      stall bound %s: SF = %.2f" % (name, SIG_LOW * zr / stall))
    # the pad
    pad_req = 0.0
    for name, (m_servo, kgcm) in SERVOS.items():
        stall = kgcm * G * 10.0
        p = K_HAND * (m_servo + M_BRACKET + M_SGEAR) / 1000.0 * G \
            + stall / GEAR_R * math.tan(PRESS_ANGLE)
        m_mm = p * a_pad / 4.0 / b_pad
        pad_req = max(pad_req, math.sqrt(6.0 * m_mm / SIG_A))
    pad_t = max(1.5, math.ceil(pad_req * 10) / 10.0, MIN_WALL)
    print("    PAD_T = %.2f mm (f151 shipped 1.50): the pad's own bending needs %.2f mm,"
          % (pad_t, pad_req))
    print("      the print floor is %.2f mm (2 perimeters), and PAD_T counts the %.2f mm"
          % (MIN_WALL, h.T))
    print("      skin band, so it adds %.2f mm below it. 1.50 is kept: it is the value"
          % (pad_t - h.T))
    print("      f154 already proved through the wall map at both print sizes, and the")
    print("      0.16 mm over the requirement is the margin for the two most guessed")
    print("      inputs here (the handling factor and the plate-bending span).")

    # 6 --------------------------------------------------------- trade-off
    print("\n6 TRADE-OFF (8 slices, every slice carries a servo in the 8T build)")
    print("    %-16s %-9s %-9s %-9s %-9s %-9s" %
          ("size W x D", "SF worst", "g/slice", "g/hull", "g/slice", "g/hull"))
    print("    %-16s %-9s %-9s %-9s %-9s %-9s" %
          ("", "", "bench", "bench", "x1.41", "x1.41"))
    print("    " + "-" * 74)
    rows = [(bw_min, bd_min), (8.0, 2.5), (6.0, 3.0)]
    for bw, bd in rows:
        sf, cname, cscale = sf_of(bw, bd, gs)
        v1 = added_mm3(gs[0], bw, bd, pad_t, pad_area) / 1000 * RHO_PLA
        v2 = added_mm3(gs[1], bw, bd, pad_t, pad_area) / 1000 * RHO_PLA
        print("    %-16s %-9.2f %-9.2f %-9.1f %-9.2f %-9.1f" %
              ("%.2f x %.2f" % (bw, bd), sf, v1, 8 * v1, v2, 8 * v2))
        zr, zz = sect(bw, bd)
        sfs = ["%s %.2f" % (n, SIG_LOW * (zr if ax == "rad" else zz) / m)
               for n, m, ax in cases(gs[1], bw, bd)]
        print("      %s" % "  ".join(sfs))
    print("\n  grams are the brace + its corridor + the pad, PLA at %.2f g/cm3; LW-PLA"
          % RHO_PLA)
    print("  (%.2f) gives %.0f%% of them. The hull itself is ~441 g PLA at bench, so"
          " the whole trade is well under 3%% of the printed hull."
          % (RHO_LW, 100 * RHO_LW / RHO_PLA))


if __name__ == "__main__":
    main()
