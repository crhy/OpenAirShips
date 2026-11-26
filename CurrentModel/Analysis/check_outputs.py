#!/usr/bin/env python
"""check_outputs.py - audit every CAD and print file OpenAirShips ships.

Answers one question with numbers: is each file under `CurrentModel/CAD Files`
and `CurrentModel/Print Files` a real, solid, watertight, printable thing?

Run it headless under FreeCAD (it uses FreeCAD's Part and Mesh modules, no
network, nothing is written except --json):

    flatpak run --command=freecadcmd org.freecad.FreeCAD \\
        CurrentModel/Analysis/check_outputs.py --pass "--json out.json"

`freecadcmd` swallows anything that looks like an option unless it follows
`--pass`, and it tries to open every other bare argument as a file, so keep
all of this script's own arguments inside one quoted string after `--pass`.

What it checks
  .FCStd   opens it, lists the objects, and for every shape: isNull/isValid,
           solid/shell/face count, volume, bbox; whether the document has any
           visible geometry at all, and whether GuiDocument.xml switches each
           of those parts on (that file is what makes the GUI show the parts on
           open); the zip layout (Document.xml, GuiDocument.xml, the .brp parts
           and their sizes), the program that wrote it, and the stored document
           label vs the file name; how long the shape takes to tessellate, which
           is what a viewer pays before it shows anything.
  .step    loads it and reports the same shape numbers, plus shell closedness
           and the STEP dialect, and re-runs the generator's meshing ladder
           (0.02, 0.015, 0.03, 0.01, 0.05) to show whether the first pass is
           watertight or whether a retry is what makes the print file close.
  .stl     loads it as a mesh and reports facets, points, shells/components,
           open (boundary) edges, non-manifold edges, self-intersections,
           orientation, volume; the STL header's declared facet count; whether
           the bounding box fits the printers the docs name; and a wall-thickness
           map (the model's own walls against the 0.4 mm nozzle / 0.2 mm layer
           the build notes specify). The map measures both ends of the wall:
           facets thinner than the nozzle, and thick material - the % of the
           sampled surface whose wall is over NOMINAL_WALL + 0.25 mm, grouped
           into blobs, each reported with its area and where it sits (r, z,
           azimuth), and the facets thinner than the nozzle, grouped and placed
           the same way. One uniform thickness is only provable both ways. A hit
           whose face meets the ray at less than GRAZE_DEG is skipped: that ray is
           grazing a surface that passes beside the facet, not measuring the wall
           behind it (see GRAZE_DEG for the measurements, and build/f151/
           grazeprobe.py for the check that a real 0.15 mm wall is still found).

Cross-check: every .FCStd and .stl is compared by volume with the .step it was
made from, so a print file that is not the current model shows up.

One line per file: PASS or FAIL with the reasons. Exit code is non-zero if any
file fails.

Options (inside the `--pass` string)
  --json PATH        machine-readable dump of every record
  --cad-root PATH    root scanned for .FCStd/.step (default CurrentModel/CAD Files)
  --stl-root PATH    root scanned for .stl      (default CurrentModel/Print Files)
  --filter SUBSTR    only files whose path contains SUBSTR
  --only cad|print   cad = the .FCStd and .step files only, print = the .stl
                     files only (default: both)
  --no-tess          skip tessellating shapes (faster, display cost not measured)
  --no-thin          skip the STL wall-thickness scan
  --thin-report      print every facet the wall map found under the nozzle, with
                     its coordinates, clustered within 2 mm: the numbers a fix
                     has to be pointed at (see the thin cluster lines below)
  --samples N        how many facets the wall map samples (default 6000; raise
                     it to check a whole mesh, the scan costs about as much time)
  --joints PATH      check the joint map the generator writes (<slice>.joints.json):
                     every peg/hole boss against the fan-housing wall, the plenum
                     air and the impeller's swept volume, and every hole against
                     the air path (the fan duct's bore and the bulb's bore, both
                     measured in the seam plane the joints live in). One line per
                     joint; a clearance short of the rule is a FAIL.
"""

import argparse
import json
import math
import os
import re
import shlex
import struct
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

import FreeCAD as App
import MeshPart
import Part
import Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
CURRENT = os.path.dirname(HERE)                     # CurrentModel/
NOZZLE = 0.40          # mm, the nozzle every build note assumes
MIN_FACET_AREA = 1e-4  # mm2, under this a mesh facet is a mesher sliver, not a wall.
                       # Its normal is noise, and the wall ray starts 0.005 mm along
                       # that normal, so it reads 0.005-0.03 mm of "wall". Every build
                       # since f148 carries 10-14 facets under 1e-6 mm2 (about 150 under
                       # 1e-4) where the duct's wall face meets the skin band, at both
                       # sizes: f149 measured the same 0.000 mm2 facet at r=71 z=-142 in
                       # the f148 STEP's mesh and in its own, and which of them the
                       # stride sampling lands on has been deciding the gate.
LAYER = 0.20           # mm, the layer height the build notes assume
GRAZE_DEG = 10.0       # deg, the least angle at which a wall ray may meet the face it
                       # hits. A ray that runs nearly ALONG a face is not measuring a wall
                       # behind the facet it started from, it is grazing a surface that
                       # passes beside it, and the reading is then the distance to that
                       # surface along the graze, not a wall. Every surface of revolution in
                       # this model (the duct's bulb dome and tube, the shroud turn, the
                       # shaft) is parallel to the seam face's own wall rays, so a facet on
                       # the seam face within a fraction of a mm of where one of them crosses
                       # it reads 0.005-0.3 mm where the BREP wall is 0.80-0.86 mm: f148
                       # measured that at the bulb dome ("the wall map's ray runs along the
                       # seam face and reports 0.005-0.12 mm where the BREP wall is 0.800 mm")
                       # and f150 at the shroud turn (build/f150/thin-8T-40k.log cluster 2: a
                       # 0.001 mm2 facet at (32.47, 8.04, -65.98) reading 0.148 mm, the same
                       # facet f151's bench mesh lands on at the 6 000-facet stride). Which of
                       # them the stride sampling lands on has been deciding the gate: the
                       # same STEP reads min 0.19 mm at LinearDeflection 0.03 and 0.44 mm at
                       # 0.05, and at 15 000 or 40 000 samples every deflection finds one
                       # (build/f151/meshprobe2.log). A real thin wall is hit near-perpendicular
                       # (the ray crosses it), so this only rejects grazes: build/f151/
                       # grazeprobe.py builds a mesh with a 0.15 mm wall and a 0.86 mm wall and
                       # the map still reports the 0.15.
VOL_TOL = 0.005        # 0.5 % volume difference allowed between CAD and print
NOMINAL_WALL = 0.86    # mm, the model's one wall thickness (airship_slice.py T)
THICK_AT = NOMINAL_WALL + 0.25   # a wall this far over nominal is a thick blob
BLOB_LINK = 3.0        # mm: thick facets this far apart are one blob
JOINT_CLEAR = 1.0     # mm a joint keeps from the fan housing and the impeller
AIR_KEEP = 0.6        # mm of wall a hole leaves toward the air path
BEDS = [(400.0, 400.0, 450.0, "Anycubic Kobra Max"),
        (210.0, 210.0, 250.0, "Prusa MK3S+"),
        (300.0, 300.0, 400.0, "Creality CR-10 Pro")]   # f118 item 5: rhY's printer

TESS_OFF = False
THIN_OFF = False
THIN_REPORT = False
WALL_SAMPLES = 6000


def version_string():
    try:
        return "FreeCAD " + ".".join(str(x) for x in App.Version()[:3])
    except Exception:
        return "FreeCAD ?"


def shape_info(s):
    """Numbers for one TopoShape. Cheap: no tessellation, no BRepCheck."""
    out = {}
    out["isNull"] = bool(s.isNull())
    if s.isNull():
        return out
    out["isValid"] = bool(s.isValid())
    out["type"] = s.ShapeType
    out["solids"] = len(s.Solids)
    out["shells"] = len(s.Shells)
    out["faces"] = len(s.Faces)
    out["edges"] = len(s.Edges)
    out["volume"] = float(s.Volume)
    out["area"] = float(s.Area)
    bb = s.BoundBox
    out["bbox"] = [bb.XLength, bb.YLength, bb.ZLength]
    out["bboxMin"] = [bb.XMin, bb.YMin, bb.ZMin]
    out["bboxMax"] = [bb.XMax, bb.YMax, bb.ZMax]
    closed = []
    for sh in s.Shells:
        try:
            closed.append(bool(sh.isClosed()))
        except Exception:
            closed.append(None)
    out["shellsClosed"] = closed
    if out["isValid"] is False:            # only pay for BRepCheck when it fails
        try:
            r = s.check()
            out["check"] = r if isinstance(r, str) and r.strip() else ""
        except Exception:
            out["check"] = ""
    return out


def tess_cost(shape, deflection=0.5):
    """What a viewer pays to put the shape on screen."""
    t = time.time()
    try:
        verts, tris = shape.tessellate(deflection)
        return {"triangles": len(tris), "points": len(verts),
                "seconds": round(time.time() - t, 1)}
    except Exception as exc:
        return {"error": str(exc), "seconds": round(time.time() - t, 1)}


def mesh_topology(m):
    """(points, facets) plus boundary / non-manifold edge counts."""
    pts, facets = m.Topology
    seen = {}
    for f in facets:
        a, b, c = f
        for u, v in ((a, b), (b, c), (a, c)):
            k = (u, v) if u < v else (v, u)
            seen[k] = seen.get(k, 0) + 1
    return {"points": len(pts), "facets": len(facets),
            "openEdges": sum(1 for n in seen.values() if n == 1),
            "nonManifoldEdges": sum(1 for n in seen.values() if n > 2),
            "edges": len(seen)}


def group_blobs(items, cen, fac_area, link=BLOB_LINK):
    """Group (facet, thickness) items into blobs: facets within `link` of each
    other. Used for both ends of the wall map - thick material, and walls thinner
    than the nozzle - because both need the same answer: how much, how thick,
    and where, so the fix can be pointed at the code that made it."""
    cell_of, parent = {}, list(range(len(items)))

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for k, (i, _) in enumerate(items):
        cx, cy, cz = cen[i]
        key = (int(cx // link), int(cy // link), int(cz // link))
        for gx in range(key[0] - 1, key[0] + 2):
            for gy in range(key[1] - 1, key[1] + 2):
                for gz in range(key[2] - 1, key[2] + 2):
                    for j in cell_of.get((gx, gy, gz), ()):
                        a_, b_ = cen[items[j][0]], cen[i]
                        if (math.sqrt((a_[0] - b_[0]) ** 2 + (a_[1] - b_[1]) ** 2
                                      + (a_[2] - b_[2]) ** 2) <= link):
                            ra, rb = find(j), find(k)
                            if ra != rb:
                                parent[rb] = ra
        cell_of.setdefault(key, []).append(k)

    groups = {}
    for k in range(len(items)):
        groups.setdefault(find(k), []).append(k)
    blobs = []
    for ks in groups.values():
        cs = [cen[items[k][0]] for k in ks]
        ar = sum(fac_area[items[k][0]] for k in ks)
        ts = [items[k][1] for k in ks]
        cx = sum(c[0] for c in cs) / len(cs)
        cy = sum(c[1] for c in cs) / len(cs)
        cz = sum(c[2] for c in cs) / len(cs)
        blobs.append({
            "facets": len(ks), "area": round(ar, 1),
            "thickness": [round(min(ts), 2), round(max(ts), 2)],
            "at": [round(cx, 1), round(cy, 1), round(cz, 1)],
            "r": round(math.hypot(cx, cy), 1),
            "z": round(cz, 1),
            "deg": round(math.degrees(math.atan2(cy, cx)), 1),
            "bbox": [round(min(c[d] for c in cs), 1) for d in range(3)]
                    + [round(max(c[d] for c in cs), 1) for d in range(3)]})
    blobs.sort(key=lambda b_: -b_["area"])
    return blobs


def wall_map(m, max_depth=4.0, cell=1.0, samples=6000, report=False):
    """Cast each facet's inward normal and find the surface behind it.

    Two ends of one measurement. A wall thinner than the nozzle cannot be printed
    as drawn: the slicer has to widen it or leave a gap in it. A wall more than
    0.25 mm over the model's own nominal wall (NOMINAL_WALL, the single T every
    skin, duct, shaft, floor, keel, hatch ring, housing and rib face must have)
    is thick material: extra weight the design did not ask for. Thick facets are
    grouped into blobs - facets within BLOB_LINK of each other - and each blob is
    reported with its area and its place (r, z, azimuth), so the fix can be
    pointed at the code that made it.
    """
    pts, facets = m.Topology
    nfac = len(facets)
    step = max(1, nfac // samples)
    P = [(p.x, p.y, p.z) for p in pts]
    cen, nor, fac_area = {}, {}, {}
    facet_vertices = [frozenset(f) for f in facets]
    grid = {}
    tiny = 0
    graze = 0
    edge_adjacent = 0
    for i, f in enumerate(facets):
        a, b, c = (P[f[0]], P[f[1]], P[f[2]])
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz)
        cx, cy, cz = (a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0,\
                     (a[2] + b[2] + c[2]) / 3.0
        cen[i] = (cx, cy, cz)
        fac_area[i] = 0.5 * ln
        if ln < 1e-12 or fac_area[i] < MIN_FACET_AREA:
            nor[i] = None                          # not a wall: see MIN_FACET_AREA
            tiny += 1
            continue
        nor[i] = (nx / ln, ny / ln, nz / ln)
        grid.setdefault((int(cx // cell), int(cy // cell), int(cz // cell)),
                        []).append(i)

    reach = int(max_depth / cell) + 1
    hits = []                      # (facet, wall thickness, hit facet, incidence) for hits
    d2max = max_depth * max_depth
    for i in range(0, nfac, step):
        if nor.get(i) is None:
            continue
        c = cen[i]
        n = nor[i]
        ox, oy, oz = c[0] + n[0] * 0.005, c[1] + n[1] * 0.005, c[2] + n[2] * 0.005
        dx, dy, dz = -n[0], -n[1], -n[2]
        kx, ky, kz = int(ox // cell), int(oy // cell), int(oz // cell)
        best = None
        best_j = None
        best_incidence = None
        for gx in range(kx - reach, kx + reach + 1):
            for gy in range(ky - reach, ky + reach + 1):
                for gz in range(kz - reach, kz + reach + 1):
                    for j in grid.get((gx, gy, gz), ()):
                        if j == i:
                            continue
                        # A ray leaving a triangle beside a crease can cross the
                        # neighbouring triangle within a few microns of their
                        # common edge.  That is a surface corner, not the wall
                        # behind the sampled face.  A genuine opposite wall does
                        # not share a mesh edge with the face being measured.
                        if len(facet_vertices[i].intersection(facet_vertices[j])) >= 2:
                            edge_adjacent += 1
                            continue
                        cc = cen[j]
                        ex, ey, ez = cc[0] - ox, cc[1] - oy, cc[2] - oz
                        if ex * ex + ey * ey + ez * ez > d2max:
                            continue
                        ax, ay, az = P[facets[j][0]]
                        e1 = (P[facets[j][1]][0] - ax, P[facets[j][1]][1] - ay,
                              P[facets[j][1]][2] - az)
                        e2 = (P[facets[j][2]][0] - ax, P[facets[j][2]][1] - ay,
                              P[facets[j][2]][2] - az)
                        pv = (dy * e2[2] - dz * e2[1], dz * e2[0] - dx * e2[2],
                              dx * e2[1] - dy * e2[0])
                        det = e1[0] * pv[0] + e1[1] * pv[1] + e1[2] * pv[2]
                        if abs(det) < 1e-9:
                            continue
                        tx, ty, tz = ox - ax, oy - ay, oz - az
                        u = (tx * pv[0] + ty * pv[1] + tz * pv[2]) / det
                        if u < -1e-9 or u > 1 + 1e-9:
                            continue
                        q = (ty * e1[2] - tz * e1[1], tz * e1[0] - tx * e1[2],
                             tx * e1[1] - ty * e1[0])
                        v = (dx * q[0] + dy * q[1] + dz * q[2]) / det
                        if v < -1e-9 or u + v > 1 + 1e-9:
                            continue
                        t = (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2]) / det
                        if t > 0.005 and t <= max_depth and (best is None or t < best):
                            # f151: reject a hit whose face runs nearly along the ray - see
                            # GRAZE_DEG. The hit triangle's own normal is e1 x e2. A real
                            # opposite wall also has to face the ray: on an oriented closed
                            # mesh the ray enters through the sampled outward face and exits
                            # through a face whose outward normal points along the ray. Using
                            # abs(dot) here admitted same-facing neighbour triangles on a
                            # finely tessellated curved face. Edge-adjacent triangles are
                            # rejected above as well: at a sharp blend their normals can be
                            # opposed even though they are two sides of the same surface edge.
                            hx, hy, hz = (e1[1] * e2[2] - e1[2] * e2[1],
                                          e1[2] * e2[0] - e1[0] * e2[2],
                                          e1[0] * e2[1] - e1[1] * e2[0])
                            hl = math.sqrt(hx * hx + hy * hy + hz * hz)
                            incidence = ((dx * hx + dy * hy + dz * hz) / hl
                                         if hl > 1e-12 else 0.0)
                            if incidence < math.sin(math.radians(GRAZE_DEG)):
                                graze += 1
                                continue
                            best = t
                            best_j = j
                            best_incidence = incidence
        if best is not None:
            hits.append((i, best, best_j, best_incidence))
    if not hits:
        return {"sampled": 0}

    vals = sorted(t for _, t, _, _ in hits)
    hit_area = sum(fac_area[i] for i, _, _, _ in hits)
    out = {"sampled": len(vals), "min": round(vals[0], 3),
           "median": round(vals[len(vals) // 2], 3),
           "underNozzle": sum(1 for t in vals if t < NOZZLE),
           "underLayer": sum(1 for t in vals if t < LAYER),
           "nominal": NOMINAL_WALL, "thickAt": round(THICK_AT, 3),
           "tinySkipped": tiny,
           "grazeSkipped": graze,
           "edgeAdjacentSkipped": edge_adjacent,
           "hitArea": round(hit_area, 1)}

    # thick material: group the facets over THICK_AT into blobs
    thick = [(i, t) for i, t, _, _ in hits if t > THICK_AT]
    out["thinFacets"] = sum(1 for _, t, _, _ in hits if t < NOMINAL_WALL - 0.25)
    out["normalFacets"] = len(hits) - len(thick) - out["thinFacets"]
    bins = [(0.0, LAYER), (LAYER, NOZZLE), (NOZZLE, NOMINAL_WALL - 0.25),
            (NOMINAL_WALL - 0.25, THICK_AT), (THICK_AT, 2.0), (2.0, 4.0)]
    out["hist"] = ["%.2f-%.2f mm: %d" % (lo, hi, sum(1 for t in vals if lo <= t < hi))
                   for lo, hi in bins]
    out["overMap"] = ">= 4 mm (not a wall): %d" % sum(1 for t in vals if t >= 4.0)
    out["thickFacets"], out["thickArea"], out["thickAreaPct"] = 0, 0.0, 0.0
    out["blobs"], out["blobCount"] = [], 0
    blobs = group_blobs(thick, cen, fac_area)
    ta = sum(b_["area"] for b_ in blobs)
    out["thickFacets"] = len(thick)
    out["thickArea"] = round(ta, 1)
    out["thickAreaPct"] = round(100.0 * ta / hit_area, 2) if hit_area else 0.0
    out["blobs"] = blobs[:14]
    out["blobCount"] = len(blobs)

    # the thin end, grouped the same way: a wall under the nozzle is not printable
    # as drawn, and knowing WHERE it is is what makes the failure fixable.
    if report:
        # every facet under the nozzle, with its coordinates: the blobs say how
        # much and where, this says which facets, so the generator code that
        # made the sliver can be found from the point
        under = []
        for i, t, j, incidence in hits:
            if t < NOZZLE:
                c, n = cen[i], nor[i]
                under.append({"facet": i, "at": [round(v, 3) for v in c],
                              "wall": round(t, 4), "area": round(fac_area[i], 4),
                              "normal": [round(v, 4) for v in n], "hitFacet": j,
                              "incidence": round(incidence, 4)})
        under.sort(key=lambda d_: d_["wall"])
        out["underFacets"] = under
    slim = [(i, t) for i, t, _, _ in hits if t < NOZZLE]
    slim_blobs = group_blobs(slim, cen, fac_area)
    out["underArea"] = round(sum(b_["area"] for b_ in slim_blobs), 1)
    out["underBlobs"] = slim_blobs[:14]
    out["underBlobCount"] = len(slim_blobs)
    return out


def cluster3d(items, link=2.0):
    """Group thin facets whose centres are within `link` of each other.

    2 mm, not BLOB_LINK: a sliver is a handful of facets, and at the mesh's
    ~0.5 mm facet size that is the size of one defect, so each cluster is one
    thing the generator did once.
    """
    parent = list(range(len(items)))

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    cell = {}
    for k, it in enumerate(items):
        a = it["at"]
        key = tuple(int(v // link) for v in a)
        for gx in range(key[0] - 1, key[0] + 2):
            for gy in range(key[1] - 1, key[1] + 2):
                for gz in range(key[2] - 1, key[2] + 2):
                    for j in cell.get((gx, gy, gz), ()):
                        b = items[j]["at"]
                        if math.sqrt(sum((a[d] - b[d]) ** 2 for d in range(3))) <= link:
                            ra, rb = find(j), find(k)
                            if ra != rb:
                                parent[rb] = ra
        cell.setdefault(key, []).append(k)
    groups = {}
    for k in range(len(items)):
        groups.setdefault(find(k), []).append(items[k])
    out = list(groups.values())
    out.sort(key=lambda g_: (min(x["wall"] for x in g_), -len(g_)))
    return out


def thin_report_lines(th):
    """The under-nozzle facets, one line each, grouped into 2 mm clusters.

    Coordinates are in the frame the wall scan ran in (model frame for the
    PieSlice STLs, whose print pose the scan undoes), so they can be compared
    with the generator's own numbers: r = hull radius, z, azimuth.
    """
    items = th.get("underFacets", [])
    if not items:
        return ["thin report: no sampled facet under %.2f mm" % NOZZLE]
    lines = ["thin report: %d sampled facets under the %.2f mm nozzle, min %.3f mm"
             % (len(items), NOZZLE, items[0]["wall"])]
    for n, g in enumerate(cluster3d(items), 1):
        cs = [x["at"] for x in g]
        cx = sum(c[0] for c in cs) / len(cs)
        cy = sum(c[1] for c in cs) / len(cs)
        cz = sum(c[2] for c in cs) / len(cs)
        lines.append(
            "thin cluster %d: %d facets, wall %.3f-%.3f mm, centre (%.1f, %.1f, %.1f) "
            "r=%.1f z=%.1f az=%.1f deg" %
            (n, len(g), min(x["wall"] for x in g), max(x["wall"] for x in g),
             cx, cy, cz, math.hypot(cx, cy), cz,
             math.degrees(math.atan2(cy, cx))))
        for x in sorted(g, key=lambda q_: q_["at"]):
            lines.append("      facet %d -> %d (%8.2f, %8.2f, %8.2f) wall %6.3f mm "
                         "area %6.3f mm2 incidence %.3f n=(%5.2f,%5.2f,%5.2f)" %
                         (x["facet"], x["hitFacet"], *x["at"], x["wall"], x["area"],
                          x["incidence"], *x["normal"]))
    return lines


def blob_text(b):
    """One blob, in the words the notes and the issue need: how much, how thick,
    where (cylindrical coordinates, because the hull is a body of revolution)."""
    return ("%.0f mm2 %.2f-%.2f mm at r=%.0f z=%.0f az=%.0f deg (%d facets)"
            % (b["area"], b["thickness"][0], b["thickness"][1], b["r"], b["z"],
               b["deg"], b["facets"]))


def revolved(pts):
    """A closed (r, z) polygon revolved about Z. The joint map's keep-clear
    profiles for bodies of revolution (the housing wall, the plenum air, the
    impeller's swept volume, the shaft bore) are meridian sections, so a revolve
    turns them into the volume the generator really builds."""
    vs = [App.Vector(r, 0, z) for r, z in pts]
    vs.append(vs[0])
    try:
        return Part.Face(Part.makePolygon(vs)).revolve(App.Vector(), App.Vector(0, 0, 1), 360)
    except Exception:
        return None


def seg_dist(p, a, b):
    ax, ay = p
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy
    t = max(0.0, min(1.0, ((ax - a[0]) * vx + (ay - a[1]) * vy) / L2)) if L2 else 0.0
    return math.hypot(ax - (a[0] + t * vx), ay - (a[1] + t * vy))


def poly_inside(poly, x, y):
    n, inside_ = len(poly), False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside_ = not inside_
        j = i
    return inside_


def circle_gap(cx, cy, rad, poly):
    """How far a circle in the (r, z) plane stands from a closed polygon there;
    0 if it touches or crosses it. The duct is not a body of revolution, so its
    bore is compared in the seam plane - the plane the joints live in - which
    only ever under-states the distance, the conservative way round for a
    clearance rule."""
    if poly_inside(poly, cx, cy):
        return 0.0
    d = min(seg_dist((cx, cy), poly[i], poly[i - 1]) for i in range(len(poly)))
    return max(0.0, d - rad)


def check_joints(path):
    """Joint clearances, from the joint map airship_slice.py writes next to the
    STEP (<slice>.joints.json).

    For every peg/hole pair on a seam: the boss (ØBOSS_D x BOSS_L), the peg and
    the hole must keep JOINT_CLEAR mm from the fan-housing wall, the plenum air
    and the impeller's swept volume; the hole must keep AIR_KEEP mm of wall
    between itself and the air path (the rule in joints()' docstring). Each
    joint also reports the wall faces its boss is fused to, which is what the
    design owner asks for in the notes.
    """
    rec = {"kind": "joints", "path": path, "problems": [], "warnings": [], "facts": {}}
    facts = rec["facts"]
    try:
        with open(path) as fh:
            jm = json.load(fh)
    except Exception as exc:
        rec["problems"].append("joint map not readable: %s" % exc)
        return rec
    facts["variant"] = jm.get("variant", "")
    facts["scale"] = jm.get("scale", 1.0)
    facts["nominalWall"] = jm.get("nominal_wall")
    clear = []
    for c in jm.get("keep_clear", []):
        prof = [tuple(p) for p in c["profile"]]
        kind = c.get("kind", "joint")
        if kind == "air2d":                       # measured in the seam plane
            clear.append((c["name"], kind, prof))
            continue
        s = revolved(prof)
        if s is None or s.isNull():
            rec["problems"].append("keep-clear profile '%s' did not build" % c["name"])
            continue
        clear.append((c["name"], kind, s))
    if not clear:
        rec["problems"].append("no keep-clear volume in the joint map")
        return rec

    rows = []
    for j in jm.get("joints", []):
        r, z = j["r"], j["z"]
        name = j["name"]
        tools = {"boss": (j["boss_d"] / 2.0, j["boss_l"]),
                 "peg": (j["peg_d"] / 2.0, j["peg_l"]),
                 "hole": (j["hole_d"] / 2.0, j["hole_l"])}
        row = {"name": name, "r": r, "z": z, "fused_to": j.get("fused_to", []),
               "why": j.get("why", ""), "clear": {}, "min": None, "airMin": None}
        for tool, (tr, tl) in tools.items():
            # stand the cylinder up on the seam plane, axis along the tangent:
            # the same place and pose the generator puts its boss in. Azimuth 0
            # is used because the revolved keep-clear volumes are symmetric.
            cyl = Part.makeCylinder(tr, tl, App.Vector(), App.Vector(0, 0, 1))
            cyl.Placement = App.Placement(App.Vector(r, 0, z),
                                          App.Rotation(App.Vector(1, 0, 0), -90))
            for cname, kind, vol in clear:
                if kind == "air2d":
                    d = circle_gap(r, z, tr, vol)
                else:
                    try:
                        d = cyl.distToShape(vol)[0]
                    except Exception as exc:
                        rec["problems"].append("%s vs %s: distance failed: %s"
                                               % (name, cname, exc))
                        continue
                need = JOINT_CLEAR if kind == "joint" else AIR_KEEP
                row["clear"]["%s/%s" % (tool, cname)] = round(d, 3)
                if kind == "joint":
                    if row["min"] is None or d < row["min"]:
                        row["min"] = d
                    if d < need:
                        rec["problems"].append(
                            "%s %s is %.2f mm from %s, needs %.1f mm clear"
                            % (name, tool, d, cname, need))
                elif tool == "hole":
                    if row["airMin"] is None or d < row["airMin"]:
                        row["airMin"] = d
                    if d < need:
                        rec["problems"].append(
                            "%s hole leaves %.2f mm to %s, needs %.1f mm of wall"
                            % (name, d, cname, need))
        rows.append(row)
    facts["joints"] = rows
    facts["count"] = len(rows)
    facts["keepClear"] = [c[0] for c in clear]
    return rec


def mesh_ladder(shape):
    """make_fcstd.py and make_pieces.py mesh a shape at 0.02, then 0.015, 0.03,
    0.01, 0.05, and keep the first deflection whose mesh is watertight. Report
    what the shape really does, so a gap the retry hides is still visible."""
    tries = []
    first = None
    for lin in (0.02, 0.015, 0.03, 0.01, 0.05):
        mm = MeshPart.meshFromShape(Shape=shape, LinearDeflection=lin,
                                    AngularDeflection=0.1, Relative=False)
        t = mesh_topology(mm)
        tries.append({"deflection": lin, "facets": t["facets"],
                      "solid": bool(mm.isSolid()), "openEdges": t["openEdges"]})
        if mm.isSolid():
            first = lin
            break
    return {"tries": tries, "firstSolid": first}


# --------------------------------------------------------------------- FCStd
def version_pair(text):
    """(major, minor) of a FreeCAD version string: '1.1R45039 (Git)' -> (1, 1)."""
    nums = re.findall(r"\d+", text)
    return tuple(int(x) for x in nums[:2])


def gui_view_objects(xml):
    """(object name -> visible) for the ViewProvider entries in GuiDocument.xml.

    This is the file the GUI reads back on open: no entry, or an entry with
    Visibility off, and the part is not drawn.
    """
    try:
        root = ET.fromstring(xml)
    except Exception as exc:
        return {}, "not parseable: %s" % exc
    out = {}
    for vp in root.iter("ViewProvider"):
        name, visible = vp.get("name"), False
        for prop in vp.iter("Property"):
            if prop.get("name") != "Visibility":
                continue
            node = prop.find("Bool")
            if node is not None:
                visible = node.get("value", "true").strip().lower() not in ("false", "0")
        if name:
            out[name] = visible
    return out, ""


def check_fcstd(path):
    rec = {"kind": "FCStd", "path": path, "problems": [], "warnings": [], "facts": {}}
    facts = rec["facts"]

    # the zip container: what FreeCAD reads before it sees any geometry
    try:
        zf = zipfile.ZipFile(path)
        names = zf.namelist()
    except Exception as exc:
        rec["problems"].append("not a readable zip: %s" % exc)
        return rec
    infos = [(i.filename, i.file_size) for i in zf.infolist()]
    brps = [(n, sz) for n, sz in infos if n.endswith(".brp")]
    facts["zipEntries"] = len(names)
    facts["hasDocumentXml"] = "Document.xml" in names
    facts["hasGuiDocumentXml"] = "GuiDocument.xml" in names
    facts["brpFiles"] = [{"name": n, "bytes": sz} for n, sz in brps]
    facts["emptyBrpFiles"] = [n for n, sz in brps if sz == 0]
    facts["bytesCompressed"] = os.path.getsize(path)
    facts["bytesUncompressed"] = sum(sz for _, sz in infos)
    facts["brpBytesTotal"] = sum(sz for _, sz in brps)
    if "Document.xml" in names:
        xml = zf.read("Document.xml").decode("utf-8", "replace")
        m = re.search(r'ProgramVersion="([^"]*)"', xml)
        facts["programVersion"] = m.group(1) if m else ""
        m = re.search(r'<Property name="Label"[^>]*>\s*<String value="([^"]*)"', xml)
        facts["storedLabel"] = m.group(1) if m else ""
        m = re.search(r'<Objects Count="(\d+)"', xml)
        facts["objectsInXml"] = int(m.group(1)) if m else 0
    if "GuiDocument.xml" in names:
        views, err = gui_view_objects(
            zf.read("GuiDocument.xml").decode("utf-8", "replace"))
        facts["viewObjects"] = views
        facts["guiParseError"] = err
    zf.close()

    # open it the way FreeCAD does
    doc = None
    t = time.time()
    try:
        doc = App.openDocument(path)
    except Exception as exc:
        rec["problems"].append("openDocument raised: %s" % exc)
    facts["openSeconds"] = round(time.time() - t, 1)
    if doc is None:
        return rec

    facts["docName"] = doc.Name
    facts["labelAfterOpen"] = doc.Label
    objs = []
    for o in doc.Objects:
        info = {"name": o.Name, "type": getattr(o, "Type", o.__class__.__name__),
                "label": o.Label}
        if hasattr(o, "Shape"):
            info["visibility"] = bool(getattr(o, "Visibility", True))
            info.update(shape_info(o.Shape))
        objs.append(info)
    facts["objects"] = objs
    facts["objectCount"] = len(objs)

    geo = [o for o in objs if "isNull" in o and not o["isNull"]]
    visible = [o for o in geo if o.get("visibility", True)]
    facts["objectsWithGeometry"] = [o["name"] for o in geo]
    facts["visibleGeometry"] = [o["name"] for o in visible]
    facts["hasVisibleGeometry"] = bool(visible)

    main = None
    for o in geo:
        if o.get("volume", 0.0) and (main is None or o["volume"] > main.get("volume", 0.0)):
            main = o
    facts["mainObject"] = main["name"] if main else None
    facts["totalVolume"] = sum(o.get("volume", 0.0) for o in geo)
    if main:
        facts["mainValid"] = main.get("isValid")
        facts["mainSolids"] = main.get("solids")
        facts["mainVolume"] = main.get("volume")
        facts["mainFaces"] = main.get("faces")
        facts["mainShellsClosed"] = main.get("shellsClosed")
        if not TESS_OFF:
            for o in doc.Objects:
                if o.Name == main["name"]:
                    facts["tessellate"] = tess_cost(o.Shape)
                    break

    # what a user would complain about
    if not facts["hasVisibleGeometry"]:
        rec["problems"].append("no visible geometry in the document")
    if not facts["hasDocumentXml"]:
        rec["problems"].append("Document.xml missing from the zip")
    if not facts["hasGuiDocumentXml"]:
        rec["problems"].append(
            "GuiDocument.xml missing: the GUI restores no camera, no per-object "
            "visibility and no display mode, so the parts are not switched on "
            "for the viewer")
    elif facts.get("guiParseError"):
        rec["problems"].append("GuiDocument.xml: %s" % facts["guiParseError"])
    else:
        views = facts.get("viewObjects", {})
        hidden = [o["name"] for o in geo if not views.get(o["name"], False)]
        if hidden:
            rec["problems"].append(
                "GuiDocument.xml has no visible ViewObject for: %s"
                % ", ".join(hidden))
    if facts["emptyBrpFiles"]:
        real = [n for n in facts["emptyBrpFiles"] if "Suppressed" not in n]
        if real:
            rec["problems"].append("empty .brp: " + ", ".join(real))
        else:
            rec["warnings"].append(
                "empty .brp: " + ", ".join(facts["emptyBrpFiles"]) +
                " (FreeCAD's suppressed-shape slot)")
    if facts.get("mainValid") is False:
        rec["problems"].append("main shape is not valid")
    if main and main.get("isNull"):
        rec["problems"].append("main shape is null")
    if any(c is False for c in main.get("shellsClosed", [])) if main else False:
        rec["problems"].append("main shape has an open shell")
    stored = facts.get("storedLabel", "")
    stem = os.path.basename(path)[:-len(".FCStd")]
    if stored and stored.lower() not in stem.lower():
        rec["problems"].append(
            "stored document label '%s' does not match the file name '%s'" % (stored, stem))
    if version_pair(facts.get("programVersion", "")) != version_pair(version_string()):
        rec["warnings"].append(
            "written by %s, read by %s: FreeCAD rebuilds the shape's element map "
            "when the document is opened"
            % (facts.get("programVersion", "?"), version_string()))
    if facts.get("brpBytesTotal", 0) > 20_000_000:
        rec["warnings"].append(
            "%s bytes of brep stored in %d shape files inside a %s byte document"
            % ("{:,}".format(facts["brpBytesTotal"]), len(brps),
               "{:,}".format(facts["bytesCompressed"])))
    dup = [o["name"] for o in geo if main and abs(o.get("volume", 0.0)
                                                 - main.get("volume", 0.0)) < 1e-6]
    if len(dup) > 1:
        rec["warnings"].append(
            "the same shape is stored %d times: %s" % (len(dup), ", ".join(dup)))
    App.closeDocument(doc.Name)
    return rec


# ------------------------------------------------------------------------ STEP
def check_step(path):
    rec = {"kind": "STEP", "path": path, "problems": [], "warnings": [], "facts": {}}
    facts = rec["facts"]
    with open(path, "rb") as fh:
        head = fh.read(4096)
    facts["bytes"] = os.path.getsize(path)
    facts["ascii"] = head.lstrip().startswith(b"ISO 3D REPRESENTATION")
    m = re.search(rb"FILE_NAME\('([^']*)','([^']*)'", head)
    facts["stepWriter"] = m.group(1).decode() if m else ""
    facts["stepDate"] = m.group(2).decode() if m else ""

    s = Part.Shape()
    t = time.time()
    try:
        s.read(path)
    except Exception as exc:
        rec["problems"].append("read failed: %s" % exc)
        return rec
    facts["readSeconds"] = round(time.time() - t, 1)
    info = shape_info(s)
    facts.update(info)
    if info.get("isNull"):
        rec["problems"].append("shape is null after read")
    if info.get("isValid") is False:
        rec["problems"].append("shape is not valid: %s" % info.get("check", ""))
    if not info.get("solids"):
        rec["problems"].append("no solid: nothing printable")
    if any(c is False for c in info.get("shellsClosed", [])):
        rec["problems"].append("open shell: the solid has a hole in its skin")
    if info.get("solids", 0) > 1:
        rec["warnings"].append(
            "%d solids in one file (the docs promise a single solid)" % info["solids"])
    if not TESS_OFF and info.get("solids"):
        facts["tessellate"] = tess_cost(s)
        facts["meshLadder"] = mesh_ladder(s)
        tries = facts["meshLadder"]["tries"]
        if tries[0]["openEdges"]:
            rec["warnings"].append(
                "meshing at the generator's first deflection 0.02 leaves %d open edges "
                "(%d facets); the retry at %s is what made the print file watertight"
                % (tries[0]["openEdges"], tries[0]["facets"],
                   facts["meshLadder"]["firstSolid"]))
        if facts["meshLadder"]["firstSolid"] is None:
            rec["problems"].append(
                "no deflection in the generator's ladder gives a watertight mesh: "
                "make_fcstd.py would write a non-watertight STL")
    return rec


# ------------------------------------------------------------------------- STL
def check_stl(path):
    rec = {"kind": "STL", "path": path, "problems": [], "warnings": [], "facts": {}}
    facts = rec["facts"]

    # container: a binary STL declares its facet count in the header
    with open(path, "rb") as fh:
        head = fh.read(84)
    facts["bytes"] = os.path.getsize(path)
    facts["ascii"] = head.lstrip().startswith(b"solid")
    if not facts["ascii"]:
        facts["declaredFacets"] = struct.unpack("<I", head[80:84])[0]
        facts["header"] = head[:80].decode("latin-1", "replace").strip()
        facts["actualFacets"] = (facts["bytes"] - 84) // 50
        if (facts["bytes"] - 84) % 50:
            rec["problems"].append("truncated: facet records do not divide evenly")
        elif facts["declaredFacets"] != facts["actualFacets"]:
            rec["problems"].append(
                "header declares %d facets, file holds %d"
                % (facts["declaredFacets"], facts["actualFacets"]))

    m = Mesh.Mesh(path)
    facts["facets"] = m.CountFacets
    facts["points"] = m.CountPoints
    facts["isSolid"] = bool(m.isSolid())
    facts["hasNonManifolds"] = bool(m.hasNonManifolds())
    facts["hasSelfIntersections"] = bool(m.hasSelfIntersections())
    facts["hasNonUniformOrientedFacets"] = bool(m.hasNonUniformOrientedFacets())
    facts["hasCorruptedFacets"] = bool(m.hasCorruptedFacets())
    facts["components"] = m.countComponents()
    facts["volume"] = float(m.Volume)
    bb = m.BoundBox
    facts["bbox"] = [bb.XLength, bb.YLength, bb.ZLength]
    facts["bboxMin"] = [bb.XMin, bb.YMin, bb.ZMin]
    facts["bboxMax"] = [bb.XMax, bb.YMax, bb.ZMax]
    try:
        facts.update(mesh_topology(m))
    except Exception as exc:
        facts["topologyError"] = str(exc)
    if facts["facets"] != facts.get("declaredFacets", facts["facets"]):
        rec["problems"].append("header declares %s facets, mesh has %d"
                               % (facts.get("declaredFacets"), facts["facets"]))
    if not facts["isSolid"] or facts.get("openEdges", 0):
        rec["problems"].append(
            "not watertight: %s open edges, isSolid=%s"
            % (facts.get("openEdges", "?"), facts["isSolid"]))
    if facts["hasNonManifolds"] or facts.get("nonManifoldEdges", 0):
        rec["problems"].append("non-manifold edges: %s"
                               % facts.get("nonManifoldEdges", "?"))
    if facts["hasSelfIntersections"]:
        rec["problems"].append("self-intersecting mesh")
    if facts["hasNonUniformOrientedFacets"]:
        rec["problems"].append("facets not consistently oriented")
    if facts["hasCorruptedFacets"]:
        rec["problems"].append("corrupted facets")
    if facts["components"] > 1:
        rec["warnings"].append("%d separate parts in one file" % facts["components"])
    if facts["volume"] <= 0:
        rec["problems"].append("non-positive mesh volume %s" % facts["volume"])

    # does it fit the printers the docs name, where it sits on the bed?
    dims = facts["bbox"]
    fits = [name for w, d, h, name in BEDS if sorted(dims) <= sorted([w, d, h])]
    facts["fitsBeds"] = fits
    facts["atOrigin"] = all(abs(v) < 0.05 for v in facts["bboxMin"])
    if not fits:
        rec["problems"].append(
            "bounding box %.0f x %.0f x %.0f mm fits no documented bed" % tuple(dims))
    if not facts["atOrigin"]:
        rec["warnings"].append(
            "not placed at the bed origin: min corner is (%.1f, %.1f, %.1f), "
            "max (%.1f, %.1f, %.1f)" % (*facts["bboxMin"], *facts["bboxMax"]))

    # wall thickness against the nozzle the build notes specify, and the thick
    # material the one-wall rule forbids. The hull STLs are laid flat for printing
    # (make_fcstd.py's pose), so undo that pose first: the thick blobs are then
    # reported where the code that makes them says they are, in model coordinates.
    if not THIN_OFF:
        scan = m
        if re.search(r"PieSlice1026", os.path.basename(path)):
            scan = m.copy()
            scan.transformGeometry(App.Rotation(App.Vector(1, 0, 0), -90).toMatrix())
            scan.transformGeometry(App.Rotation(App.Vector(0, 0, 1), -22.5).toMatrix())
            facts["wallScanFrame"] = "model frame (the print pose is undone)"
        facts["thickness"] = wall_map(scan, samples=WALL_SAMPLES, report=THIN_REPORT)
        th = facts["thickness"]
        if th.get("sampled"):
            if th["min"] < LAYER:
                rec["problems"].append(
                    "walls thinner than the %.2f mm layer: %.3f mm at %d of %d sampled "
                    "facets (%d under the %.2f mm nozzle)"
                    % (LAYER, th["min"], th["underLayer"], th["sampled"],
                       th["underNozzle"], NOZZLE))
            elif th["min"] < NOZZLE:
                rec["warnings"].append(
                    "%.3f mm thick at %d of %d sampled facets, under the %.2f mm nozzle"
                    % (th["min"], th["underNozzle"], th["sampled"], NOZZLE))
            if th.get("underBlobCount"):
                rec["warnings"].append(
                    "thin material: %.0f mm2 of the sampled wall is under the %.2f mm "
                    "nozzle in %d blob(s)"
                    % (th["underArea"], NOZZLE, th["underBlobCount"]))
                for b in th["underBlobs"][:8]:
                    rec["warnings"].append("thin blob   " + blob_text(b))
        if th.get("thickFacets"):
            rec["warnings"].append(
                "thick material: %.1f%% of the sampled wall (%.0f of %.0f mm2) is over %.2f mm "
                "(nominal %.2f + 0.25 mm) in %d blob(s)"
                % (th["thickAreaPct"], th["thickArea"], th["hitArea"], th["thickAt"],
                   th["nominal"], th.get("blobCount", 0)))
            for b in th["blobs"][:8]:
                rec["warnings"].append("thick blob  " + blob_text(b))
    return rec


# ------------------------------------------------------------- cross-checks
STEP_FOR_STL = {
    "PieSlice1026-v0.2.1-8T.stl": "airship pie slice 1026.step",
    "PieSlice1026-v0.2.1-8T-KobraMax.stl": "airship pie slice 1026 x1.9.step",
    "PieSlice1026-v0.2.1-8T-CR10Pro.stl": "airship pie slice 1026 CR10Pro.step",
    "PieSlice1026-v0.2.1-4T-left.stl": "airship pie slice 1026 4T left.step",
    "PieSlice1026-v0.2.1-4T-left-KobraMax.stl": "airship pie slice 1026 4T left x1.9.step",
    "PieSlice1026-v0.2.1-4T-right.stl": "airship pie slice 1026 4T right.step",
    "PieSlice1026-v0.2.1-4T-right-KobraMax.stl": "airship pie slice 1026 4T right x1.9.step",
}
PIECE_DIR = "pieces/airship pie slice 1026 4T {kind} 12s small x3.8/{piece}.step"
TUBE = "pieces/airship pie slice 1026 4T left 12s small x3.8/intake_tube_{n}.step"
SLICE_DIR = os.path.join(CURRENT, "CAD Files", "SimplifiedSlice")
_STEP_VOL = {}


def step_for_stl(path):
    base = os.path.basename(path)
    if base in STEP_FOR_STL:
        return os.path.join(SLICE_DIR, STEP_FOR_STL[base])
    m = re.match(r"PieSlice1026-v0\.2\.1-(left|right|plain)-(.+)\.stl$", base)
    if m:
        return os.path.join(SLICE_DIR,
                            PIECE_DIR.format(kind=m.group(1), piece=m.group(2).replace("-", "_")))
    m = re.match(r"PieSlice1026-v0\.2\.1-intake-tube-(\d)\.stl$", base)
    if m:
        return os.path.join(SLICE_DIR, TUBE.format(n=m.group(1)))
    return None


def step_for_fcstd(path):
    stem = os.path.basename(path)[:-len(".FCStd")]
    cand = os.path.join(os.path.dirname(path), stem + ".step")
    return cand if os.path.exists(cand) else None


def step_volume(path):
    if path in _STEP_VOL:
        return _STEP_VOL[path]
    s = Part.Shape()
    try:
        s.read(path)
    except Exception as exc:
        _STEP_VOL[path] = (None, str(exc))
        return _STEP_VOL[path]
    v = float(s.Volume)
    del s
    _STEP_VOL[path] = (v, "")
    return _STEP_VOL[path]


def compare_volume(rec, step_path):
    """Compare this file's volume with the STEP it was produced from."""
    a = rec["facts"].get("volume", rec["facts"].get("mainVolume"))
    if a is None or not step_path or not os.path.exists(step_path):
        rec["cross"] = {"step": step_path or "no STEP with this name", "status": "not compared"}
        return
    b, err = step_volume(step_path)
    if b is None:
        rec["cross"] = {"step": step_path, "status": "STEP read failed: %s" % err}
        return
    rel = abs(a - b) / max(abs(b), 1.0)
    rec["cross"] = {"step": os.path.relpath(step_path, CURRENT), "volume": a,
                    "stepVolume": b, "relDiff": round(rel, 5),
                    "status": "same" if rel <= VOL_TOL else "DIFFERENT"}
    if rel > VOL_TOL:
        rec["problems"].append(
            "volume %s mm3 vs the STEP's %s mm3 (%.1f %% apart): this file is not "
            "the model the STEP describes" % ("{:,.0f}".format(a), "{:,.0f}".format(b),
                                              rel * 100))


def name_tokens(text):
    return set(re.findall(r"[a-z0-9.]+", text.lower()))


def pick_step(path, candidates):
    """The candidate STEP in the sibling folder whose name best matches this
    document. A pieces document and the other slice types share part names
    (middle, top_outer, ...), so the folder name is what tells them apart.
    """
    tok = name_tokens(os.path.basename(path))
    return max(candidates, key=lambda sp: (len(tok & name_tokens(
        os.path.basename(os.path.dirname(sp)))),
        -len(os.path.relpath(sp, os.path.dirname(path)))))


def compare_assembly(rec, path):
    """A Propulsion or pieces .FCStd is an assembly of separate parts, and the
    parts are the .step files in the folders next to it, so match them by name
    and compare the sums."""
    here = os.path.dirname(path)
    steps = walk(here, (".step",))
    if not steps:
        rec["cross"] = {"step": "no sibling STEP parts", "status": "not compared"}
        return
    by_name = {}
    for sp in steps:
        by_name.setdefault(os.path.splitext(os.path.basename(sp))[0], []).append(sp)
    own = {o["name"]: o["volume"] for o in rec["facts"].get("objects", [])
           if "volume" in o}
    matched, missing, total = [], [], 0.0
    for name in sorted(own):
        cand = by_name.get(name)
        if not cand:
            missing.append(name)
            continue
        sp = pick_step(path, cand)
        matched.append(sp)
        v, err = step_volume(sp)
        if v is None:
            missing.append("%s (%s)" % (name, err))
        else:
            total += v
    own_names = set(own)
    extra = sorted({os.path.basename(sp) for sp in steps
                    if os.path.splitext(os.path.basename(sp))[0] not in own_names})
    own_total = sum(own.values())
    rel = abs(own_total - total) / max(abs(total), 1.0)
    rec["cross"] = {"parts": [os.path.relpath(sp, CURRENT) for sp in matched],
                    "volume": own_total, "stepPartsVolume": total,
                    "relDiff": round(rel, 5),
                    "missing": missing, "extra": extra,
                    "status": "same" if rel <= VOL_TOL and not missing else "DIFFERENT"}
    if missing:
        rec["problems"].append(
            "parts with no readable sibling STEP: %s" % ", ".join(missing))
    if rel > VOL_TOL:
        rec["problems"].append(
            "assembly volume %s mm3 vs the %d matched sibling STEP parts' %s mm3 "
            "(%.1f %% apart): the document is not the parts on disk"
            % ("{:,.0f}".format(own_total), len(matched), "{:,.0f}".format(total),
               rel * 100))
    if extra:
        rec["warnings"].append(
            "sibling STEP not in the document: %s"
            % ", ".join(os.path.basename(e) for e in extra))


# ------------------------------------------------------------------- driver
def walk(root, exts):
    out = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(exts):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def script_argv():
    """freecadcmd puts its own name and the script path in sys.argv; drop both."""
    me = os.path.splitext(os.path.abspath(__file__))[0]
    out = []
    for a in sys.argv[1:]:
        if os.path.splitext(os.path.abspath(a))[0] == me:
            continue
        out.append(a)
    return out


def main(argv):
    global TESS_OFF, THIN_OFF, THIN_REPORT, WALL_SAMPLES
    ap = argparse.ArgumentParser(prog="check_outputs.py", add_help=False)
    ap.add_argument("--json", dest="json")
    ap.add_argument("--cad-root", dest="cad_roots", action="append")
    ap.add_argument("--stl-root", dest="stl_roots", action="append")
    ap.add_argument("--filter", dest="filter", default="")
    ap.add_argument("--only", dest="only", default="all",
                    choices=("cad", "print", "all"))
    ap.add_argument("--no-tess", dest="no_tess", action="store_true")
    ap.add_argument("--no-thin", dest="no_thin", action="store_true")
    ap.add_argument("--joints", dest="joints", action="append")
    ap.add_argument("--thin-report", dest="thin_report", action="store_true")
    ap.add_argument("--samples", dest="samples", type=int, default=6000)
    ns = ap.parse_args(shlex.split(" ".join(a for a in argv if a != "--pass")))
    TESS_OFF = ns.no_tess
    THIN_OFF = ns.no_thin
    THIN_REPORT = ns.thin_report
    WALL_SAMPLES = max(100, ns.samples)

    cad_roots = ns.cad_roots or [os.path.join(CURRENT, "CAD Files")]
    stl_roots = ns.stl_roots or [os.path.join(CURRENT, "Print Files")]

    cad_exts = (".fcstd", ".step") if ns.only in ("cad", "all") else ()
    stl_exts = (".stl",) if ns.only in ("print", "all") else ()
    files = []
    for r in cad_roots:
        files += walk(r, cad_exts)
    for r in stl_roots:
        files += walk(r, stl_exts)
    files = [f for f in files if ns.filter in f]
    order = {".fcstd": 0, ".step": 1, ".stl": 2}
    files.sort(key=lambda p: (order[os.path.splitext(p)[1].lower()], p))

    recs, fails = [], 0
    for p in files:
        ext = os.path.splitext(p)[1].lower()
        t = time.time()
        rec = check_fcstd(p) if ext == ".fcstd" else check_step(p) if ext == ".step" \
            else check_stl(p)
        if rec["kind"] in ("FCStd", "STL"):
            partner = (step_for_fcstd(p) if rec["kind"] == "FCStd"
                       else step_for_stl(p))
            if rec["kind"] == "FCStd" and not partner:
                compare_assembly(rec, p)
            else:
                compare_volume(rec, partner)
        rec["seconds"] = round(time.time() - t, 1)
        recs.append(rec)

        f, problems, warns = rec["facts"], rec["problems"], rec["warnings"]
        status = "FAIL" if problems else "PASS"
        if problems:
            fails += 1
        detail = []
        if rec["kind"] == "STL":
            th = f.get("thickness", {})
            detail = ["facets {:,}".format(f.get("facets", 0)),
                      "open {}".format(f.get("openEdges", "?")),
                      "nonmani {}".format(f.get("nonManifoldEdges", "?")),
                      "selfint {}".format(f.get("hasSelfIntersections")),
                      "orientOK {}".format(not f.get("hasNonUniformOrientedFacets")),
                      "parts {}".format(f.get("components")),
                      "vol {:,.0f} mm3".format(f.get("volume", 0)),
                      "bbox {:.0f}x{:.0f}x{:.0f}".format(*f.get("bbox", [0, 0, 0])),
                      "bed {}".format("/".join(f.get("fitsBeds", ["-"])) or "-"),
                      "wall min {} mm <nozzle {} <layer {}".format(
                          th.get("min", "-"), th.get("underNozzle", "-"),
                          th.get("underLayer", "-")),
                      "sliver facets skipped {}".format(th.get("tinySkipped", "-")),
                      "grazing hits skipped {}".format(th.get("grazeSkipped", "-")),
                      "thick {}% ({} mm2, {} blobs)".format(
                          th.get("thickAreaPct", "-"), th.get("thickArea", "-"),
                          th.get("blobCount", 0))]
        else:
            vol = f.get("totalVolume", f.get("volume", f.get("mainVolume", 0)))
            detail = ["solids {}".format(f.get("solids", f.get("mainSolids", 0))),
                      "faces {:,}".format(f.get("faces", 0)),
                      "valid {}".format(f.get("isValid", f.get("mainValid"))),
                      "vol {:,.0f} mm3".format(vol)]
            if rec["kind"] == "STEP":
                lad = f.get("meshLadder", {})
                te = f.get("tessellate", {})
                detail += ["tess {} tris in {} s".format(te.get("triangles", "-"),
                                                           te.get("seconds", "-")),
                           "mesh@0.02 open {}".format(
                               lad["tries"][0]["openEdges"] if lad else "-"),
                           "firstSolid {}".format(lad.get("firstSolid", "-"))]
            if rec["kind"] == "FCStd":
                te = f.get("tessellate", {})
                detail = ["objects {}".format(f.get("objectCount")),
                          "visible {}".format(len(f.get("visibleGeometry", []))),
                          "main {}".format(f.get("mainObject")),
                          "vol {:,.0f} mm3".format(f.get("mainVolume", 0)),
                          "gui {}".format(f.get("hasGuiDocumentXml")),
                          "brp {:,} b".format(f.get("brpBytesTotal", 0)),
                          "tess {} tris in {} s".format(te.get("triangles", "-"),
                                                        te.get("seconds", "-"))]
        cross_rec = rec.get("cross", {})
        cross = cross_rec.get("status", "")
        if cross:
            detail.append("vs {} {}".format(
                "STEP parts" if cross_rec.get("parts") else "STEP", cross))
        print("{}  {}  [{}] {}".format(
            status, os.path.relpath(p, CURRENT), rec["kind"], "  ".join(detail)))
        for w in problems:
            print("      PROBLEM  {}".format(w))
        for w in warns:
            print("      note     {}".format(w))
        if THIN_REPORT and rec["kind"] == "STL":
            for line in thin_report_lines(f.get("thickness", {})):
                print(line)
            sys.stdout.flush()

    for jp in ns.joints or []:
        rec = check_joints(jp)
        recs.append(rec)
        f, problems = rec["facts"], rec["problems"]
        status = "FAIL" if problems else "PASS"
        if problems:
            fails += 1
        print("{}  {}  [joints] {} joints, clear of: {}".format(
            status, os.path.relpath(jp, CURRENT), f.get("count", 0),
            ", ".join(f.get("keepClear", []))))
        for j in f.get("joints", []):
            print("      {:<24} r={:7.1f} z={:7.1f}  fused to {}  from fan/housing: {}  "
                  "wall to air: {}".format(
                      j["name"], j["r"], j["z"],
                      "+".join(j["fused_to"]) or "-",
                      " ".join("%s %.2f mm" % (k, v) for k, v in sorted(j["clear"].items())
                                if not k.endswith(("/plenum air", "/duct bore", "/shaft bore"))),
                      " ".join("%s %.2f mm" % (k, v) for k, v in sorted(j["clear"].items())
                                if k.endswith(("/plenum air", "/duct bore",
                                               "/shaft bore", "/bulb bore")))))
        for w in problems:
            print("      PROBLEM  {}".format(w))
        sys.stdout.flush()

    if ns.json:
        with open(ns.json, "w") as fh:
            json.dump(recs, fh, indent=1, default=str)
        print("\nwrote {} ({} records)".format(ns.json, len(recs)))

    n = len(recs)
    print("\n{} files checked, {} pass, {} fail".format(n, n - fails, fails))
    # freecadcmd's exit path does not flush Python's stdout, so without this
    # the summary lines never reach the log
    sys.stdout.flush()
    sys.stderr.flush()
    return 1 if fails else 0


if __name__ in ("__main__", os.path.splitext(os.path.basename(__file__))[0]):
    sys.exit(main(script_argv()))
