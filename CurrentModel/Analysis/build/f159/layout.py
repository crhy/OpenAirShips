#!/usr/bin/env python
"""f159: the lattice layout census in ONE global skin frame.

  layout.py [scale ...]

No CAD is built. Every window that `clip_window` finally cuts is laid out in a single
global uv frame (u = arc along the equator from the near seam, v = signed arc up/down the
hull), so walls and near-coincident cut boundaries can be MEASURED instead of argued:

  * the thinnest wall between two neighbouring windows (rule 4 wants >= RIB);
  * pairs of window boundaries within 0.05 mm of each other (rule 10: a cut boundary may
    never land on a face the part already has - section 8's coincident-face rows);
  * the SAME for the outlines as the CUTTER builds them: windows()/junction() resample the
    final polygon at 96 (oval) / 80 (junction) evenly spaced points, so two neighbours
    clipped by one and the same CURVED keep-out boundary carry two different chord
    polylines on that curve, and the boolean leaves a 0.001-0.014 mm sliver between them
    (the CR-10 Pro's 0.013 mm facet at r 290 z 4 az -6, the mount's ring blend);
  * the distance from every cut wall to the servo mount's own face (BRACE_EDGE_CLEAR);
  * the window census and the total open area, which is where the grams go.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "CAD Files", "SimplifiedSlice")))

os.environ.setdefault("OAS_VARIANT", "8T")

scales = [float(a) for a in sys.argv[1:]] or [1.0]
for scale in scales:
    os.environ["OAS_SCALE"] = str(scale)
    for mod in [m for m in list(sys.modules) if m.startswith("airship_slice")]:
        del sys.modules[mod]
    import airship_slice as m                  # noqa: E402
    from shapely.geometry import Polygon, Point, box  # noqa: E402
    from shapely.ops import unary_union        # noqa: E402

    print("=== OAS_SCALE %s (A %.2f B %.2f, SEAM_JUNCTION_OPEN %s)"
          % (scale, m.A, m.B, m.SEAM_JUNCTION_OPEN))

    def g_uv(p):
        """a skin point -> (u mm along the equator from the near seam, v mm up the hull)"""
        if hasattr(p, "x"):
            x, y, z = p.x, p.y, p.z
        else:
            x, y, z = p[0], p[1], p[2]
        r = math.hypot(x, y)
        az = math.degrees(math.atan2(y, x))
        psi = m.psi_of(p if hasattr(p, "x") else m.cq.Vector(x, y, z))
        u = (az - (-m.HALF)) / 180.0 * math.pi * m.hull_r(0.0)
        while u > 180.0 / 180.0 * math.pi * m.hull_r(0.0):
            u -= 180.0 / 180.0 * math.pi * m.hull_r(0.0)
        return (u, m.ellipse_arc(0.0, psi))

    exact = []            # (name, Polygon) as clip_window decides it
    cut = []              # (name, Polygon) as skin_cutter actually gets it (96/80 chords)

    def add(name, poly, psi, theta, to_uv, to_skin, sgn, others=(), tip=0.0, npts=96):
        g = m.clip_window(poly, psi, theta, to_uv, to_skin, sgn, others=others, tip=tip)
        if g is None:
            return
        for part in getattr(g, "geoms", [g]):
            ring = list(part.exterior.coords)[:-1]
            P = Polygon([g_uv(to_skin(u, v)[0]) for u, v in ring])
            if P.is_valid and P.area > 1.0:
                exact.append((name, P))
            per = part.length
            ch = [g_uv(to_skin(*(lambda q: (q.x, q.y))(part.exterior.interpolate(per * i / npts)))[0])
                  for i in range(npts)]
            C = Polygon(ch)
            if C.area > 1.0:
                cut.append((name, C))

    rows = m.skin_ribs()
    nrows = len(rows) - 1
    ovals = {k: [m.oval_on_skin(rows[k], rows[k + 1], sd) for sd in (-1, 1)]
             for k in range(nrows)}

    for k in range(nrows):
        for o in ovals[k]:
            psi = (rows[k] + rows[k + 1]) / 2
            to_uv, to_skin, sgn = m.skin_frame(psi, 0.0)
            add("oval%d" % k, Polygon([to_uv(p) for p, _ in o]), psi, 0.0,
                to_uv, to_skin, sgn, tip=0.0)
    def turn(rings, deg):
        c, s_ = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        rot = lambda p: m.cq.Vector(p.x * c - p.y * s_, p.x * s_ + p.y * c, p.z)
        return [[(rot(p), rot(nv)) for p, nv in r] for r in rings]

    for j, psi in enumerate(rows):
        near = ovals.get(j - 1, []) + ovals.get(j, [])
        for th, around in ((0.0, near), (-m.HALF, near + turn(near, -2 * m.HALF)),
                           (m.HALF, near + turn(near, 2 * m.HALF))):
            to_uv, to_skin, sgn = m.skin_frame(psi, math.radians(th))
            raw, reach = [], 60.0 * m.SCALE
            for ring in around:
                uv = [to_uv(p) for p, _ in ring]
                if min(math.hypot(a_, b_) for a_, b_ in uv) < reach:
                    raw.append(Polygon(uv))
            region = box(-reach, -reach, reach, reach).difference(
                unary_union([p.buffer(m.RIB) for p in raw]))
            vv = sorted((sgn * (rows[max(j - 1, 0)] - psi) * m.ds_dpsi(psi),
                         sgn * (rows[min(j + 1, nrows)] - psi) * m.ds_dpsi(psi)))
            region = region.intersection(box(-reach, vv[0], reach, vv[1]))
            if region.is_empty:
                continue
            # f162 item 3 (mirror of junction()): a seam junction claims only the cell
            # above its own rib and stands RIB/2 off the rib lines ending it.
            if abs(abs(math.radians(th)) - m.lattice_band()[2]) < 1e-9:
                if (rows[max(j - 1, 0)] - psi) * (rows[min(j + 1, nrows)] - psi) < -1e-12:
                    v_up = sgn * (rows[min(j + 1, nrows)] - psi) * m.ds_dpsi(psi)
                    mm = m.RIB / 2.0 * (1.0 if v_up > 0 else -1.0)
                    v0, v1 = sorted((mm, v_up - mm))
                else:
                    far = vv[1] if abs(vv[0]) < 1e-9 else vv[0]
                    v0, v1 = sorted((0.0, far - (m.RIB / 2.0 if far > 0 else -m.RIB / 2.0)))
                region = region.intersection(box(-reach, v0, reach, v1))
                if region.is_empty:
                    continue
            probe = Point(0, 0)
            near_p = [g_ for g_ in getattr(region, "geoms", [region])
                      if g_.area > 0 and g_.distance(probe) < 3.0]
            if not near_p:
                continue
            add("junc r%d az %+.0f" % (j, th),
                min(near_p, key=lambda g_: g_.distance(probe)),
                psi, math.radians(th), to_uv, to_skin, sgn, others=raw, npts=80)

    def census(lst, tag):
        print("  %s: %d windows, %.0f mm2 open" % (tag, len(lst), sum(p.area for _, p in lst)))
        worst, where = 1e9, None
        coinc = set()
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                na, pa = lst[a]
                nb, pb = lst[b]
                if pa.distance(pb) > 6.0:
                    continue
                d = pa.distance(pb)
                if d < worst:
                    worst, where = d, (na, nb)
                db = pa.exterior.distance(pb.exterior)
                if db < 0.05:
                    coinc.add((round(db, 4), na, nb))
                if db < 0.6:
                    coinc.add((round(db, 4), na, nb))
        print("    thinnest wall between windows %.3f mm  %s" % (worst, where))
        for t in sorted(coinc)[:12]:
            print("    boundaries %.4f mm apart: %s <-> %s" % t)
        for t in sorted(coinc)[:6]:
            _, na, nb = t
            pa = [p for p in lst if p[0] == na][0][1]
            pb = [p for p in lst if p[0] == nb][0][1]
            print("      %s bbox %s\n      %s bbox %s" % (na, tuple(round(x, 1) for x in pa.bounds),
                                                          nb, tuple(round(x, 1) for x in pb.bounds)))

    census(exact, "clip_window outlines")
    census(cut, "as cut (96/80 chords)")

    mo = m.servo_mount_outline()
    if mo:
        poly, pclear, to_skin, g = mo
        face = Polygon([g_uv(to_skin(u, v)[0]) for u, v in poly.exterior.coords])
        worst, where = 1e9, None
        for name, p in exact:
            d = face.distance(p)
            if d < worst:
                worst, where = d, name
        print("  closest lattice window to the mount's own face %.3f mm (%s); "
              "BRACE_EDGE_CLEAR %.2f, mount %.0f mm2 grown %.0f mm2"
              % (worst, where, m.BRACE_EDGE_CLEAR, poly.area, pclear.area))

    # vertex dump for the touching pair, to see what the opened seam junctions are
    for want in ("junc r6 az -22", "junc r7 az -22"):
        for name, p in exact:
            if name == want:
                print("%s: %.1f mm2  ring %s" % (name, p.area,
                      [(round(x, 1), round(y, 1)) for x, y in list(p.exterior.coords)[:14]]))

    print("  ribs (psi deg, arc mm): " + ", ".join(
        "%.2f/%.1f" % (math.degrees(psi), m.ellipse_arc(0.0, psi)) for psi in rows))

    names = {n for n, _ in exact}
    pairsets = [(("junc r%d az -22" % a, "junc r%d az -22" % b),
                 ("junc r%d az +22" % a, "junc r%d az +22" % b))
                for a, b in ((6, 7), (5, 6))]
    for na, nb in [ps for ps in pairsets if ps[0] in names and ps[1] in names]:
        pa = [p for p in exact if p[0] == na][0][1]
        pb = [p for p in exact if p[0] == nb][0][1]
        inter = pa.intersection(pb)
        print("%s & %s: overlap %.2f mm2, boundary distance %.4f, shared geom %s"
              % (na, nb, inter.area, pa.exterior.distance(pb.exterior),
                 [round(x, 2) for x in inter.bounds]))

    # debug: local uv bbox vs global bbox for the two seam junctions
    import shapely.geometry as _sg
    for j in (6, 7):
        psi = rows[j]
        near = ovals.get(j - 1, []) + ovals.get(j, [])
        for th, around in ((-m.HALF, near + turn(near, -2 * m.HALF)),):
            to_uv, to_skin, sgn = m.skin_frame(psi, math.radians(th))
            raw, reach = [], 60.0 * m.SCALE
            for ring in around:
                uv = [to_uv(p) for p, _ in ring]
                if min(math.hypot(a_, b_) for a_, b_ in uv) < reach:
                    raw.append(_sg.Polygon(uv))
            region = _sg.box(-reach, -reach, reach, reach).difference(
                unary_union([p.buffer(m.RIB) for p in raw]))
            vv = sorted((sgn * (rows[max(j - 1, 0)] - psi) * m.ds_dpsi(psi),
                         sgn * (rows[min(j + 1, nrows)] - psi) * m.ds_dpsi(psi)))
            region = region.intersection(_sg.box(-reach, vv[0], reach, vv[1]))
            probe = _sg.Point(0, 0)
            parts = [g_ for g_ in getattr(region, "geoms", [region])
                     if g_.area > 0 and g_.distance(probe) < 3.0]
            if not parts:
                print("  r%d: no part near the origin (region %s)" % (j, region.bounds))
                continue
            g0 = min(parts, key=lambda g_: g_.distance(probe))
            print("  r%d az %.0f: local bbox %s area %.1f; after clip_window bbox %s"
                  % (j, th, tuple(round(x, 1) for x in g0.bounds), g0.area,
                     tuple(round(x, 1) for x in (m.clip_window(
                         _sg.Polygon(g0.exterior.coords), psi, math.radians(th),
                         to_uv, to_skin, sgn, others=raw) or _sg.Polygon()).bounds)))
