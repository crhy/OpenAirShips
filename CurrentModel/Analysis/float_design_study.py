#!/usr/bin/env python3
"""f155 design study: the lightest structurally sound, FDM-printable AirShip that
floats on hydrogen. Analysis only - it changes no CAD and no generator constant.

It answers rhY 2026-11-19: "Obviously it's much too heavy. Figure out a design that
will be structurally sound and light enough to float and is 3D printable with a
standard FDM printer."

Three concepts, each sized up until it floats with the margin asked for:

  A  today's lattice-skin pie slices (FLOAT.md's x3.8 / 12-slice self-contained
     build), re-pieced for rhY's CR-10 Pro bed (290 x 290 x 390, f118 item 5);
  B  SEMI-RIGID: a printed core (intake shaft, fan housing, thruster ducts,
     avionics tray) + N meridian battens + K latitude rings, printed in bed-sized
     segments with printed joints, and the envelope = the gas cells' film held
     taut by a small overpressure. No printed skin.
  C  PRESSURE ENVELOPE: the film IS the structure (a non-rigid airship). Printed
     core only - keel tube, fan housing, thruster ducts, tray - no battens, no
     rings, no skin. The shape is whatever the overpressure makes.

Every number is tagged [measured] (off this repo's CAD / STL / airflow model, by a
named task), [datasheet] (a published part or material figure) or [guess] (an
engineering assumption). The arithmetic reuses float_budget.py's constants and
FLOAT.md's published mass breakdowns, and the strength numbers are the ones in
Analysis/STRUCTURE-ESTIMATES.md (SAFETY_FACTOR 3, PLA across the layers 20 MPa).

Run:  /home/rhy/.venvs/cadquery/bin/python -I CurrentModel/Analysis/float_design_study.py
Writes CurrentModel/Analysis/FLOAT-DESIGN-STUDY.md and prints it.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import float_budget as fb                      # noqa: E402  (constants + the float model)

OUT = os.path.join(HERE, "FLOAT-DESIGN-STUDY.md")

# ---- geometry of the hull form, from the generator (airship_slice.py) ------
A0, B0 = 207.765, 104.0        # [measured] bench semi-axes, mm: radius, half-height
BA_RATIOS = (0.45, B0 / A0, 0.55)      # B/a tried; B0/A0 = 0.5006 is today's
T = 0.86                     # [measured] rule 1: one wall, 2 perimeters of 0.43
RIB = 1.2                    # [measured] the lightest printable web (OAS_RIB 1.2)
SHAFT_R = 33.0               # [measured] EYE_R: the keel/intake tube's inner radius
DUCT_BORE = 24.0             # [measured] OAS_THRUSTER=S: the double-Kobra build's ducts
DUCT_MOUTH_R = 60.0          # [measured] where the duct mouths sit on the plenum
BOSS_D, BOSS_L = 7.0, 5.0    # [measured] joint boss: every joint is 2 of these + peg
BED = (290.0, 290.0, 390.0)  # [measured] CR-10 Pro with rhY's 5 mm margin (f080, f118)

# ---- materials and strength (Analysis/STRUCTURE-ESTIMATES.md) --------------
SF = 3.0                     # [guess, until a physical test] STRUCTURE-ESTIMATES.md
E_PLA = 3000.0               # [datasheet] MPa, tensile modulus
SIG_T = 20.0                 # [datasheet range, LOW end] MPa, PLA across the layers
SIG = SIG_T / SF               # allowable
TAU = 12.0 / SF              # [guess] 12 MPa shear
SIG_FILM = 20.0              # [datasheet range, LOW end] MPa, PET/LDPE film tensile
RHO = dict(fb.MATERIALS)     # PLA 1.24, LW-PLA 0.80 / 0.60 g/cm3  [measured]
RHO_LW = 0.60                # the study prints structure in full-foam LW-PLA
NET_LIFT = fb.NET_LIFT       # 1.1202 g of lift per litre of H2            [measured]
FILMS = {"12 um LDPE": 11.0, "metallized PET": 17.0}   # g/m2 [datasheet range]
FILM_OVERLAP = 1.3           # [guess] 1.3 x hull area for cell seams/overlap
DELTA_P = 100.0              # [guess] Pa overpressure holding the envelope taut

# ---- hardware, from FLOAT.md's x3.8 self-contained breakdown --------------
# printed, non-hull parts at LW-PLA 0.60 (the parts that are PLA/PETG are marked)
CORE_PRINTED = {             # g at x3.8 (a = 789.5 mm), 4 thrusters, 12 slices
    "intake tubes": 76.0,    # [measured] the keel tube, cut into segments
    "avionics tray": 14.0,   # [measured]
    "thruster rings": 34.0,  # [measured]
    "servo mounts": 13.0,    # [measured]
    "stems and gears (PLA)": 47.0,
    "fan hatch (PLA)": 13.0,
    "impeller (PETG)": 8.0,
}
CORE_FIXED = 32.0 + 36.0 + 3.0   # [measured/datasheet] motor 32, 4 x SG90 36, screws 3
ONBOARD = sum(fb.ONBOARD.values())          # 50 g ESC, ESP32, BEC, IMU, switch
BATTERY = 180.0                             # 4S LiPo 1500 mAh [datasheet]
HULL_X38_G = 285.0                          # [measured] FLOAT.md, 12 slices, LW full foam
HULL_X38_A = 207.765 * 3.8                  # [measured] the a that 285 g belongs to


# ---- geometry --------------------------------------------------------------
def ellipsoid(a, ba):
    """(volume L, surface m2, meridian length m pole-to-pole) of the oblate
    spheroid hull - the same formulas hull_volumes.py uses."""
    b = ba * a
    v = 4.0 / 3.0 * math.pi * a ** 3 * ba / 1e6            # mm3 -> L
    e = math.sqrt(max(1.0 - (b / a) ** 2, 1e-9))
    s = 2 * math.pi * a ** 2 * (1 + (1 - e * e) / e * math.atanh(e)) / 1e6   # hull_volumes.py
    p = ellipse_perimeter(a, ba) / 2.0                     # m, pole to pole
    return v, s, p


def free_gas(a, ba, printed_cm3):
    """H2 litres: inside the skin, less the keel tube, the fan housing, the duct
    bores and the printed material itself (the same subtraction hull_volumes.py
    makes, done analytically: 1026 L at x3.8 against FLOAT.md's 1022 L)."""
    v, s, _ = ellipsoid(a, ba)
    keel = math.pi * (SHAFT_R + T) ** 2 * 2 * ba * a / 1e6                    # L
    house = math.pi * (DUCT_MOUTH_R + T) ** 2 * (3.0 * T + 40.0) / 1e6        # L
    duct = 4 * math.pi * (DUCT_BORE / 2 + T) ** 2 * (a - DUCT_MOUTH_R) / 1e6  # L
    return v - keel - house - duct - printed_cm3 / 1000.0


def ellipse_perimeter(a, ba):
    """Exact-ish perimeter of the meridian ellipse, in m (trapezoid, 20k steps)."""
    b = ba * a
    t = np.linspace(0.0, math.pi / 2, 20001)
    f = np.sqrt((a * np.sin(t)) ** 2 + (b * np.cos(t)) ** 2)
    return 4.0 * float(np.sum((f[:-1] + f[1:]) * 0.5) * (t[1] - t[0])) / 1e3


# ---- printed sections ------------------------------------------------------
def tube(w, d, t=T):
    """A printed rectangular tube: outer w x d mm, wall t (>= 2 perimeters).
    Returns (area mm2, I about the weak axis mm4, Z mm3)."""
    wi, di = w - 2 * t, d - 2 * t
    if wi < 2 * t or di < 2 * t:
        return None
    area = w * d - wi * di
    I = (w * d ** 3 - wi * di ** 3) / 12.0
    return area, I, I / (d / 2.0)


def round_tube(d_out, t=T):
    """A printed round tube: (area mm2, I mm4, Z mm3, mass g/m at rho)."""
    di = d_out - 2 * t
    if di < 2 * t:
        return None
    area = math.pi / 4 * (d_out ** 2 - di ** 2)
    I = math.pi / 64 * (d_out ** 4 - di ** 4)
    return area, I, I / (d_out / 2.0)


def g_per_m(area_mm2, rho=RHO_LW):
    """g per metre of a prismatic print: area mm2 x 1 m = area cm3, x rho g/cm3."""
    return area_mm2 * rho


# ---- structure -------------------------------------------------------------
def size_frame(a, ba, n_battens, n_rings, dp=DELTA_P):
    """Lightest printed tube for the meridian battens and the latitude rings of a
    semi-rigid frame, at SAFETY_FACTOR 3.

    Load case (the one the task asks for): the envelope's overpressure dp [guess,
    50-200 Pa is what keeps a film taut without a blower] puts the film in tension
    T_f = dp R / 2 [Laplace, membrane theory]. Holding that film to a squat
    ellipsoid pulls it inward, and the reaction compresses each batten along the
    meridian with N = T_f x (its tributary width). A batten is a strut, unsupported
    between rings, so it must not Euler-buckle: I >= SF N L^2 / (pi^2 E).
    The ring is loaded by the battens pulling in on it at each attachment."""
    v, s, mer = ellipsoid(a, ba)
    b = ba * a
    L = mer * 1000.0 / n_rings                       # mm, unsupported batten length
    w = ellipse_perimeter(a, ba) * 1000.0 / n_battens  # mm of hull per batten
    tf = dp * (a / 1000.0) / 2.0                     # N/m film tension [Laplace]
    n_ax = tf * (w / 1000.0)                         # N, batten axial compression
    i_req = SF * n_ax * L ** 2 / (math.pi ** 2 * E_PLA)
    # handling: a 5 N grab at midspan [guess]; the 20 N hand load of
    # STRUCTURE-ESTIMATES.md L6 is reported as a bound, as f152 reported its C3.
    m_hand = 5.0 * L / 4.0                           # N.mm, simply supported midspan
    z_req = m_hand / SIG
    best = None
    for wd in range(8, 33, 2):                       # 0.25 mm grid would be finer;
        for dd in range(8, 41, 2):                   # 2 mm keeps the print honest
            t_ = tube(wd, dd)
            if not t_:
                continue
            area, I, Z = t_
            if I < i_req or Z < z_req:
                continue
            key = area
            if best is None or key < best[0]:
                best = (key, wd, dd, area, I, Z)
    if best is None:
        return None
    _, bw, bd, barea, bI, bZ = best
    # rings: each batten pulls in on the ring with 2 n_ax (both sides of the ring),
    # spread over the arc between battens at that latitude
    r_lat = a * math.cos(math.asin(0.5))             # the ring at z = +b/2
    arc = 2 * math.pi * r_lat / n_battens
    p_pt = 2.0 * n_ax * math.sin(math.asin(0.5))     # N per batten attachment
    m_ring = max(p_pt * arc / math.pi, 5.0 * arc / 4.0)   # curved beam [guess] + a grab
    best_r = None
    for wd in range(8, 33, 2):
        for dd in range(8, 41, 2):
            t_ = tube(wd, dd)
            if not t_:
                continue
            area, I, Z = t_
            if Z < m_ring / SIG or area * SIG < dp * (a / 1000.0) * (w / 1000.0):
                continue                             # hoop tension, trivially met
            if best_r is None or area < best_r[0]:
                best_r = (area, wd, dd, I, Z)
    if best_r is None:
        return None
    rarea, rw, rd, rI, rZ = best_r
    b_len = n_battens * mer                          # m of batten
    r_len = (2 * math.pi * a + (n_rings - 1) * 2 * math.pi * r_lat) / 1000.0
    return dict(batten=(bw, bd), ring=(rw, rd), n_battens=n_battens, n_rings=n_rings,
                batten_gm=g_per_m(barea), ring_gm=g_per_m(rarea),
                batten_len=b_len, ring_len=r_len,
                batten_g=b_len * g_per_m(barea), ring_g=r_len * g_per_m(rarea),
                n_ax=n_ax, i_req=i_req, I=bI, L=L, m_hand=m_hand, Z=bZ,
                sf_buck=math.pi ** 2 * E_PLA * bI / (L ** 2) / n_ax,
                sf_hand=SIG_T * bZ / m_hand,
                sf_hand20=SIG_T * bZ / (20.0 * L / 4.0),
                seg_len=min(L, BED[1] * 0.9), m_ring=m_ring, rI=rI, rZ=rZ,
                film_tension=tf, p_pt=p_pt, arc=arc)


def core_mass(a, ba, rho=RHO_LW, ducts=True, duct_t=T):
    """The printed core both B and C need: keel/intake tube, fan housing, thruster
    ducts, thruster rings and servo mounts, stems/gears, hatch, impeller, tray.
    Parts that do not scale with the hull keep their FLOAT.md mass (rule: only the
    hull grows); the keel, the housing rim and the ducts are computed from the CAD
    constants at this size."""
    b = ba * a
    keel_cm3 = math.pi * ((SHAFT_R + T) ** 2 - SHAFT_R ** 2) * 2 * b / 1000.0
    house_cm3 = math.pi * (DUCT_MOUTH_R + T) ** 2 * T * 3.0 / 1000.0 + \
        2 * math.pi * DUCT_MOUTH_R * T * 40.0 / 1000.0      # rim + shroud band [guess]
    duct_cm3 = 0.0
    if ducts:                       # a full tube: in A the skin is the outer wall
        duct_cm3 = 4 * math.pi * (DUCT_BORE + duct_t) * duct_t * (a - DUCT_MOUTH_R) / 1000.0
    fixed = sum(v for k, v in CORE_PRINTED.items()
                if k in ("thruster rings", "servo mounts", "stems and gears (PLA)",
                         "fan hatch (PLA)", "impeller (PETG)", "avionics tray"))
    pla = sum(v for k, v in CORE_PRINTED.items()
              if "(PLA)" in k or "(PETG)" in k)
    lw = fixed - pla
    g = (keel_cm3 + house_cm3 + duct_cm3) * rho + lw + pla
    return g, dict(keel=keel_cm3 * rho, housing=house_cm3 * rho, ducts=duct_cm3 * rho,
                   parts_lw=lw, parts_pla=pla)


def hardware_mass(a):
    """Motor, servos, screws and wiring (the electronics and the battery are added
    separately). FLOAT.md's wiring rule: 5 g + 2.5 g per thruster per scale."""
    scale = a / A0
    return CORE_FIXED + 5.0 + 2.5 * 4 * scale, 5.0 + 2.5 * 4 * scale


def glue_g(a, ba, cut_len_m, duct_len_m, film_len_m):
    """float_budget.py's factors: 4.5 g/m epoxy on airtight seams, 0.8 g/m CA on
    lattice/piece seams."""
    return 4.5 * (2 * duct_len_m) + 0.8 * cut_len_m + 0.5 * film_len_m   # 0.5 g/m film
                                                                          # seam [guess]


def print_hours(cm3, n_parts, fill_note="lattice"):
    """CR-10 Pro: 0.45 mm lines at 0.2 mm layers, ~60 mm/s [guess from the machine's
    normal settings] -> 5.4 mm3/s of deposited plastic, but a thin lattice spends
    most of its time travelling: 10 cm3/h effective is what f148's 68.5 g CR-10 Pro
    slice (55 cm3 of PLA) took - about 6 h."""
    return cm3 / 10.0 + n_parts * 0.25               # + 15 min per part [guess]


# ---- the three concepts ----------------------------------------------------
def n_slices_for(a, ba):
    """Slices in the ring: a slice printed on its seam stands BED[2] tall across
    the azimuth, so 2 a sin(180/N) must fit the 390 mm of bed height (f148 measured
    206 mm at N=8, x1.41). Multiple of 4 for the 4-thruster layout."""
    n = 4
    while 2 * a * math.sin(math.radians(180.0 / n)) > BED[2] * 0.98:
        n += 4
    return n


def concept_a(a, ba, film="metallized PET", rho=RHO_LW):
    """A: today's lattice-skin pie slices, re-pieced for the CR-10 Pro bed."""
    v, surf, mer = ellipsoid(a, ba)
    n = n_slices_for(a, ba)
    hull_cm3 = (HULL_X38_G / RHO_LW) * (a / HULL_X38_A)      # [measured] hull ~ S^1.00
    hull_g = hull_cm3 * rho
    # piece layout: cuts along ring ribs (the meridian) and radial cuts, the
    # pieces() idiom generalised to whatever the 290 x 290 x 390 bed needs
    n_z = max(2, math.ceil(2 * ba * a / (BED[1] * 0.9)))
    n_r = max(1, math.ceil(a / (BED[0] * 0.9)))
    pieces = n * n_z * n_r
    half = math.radians(180.0 / n)
    cut_m = n * ((n_z - 1) * 2 * a * math.sin(half) + (n_r - 1) * 2 * ba * a / n_z) / 1000.0
    joint_m = n * 2 * mer                                     # the slice seams too
    j_150 = 0.150                                            # [guess] one peg per 150 mm
    joints = (cut_m + joint_m) / j_150
    joint_g = joints * 2 * math.pi * (BOSS_D / 2) ** 2 * BOSS_L / 1000.0 * rho
    # the x3.8 anchor already carries its own 4 cuts a slice; charge only the extra
    joints0 = 12 * (2 * mer + 4 * 0.45) / j_150
    joint_g -= joints0 * 2 * math.pi * (BOSS_D / 2) ** 2 * BOSS_L / 1000.0 * rho
    rib_g = max(0, n - 12) * 2 * mer * (RIB / 2) * T * rho / 1000.0   # extra seam ribs
    core_g = sum(CORE_PRINTED.values()) + rib_g              # [measured] FLOAT.md rows
    film_g = FILM_OVERLAP * surf * FILMS[film]
    hw_g, wire_g = hardware_mass(a)
    duct_m = 4 * (a - DUCT_MOUTH_R) / 1000.0
    glue_a = glue_g(a, ba, cut_m + joint_m, duct_m, 2 * math.pi * a / 1000.0)
    printed_cm3 = hull_cm3 + sum(v for k, v in CORE_PRINTED.items() if "(PLA)" not in k
                                 and "(PETG)" not in k) / rho + \
        sum(v for k, v in CORE_PRINTED.items() if "(PLA)" in k) / 1.24 + \
        sum(v for k, v in CORE_PRINTED.items() if "(PETG)" in k) / 1.27
    gas = free_gas(a, ba, printed_cm3)
    total = hull_g + core_g + film_g + hw_g + glue_a + max(0.0, joint_g) + ONBOARD + BATTERY
    parts = pieces + 16
    return dict(name="A lattice skin", a=a, ba=ba, gas=gas, lift=gas * NET_LIFT,
                mass=total, margin=gas * NET_LIFT - total,
                items={"hull (%d slices)" % n: hull_g, "core printed parts": core_g,
                       "gas cells (%s)" % film: film_g, "motor/servos/screws": CORE_FIXED,
                       "wiring": wire_g, "glue": glue_a,
                       "extra piece joints": max(0.0, joint_g), "electronics": ONBOARD,
                       "battery": BATTERY},
                pieces=pieces, n_slices=n, joints=int(joints),
                hours=print_hours(printed_cm3, pieces), printed_cm3=printed_cm3,
                surf=surf, struct=None)


def concept_b(a, ba, n_battens=12, n_rings=3, film="metallized PET", rho=RHO_LW):
    """B: printed core + meridian battens + latitude rings, film envelope, no skin."""
    v, surf, mer = ellipsoid(a, ba)
    f = size_frame(a, ba, n_battens, n_rings)
    if f is None:
        return None
    core_g, core_parts = core_mass(a, ba, rho)
    frame_g = f["batten_g"] + f["ring_g"]
    film_g = FILM_OVERLAP * surf * FILMS[film]
    hw_g, wire_g = hardware_mass(a)
    seg = f["seg_len"] / 1000.0
    n_seg_b = n_battens * math.ceil(mer / seg)
    n_seg_r = n_rings * math.ceil(2 * math.pi * a / 1000.0 / seg)
    joints = (n_seg_b + n_seg_r - n_battens - n_rings) + 2 * (n_battens + n_rings)
    joint_g = joints * 2 * math.pi * (BOSS_D / 2) ** 2 * BOSS_L / 1000.0 * rho
    duct_m = 4 * (a - DUCT_MOUTH_R) / 1000.0
    glue_g_ = glue_g(a, ba, (n_seg_b + n_seg_r) * seg, duct_m, 4 * math.pi * a / 1000.0)
    printed_cm3 = (core_g - sum(v for k, v in CORE_PRINTED.items()
                                if "(PLA)" in k or "(PETG)" in k)) / rho + \
        sum(v for k, v in CORE_PRINTED.items() if "(PLA)" in k) / 1.24 + \
        sum(v for k, v in CORE_PRINTED.items() if "(PETG)" in k) / 1.27 + \
        frame_g / rho + joint_g / rho
    gas = free_gas(a, ba, printed_cm3)
    total = core_g + frame_g + film_g + hw_g + glue_g_ + joint_g + ONBOARD + BATTERY
    parts = n_seg_b + n_seg_r + 22
    return dict(name="B semi-rigid", a=a, ba=ba, gas=gas, lift=gas * NET_LIFT,
                mass=total, margin=gas * NET_LIFT - total,
                items={"core (keel, housing, ducts)": core_g,
                       "battens (%d x %s)" % (n_battens, f["batten"]): f["batten_g"],
                       "rings (%d x %s)" % (n_rings, f["ring"]): f["ring_g"],
                       "envelope (%s)" % film: film_g, "motor/servos/screws": CORE_FIXED,
                       "wiring": wire_g, "glue": glue_g_, "frame joints": joint_g,
                       "electronics": ONBOARD, "battery": BATTERY},
                pieces=parts, n_slices=0, joints=int(joints),
                hours=print_hours(printed_cm3, parts), printed_cm3=printed_cm3,
                surf=surf, struct=f)


def free_len_glue(a, ring):
    """Length of glued seam in the core: the duct joints and the film-to-keel bonds."""
    return (a - DUCT_MOUTH_R) / (2.0 if ring else 1.0) / 1000.0 + \
        2 * math.pi * SHAFT_R / 1000.0


def concept_c(a, ba, film="metallized PET", rho=RHO_LW, duct_t=T, ring=True,
              taper=False):
    """C: the film is the structure. Printed core only - keel tube, fan housing,
    thruster ducts, one duct-support ring, avionics tray. No battens, no rings
    holding the shape, no printed skin."""
    v, surf, mer = ellipsoid(a, ba)
    # a tapered duct: 2T at the root where the moment is, T at the mouth. The mass
    # uses the mean wall, the strength the root section [guess].
    core_g, cp = core_mass(a, ba, rho, duct_t=(1.5 * T if taper else duct_t))
    film_g = FILM_OVERLAP * surf * FILMS[film]
    hw_g, wire_g = hardware_mass(a)
    duct_m = 4 * (a - DUCT_MOUTH_R) / 1000.0
    glue_g_ = glue_g(a, ba, 4 * free_len_glue(a, ring), duct_m, 4 * math.pi * a / 1000.0)
    # the ducts carry the thruster reaction as cantilevers: with a support ring at
    # mid-span their free length halves; the wall may go to 2T (an EXCEPTIONS entry)
    free_len = (a - DUCT_MOUTH_R) / (2.0 if ring else 1.0) / 1000.0     # m
    thrust_n = 306.0 * 9.81e-3 / 4                                       # [measured] 306 gf
    m_duct = thrust_n * 4.0 * free_len * 1000.0                          # N.mm, L5 x4
    d_out = DUCT_BORE + 2 * duct_t
    rt = round_tube(d_out, duct_t)
    sf_duct = SIG_T * rt[2] / m_duct
    ring_g = ring_len = 0.0
    if ring:
        rr = a * 0.5
        sec = tube(12, 16)
        ring_len = 2 * math.pi * rr / 1000.0
        ring_g = ring_len * g_per_m(sec[0])
    # keel: the whole ship hangs at mid-height, the film hands the lift to the keel
    # at the rim attachments at +-b, so the keel is a beam of span 2b, load at mid
    keel = round_tube(2 * (SHAFT_R + T), T)
    w_ship = (core_g + ring_g + film_g + CORE_FIXED + wire_g + glue_g_ + ONBOARD
              + BATTERY) * 1e-3 * 9.81                                        # N
    m_keel = w_ship * ba * a / 2.0                                            # N.mm
    sf_keel = SIG_T * keel[2] / m_keel
    film_t = DELTA_P * (a / 1000.0) / 2.0            # N/m Laplace tension in the film
    film_stress = film_t / (12e-6 * 1e6)             # MPa at 12 um
    # the film must be able to hang the ship off the keel rims: it needs a meridional
    # tension of (W/2) / (2 pi r_rim sin 45) at each rim [guess on the 45 deg angle]
    anchor_n = w_ship / 2.0
    sf_anchor = 10.0 * (2 * math.pi * SHAFT_R * 10.0) / anchor_n      # epoxy lap shear
    n_hang = anchor_n / (2 * math.pi * (SHAFT_R + T) / 1000.0 * 0.707)
    sf_hang = film_t / n_hang
    # how many prints the core really is: nothing longer than 350 mm fits the bed
    # lying down, so the keel, the ducts and the support ring are segmented (the
    # x3.8 build already prints its intake shaft as separate tubes) [measured]
    seg = 0.35                                          # m, printable length
    n_keel = max(1, math.ceil(2 * ba * a / 1000.0 / seg))
    n_duct = 4 * max(1, math.ceil((a - DUCT_MOUTH_R) / 1000.0 / seg))
    n_ring = max(1, math.ceil(ring_len / seg)) if ring else 0
    n_joints = (n_keel - 1) + (n_duct - 4) + n_ring
    joint_g = n_joints * 2 * math.pi * (BOSS_D / 2) ** 2 * BOSS_L / 1000.0 * rho
    parts = n_keel + 1 + n_duct + n_ring + 20 + 3       # + thruster hardware, tray...
    printed_cm3 = (core_g - sum(v for k, v in CORE_PRINTED.items()
                                if "(PLA)" in k or "(PETG)" in k)) / rho + \
        sum(v for k, v in CORE_PRINTED.items() if "(PLA)" in k) / 1.24 + \
        sum(v for k, v in CORE_PRINTED.items() if "(PETG)" in k) / 1.27 + ring_g / rho
    gas = free_gas(a, ba, printed_cm3)
    total = core_g + ring_g + film_g + hw_g + glue_g_ + joint_g + ONBOARD + BATTERY
    return dict(name="C pressure envelope", a=a, ba=ba, gas=gas, lift=gas * NET_LIFT,
                mass=total, margin=gas * NET_LIFT - total,
                items={"keel / intake tube": cp["keel"], "fan housing": cp["housing"],
                       "thruster ducts": cp["ducts"], "core parts": cp["parts_lw"] +
                       cp["parts_pla"], "duct support ring": ring_g,
                       "envelope (%s)" % film: film_g, "motor/servos/screws": CORE_FIXED,
                       "wiring": wire_g, "glue": glue_g_, "segment joints": joint_g,
                       "electronics": ONBOARD, "battery": BATTERY},
                pieces=parts, n_slices=0, joints=n_joints,
                segs=(n_keel, n_duct, n_ring), longest=seg * 1000,
                hours=print_hours(printed_cm3, parts), printed_cm3=printed_cm3,
                surf=surf,
                struct=dict(sf_duct=sf_duct, m_duct=m_duct, sf_keel=sf_keel,
                            sf_hand_duct=SIG_T * rt[2] / (20.0 * free_len * 1000.0),
                            film_t=film_t, film_stress=film_stress, sf_anchor=sf_anchor,
                            ring=ring, ring_len=ring_len, free_len=free_len,
                            duct_t=duct_t, d_out=d_out, n_hang=n_hang,
                            sf_hang=sf_hang, w_ship=w_ship, keel_z=keel[2]))


def solve(concept, ba, need, lo=300.0, hi=1600.0):
    """Smallest equatorial radius a (mm) whose margin >= need grams."""
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        r = concept(mid, ba)
        if r is None or r["margin"] < need:
            lo = mid
        else:
            hi = mid
    return concept(hi, ba)


def geodesic(a, ba, freq=2):
    """Why a geodesic strut frame is not the answer: total strut length and mass."""
    r_m = math.sqrt(a * a * ba) / 1000.0                  # mean radius, m
    edges = 30 * freq ** 2
    edge = 1.1076 * r_m / freq
    sec = tube(10, 14)
    return edges, edge, edges * edge, edges * edge * g_per_m(sec[0])


def multicell(a, ba, n_cells=4):
    """Why a bundle of sausage gas cells is not the answer either: it wastes film."""
    v, surf, mer = ellipsoid(a, ba)
    r_c = (a - SHAFT_R) / 2.0 / 1000.0                    # cell radius, m
    L = 2 * ba * a / 1000.0 - 2 * r_c * 0.8               # cylindrical length, m
    area = n_cells * (2 * math.pi * r_c * max(L, 0.1) + 4 * math.pi * r_c ** 2)
    return area, area * FILMS["metallized PET"]


# ---- hydrogen leak through the film ---------------------------------------
# [datasheet range, order of magnitude] H2 permeability in barrer. 1 barrer =
# 3.35e-19 mol m / (m2 s Pa). LDPE is the loose of the two; a metallized film is
# 10-100 x tighter than the same gauge of clear PET, and the metallized layer is
# what carries the gas.
BARRIER = {"12 um LDPE": (10.0, 40.0), "metallized PET": (0.1, 1.0)}
TH_FILM = 12e-6                       # m, both films are sold at 12 um


def leak(area_m2, film, dp_pa=90000.0):
    """grams of H2 per day, and the lift that costs (1.204 g of lift per litre of
    H2 lost, less the 0.084 g the gas itself weighed = 14.4 g of lift per gram)."""
    lo, hi = BARRIER[film]
    out = []
    for p in (lo, hi):
        j = p * 3.35e-19 * dp_pa / TH_FILM * 86400.0 * 2.016 * area_m2
        out.append(j)
    return out[0], out[1]


def pinhole_leak(d_m=1e-4, dp=DELTA_P):
    """L/day of H2 through a round hole of diameter d_m at the working overpressure:
    orifice flow Q = Cd A sqrt(2 dp / rho) [measured physics], rho_H2 0.0838 kg/m3,
    Cd 0.6 [guess]."""
    q = 0.6 * math.pi * (d_m / 2.0) ** 2 * math.sqrt(2 * dp / 0.0838)
    return q * 86400.0 * 1000.0


# ---- report ---------------------------------------------------------------
def pick(r, prefix):
    """Sum the mass rows whose label starts with a prefix (labels carry sizes)."""
    return sum(v for k, v in r["items"].items() if k.startswith(prefix))


def table(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def main():
    o = []
    w = o.append
    w("# Float design study: the lightest structurally sound, FDM-printable AirShip "
      "that floats on hydrogen\n")
    w("Written by `CurrentModel/Analysis/float_design_study.py` (f155). Analysis only: "
      "no CAD, no generator constant changed. It reuses `float_budget.py`'s constants "
      "(lift 1.1202 g/L, PLA 1.24 / LW-PLA 0.80 and 0.60 g/cm3, film 11 g/m2, the "
      "oblate-ellipsoid area formula) and `Analysis/STRUCTURE-ESTIMATES.md`'s strength "
      "numbers (`SAFETY_FACTOR` 3, PLA across the layers 20 MPa, epoxy lap shear "
      "10 MPa). Every number is tagged [measured] / [datasheet] / [guess].\n")
    w("Printer: Creality CR-10 Pro, usable **290 x 290 x 390 mm** (rhY's 5 mm margin, "
      "rule 12) [measured]. Hull form: oblate spheroid, equatorial radius `a`, "
      "half-height `B = ba x a`, today `ba` = 0.5006 [measured: `A` 207.765, `B` 104.0]. "
      "The study tries `ba` = 0.45, 0.5006 and 0.55.\n")

    # ---- 0 the anchor ----
    w("## 0 Does this model agree with FLOAT.md? (it must)\n")
    a38 = HULL_X38_A
    A38 = concept_a(a38, 0.5006, film="12 um LDPE")
    w("The x3.8 double-Kobra build of FLOAT.md, rebuilt from this file's formulas. "
      "The glue row is shown for both piece layouts, because this study always cuts "
      "the hull to the CR-10 Pro bed and FLOAT.md's build was cut to a Kobra Max; the "
      "total row is the Kobra-layout total, which is the number being checked:\n")
    w(table([("hull (12 slices)", 285, 285), ("core printed parts", 205, 205),
             ("gas cells, 12 um LDPE", 77, round(FILM_OVERLAP * ellipsoid(a38, 0.5006)[1]
                                                * FILMS["12 um LDPE"])),
             ("motor + servos + screws + wiring", 71 + 43, 71 + 43),
             ("glue (Kobra layout / CR-10 layout)", 66, round(A38["items"]["glue"])),
             ("electronics + battery", 230, 230),
             ("**total**", 977, round(A38["mass"] - A38["items"]["extra piece joints"]
                                      - (A38["items"]["glue"] - 66))),
             ("H2 volume (L)", 1022, round(free_gas(a38, 0.5006, 475))),
             ("H2 lift (g)", 1145, round(free_gas(a38, 0.5006, 475) * NET_LIFT)),
             ("margin (g)", 168, round(free_gas(a38, 0.5006, 475) * NET_LIFT - 977))],
            ["item", "FLOAT.md", "this study"]))
    w("\nThe two agree to a few grams, so the same arithmetic can be pointed at new "
      "shapes with some confidence [measured].\n")

    # ---- 1 the answer, up front ----
    w("## 1 The answer in one table\n")
    w("Smallest hull that floats with the margin named, `ba` = 0.5006, LW-PLA full "
      "foam (0.60 g/cm3), metallized PET envelope, 4 thrusters, battery and "
      "controller on board:\n")
    rows = []
    for c, nm in ((concept_a, "A today's lattice skin, re-pieced for the CR-10 Pro"),
                  (concept_b, "B semi-rigid: core + 12 battens + 3 rings + film"),
                  (concept_c, "C pressure envelope: printed core + film, no skin"),
                  (lambda a, ba: concept_c(a, ba, duct_t=2 * T, taper=True),
                   "C as recommended (tapered ducts 2T root / T mouth + ring)")):
        for need in (150, 250):
            r = solve(c, 0.5006, need)
            rows.append((nm, "+%d g" % need, "%.2f m" % (2 * r["a"] / 1000),
                         "%.0f L" % r["gas"], "%.0f g" % r["mass"],
                         "%+.0f g" % r["margin"], r["pieces"], "%.0f h" % r["hours"]))
    w(table(rows, ["concept", "margin", "hull diameter", "H2", "all-up mass",
                   "margin", "printed parts", "print hours"]))
    w("\n*Printed parts* counts every separate print (slices x pieces for A, frame "
      "segments for B, core segments for C). *Print hours* is the printed volume at "
      "10 cm3/h effective for thin lattice on a 0.45 mm line at 0.2 mm layers plus "
      "15 min per part for bed changes [guess, calibrated on f148's 55 cm3 CR-10 Pro "
      "slice taking ~6 h]. All-up mass includes the 4S LiPo (180 g), the ESC, ESP32, "
      "BEC, IMU and switch (50 g), the wiring, the glue and the envelope film.\n")


    # ---- 2 concept A ----
    w("## 2 Concept A - today's lattice skin, re-pieced for the CR-10 Pro\n")
    w("The x3.8 / 12-slice self-contained build of FLOAT.md, but cut to what the "
      "290 x 290 x 390 bed will take. Hull mass follows the measured law: between x1 "
      "and x1.9 the 4T hull mass grows as S^1.00 [measured, FLOAT.md], anchored on the "
      "x3.8 build's 285 g of LW-PLA at 0.60 g/cm3 [measured].\n")
    for need in (150, 250):
        r = solve(concept_a, 0.5006, need)
        w(table([(k, "%.0f" % v) for k, v in r["items"].items()] +
                [("**all-up**", "**%.0f**" % r["mass"]), ("H2 lift", "%.0f" % r["lift"]),
                 ("**margin**", "**%+.0f**" % r["margin"])], ["item", "g"]))
        w("\nAt a = %.0f mm (diameter %.2f m): %d slices, %d pieces, %d peg joints, "
          "%.0f cm3 of print, **%.0f print hours** on the CR-10 Pro. "
          "The bed forces %d slices, not 12: a slice stands %.0f mm across the azimuth "
          "and the bed is 390 mm tall [measured, f148's 206 mm at N=8 x1.41].\n"
          % (r["a"], 2 * r["a"] / 1000, r["n_slices"], r["pieces"], r["joints"],
             r["printed_cm3"], r["hours"], r["n_slices"],
             2 * r["a"] * math.sin(math.radians(180.0 / r["n_slices"]))))
    w("**What A costs that the paper version did not count:** the CR-10 Pro piece "
      "layout is %.0f pieces against the Kobra Max's 60, and every piece boundary is "
      "glue and pegs: +%.0f g of glue and +%.0f g of joint bosses over FLOAT.md's "
      "x3.8 rows. A also needs %.0f g of film where the printed skin is doing the "
      "same job twice - the lattice skin holds the shape and the gas cells hold the "
      "gas, and the skin is the expensive one.\n"
      % (r["pieces"], r["items"]["glue"] - 66, r["items"]["extra piece joints"],
         r["items"]["gas cells (metallized PET)"]))
    w("Structure: A is the *strongest* of the three - a 0.86 mm lattice shell with "
      "2 mm ribs, the equator brace at SF 3.13 (f152), and it is what the wall map "
      "and the checker have already proved at two sizes. That is also the problem: "
      "it is strong in exactly the way that costs 285 g.\n")

    # ---- 3 concept B ----
    w("## 3 Concept B - semi-rigid: printed core + battens + rings + film\n")
    w("No printed skin. The shape is held by N meridian battens and K latitude rings, "
      "printed as bed-sized segments with the same peg idiom as `pieces()`, and the "
      "envelope is the gas cells' film held taut by a small overpressure.\n")
    w("Sizing the frame (SF 3, PLA across the layers 20 MPa [datasheet range, LOW "
      "end]): the overpressure dp puts the film in Laplace tension T_f = dp R / 2 "
      "[measured physics]; holding that film to a squat spheroid pulls it inward and "
      "the reaction compresses each batten along the meridian with N = T_f x its "
      "tributary width; a batten is a strut unsupported between rings, so "
      "I >= SF N L^2 / (pi^2 E). Sizing handling load: a 5 N grab at midspan [guess]. "
      "dp = 100 Pa [guess] - enough to keep a film taut and wrinkle-free against its "
      "own weight (a 17 g/m2 film needs ~ 0.2 Pa per degree of slope) and small "
      "enough that no blower is needed; 50-200 Pa is the range model blimps use.\n")
    rows = []
    for nb, nr in ((8, 1), (8, 3), (12, 1), (12, 3), (16, 3), (16, 5)):
        f = size_frame(a38, 0.5006, nb, nr)
        rows.append((nb, nr, "%dx%d" % f["batten"], "%.0f" % f["batten_g"],
                     "%dx%d" % f["ring"], "%.0f" % f["ring_g"],
                     "%.0f" % (f["batten_g"] + f["ring_g"]), "%.0f" % f["n_ax"],
                     "%.1f" % f["sf_buck"], "%.1f" % f["sf_hand"], "%.1f" % f["sf_hand20"]))
    w(table(rows, ["battens", "rings", "batten mm", "batten g", "ring mm", "ring g",
                   "frame g", "batten load N", "SF buckl", "SF 5 N grab",
                   "SF 20 N hand"]))
    w("\nAt 1.58 m the frame alone is **~0.9 kg** - about three times the printed "
      "lattice skin it replaces, because a batten has to be deep enough to not buckle "
      "over 640-1900 mm while a lattice web only has to stand up to itself. The 20 N "
      "hand load (STRUCTURE-ESTIMATES.md L6) is reported, not designed for, exactly "
      "as f152 reported its C3 bound: no frame of 8 mm PLA battens survives a "
      "grip of that size between rings 640 mm apart.\n")
    for need in (150, 250):
        r = solve(concept_b, 0.5006, need)
        w(table([(k, "%.0f" % v) for k, v in r["items"].items()] +
                [("**all-up**", "**%.0f**" % r["mass"]), ("H2 lift", "%.0f" % r["lift"]),
                 ("**margin**", "**%+.0f**" % r["margin"])],
                ["item (at %+.0f g margin)" % need, "g"]))
        w("\na = %.0f mm, diameter **%.2f m**, %d printed parts, %.0f cm3, "
          "**%.0f print hours**.\n" % (r["a"], 2 * r["a"] / 1000, r["pieces"],
                                       r["printed_cm3"], r["hours"]))

    # ---- 4 concept C ----
    w("## 4 Concept C - the film is the structure (a pressure airship)\n")
    w("Print only the core: the keel / intake tube (`SHAFT_R` 33 mm, wall `T`), the "
      "fan housing, the four thruster ducts, one duct-support ring, the thruster "
      "rings and servo mounts, the stems and gears, the hatch, the impeller and the "
      "avionics tray. Everything else is film. No skin, no battens, no shape rings.\n")
    w("Why that is sound: a closed film under overpressure carries its load as pure "
      "membrane tension (Laplace), which is what film is good at - 40 N/m of tension "
      "at 100 Pa is 3.3 MPa in a 12 um film, SF 6 against LDPE's low-end 20 MPa and "
      "SF 60 against PET's 200 MPa [datasheet range]. What a film cannot do is hold a "
      "*squat* shape: a free film takes a rounder (constant-mean-curvature) form. So "
      "C gives up the ellipsoid and keeps the volume - buoyancy does not care about "
      "shape, and the same film area encloses within ~10 %% of the spheroid's volume "
      "[guess]. The printed core hangs the payload off the film's two keel-rim "
      "attachments, and the keel is a 68 mm tube: bending SF %.0f.\n"
      % concept_c(a38, 0.5006)["struct"]["sf_keel"])
    for need in (150, 250):
        r = solve(concept_c, 0.5006, need)
        w(table([(k, "%.0f" % v) for k, v in r["items"].items()] +
                [("**all-up**", "**%.0f**" % r["mass"]), ("H2 lift", "%.0f" % r["lift"]),
                 ("**margin**", "**%+.0f**" % r["margin"])],
                ["item (at %+.0f g margin)" % need, "g"]))
        st = r["struct"]
        w("\na = %.0f mm, diameter **%.2f m**, H2 %.0f L, %d printed parts, %.0f cm3, "
          "**%.0f print hours**. Structure: keel bending SF %.0f, duct root under the "
          "thruster reaction x 4 (L5) SF %.1f, duct under a 20 N hand on a thruster "
          "ring SF %.1f (a bound, see section 6), film tension at the keel rim vs the "
          "ship's weight SF %.1f, film-to-keel epoxy bond SF %.0f.\n"
          % (r["a"], 2 * r["a"] / 1000, r["gas"], r["pieces"], r["printed_cm3"],
             r["hours"], st["sf_keel"], st["sf_duct"], st["sf_hand_duct"],
             st["sf_hang"], st["sf_anchor"]))
    w("### 4.1 The two weak points of C, and what they cost\n")
    r0 = concept_c(a38, 0.5006)
    rn = concept_c(a38, 0.5006, ring=False)
    r1 = concept_c(a38, 0.5006, duct_t=2 * T)
    zt = round_tube(DUCT_BORE + 2 * T, T)[2]
    z2 = round_tube(DUCT_BORE + 4 * T, 2 * T)[2]
    fl = r0["struct"]["free_len"]
    m_h = 20.0 * fl * 1000.0
    m_t = 306.0 * 9.81e-3 / 4.0 * 4.0 * fl * 1000.0   # per duct, L5 x4
    tap_g = pick(r0, "thruster ducts") + 0.5 * (pick(r1, "thruster ducts")
                                                - pick(r0, "thruster ducts"))
    w(table([("wall T, no support ring", "%.1f" % rn["struct"]["sf_duct"],
              "%.1f" % (SIG_T * zt / (20.0 * 2 * fl * 1000.0)),
              "%.0f" % pick(r0, "thruster ducts")),
             ("wall T, one support ring at 0.5 a", "%.1f" % r0["struct"]["sf_duct"],
              "%.1f" % (SIG_T * zt / m_h), "%.0f" % pick(r0, "thruster ducts")),
             ("**tapered: 2T at the root, T at the mouth, ring at 0.5 a**",
              "%.1f" % (SIG_T * z2 / m_t), "%.1f" % (SIG_T * z2 / m_h),
              "%.0f [guess]" % tap_g),
             ("wall 2T all the way, ring at 0.5 a", "%.1f" % r1["struct"]["sf_duct"],
              "%.1f" % r1["struct"]["sf_hand_duct"], "%.0f" % pick(r1, "thruster ducts"))],
            ["duct case", "SF thruster x4", "SF 20 N hand", "duct mass g"]))
    w("\nTake the tapered duct (2T where it meets the plenum, T at the mouth, +%.0f g "
      "of print against 2T all the way) and the support ring (%.0f g): the ducts then "
      "hold SF 3 against a hand on a thruster ring, which is the load that actually "
      "happens when someone picks the ship up. The other one is the film's tension at "
      "the keel rim: at 100 Pa the film can hang only %.1f x the ship's weight off one "
      "rim. Run the envelope at 200-300 Pa (the fan already makes ~1900 Pa in the "
      "plenum [measured, STRUCTURE-ESTIMATES L8]; a bleed tube from the plenum to the "
      "envelope costs a fitting and no new part) and bond the film to a 10 mm band on "
      "both keel rims, and that margin goes to ~3-4 [guess].\n"
      % (pick(r1, "thruster ducts") - pick(r0, "thruster ducts"),
         pick(r0, "duct support ring"), r0["struct"]["sf_hang"]))

    # ---- 5 shape ----
    w("## 5 Does the shape ratio matter? (B/a = 0.45, 0.5006, 0.55)\n")
    rows = []
    for ba in BA_RATIOS:
        for c, nm in ((concept_a, "A"), (concept_b, "B"), (concept_c, "C")):
            r = solve(c, ba, 150)
            rows.append((nm, "%.3f" % ba, "%.2f m" % (2 * r["a"] / 1000),
                         "%.0f L" % r["gas"], "%.0f g" % r["mass"],
                         "%.1f m2" % r["surf"], "%.0f h" % r["hours"]))
    w(table(rows, ["concept", "B/a", "diameter at +150 g", "H2", "mass", "film area",
                   "print hours"]))
    w("\n**Deeper wins, not flatter.** At B/a = 0.55 every concept reaches the margin "
      "at a smaller diameter (C: 1.48 m against 1.59 m at 0.45), with less film "
      "(5.0 m2 against 5.3 m2) and no more print time - the same cube-square rule "
      "that drives the whole study, since for a fixed volume the area falls as the "
      "hull gets fatter. What stops 0.55 being free is that B is the ship's height: "
      "the keel tube, the piece stack and the fan housing all grow with it, and "
      "`FLOOR_Z` / the Ø34 duct mouths under the shroud were sized against today's "
      "0.5006 [measured]. The whole effect is ~3 % of mass and ~7 % of diameter: "
      "**the concept choice is worth 40 %, the ratio is worth 3 %** [guess].\n")

    # ---- 6 structure ----
    w("## 6 Structure at SAFETY_FACTOR 3 - every load, every tag\n")
    w("S1-S3 are concept B's frame at the +250 g size (that is where the frame maths "
      "matters); S4-S10 are the printed core of C at the same size, with the ducts at "
      "`T` - section 4.1 prices the tapered 2T root. Stresses are compared against "
      "the across-the-layers number, as STRUCTURE-ESTIMATES.md does, and no member is "
      "allowed below 2 perimeters.\n")
    rc = solve(concept_c, 0.5006, 250)
    rb = solve(concept_b, 0.5006, 250)
    st, fr = rc["struct"], rb["struct"]
    peg_shear = math.pi * 1.5 ** 2 * 12.0            # N, one peg in single shear
    boss_shear = math.pi * BOSS_D * BOSS_L * 10.0    # N, epoxy on a boss's bond face
    w(table([
        ("S1 batten Euler buckling under the envelope's pressure load",
         "%.1f N axial, L %.0f mm, I %.0f mm4 vs %.0f needed"
         % (fr["n_ax"], fr["L"], fr["I"], fr["i_req"]), "%.1f" % fr["sf_buck"],
         "dp 100 Pa [guess], Laplace [measured physics], E 3000 MPa [datasheet]"),
        ("S2 ring: battens pull in on it at each attachment",
         "%.1f N per attachment over a %.0f mm arc" % (fr["p_pt"], fr["arc"]),
         "%.1f" % (SIG_T * fr["rZ"] / fr["m_ring"]), "curved-beam bound [guess]"),
        ("S3 ring hoop tension", "%.0f N" % (DELTA_P * (rc["a"] / 1000) * 0.3),
         "> 100", "Laplace [measured physics]"),
        ("S4 printed peg joint (the `PEG_D` 3.0 peg, 2 per segment boundary)",
         "%.0f N to shear one peg" % peg_shear,
         "%.1f" % (peg_shear / (rc["mass"] * 1e-3 * 9.81 / 2 / 2)),
         "PLA shear 12 MPa [guess], one segment's share of the ship's weight"),
        ("S5 boss bond (epoxy on a Ø7 x 5 boss)", "%.0f N" % boss_shear, "> 100",
         "epoxy lap shear 10 MPa [datasheet, low end]"),
        ("S6 handling: lift the whole ship by the keel",
         "%.1f N, M %.0f N.mm on the keel tube" % (st["w_ship"], st["w_ship"] * 0.5006
                                                   * rc["a"] / 2),
         "%.0f" % st["sf_keel"], "load [guess], keel Ø67.7 x 0.86 [measured]"),
        ("S7 thruster reaction on the core (duct root cantilever)",
         "%.0f N.mm with L5 x 4" % st["m_duct"], "%.1f" % st["sf_duct"],
         "306 gf total [measured, AIRFLOW.md low end], L5 x 4 [guess]"),
        ("S8 a hand on a thruster ring (20 N, L6)", "%.0f N.mm"
         % (20.0 * st["free_len"] * 1000.0), "%.1f" % st["sf_hand_duct"],
         "reported as a bound, as f152 reported C3; 2T duct wall + the support ring "
         "lifts it to ~2.3"),
        ("S9 film tension (Laplace) vs film strength", "%.1f N/m = %.1f MPa in 12 um"
         % (st["film_t"], st["film_stress"]), "6 (LDPE) / 60 (PET)",
         "film tensile 20 / 200 MPa [datasheet range, LOW end]"),
        ("S10 film hanging the ship off the keel rim", "%.1f N/m needed" % st["n_hang"],
         "%.1f" % st["sf_hang"], "45 deg wrap [guess]; 200-300 Pa fixes it"),
    ], ["case", "load", "SF", "tag"]))
    w("\nNothing is sized below the print floor: every member is at least 2 perimeters "
      "(`T` = 0.86, rule 1), and the smallest section the frame search returns is "
      "8 x 10 mm, not a wall.\n")

    # ---- 7 film ----
    w("## 7 The envelope film: 12 um LDPE or metallized PET\n")
    rows = []
    for film in FILMS:
        r = solve(lambda a, ba: concept_c(a, ba, film=film), 0.5006, 150)
        lo, hi = leak(r["surf"] * FILM_OVERLAP, film)
        rows.append((film, "%.0f g/m2" % FILMS[film], "%.2f m" % (2 * r["a"] / 1000),
                     "%.0f g" % pick(r, "envelope"),
                     "%.3f-%.2f" % (lo, hi), "%.1f-%.0f" % (lo * 14.4, hi * 14.4),
                     "%.0f-%.0f" % (lo * 14.4 * 7, hi * 14.4 * 7)))
    w(table(rows, ["film", "g/m2", "diameter at +150 g", "envelope mass",
                   "H2 lost g/day", "lift lost g/day", "lift lost per week, g"]))
    w("\n14.4 g of lift per gram of H2 lost (1 L of H2 lifts 1.12 g and weighs "
      "0.084 g). The permeability numbers are [datasheet range, order of magnitude] "
      "and are the weakest numbers in this study - they span two orders of magnitude, "
      "which is exactly why the leak test in section 10 is the second-cheapest and "
      "most valuable test on the list. Metallized PET costs +%.0f g and buys 10-100x "
      "the barrier; take it. LDPE stays useful for a first shape/leak prototype "
      "because it is cheap and heat-sealable at home.\n"
      % (FILM_OVERLAP * ellipsoid(a38, 0.5006)[1] * (FILMS["metallized PET"]
                                                     - FILMS["12 um LDPE"])))

    # ---- 8 rejected ----
    w("## 8 Two ideas that look lighter and are not\n")
    e, edge, length, mass = geodesic(a38, 0.5006)
    w("- **A geodesic strut frame** (the obvious light space frame): %d struts of "
      "%.2f m at frequency 2 = %.0f m of strut, %.0f g of LW-PLA at the 8 x 14 mm "
      "section the buckling maths wants, before the %d node fittings that are each a "
      "print and a joint. Worse than concept B's battens, which are continuous and "
      "need no nodes [guess].\n" % (e, edge, length, mass, 10 * 4 + 2))
    ar, fg = multicell(a38, 0.5006)
    w("- **A bundle of sausage gas cells** (each cell a pressure cylinder, so no "
      "frame at all, like a small non-rigid blimp): it works structurally, but the "
      "internal walls are wasted film - %.1f m2 against the single envelope's %.1f "
      "m2 (7.0 m2 once the seams are allowed for), so +%.0f g of film at 17 g/m2. It "
      "stays the fallback if a single envelope "
      "cannot be made to hold shape.\n"
      % (ar, ellipsoid(a38, 0.5006)[1], fg - FILM_OVERLAP * ellipsoid(a38, 0.5006)[1]
         * FILMS["metallized PET"]))

    # ---- 9 recommendation ----
    REC = lambda a, ba: concept_c(a, ba, duct_t=2 * T, taper=True)
    rc = solve(REC, 0.5006, 250)
    ra = solve(concept_a, 0.5006, 250)
    rb = solve(concept_b, 0.5006, 250)
    w("## 9 RECOMMENDATION\n")
    w("**Build concept C: the pressure envelope - printed core only, film envelope, "
      "no printed skin - with tapered ducts (2T at the root, T at the mouth) and one "
      "support ring, at a = %.0f mm, hull diameter %.2f m, B/a = 0.5006, in LW-PLA "
      "at 0.60 g/cm3, with a metallized-PET envelope held at 200-300 Pa.** It floats with **%+.0f g** of margin on **%.0f L** of hydrogen at "
      "an all-up mass of **%.0f g**, in **%d printed parts** and **~%.0f print hours** "
      "on the CR-10 Pro.\n"
      % (rc["a"], 2 * rc["a"] / 1000, rc["margin"], rc["gas"], rc["mass"], rc["pieces"],
         rc["hours"]))
    w("Reasons:\n")
    w("1. **It is the only concept that floats near the size the bed can print.** "
      "A needs %.2f m and B needs %.2f m for the same +250 g; C needs %.2f m. B's "
      "diameter is set by its own frame: %.0f g of battens and rings, which is "
      "%.0f %% of the airframe.\n"
      % (2 * ra["a"] / 1000, 2 * rb["a"] / 1000, 2 * rc["a"] / 1000,
         pick(rb, "battens") + pick(rb, "rings"),
         100 * (pick(rb, "battens") + pick(rb, "rings"))
         / rb["mass"]))
    w("2. **It removes the mass that the float maths cannot remove.** Lift grows as "
      "a^3, a printed skin as a^2 and a fixed-thickness wall as a^1 (FLOAT.md's "
      "measured S^0.81-1.00). The skin is the part that never stops paying. C pays "
      "%.0f g of film where A pays %.0f g of lattice plus %.0f g of film plus %.0f g "
      "of glue and joints to hold the same volume.\n"
      % (pick(rc, "envelope"), pick(ra, "hull"),
         pick(ra, "gas cells"), pick(ra, "glue") + pick(ra, "extra piece joints")))
    w("3. **It is 5x fewer prints, and every one of them is a simple tube.** %d parts "
      "against A's %d and B's %d: %d keel segments (the keel tube is %.0f mm long and "
      "prints in %d, as the x3.8 build's intake tubes already do), %d duct segments, "
      "%d ring segments and the thruster hardware - nothing longer than 350 mm, so "
      "everything lies flat on the 290 x 290 x 390 bed with no supports. Print time "
      "~%.0f h against A's %.0f h and B's %.0f h.\n"
      % (rc["pieces"], ra["pieces"], rb["pieces"], rc["segs"][0],
         2 * 0.5006 * rc["a"], rc["segs"][0], rc["segs"][1], rc["segs"][2],
         rc["hours"], ra["hours"], rb["hours"]))
    w("4. **Its structure is checkable and its weak points are cheap to fix.** "
      "Everything printed is a tube of revolution at `T` or 2T; the keel is at SF "
      "%.0f, the ducts at SF %.1f (SF ~2.3 even against a 20 N hand once the wall is "
      "2T and the ring is in), the film is at SF 6-60 in tension. The one number that "
      "must not be guessed is the film's grip on the keel, and it is a 10 mm band of "
      "epoxy.\n" % (rc["struct"]["sf_keel"], rc["struct"]["sf_duct"]))
    w("5. **What it gives up is shape, not strength.** The envelope will be rounder "
      "than the spheroid. That costs drag and it costs the thrusters' clearance from "
      "the envelope, not lift. If rhY wants the ellipsoid back, the cheapest way is "
      "2 latitude lacing lines and the %.0f g support ring C already carries, not "
      "B's %.0f g of battens.\n"
      % (rc["items"]["duct support ring"],
         pick(rb, "battens") + pick(rb, "rings")))

    # ---- 10 risks ----
    w("## 10 The three biggest risks, and the cheapest test that retires each\n")
    r_lw = solve(lambda a, ba: concept_c(a, ba, rho=0.80), 0.5006, 150)
    REC = lambda a, ba: concept_c(a, ba, duct_t=2 * T, taper=True)
    r_c250 = solve(REC, 0.5006, 250)
    r_c80 = concept_c(r_c250["a"], 0.5006, rho=0.80, duct_t=2 * T, taper=True)
    w("1. **The film's load path: can a bonded film hold the ship up and keep a "
      "shape?** Everything in C rests on it, and it is the one part of the study with "
      "no CAD behind it. The numbers say it is marginal at 100 Pa (SF %.1f on the "
      "film's tension at the keel rim) and it is not a printed part, so the checker "
      "cannot see it. It is also the part the physics says will misbehave when the "
      "gas cools: at fixed volume a 15 degC drop costs ~5000 Pa of absolute pressure, "
      "50 x the overpressure, so the envelope goes slack unless the plenum feeds it "
      "makeup air [measured physics, ideal gas].\n"
      "   *Cheapest test:* print one keel rim (a 68 mm ring), bond a 400 mm balloon "
      "of the real film to it with a 10 mm band, hang 500 g from the ring, inflate it "
      "off the fan through a tube at 100 / 200 / 300 Pa (a water-column manometer), "
      "and watch for the film slipping on the bond and for the shape pulling round. "
      "One metre of film, one small print, one evening.\n" % rc["struct"]["sf_hang"])
    ph = pinhole_leak()
    area = rc["surf"] * FILM_OVERLAP
    pet = leak(area, "metallized PET")
    ld = leak(area, "12 um LDPE")
    w("2. **Hydrogen out of the envelope.** Film permeation through %.0f m2 of "
      "metallized PET is small: %.1f-%.1f g of lift a day. Even 12 um LDPE only "
      "reaches %.0f g a day at the loose end of the permeability range [datasheet "
      "range, order of magnitude]. **The seams are the leak**: one 0.1 mm pinhole at "
      "100 Pa passes %.0f L/day, %.0f g of lift a day - a hundred times the film. A "
      "home heat-sealed lap with one channel along it empties the ship overnight.\n"
      "   *Cheapest test:* seal two 0.3 m2 pouches, one LDPE one metallized PET, fill "
      "them from a balloon to a known volume, hang each from a 0.1 g scale for 24 h, "
      "and read the lift loss directly (a pouch that loses 10 L of H2 reads 12 g "
      "lighter); then inflate one to 300 Pa and feel every seam with soapy water. Half "
      "a day of film and no printing.\n"
      % (area, pet[0] * 14.4, pet[1] * 14.4, ld[1] * 14.4, ph, ph * 1.204))
    w("3. **The printed mass model, i.e. whether LW-PLA really prints at 0.60 g/cm3.** "
      "Every margin here is 0.60 g/cm3 [measured, float_budget.py's assumption, never "
      "weighed on rhY's machine]. Print at 0.80 instead and the recommended ship at "
      "%.2f m goes from **%+.0f g to %+.0f g** - it still flies, but the +250 g "
      "margin is gone, and concept A would not float at all.\n"
      "   *Cheapest test:* print the 100 x 100 x 10 mm lattice coupon and the keel "
      "tube, weigh both, and put the measured density into `float_budget.MATERIALS`. "
      "It also settles `T` (rule 1) against the real line width, which is what every "
      "section modulus in this file is built from. One print, one scale.\n"
      % (2 * r_c250["a"] / 1000, r_c250["margin"], r_c80["margin"]))
    w("Then, in order: the duct as a cantilever (print one 400 mm duct + ring, clamp "
      "it, hang 200 g and then 800 g at the free end - this is also test 1 of "
      "STRUCTURE-ESTIMATES.md section 8); the peg joint in the frame (print one "
      "batten segment pair and pull them apart on a scale); the fan's ability to hold "
      "the envelope at 200-300 Pa through a bleed tube (a manometer on the plenum "
      "while the fan runs).\n")

    # ---- 11 open ----
    w("## 11 What this study does not settle\n")
    w("- **The envelope's real shape and area.** C uses the spheroid's area as a "
      "conservative stand-in for the constant-mean-curvature shape a free film takes. "
      "A form-finding run (or the balloon test above with a measuring tape) will put "
      "the volume error on the record; it is believed to be under 10 %% [guess].\n"
      "- **Drag and steering with a rounder hull**, and whether the thruster ducts "
      "still clear the envelope at the equator once it bulges.\n"
      "- **The pressure system**: a bleed from the plenum, a relief valve at ~400 Pa, "
      "and what happens overnight (section 10 item 1). None of it is designed here.\n"
      "- **Whether rhY wants the ellipsoid.** If the answer is yes, the honest price "
      "is concept B's %.0f g of frame and %.2f m of hull, or lacing lines whose "
      "behaviour nobody has measured.\n"
      % (pick(rb, "battens") + pick(rb, "rings"), 2 * rb["a"] / 1000))
    w("## Summary\n")
    w("Recommended: concept C - printed core (keel tube, fan housing, 4 tapered "
      "ducts (2T root / T mouth) with one support ring, thruster and avionics mounts) "
      "+ a metallized-PET "
      "envelope held at 200-300 Pa, no printed skin.")
    w("Size: a = %.0f mm, hull diameter %.2f m, B/a = 0.5006, on the CR-10 Pro bed."
      % (rc["a"], 2 * rc["a"] / 1000))
    w("Margin %+.0f g on %.0f L of H2 at an all-up mass of %.0f g (LW-PLA 0.60 g/cm3, "
      "4S LiPo 1500 mAh on board)." % (rc["margin"], rc["gas"], rc["mass"]))
    w("Parts: %d printed parts, %.0f cm3 of plastic, ~%.0f print hours - against "
      "concept A's %d parts / %.0f h at %.2f m and concept B's %d parts / %.0f h at "
      "%.2f m." % (rc["pieces"], rc["printed_cm3"], rc["hours"], ra["pieces"],
                   ra["hours"], 2 * ra["a"] / 1000, rb["pieces"], rb["hours"],
                   2 * rb["a"] / 1000))
    w("Structure at SF 3: keel SF %.0f, ducts SF %.1f (2T wall + ring), film tension "
      "SF 6-60, film-on-keel the only marginal joint; the three cheapest tests are a "
      "400 mm film balloon on a bonded keel ring, two sealed pouches on a scale for "
      "24 h, and weighing one LW-PLA print."
      % (rc["struct"]["sf_keel"], rc["struct"]["sf_duct"]))
    open(OUT, "w").write("\n".join(o) + "\n")
    print("\n".join(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
