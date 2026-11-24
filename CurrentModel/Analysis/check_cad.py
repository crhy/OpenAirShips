#!/usr/bin/env python3
"""CAD-level (B-rep) checker for the airship STEP — issue #36, task c02.

Checks the STEP from "CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py",
not the printed mesh: the STL checker (check_outputs.py) reads the tessellation,
and a coincident-face sliver wall or an internal face survives the fuse long
before the mesh notices. This walks the B-rep through CadQuery/OCP and FAILS
(exit 1, one line per failure) on:

  solids    more than 1 solid
  shells    more than 1 outer shell
  invalid   BRepCheck_Analyzer says the shape is invalid
  slivers   any face under FACE_MIN (1.0) mm2
  short     any edge under EDGE_MIN (0.2) mm
  hairline  any pair of faces of the solid closer than HAIRLINE (0.2) mm but
            not touching (seam cracks / hairline gaps): BRepExtrema_DistShapeShape
            on face pairs whose bounding boxes come within 0.2 mm
  internal  any face with material on both sides (a point 0.05 mm along +/- the
            normal is inside the solid twice): a face shared by two solids
            before the fuse shows up like this

Prints counts and the worst 10 locations (x,y,z mm) per check.

    /home/rhy/.venvs/cadquery/bin/python -I CurrentModel/Analysis/check_cad.py \
        "CurrentModel/CAD Files/SimplifiedSlice/airship pie slice 1026 CR10Pro.step" \
        [--json out.json]
"""
import argparse
import faulthandler
import json
import os
import sys
import time

faulthandler.enable()

import cadquery as cq
import numpy as np
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN, TopAbs_REVERSED

FACE_MIN = 1.0        # mm2: a face under this is a sliver wall's two faces
EDGE_MIN = 0.2        # mm: an edge under this is a pinched seam
HAIRLINE = 0.2        # mm: faces this close but not touching = a gap to fill
TOUCHING = 1e-6       # mm: below this the faces touch, which is not a gap
SIDE = 0.05           # mm the internal-face probe stands off the face
TOL = 1e-6


def bnds(shape):
    bb = shape.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def center(shape):
    c = shape.Center()
    return (round(c.x, 3), round(c.y, 3), round(c.z, 3))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    t0 = time.time()
    ws = cq.importers.importStep(args.step)
    vals = ws.vals() if isinstance(ws, cq.Workplane) else [ws]
    shape = cq.Compound.makeCompound(vals)
    print("# check_cad on %s" % args.step)
    print("# loaded %.1fs, %d shape(s)" % (time.time() - t0, len(vals)))

    fails, results = [], {}

    def fail(check, line):
        fails.append(line)
        print("FAIL %s: %s" % (check, line))

    # --- solids / shells ------------------------------------------------------
    solids = shape.Solids()
    results["solids"] = {"count": len(solids)}
    if len(solids) > 1:
        fail("solids", "the STEP holds %d solids, expected 1" % len(solids))

    outer_shells = 0
    for s in solids:
        for sh in s.Shells():
            # OCC convention: the outer shell of a solid is FORWARD, voids are
            # REVERSED; anything FORWARD is an outside.
            if sh.wrapped.Orientation() != TopAbs_REVERSED:
                outer_shells += 1
    results["shells"] = {"count": outer_shells}
    if outer_shells > 1:
        fail("shells", "%d outer shells, expected 1" % outer_shells)

    # --- BRepCheck_Analyzer ----------------------------------------------------
    valid = BRepCheck_Analyzer(shape.wrapped).IsValid()
    results["invalid"] = {"valid": valid}
    if not valid:
        fail("invalid", "BRepCheck_Analyzer says the shape is invalid")

    faces = shape.Faces()
    edges = shape.Edges()

    # --- sliver faces ----------------------------------------------------------
    t = time.time()
    slivers = [(f.Area(), center(f)) for f in faces if f.Area() < FACE_MIN]
    slivers.sort()
    results["slivers"] = {"checked": len(faces), "count": len(slivers),
                          "worst": [(a, loc) for a, loc in slivers[:10]]}
    for a, loc in slivers:
        fail("slivers", "face %.4f mm2 at x=%.3f y=%.3f z=%.3f" % (a, *loc))
    print("# slivers: %d faces checked, %d under %.1f mm2 (%.1fs)"
          % (len(faces), len(slivers), FACE_MIN, time.time() - t))

    # --- short edges ------------------------------------------------------------
    t = time.time()
    shorts = [(e.Length(), center(e)) for e in edges if e.Length() < EDGE_MIN]
    shorts.sort()
    results["short"] = {"checked": len(edges), "count": len(shorts),
                        "worst": [(l, loc) for l, loc in shorts[:10]]}
    for l, loc in shorts:
        fail("short", "edge %.4f mm long at x=%.3f y=%.3f z=%.3f" % (l, *loc))
    print("# short: %d edges checked, %d under %.1f mm (%.1fs)"
          % (len(edges), len(shorts), EDGE_MIN, time.time() - t))

    # --- hairline gaps between face pairs ---------------------------------------
    # A bbox gap is a lower bound on the face distance, so only pairs whose
    # bounding boxes come within HAIRLINE can be closer than HAIRLINE.
    t = time.time()
    # faces that share an edge touch at that edge and are never a gap: skip them
    # before the (expensive) extrema. hash(Shape) is IsSame-consistent here.
    seen = {}
    adjacent = set()
    for i, f in enumerate(faces):
        for e in f.Edges():
            k = hash(e.wrapped)
            if k in seen:
                adjacent.add((seen[k], i) if seen[k] < i else (i, seen[k]))
            else:
                seen[k] = i
    bb = np.array([bnds(f) for f in faces])
    order = np.argsort(bb[:, 0])
    xs = bb[order, 0]
    pairs = []
    for k, i in enumerate(order):
        stop = np.searchsorted(xs, bb[i, 1] + HAIRLINE, side="right")
        cand = order[k + 1:stop]
        if not len(cand):
            continue
        others = bb[cand]
        # gap between the two bounding boxes: max over the axes of the per-axis
        # separation (0 when they overlap on that axis)
        mi, Mi = bb[i, 0::2], bb[i, 1::2]
        mo, Mo = others[:, 0::2], others[:, 1::2]
        gap = np.max(np.maximum(np.maximum(mi - Mo, mo - Mi), 0), axis=1)
        for j in cand[gap < HAIRLINE]:
            j = int(j)
            if (min(i, j), max(i, j)) in adjacent:
                continue
            pairs.append((int(i), j))
    npairs = len(pairs)

    # BRepExtrema on this model's BSpline soup has segfaulted on degenerate face
    # pairs, which kills the process silently: run the measurements in forked
    # chunk workers (copy-on-write, the loaded STEP is shared) and retry a
    # crashing chunk pair by pair, reporting the crash itself as a failure.
    PAIR_TIMEOUT = 10         # s per pair: a hung BRepExtrema kills its worker

    def worker(w, chunk):
        import signal
        # SIG_DFL: the 10 s alarm kills the worker even inside C++ (a Python
        # handler cannot interrupt BRepExtrema, it only defers to the pair's end)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        hits = []
        for (i, j) in chunk:
            signal.alarm(PAIR_TIMEOUT)
            dist = BRepExtrema_DistShapeShape(faces[i].wrapped, faces[j].wrapped)
            signal.alarm(0)
            if not dist.IsDone() or not dist.NbSolution():
                continue
            d = dist.Value()
            if TOUCHING < d < HAIRLINE:
                p1, p2 = dist.PointOnShape1(1), dist.PointOnShape2(1)
                hits.append([i, j, d, (p1.X(), p1.Y(), p1.Z()),
                             (p2.X(), p2.Y(), p2.Z())])
        os.write(w, json.dumps(hits).encode())
        os.close(w)
        os._exit(0)

    def run(chunk):
        rd, w = os.pipe()
        pid = os.fork()
        if pid == 0:
            try:
                worker(w, chunk)
            except BaseException:
                os.close(w)
                os._exit(2)
        os.close(w)
        data = b""
        while True:
            blk = os.read(rd, 1 << 16)
            if not blk:
                break
            data += blk
        os.close(rd)
        _, status = os.waitpid(pid, 0)
        if os.WIFSIGNALED(status) or os.waitstatus_to_exitcode(status) != 0:
            return None
        return json.loads(data or b"[]")

    hair = []
    broken = 0
    bad = set()
    def add(d, p1, p2, i=None, j=None):
        """Record one hit; a None distance (the worker timed out or crashed on
        the pair) counts as a failure at the two face centres."""
        if d is None:
            c1, c2 = center(faces[i]), center(faces[j])
            p1 = p2 = ((c1[0] + c2[0]) / 2, (c1[1] + c2[1]) / 2,
                       (c1[2] + c2[2]) / 2)
        hair.append((d if d is not None else HAIRLINE,
                     (round((p1[0] + p2[0]) / 2, 3), round((p1[1] + p2[1]) / 2, 3),
                      round((p1[2] + p2[2]) / 2, 3))))
        return 1 if d is None else 0

    for start in range(0, npairs, 500):
        chunk = []
        for (i, j) in pairs[start:start + 500]:
            if i in bad or j in bad:
                broken += 1
                c1, c2 = center(faces[i]), center(faces[j])
                hair.append((HAIRLINE, (round((c1[0] + c2[0]) / 2, 3),
                                        round((c1[1] + c2[1]) / 2, 3),
                                        round((c1[2] + c2[2]) / 2, 3))))
            else:
                chunk.append((i, j))
        if not chunk:
            continue
        got = run(chunk)
        if got is None:
            print("# hairline: chunk %d crashed (bad face), retrying per-pair"
                  % start, flush=True)
            for (i, j) in chunk:
                if i in bad or j in bad:
                    broken += 1
                    c1, c2 = center(faces[i]), center(faces[j])
                    hair.append((HAIRLINE, (round((c1[0] + c2[0]) / 2, 3),
                                            round((c1[1] + c2[1]) / 2, 3),
                                            round((c1[2] + c2[2]) / 2, 3))))
                    continue
                one = run([(i, j)])
                if one is None:
                    bad.add(i)
                    bad.add(j)
                    broken += 1
                    c1, c2 = center(faces[i]), center(faces[j])
                    hair.append((HAIRLINE, (round((c1[0] + c2[0]) / 2, 3),
                                            round((c1[1] + c2[1]) / 2, 3),
                                            round((c1[2] + c2[2]) / 2, 3))))
                else:
                    for _, _, d, p1, p2 in one:
                        broken += add(d, p1, p2, i, j)
        else:
            for _, _, d, p1, p2 in got:
                broken += add(d, p1, p2)
        if (start // 500) % 20 == 0:
            print("# hairline: %d/%d pairs, %d gaps (%.1fs)"
                  % (start + len(chunk), npairs, len(hair),
                     time.time() - t), flush=True)
    hair.sort()
    results["hairline"] = {"pairs": npairs, "count": len(hair),
                           "crashed": broken,
                           "worst": [(d, loc) for d, loc in hair[:10]]}
    for d, loc in hair:
        fail("hairline", "faces %.4f mm apart (not touching) at x=%.3f y=%.3f z=%.3f"
             % (d, *loc))
    if broken:
        fail("hairline", "%d face pairs crash BRepExtrema (degenerate faces)"
             % broken)
    print("# hairline: %d candidate pairs tested, %d gaps under %.1f mm, "
          "%d crashes (%.1fs)" % (npairs, len(hair), HAIRLINE, broken,
                                  time.time() - t))

    # --- internal faces ----------------------------------------------------------
    # A face shared by two solids before the fuse has material on both sides:
    # test a point SIDE mm along +/- the surface normal; both inside = internal.
    t = time.time()
    internal = []
    nchecked = 0
    for s in solids:
        cls = BRepClass3d_SolidClassifier(s.wrapped)
        for f in s.Faces():
            nchecked += 1
            try:
                n = f.normalAt()          # unoriented surface normal at the uv centre
            except Exception:
                continue
            c = f.Center()
            inside = []
            for sign in (+1, -1):
                p = gp_Pnt(c.x + sign * SIDE * n.x, c.y + sign * SIDE * n.y,
                           c.z + sign * SIDE * n.z)
                cls.Perform(p, TOL)
                inside.append(cls.State() == TopAbs_IN)
            if all(inside):
                internal.append(center(f))
    results["internal"] = {"checked": nchecked, "count": len(internal),
                           "worst": internal[:10]}
    for loc in internal:
        fail("internal", "face has material on both sides at x=%.3f y=%.3f z=%.3f"
             % loc)
    print("# internal: %d faces checked, %d with material both sides (%.1fs)"
          % (nchecked, len(internal), time.time() - t))

    # --- summary ------------------------------------------------------------------
    print("# checks: solids %d | outer shells %d | invalid %s | slivers %d/%d faces"
          " | short %d/%d edges | hairline %d/%d pairs | internal %d/%d faces"
          % (len(solids), outer_shells, "no" if valid else "YES",
             len(slivers), len(faces), len(shorts), len(edges),
             len(hair), npairs, len(internal), nchecked))
    for name in ("slivers", "short", "hairline", "internal"):
        worst = results[name]["worst"]
        if worst:
            print("# worst 10 %s locations (x,y,z mm):" % name, flush=True)
            for item in worst:
                if name == "internal":
                    print("#   x=%.3f y=%.3f z=%.3f" % tuple(item))
                else:
                    val, loc = item
                    print("#   %.4f at x=%.3f y=%.3f z=%.3f" % (val, *loc))

    results["failures"] = len(fails)
    results["exit"] = 1 if fails else 0
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(results, fh, indent=1)
        print("# wrote %s" % args.json_out)
    print("# %d failures -> exit %d" % (len(fails), 1 if fails else 0))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
