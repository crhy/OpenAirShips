#!/usr/bin/env python3
"""FEA of one airship slice: STEP -> gmsh tet mesh -> CalculiX -> von Mises report.

    /home/rhy/.venvs/fea/bin/python CurrentModel/Analysis/fea_slice.py \
        "CurrentModel/CAD Files/Slice2/slice-CR10Pro.step" [--size 1.5] \
        [--cases L1,L3,...] [--jobdir DIR] [--json out.json] [--skip-mesh]

Toolchain (see Analysis/FEA.md): gmsh 4.15.2 (pip wheel, reads the STEP's OCC
geometry, 10-node tets) + CalculiX ccx 2.21 (the FreeCAD flatpak binary,
`flatpak run --filesystem=host --command=ccx org.freecad.FreeCAD`).

Units: mm, N, MPa, tonne, s.  Material PLA: E = 3500 MPa, nu = 0.36,
density 1.24e-9 t/mm3.  Strength: yield 50 MPa, derated x 1/3 for the
layer lines -> allowable 16.67 MPa; SF = 16.67 / max von Mises.

Load cases (SPEC.md R18 / STRUCTURE-ESTIMATES.md section 3, MG90S servo):
  L1  servo mass x handling:  0.92 N (-Z) on the pad under the bracket
  L3  gear force at stall:    12.0 N tangential + 4.4 N radial-in on the
                              spline hole (= L2 stall torque through the gears)
  L2  stall torque alone:     215.8 N.mm couple about the radial spline axis
  L4  fan thrust x4:          1.5 N along the duct axis on the sleeve bore
  L6  hand on a thruster ring: 20 N radial-in on the skin at the duct break
  L7  crash 20 g:             body force 20 x 9810 mm/s2 (-Z)
  L8  plenum pressure:        1.9e-3 MPa on the plenum walls (13 N over hatch)

BC: both 45-deg seam faces fully built-in (the neighbours hold them;
conservative for local stress). Reports per case: max von Mises + the 5 most
stressed locations, max deflection, SF; and the slice mass.
"""
import argparse
import json
import math
import os
import subprocess
import struct
import sys
import time

import numpy as np

ALLOWABLE = 50.0 / 3.0          # MPa: yield 50, x 1/3 layer-line weakness
E, NU, RHO = 3500.0, 0.36, 1.24e-9
G_GRAV = 9810.0                 # mm/s2

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def load_params():
    """Read the PARAMS dict out of slice.py without importing it (that file
    needs cadquery; this script runs in the fea venv)."""
    import ast
    src = open(os.path.join(REPO, "CurrentModel", "CAD Files", "Slice2",
                            "slice.py")).read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id",
                                                    "") == "PARAMS":
            return ast.literal_eval(node.value)
    raise RuntimeError("PARAMS not found in slice.py")


# ---------------------------------------------------------------- meshing
def mesh(step, size, jobdir):
    import gmsh
    gmsh.initialize()
    gmsh.open(step)
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", size * 0.55)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", size)
    gmsh.option.setNumber("Mesh.CharacteristicLengthFactor", 1.0)
    gmsh.model.mesh.generate(2)
    gmsh.model.mesh.optimize("Netgen")
    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.setOrder(2)          # 10-node tets
    nn, nc, _ = gmsh.model.mesh.getNodes()
    nc = nc.reshape(-1, 3)
    elemTypes, elemTags, elemNodeTags = gmsh.model.mesh.getElements()
    tets = [i for i, t in enumerate(elemTypes) if t == 11]
    if not tets:
        raise RuntimeError("no 10-node tets in the mesh")
    conn = elemNodeTags[tets[0]].reshape(-1, 10)
    # gmsh midside order (12,23,13,14,34,24) -> CalculiX C3D10 (12,23,13,14,24,34)
    conn = conn[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
    # gmsh node tags -> 0-based index
    nidx = {int(t): i for i, t in enumerate(nn)}
    conn = np.array([[nidx[int(t)] for t in row] for row in conn])
    # fix inverted tets: negative corner volume -> swap v1<->v2 (and the
    # midside pairs that follow: m13<->m23, m14<->m24)
    p = nc.astype(float)
    a, b, c, d = (p[conn[:, k]] for k in (0, 1, 2, 3))
    sgn = np.einsum("ij,ij->i", b - a, np.cross(c - a, d - a))
    bad = np.where(sgn <= 0)[0]
    if len(bad):
        conn[bad][:, [0, 1]] = conn[bad][:, [1, 0]]
        conn[bad][:, [5, 6]] = conn[bad][:, [6, 5]]
        conn[bad][:, [7, 8]] = conn[bad][:, [8, 7]]
    # CalculiX C3D10 assumes straight edges: put midside nodes at the exact
    # edge midpoints, else the Jacobian can go negative on curved skins.
    for mid, (i, j) in zip((4, 5, 6, 7, 8, 9),
                           ((0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3))):
        nc[conn[:, mid]] = (nc[conn[:, i]] + nc[conn[:, j]]) / 2.0
    # surface elements (for PRES loads): type 9 = 6-node tri (order 2)
    tris = [i for i, t in enumerate(elemTypes) if t == 9]
    surf = None
    if tris:
        sconn = elemNodeTags[tris[0]].reshape(-1, 6)
        surf = np.array([[nidx[int(t)] for t in row] for row in sconn])
    vol = 0.0
    p = nc
    a, b, c, d = (p[conn[:, k]] for k in (0, 1, 2, 3))
    vol = abs(np.einsum("ij,ij->i", a - d, np.cross(b - d, c - d))).sum() / 6.0
    gmsh.write(os.path.join(jobdir, "mesh.msh"))
    gmsh.finalize()
    return nc.astype(float), conn.astype(int), surf, vol


# ------------------------------------------------------- node-set geometry
def node_sets(nc, P, S):
    A, B = P["A"] * S, P["B"] * S
    HALF = 180.0 / P["N"]
    x, y, z = nc[:, 0], nc[:, 1], nc[:, 2]
    r = np.hypot(x, y)
    th = np.degrees(np.arctan2(y, x))

    def depth(p):
        """approx distance inside the spheroid surface (mm)."""
        rr, zz = p[:, 0], p[:, 1]
        u = np.arctan2(zz / B, np.maximum(rr, 1e-9) / A)
        ru, zu = A * np.cos(u), B * np.sin(u)
        return np.hypot(rr - ru, zz - zu)

    d = depth(nc)
    sets = {}
    # seam planes at theta = +/- HALF
    for nm, sgn in (("seam_p", 1), ("seam_m", -1)):
        n = np.array([-math.sin(math.radians(sgn * HALF)),
                      math.cos(math.radians(sgn * HALF)), 0.0])
        dist = np.abs(nc @ n)
        sets[nm] = np.where((dist < 5e-4) & (r > 1.0))[0]
    # pad outer face (bracket footprint)
    th_pad = HALF - math.degrees(P["SERVO_T"] / A)
    dth = math.degrees(P["SERVO_BRACKET_L"] / 2 / A)
    m = ((np.abs(d - P["PAD_T"]) < 0.06) &
         (np.abs(th - th_pad) < dth + 0.3) &
         (np.abs(z) <= P["SERVO_BRACKET_W"] / 2 + 0.2))
    sets["pad"] = np.where(m)[0]
    # spline hole cylinder (radial axis at th_pad, z=0)
    ax = np.array([math.cos(math.radians(th_pad)),
                   math.sin(math.radians(th_pad)), 0.0])
    q = nc - nc @ ax[:, None] * ax[None, :]
    sets["spline"] = np.where(np.abs(np.hypot(q[:, 0], q[:, 1]) -
                                     P["SERVO_HOLE"] / 2) < 0.05)[0]
    # duct bore + stem hole, both seams
    for nm, sgn in (("bore_p", 1), ("bore_m", -1),
                    ("sleeve_p", 1), ("sleeve_m", -1),
                    ("ring_p", 1), ("ring_m", -1)):
        da = np.array([math.cos(math.radians(sgn * HALF)),
                       math.sin(math.radians(sgn * HALF)), 0.0])
        q = nc - nc @ da[:, None] * da[None, :]
        dq = np.hypot(q[:, 0], q[:, 1])
        rr = nc @ da
        if nm.startswith("bore"):
            sets[nm] = np.where((np.abs(dq - P["DUCT_BORE"] / 2) < 0.05) &
                                (rr > P["DUCT_MOUTH_R"]) & (rr < A))[0]
        elif nm.startswith("sleeve"):
            sets[nm] = np.where(
                (np.abs(dq - P["STEM_HOLE"] / 2) < 0.05) &
                (rr > A - 40.0) &
                (rr < A - 40.0 + P["BOSS_LEN"] + 0.5))[0]
        else:
            sets[nm] = np.where((dq < P["DUCT_BORE"] / 2 + 15.0) &
                                (d < 0.05) & (rr > A - 30.0))[0]
    # plenum: ceiling underside, wall inside, shaft wall outside
    fz = -B + P["FLOOR_Z"]
    sets["plenum_ceil"] = np.where(
        (np.abs(z - fz) < 5e-3) & (r > P["SHAFT_R"] - 0.05) &
        (r < P["PLENUM_R"] + 0.05))[0]
    sets["plenum_wall"] = np.where(
        (np.abs(r - (P["PLENUM_R"] - P["T"])) < 0.05) & (z < fz) &
        (z > -B - 0.1))[0]
    sets["shaft_wall"] = np.where(
        (np.abs(r - (P["SHAFT_R"] + P["T"])) < 0.05) & (z > fz - 1) &
        (z < 0.05))[0]
    return sets, (A, B, HALF, th_pad)


# ------------------------------------------------------------- input deck
def write_inp(job, nc, conn, surf, sets, geo, P, S, case):
    A, B, HALF, th_pad = geo
    lines = ["*HEADING", "Slice2 FEA %s S=%.2f case %s" % (job, S, case),
             "*NODE"]
    for i, p in enumerate(nc):
        lines.append("%d,%.5f,%.5f,%.5f" % (i + 1, p[0], p[1], p[2]))
    lines.append("*ELEMENT, TYPE=C3D10, ELSET=ALL")
    for i, c in enumerate(conn):
        lines.append("%d,%s" % (i + 1, ",".join(str(v + 1) for v in c)))
    pres_sets = {}
    if case == "L8" and surf is not None:
        for nm in ("plenum_ceil", "plenum_wall", "shaft_wall"):
            mask = np.all(np.isin(surf, sets[nm][:, None]), axis=1)
            sel = np.where(mask)[0]
            if len(sel):
                pres_sets[nm.upper()] = sel
        lines.append("*ELEMENT, TYPE=C3D6")
        for i, c in enumerate(surf):
            lines.append("%d,%s" % (len(conn) + i + 1,
                                    ",".join(str(v + 1) for v in c)))
        for nm, sel in pres_sets.items():
            lines.append("*ELSET, ELSET=%s" % nm)
            for chunk in _chunks(sel + len(conn) + 1):
                lines.append(",".join(str(v) for v in chunk))
    lines += ["*NLGEOM, NO",
              "*MATERIAL, NAME=PLA", "*ELASTIC", "%.1f, %.3f" % (E, NU),
              "*DENSITY", "%.4e" % RHO,
              "*SOLID SECTION, ELSET=ALL, MATERIAL=PLA"]
    lines.append("*NSET, NSET=NALL")
    for chunk in _chunks(np.arange(1, len(nc) + 1)):
        lines.append(",".join(str(v) for v in chunk))
    for nm in sets:
        if len(sets[nm]) == 0:
            continue
        lines.append("*NSET, NSET=%s" % nm.upper())
        for chunk in _chunks(sets[nm] + 1):
            lines.append(",".join(str(v) for v in chunk))
    lines.append("*STEP")
    lines.append("*STATIC")
    lines.append("0., 1., 1., 1.")
    lines.append("*BOUNDARY")
    for nm in ("SEAM_P", "SEAM_M"):
        lines.append("%s,1,6,0.0" % nm)
    if case == "L1":
        _nload(lines, sets, "PAD", np.array([0, 0, -0.92]))
    elif case == "L3":
        e_th = np.array([-math.sin(math.radians(th_pad)),
                         math.cos(math.radians(th_pad)), 0.0])
        e_r = np.array([math.cos(math.radians(th_pad)),
                        math.sin(math.radians(th_pad)), 0.0])
        _nload(lines, sets, "SPLINE", 12.0 * e_th - 4.4 * e_r)
    elif case == "L2":
        e_th = np.array([-math.sin(math.radians(th_pad)),
                         math.cos(math.radians(th_pad)), 0.0])
        top = sets["spline"][nc[sets["spline"], 2] > 0]
        bot = sets["spline"][nc[sets["spline"], 2] <= 0]
        F = 215.8 / 8.0
        _nload(lines, {"t": top}, "T", F * e_th)
        _nload(lines, {"b": bot}, "B", -F * e_th)
    elif case == "L4":
        for nm in ("SLEEVE_P", "SLEEVE_M"):
            sgn = 1 if nm.endswith("P") else -1
            da = np.array([math.cos(math.radians(sgn * HALF)),
                           math.sin(math.radians(sgn * HALF)), 0.0])
            _nload(lines, sets, nm, 0.75 * da)
    elif case == "L6":
        for nm in ("RING_P", "RING_M"):
            sgn = 1 if nm.endswith("P") else -1
            da = np.array([math.cos(math.radians(sgn * HALF)),
                           math.sin(math.radians(sgn * HALF)), 0.0])
            _nload(lines, sets, nm, -10.0 * da)
    elif case == "L7":
        lines.append("*DLOAD")
        lines.append("ALL,GRAV,%.1f,0.,0.,-1." % (20 * G_GRAV))
    elif case == "L8":
        if not pres_sets:
            raise RuntimeError("no plenum surface elements for L8")
        lines.append("*DLOAD")
        for nm in pres_sets:
            lines.append("%s,PRES,%.4e" % (nm, 1.9e-3))
    lines.append("*NODE FILE")
    lines.append("U, S")
    lines.append("*END STEP")
    return "\n".join(lines) + "\n"


def _chunks(a, n=16):
    for i in range(0, len(a), n):
        yield a[i:i + n]


def _nload(lines, sets, nm, total):
    idx = sets[nm.lower()]
    if len(idx) == 0:
        raise RuntimeError("empty node set %s" % nm)
    f = total / len(idx)
    lines.append("*CLOAD")
    for i in idx:
        for k in range(3):
            if abs(f[k]) > 1e-12:
                lines.append("%d,%d,%.6e" % (i + 1, k + 1, f[k]))


# ---------------------------------------------------------------- ccx
def run_ccx(jobdir, job):
    cmd = ["flatpak", "run", "--filesystem=host", "--command=ccx",
           "org.freecad.FreeCAD", job]
    r = subprocess.run(cmd, cwd=jobdir, capture_output=True, text=True)
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-3000:])
        raise RuntimeError("ccx failed rc=%d" % r.returncode)
    return r.stdout + r.stderr


def parse_frd(path):
    """Parse CalculiX ASCII .frd: {'u': {node:[3]}, 's': {node: vm}}."""
    step = {"u": {}, "s": {}}
    field = None
    with open(path, "rb") as fh:
        for raw in fh:
            ln = raw.decode("latin-1").rstrip("\n")
            if ln.startswith(" -4"):
                field = ln[3:].split()[0]
            elif ln.startswith(" -1") and field in ("DISP", "STRESS"):
                nid = int(ln[3:13])
                body = ln[13:]
                vals = [float(body[j:j + 12]) for j in range(0, len(body), 12)
                        if body[j:j + 12].strip()]
                if field == "DISP" and len(vals) >= 3:
                    step["u"][nid] = vals[:3]
                elif field == "STRESS" and len(vals) >= 6:
                    xx, yy, zz, xy, yz, zx = vals[:6]
                    step["s"][nid] = math.sqrt(
                        max(0.0, 0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 +
                                        (zz - xx) ** 2) +
                        yz * yz + zx * zx + xy * xy))
    return step


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step")
    ap.add_argument("--size", type=float, default=1.5)
    ap.add_argument("--cases", default="L1,L2,L3,L4,L6,L7")
    ap.add_argument("--jobdir", default=os.path.join(REPO, "CurrentModel",
                                                     "Analysis", "build",
                                                     "fea"))
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--skip-mesh", action="store_true")
    args = ap.parse_args()

    P = load_params()
    os.makedirs(args.jobdir, exist_ok=True)
    job = os.path.splitext(os.path.basename(args.step))[0]
    t0 = time.time()

    cache = os.path.join(args.jobdir, "%s_%d_%d_nodes.npz" %
                         (job, int(os.path.getsize(args.step)),
                          int(os.path.getmtime(args.step))))
    if args.skip_mesh and os.path.exists(cache):
        z = np.load(cache)
        nc, conn, surf = z["nc"], z["conn"], z["surf"]
        vol = float(z["vol"])
    else:
        nc, conn, surf, vol = mesh(os.path.abspath(args.step), args.size,
                                   args.jobdir)
        np.savez_compressed(cache, nc=nc, conn=conn, vol=vol,
                            surf=surf if surf is not None else np.zeros((0, 6), int))
    S = nc[:, 0].max() / P["A"]
    mass = vol * 1.24e-3
    print("# %s: vol %.0f mm3 mass %.1f g S~%.3f" % (job, vol, mass, S))
    print("# mesh: %d nodes, %d tets (%.0fs)" % (len(nc), len(conn),
                                                 time.time() - t0))

    sets, geo = node_sets(nc, P, S)
    for nm in sorted(sets):
        print("  set %-12s %6d nodes" % (nm, len(sets[nm])))
    cases = args.cases.split(",")
    report = {"step": args.step, "mass_g": mass, "vol_mm3": vol,
              "scale": S, "allowable_MPa": ALLOWABLE, "cases": []}
    print("\n%-6s %10s %10s %8s   top von Mises locations (x,y,z mm)" %
          ("case", "maxVM", "maxU", "SF"))
    for case in cases:
        inp = write_inp(job, nc, conn, surf, sets, geo, P, S, case)
        jfile = os.path.join(args.jobdir, "%s_%s.inp" % (job, case))
        with open(jfile, "w") as fh:
            fh.write(inp)
        run_ccx(args.jobdir, "%s_%s" % (job, case))
        st = parse_frd(os.path.join(args.jobdir, "%s_%s.frd" %
                                    (job, case)))
        if not st["s"]:
            raise RuntimeError("no results for case %s" % case)
        nids = np.array(list(st["s"].keys()))
        vm = np.array(list(st["s"].values()))
        u = np.array([st["u"][n] for n in nids])
        umax = float(np.max(np.linalg.norm(u, axis=1)))
        order = np.argsort(-vm)[:5]
        locs = [(round(vm[i], 2),
                 tuple(round(v, 1) for v in nc[int(nids[i]) - 1]))
                for i in order]
        sf = ALLOWABLE / vm[order[0]] if vm[order[0]] > 1e-9 else 1e9
        report["cases"].append({"case": case, "maxVM_MPa": float(vm[order[0]]),
                                "maxU_mm": umax, "SF": float(sf),
                                "top5": locs})
        print("%-6s %10.3f %10.3f %8.2f   %s" %
              (case, vm[order[0]], umax, sf,
               " ".join("(%.0f,%.0f,%.0f):%.2f" % (l[1][0], l[1][1],
                                                   l[1][2], l[0])
                        for l in locs[:3])), flush=True)
    minsf = min(c["SF"] for c in report["cases"])
    print("\nmin SF = %.2f  (allowable %.2f MPa, mesh %.1f mm, %d tets)" %
          (minsf, ALLOWABLE, args.size, len(conn)))
    report["minSF"] = minsf
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=1)
        print("# wrote %s" % args.json_out)


if __name__ == "__main__":
    main()
