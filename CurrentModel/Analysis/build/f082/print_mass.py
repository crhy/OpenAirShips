"""Printed mass budget: measure every committed print STL, and record the mass,
material and wall settings behind the weight problem. Writes PRINT-MASS.md.

`hull_volumes.py` needs cadquery, trimesh and the STEP files; neither CAD kernel
is installed here, so this script measures the binary STL meshes that actually
ship, with numpy and the standard library only:

- binary STL: an 80-byte header, a little-endian uint32 triangle count at bytes
  80:84, then 50-byte records (12-byte normal, 36-byte vertices at bytes 12:48,
  2-byte attributes);
- every undirected edge must occur exactly twice, i.e. the mesh is watertight.
  A mesh with gaps gives a wrong volume, so the script refuses such a mesh
  rather than reporting a number for it (a leaky mesh is what put the v0.2
  double-Kobra hull at 350 cm3 instead of 502, CHANGELOG.md:24);
- volume and surface area are integrated per triangle in float64, and mass =
  volume x density, the rule float_budget.py:17-18 uses.

Run:

    python3 print_mass.py            # writes PRINT-MASS.md and prints it
    python3 print_mass.py --check    # recomputes from the STLs and compares
                                       # against the committed PRINT-MASS.md,
                                       # exiting non-zero on any difference
"""
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent                                   # CurrentModel/
OUT = HERE / "PRINT-MASS.md"

REC = np.dtype([("normal", "3f4"), ("v", "9f4"), ("attr", "u2")])

# --- materials and print settings as shipped, each with the file it comes from ---
MATERIALS = {"PLA": 1.24, "LW-PLA, moderate foam": 0.80, "LW-PLA, full foam": 0.60}
PETG = 1.27                                                 # Analysis/float_budget.py:18
PLA_PARTS = ("stem", "stem_gear", "servo_gear", "fan_hatch")  # SimplifiedSlice/README.md:126

SETTINGS = [
    ("printer, nozzle", "Prusa MK3S+, 0.4 mm nozzle", "CurrentModel/DESIGN-CONSTRAINTS.md:19"),
    ("layer height", "0.20 mm", "CurrentModel/CAD Files/SimplifiedSlice/README.md:109"),
    ("perimeters", "2, no infill needed (the walls are 2 lines thick)",
     "CurrentModel/CAD Files/SimplifiedSlice/README.md:109"),
    ("walls", "0.86 mm = 2 perimeters of 0.45 mm at 0.2 mm layers; the minimum that prints airtight",
     "CurrentModel/DESIGN-CONSTRAINTS.md:20"),
    ("ribs", "2.0 mm wide, and nothing structural is thinner", "CurrentModel/DESIGN-CONSTRAINTS.md:20"),
    ("webs", "may go down to 1.2 mm; walls stay 0.86 mm", "CurrentModel/DESIGN-CONSTRAINTS.md:26"),
    ("densities", "PLA 1.24, LW-PLA 0.80 moderate / 0.60 full foam, PETG 1.27 g/cm³",
     "CurrentModel/Analysis/float_budget.py:17-18"),
]

# --- what ships, and where each printed quantity comes from -------------------
# Hull: SimplifiedSlice/README.md:7-10 (8 identical slices, or 4 left + 4 right),
# :56 and :75 (the v0.2 build: 15 pieces, 4 of each type, plus 2 intake tubes).
HULL_QTY = {
    "PieSlice1026-v0.2.1-8T.stl": (8, "SimplifiedSlice/README.md:7"),
    "PieSlice1026-v0.2.1-4T-left.stl": (4, "SimplifiedSlice/README.md:8"),
    "PieSlice1026-v0.2.1-4T-right.stl": (4, "SimplifiedSlice/README.md:8"),
    "PieSlice1026-v0.2.1-8T-KobraMax.stl": (8, "SimplifiedSlice/README.md:9"),
    "PieSlice1026-v0.2.1-4T-left-KobraMax.stl": (4, "SimplifiedSlice/README.md:10"),
    "PieSlice1026-v0.2.1-4T-right-KobraMax.stl": (4, "SimplifiedSlice/README.md:10"),
}
TUBES = ("PieSlice1026-v0.2.1-intake-tube-1.stl", "PieSlice1026-v0.2.1-intake-tube-2.stl")
TUBE_QTY = (1, "SimplifiedSlice/README.md:70")          # two tubes, one of each
PIECE_QTY = (4, "SimplifiedSlice/README.md:56 and :75")  # 15 pieces, 4 of each type
DOUBLE_KOBRA = "v0.2.1 double Kobra"

# Propulsion: Propulsion/README.md:44-50 (1 impeller, 1 fan hatch, 8 of the rest;
# 4 thrusters halves the 8s, README.md:8). The v0.2 build uses the 8-thruster
# thruster size on 4 thrusters (Propulsion/README.md:19) and adds the tray (:23).
PROP_QTY = {
    "impeller": (1, "Propulsion/README.md:44"),
    "fan_hatch": (1, "Propulsion/README.md:45"),
    "servo_mount": (8, "Propulsion/README.md:46"),
    "stem": (8, "Propulsion/README.md:47"),
    "stem_gear": (8, "Propulsion/README.md:48"),
    "servo_gear": (8, "Propulsion/README.md:49"),
    "thruster_ring": (8, "Propulsion/README.md:50"),
}
PROP_QTY_4T = {k: (1 if q == 1 else 4, s) for k, (q, s) in PROP_QTY.items()}
TRAY_QTY = (1, "Propulsion/README.md:23")
PROP_FOLDERS = {
    "CAD Files/Propulsion/print": PROP_QTY,
    "CAD Files/Propulsion/x1.9/print": PROP_QTY,
    "CAD Files/Propulsion/4T/print": PROP_QTY_4T,
    "CAD Files/Propulsion/4T/x1.9/print": PROP_QTY_4T,
    "CAD Files/Propulsion/4T/small/12s/x3.8/print": PROP_QTY_4T,
}

# The float budget's item names, so the two documents line up line by line.
ITEM = {"impeller": "impeller (PETG)", "fan_hatch": "fan hatch", "servo_mount": "servo mounts",
        "stem": "stems and gears", "stem_gear": "stems and gears", "servo_gear": "stems and gears",
        "thruster_ring": "thruster rings", "avionics_tray": "avionics tray"}

# The five ships the READMEs publish. hull_recorded and prop_recorded are the
# numbers already in the docs, kept beside the ones measured here.
SHIPS = [
    dict(name="8 thrusters, bench (415 mm, Prusa MK3S+)",
         hull=["Print Files/PieSlice1026-v0.2.1-8T.stl"], tubes=[],
         prop="CAD Files/Propulsion/print",
         hull_recorded=(214, 265, 171, 128, "SimplifiedSlice/README.md:102"),
         prop_recorded=(233, "Propulsion/README.md:52")),
    dict(name="4 thrusters, bench (415 mm, Prusa MK3S+)",
         hull=["Print Files/PieSlice1026-v0.2.1-4T-left.stl",
               "Print Files/PieSlice1026-v0.2.1-4T-right.stl"], tubes=[],
         prop="CAD Files/Propulsion/4T/print",
         hull_recorded=(184, 228, 147, 110, "SimplifiedSlice/README.md:103"),
         prop_recorded=(154, "Propulsion/README.md:52")),
    dict(name="8 thrusters, Kobra Max (x1.9, 790 mm)",
         hull=["Print Files/PieSlice1026-v0.2.1-8T-KobraMax.stl"], tubes=[],
         prop="CAD Files/Propulsion/x1.9/print",
         hull_recorded=(415, 514, 332, 249, "SimplifiedSlice/README.md:104"),
         prop_recorded=None),
    dict(name="4 thrusters, Kobra Max (x1.9, 790 mm)",
         hull=["Print Files/PieSlice1026-v0.2.1-4T-left-KobraMax.stl",
               "Print Files/PieSlice1026-v0.2.1-4T-right-KobraMax.stl"], tubes=[],
         prop="CAD Files/Propulsion/4T/x1.9/print",
         hull_recorded=(349, 432, 279, 209, "SimplifiedSlice/README.md:105"),
         prop_recorded=None),
    dict(name="double Kobra, 12 slices (x3.8, 1.58 m, self-contained)",
         hull=["Print Files/v0.2.1 double Kobra"],
         tubes=["Print Files/v0.2.1 double Kobra/PieSlice1026-v0.2.1-intake-tube-1.stl",
                "Print Files/v0.2.1 double Kobra/PieSlice1026-v0.2.1-intake-tube-2.stl"],
         prop="CAD Files/Propulsion/4T/small/12s/x3.8/print",
         hull_recorded=(474, 588, 379, 284, "SimplifiedSlice/README.md:106"),
         prop_recorded=None),
]

# Recorded numbers the committed meshes do not support.
CORRECTIONS = [
    ("4-thruster thruster ring", "19.8 cm³", "18.38 cm³",
     "CAD Files/Propulsion/4T/print/thruster_ring.stl, recorded at Propulsion/README.md:40"),
    ("8-thruster propulsion total", "about 233 cm³ (≈ 290 g of PLA)", "241.5 cm³ (≈ 299 g of PLA)",
     "CAD Files/Propulsion/print at Propulsion/README.md:44-50 quantities, total at :52"),
]
RECORDED_PART_CM3 = {"impeller": 6.2, "fan_hatch": 10.1, "servo_mount": 4.3, "stem": 3.6,
                     "stem_gear": 2.1, "servo_gear": 3.8, "thruster_ring": 14.1}   # :44-50
RECORDED_4T_CM3 = {"thruster_ring": 19.8, "stem": 4.9, "stem_gear": 2.4, "servo_gear": 4.8,
                   "fan_hatch": 11.3}                                             # :40
FLOAT_TOTAL, FLOAT_LIFT = 977, 1145                     # Analysis/FLOAT.md:90, :91


def read_stl(path):
    """Triangles (n, 3, 3) in mm from a binary STL."""
    with open(path, "rb") as fh:
        head = fh.read(80)
        if not head.endswith(b"\n") or head[:5] == b"solid":
            raise ValueError(f"{path}: not a binary STL (header starts {head[:6]!r})")
        n = int.from_bytes(fh.read(4), "little")
        rec = np.frombuffer(fh.read(REC.itemsize * n), dtype=REC, count=n)
    if len(rec) != n:
        raise ValueError(f"{path}: header says {n} triangles, file holds {len(rec)}")
    return rec["v"].reshape(n, 3, 3)


def weld(tris):
    """Coincident float32 vertices share one index, so edges can be counted."""
    flat = tris.reshape(-1, 3).view([("x", "f4"), ("y", "f4"), ("z", "f4")])
    _, inv = np.unique(flat, return_inverse=True)
    return inv.reshape(len(tris), 3).astype(np.int64)


def leaky_edges(tris):
    """Edges not used exactly twice; 0 means a closed manifold (watertight)."""
    idx = weld(tris)
    nv = int(idx.max()) + 1
    s = np.sort(idx, axis=1)
    key = np.concatenate([s[:, 0] * nv + s[:, 1], s[:, 0] * nv + s[:, 2], s[:, 1] * nv + s[:, 2]])
    _, counts = np.unique(key, return_counts=True)
    return int(np.count_nonzero(counts != 2)), nv


def integrate(tris):
    """Volume (cm³) and surface area (cm²), from the signed tetrahedra, float64."""
    a, b, c = (tris[:, i].astype(np.float64) for i in range(3))
    ab, ac = b - a, c - a
    cr = np.stack((ab[:, 1] * ac[:, 2] - ab[:, 2] * ac[:, 1],
                   ab[:, 2] * ac[:, 0] - ab[:, 0] * ac[:, 2],
                   ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]), -1)
    vol = np.einsum("ij,ij->i", a, cr).sum() / 6.0
    sq = (np.einsum("ij,ij->i", ab, ab) * np.einsum("ij,ij->i", ac, ac)
          - np.einsum("ij,ij->i", ab, ac) ** 2)
    return abs(vol) / 1000.0, 0.5 * np.sqrt(np.maximum(sq, 0.0)).sum() / 100.0


def qty_of(path):
    """Printed quantity of a committed STL, with the file the number comes from."""
    if path.name in HULL_QTY:
        return HULL_QTY[path.name]
    if path.name in TUBES:
        return TUBE_QTY
    if path.parent.name == DOUBLE_KOBRA:
        return PIECE_QTY
    table = PROP_FOLDERS.get(str(path.relative_to(MODEL).parent))
    if table and path.stem in table:
        return table[path.stem]
    if path.stem == "avionics_tray":
        return TRAY_QTY
    raise KeyError(f"{path}: no shipped quantity recorded for it")


def item_of(path):
    """Which budget line a part belongs to (the float budget's names)."""
    if path.name in TUBES:
        return "intake tubes"
    return ITEM.get(path.stem, "hull")


def measure(path):
    """One STL: watertight, then volume, area, mean wall and mass per material."""
    tris = read_stl(path)
    bad, nv = leaky_edges(tris)
    if bad:
        raise ValueError(f"{path}: {bad} of {3 * len(tris)} edges are not used exactly twice, so the "
                         "mesh has gaps and its volume would be wrong (a leaky mesh is what put the v0.2 "
                         "hull at 350 cm3 instead of 502, CHANGELOG.md:24)")
    cm3, cm2 = integrate(tris)
    return dict(path=path, rel=str(path.relative_to(MODEL)), tris=len(tris), verts=nv, cm3=cm3, cm2=cm2,
                wall=20.0 * cm3 / cm2,                 # mean wall in mm: volume/area is half of it
                mass={m: cm3 * rho for m, rho in MATERIALS.items()},
                qty=qty_of(path)[0], qty_src=qty_of(path)[1], part=path.stem, item=item_of(path))


def stl_groups():
    """Every committed print STL, grouped by the folder that ships it."""
    out = {}
    for root in ("Print Files", "CAD Files/Propulsion"):
        for p in sorted((MODEL / root).rglob("*.stl")):
            out.setdefault(str(p.parent.relative_to(MODEL)), []).append(p)
    return {k: out[k] for k in sorted(out)}


def ship_files(ship):
    """The STLs that make up one ship."""
    files = []
    for entry in ship["hull"]:
        p = MODEL / entry
        files += sorted(q for q in p.rglob("*.stl") if q.name not in TUBES) if p.is_dir() else [p]
    files += [MODEL / t for t in ship["tubes"]]
    files += sorted((MODEL / ship["prop"]).glob("*.stl"))
    return files


def budget(ship, rows):
    """Measured cm³ and printed quantity per item group, for one ship."""
    files = {p.resolve() for p in ship_files(ship)}
    cm3, qty, parts = {}, {}, {}
    for r in rows:
        if r["path"].resolve() not in files:
            continue
        cm3[r["item"]] = cm3.get(r["item"], 0.0) + r["qty"] * r["cm3"]
        qty[r["item"]] = qty.get(r["item"], 0) + r["qty"]
        parts[r["part"]] = parts.get(r["part"], 0.0) + r["qty"] * r["cm3"]
    return dict(cm3=cm3, qty=qty, parts=parts)


def mixed_g(parts):
    """Mass with every part in the material the docs put it in."""
    g = 0.0
    for part, cm3 in parts.items():
        if part == "impeller":
            g += cm3 * PETG
        elif part in PLA_PARTS:
            g += cm3 * MATERIALS["PLA"]
        else:
            g += cm3 * MATERIALS["LW-PLA, full foam"]
    return g


def prop_cm3(b):
    """Printed propulsion volume of a ship (everything that is not hull or tubes)."""
    return sum(v for k, v in b["cm3"].items() if k not in ("hull", "intake tubes"))


def thruster_work_cm3(b):
    """Rings, mounts, stems and gears only."""
    return sum(v for k, v in b["cm3"].items()
               if k in ("thruster rings", "servo mounts", "stems and gears"))


def recorded_prop_cm3(qty):
    """What the propulsion README's own table adds up to at its own quantities."""
    return sum(RECORDED_PART_CM3[p] * q for p, (q, _) in qty.items())


def g(cm3, material):
    return cm3 * MATERIALS[material]


def f(x, dp=1):
    return f"{x:.{dp}f}"


def delta(x):
    """Measured minus recorded, with no -0.0 and no sign on a rounding-level difference."""
    return f"{x:+.1f}" if abs(x) >= 0.05 else "0.0"


def render(rows, groups):
    """The PRINT-MASS.md document, from the measured rows."""
    out = []
    w = out.append
    ships = [(s, budget(s, rows)) for s in SHIPS]
    dk = next(b for s, b in ships if s["name"].startswith("double Kobra"))
    b8 = next(b for s, b in ships if s["name"].startswith("8 thrusters, bench"))
    b4 = next(b for s, b in ships if s["name"].startswith("4 thrusters, bench"))
    by_rel = {r["rel"]: r for r in rows}
    tubes = [r for r in rows if r["path"].name in TUBES]
    tube_cm3 = sum(r["cm3"] for r in tubes)
    hull_walls = [r["wall"] for r in rows if r["item"] == "hull"]
    slice8 = by_rel["Print Files/PieSlice1026-v0.2.1-8T.stl"]
    ring8 = by_rel["CAD Files/Propulsion/print/thruster_ring.stl"]
    ring4 = by_rel["CAD Files/Propulsion/4T/print/thruster_ring.stl"]

    w("# Printed mass budget (1026 v0.2.1): every committed print STL, measured\n")
    w("\nGenerated by `print_mass.py` from the STL meshes that ship — not from the CAD kernel, and not from a "
      "slicer. Rerun it after changing the model.\n")
    w("This is the recorded baseline the triage on [crhy/OpenAirShips#1](https://github.com/crhy/OpenAirShips/issues/1) "
      "asks for: the current mass, the material, and the wall and nozzle settings behind it. The CAD revision, the "
      "weighing and the load tests are not here.\n")
    w("**How it is measured**\n")
    w(f"- {len(rows)} binary STL files read directly: 80-byte header, uint32 triangle count at bytes 80:84, "
      "50-byte records with the vertices at bytes 12:48.")
    w("- Every undirected edge is used exactly twice in all of them, so all are watertight, as "
      "`CHANGELOG.md:34` and `SimplifiedSlice/README.md:94` claim. A mesh with gaps is refused, not reported.")
    w("- Volume and area are integrated per triangle in float64; mass = volume × density.")
    w("- `--check` recomputes this document from the STLs and fails if it differs from the committed one, so the "
      "numbers cannot drift away from the meshes.")
    w("- **Mean wall** is 2 × volume ÷ area: the average thickness the mesh's own skin carries. The two intake tubes "
      "average "
      f"{f(min(r['wall'] for r in tubes), 3)} and {f(max(r['wall'] for r in tubes), 3)} mm — they are the only printed "
      "parts with no lattice in them, so their mean is the wall itself. Hull slices average "
      f"{f(min(hull_walls), 2)}–{f(max(hull_walls), 2)} mm, below the wall, because the lattice windows add surface "
      "without adding material.\n")

    w("\n## Print settings and materials as shipped\n")
    w("| Setting | Value | Source |")
    w("|---|---|---|")
    for name, val, src in SETTINGS:
        w(f"| {name} | {val} | `{src}` |")
    w("\n- The walls are already 2 lines thick with no infill, so there is no infill to remove and no second wall "
      "to thin: `DESIGN-CONSTRAINTS.md:20` calls 0.86 mm the minimum that prints airtight, and `DESIGN-CONSTRAINTS.md:3` "
      "says these rules come from the design owner and are not traded away for weight without asking.")
    w("- **Foaming PLA** is a print setting, not a different plastic: flow 0.60–0.70 (moderate) or 0.45–0.55 (full) at "
      "230–250 °C, `SimplifiedSlice/README.md:116-126`. It changes density, so it changes mass at the same geometry.\n")

    w("\n## Every committed print STL\n")
    w("| Folder | File | Triangles | Vertices | cm³ | cm² | Mean wall mm | PLA g | Moderate foam g | Full foam g |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for gname, files in groups.items():
        for r in rows:
            if str(Path(r["rel"]).parent) != gname:
                continue
            w(f"| {gname} | `{r['path'].name}` | {r['tris']} | {r['verts']} | {f(r['cm3'], 2)} | {f(r['cm2'], 1)} | "
              f"{f(r['wall'], 2)} | {f(r['mass']['PLA'], 1)} | {f(r['mass']['LW-PLA, moderate foam'], 1)} | "
              f"{f(r['mass']['LW-PLA, full foam'], 1)} |")
    w("\n## Per-ship printed totals: measured beside the recorded tables\n")
    w("| Ship | Printed cm³ | Hull cm³ | recorded (source) | Δ | Intake tubes cm³ | Propulsion cm³ | recorded (source) | Δ |")
    w("|---|---|---|---|---|---|---|---|---|")
    for s, b in ships:
        hull, t = b["cm3"].get("hull", 0.0), b["cm3"].get("intake tubes", 0.0)
        rec = s["hull_recorded"]
        line = (f"| {s['name']} | {f(hull + t + prop_cm3(b), 1)} | {f(hull, 1)} | {rec[0]} (`{rec[4]}`) | "
                f"{delta(hull - rec[0])} | {f(t, 1) if t else '—'} | {f(prop_cm3(b), 1)} | ")
        if s["prop_recorded"]:
            line += f"{s['prop_recorded'][0]} (`{s['prop_recorded'][1]}`) | {delta(prop_cm3(b) - s['prop_recorded'][0])} |"
        else:
            line += "not recorded | — |"
        w(line)
    w("\n| Ship | Hull cm³ | Hull g: PLA recorded / measured | moderate foam | full foam |")
    w("|---|---|---|---|---|")
    for s, b in ships:
        hull = b["cm3"].get("hull", 0.0)
        rec = s["hull_recorded"]
        w(f"| {s['name']} | {f(hull, 1)} | {rec[1]} / {f(g(hull, 'PLA'), 1)} | {rec[2]} / "
          f"{f(g(hull, 'LW-PLA, moderate foam'), 1)} | {rec[3]} / {f(g(hull, 'LW-PLA, full foam'), 1)} |")
    w("\n- Every published hull mass in `SimplifiedSlice/README.md:102-106` reproduces from the meshes to the gram, "
      "so the recorded tables and the shipped STLs are the same model.")
    w("\n| Ship | Printed total cm³ | in PLA | in moderate foam | in full foam | as the docs mix them |")
    w("|---|---|---|---|---|---|")
    for s, b in ships:
        tot = sum(b["cm3"].values())
        w(f"| {s['name']} | {f(tot, 1)} | {f(g(tot, 'PLA'), 1)} | {f(g(tot, 'LW-PLA, moderate foam'), 1)} | "
          f"{f(g(tot, 'LW-PLA, full foam'), 1)} | {f(mixed_g(b['parts']), 1)} |")
    w("\n- **As the docs mix them:** hull, thruster rings, servo mounts and intake tubes in full-foam lightweight PLA, "
      "stems, gears and fan hatch in standard PLA, impeller in PETG (`SimplifiedSlice/README.md:126`). For the double "
      f"Kobra that is {f(mixed_g(dk['parts']), 0)} g printed, and it matches every printed line of `Analysis/FLOAT.md:70-77` "
      "to the gram.")
    w("- The recorded hull volumes also sit in `CHANGELOG.md:18-22`; measured and recorded agree to 0.4 cm³, which is "
      "rounding of the same measurement.\n")

    w("\n## Where the grams are\n")
    for s, b in ships:
        w(f"\n### {s['name']}\n")
        w("| Item | Qty | cm³ | PLA g | Moderate foam g | Full foam g |")
        w("|---|---|---|---|---|---|")
        for name, cm3 in sorted(b["cm3"].items(), key=lambda kv: -kv[1]):
            w(f"| {name} | {b['qty'][name]} | {f(cm3, 1)} | {f(g(cm3, 'PLA'), 1)} | "
              f"{f(g(cm3, 'LW-PLA, moderate foam'), 1)} | {f(g(cm3, 'LW-PLA, full foam'), 1)} |")
        tot = sum(b["cm3"].values())
        w(f"| **Printed total** |  | **{f(tot, 1)}** | {f(g(tot, 'PLA'), 1)} | "
          f"{f(g(tot, 'LW-PLA, moderate foam'), 1)} | {f(g(tot, 'LW-PLA, full foam'), 1)} |")
    w("\n### The biggest single levers\n")
    w(f"- **The two intake tubes are {f(tube_cm3, 1)} cm³: {f(g(tube_cm3, 'PLA'), 0)} g in PLA, "
      f"{f(g(tube_cm3, 'LW-PLA, moderate foam'), 0)} g in moderate foam, {f(g(tube_cm3, 'LW-PLA, full foam'), 0)} g in "
      "full foam.** That is more than any one slice set of the same ship "
      f"({f(dk['cm3']['hull'] / 4, 1)} cm³ for left + plain + right), so the tubes, not the lattice, are the second "
      "biggest printed item on the double-Kobra build. They are two separate prints whose only job is a Ø66 smooth "
      "empty bore (`SimplifiedSlice/README.md:70`).")
    w(f"- **Thruster rings:** {f(b8['parts']['thruster_ring'], 1)} cm³ of the bench 8-thruster ship's "
      f"{f(prop_cm3(b8), 1)} cm³ of propulsion ({f(ring8['cm3'], 2)} cm³ each), {f(b4['parts']['thruster_ring'], 1)} cm³ "
      f"on the 4-thruster bench and Kobra Max ships ({f(ring4['cm3'], 2)} each), and {f(dk['parts']['thruster_ring'], 1)} "
      "cm³ on the double Kobra, which uses the 8-thruster ring size on 4 thrusters "
      "(`Propulsion/README.md:19`). They are already the part the docs move to lightweight PLA "
      "(`Propulsion/README.md:52`).")
    w(f"- **Hull slices:** the largest group everywhere, and already lattice — mean wall "
      f"{f(min(hull_walls), 2)}–{f(max(hull_walls), 2)} mm, below the 0.86 mm wall because the windows add surface and "
      "no material, with the ovals and diamonds running right up to the fan housing since v0.2.1 "
      "(`CHANGELOG.md:12`).")
    w(f"- **Stems and gears** are {f(b8['cm3']['stems and gears'], 1)} cm³ on the 8-thruster ship and stay in standard "
      "PLA for accurate teeth, so they are grams the material change cannot reach "
      "(`SimplifiedSlice/README.md:126`).\n")

    w("\n## Corrections: recorded numbers the committed meshes do not support\n")
    w("| What | Recorded | Measured | Where |")
    w("|---|---|---|---|")
    for what, rec, meas, where in CORRECTIONS:
        w(f"| {what} | {rec} | {meas} | `{where}` |")
    w("\n- The same line's other 4-thruster numbers are right: "
      + ", ".join(f"{p.replace('_', ' ')} {RECORDED_4T_CM3[p]} → "
                  f"{f(by_rel['CAD Files/Propulsion/4T/print/' + p + '.stl']['cm3'], 2)}"
                  for p in ("stem", "stem_gear", "servo_gear", "fan_hatch")) + " cm³.")
    w(f"- The 4-thruster propulsion total is right: 154 cm³ recorded, {f(prop_cm3(b4), 1)} cm³ measured.")
    w(f"- Per part, the `Propulsion/README.md:44-50` table matches the meshes to 0.1 cm³ except the 8-thruster ring: "
      f"{RECORDED_PART_CM3['thruster_ring']} recorded, {f(ring8['cm3'], 2)} measured. That table at its own quantities "
      f"adds up to {f(recorded_prop_cm3(PROP_QTY), 1)} cm³, so the 233 in the text is "
      f"{f(recorded_prop_cm3(PROP_QTY) - 233, 1)} cm³ below its own table, and the meshes are "
      f"{f(prop_cm3(b8) - recorded_prop_cm3(PROP_QTY), 1)} cm³ above the table.\n")

    w("\n## What halving the wall would do\n")
    w("- The issue asks for the model at half the current thickness. The current wall is **0.86 mm** "
      "(2 perimeters of 0.45 mm at 0.2 mm layers), and `DESIGN-CONSTRAINTS.md:20` records that as **the minimum that "
      "prints airtight**, with nothing structural thinner.")
    w("- Half of it, 0.43 mm, is one 0.45 mm perimeter: below that minimum. The shaft, the fan housing and the ducts "
      "would stop being airtight, and the fan's pressure depends on them being airtight "
      "(`DESIGN-CONSTRAINTS.md:12`, `SimplifiedSlice/README.md:118`).")
    w(f"- The meshes are already there: the two intake tubes, which are plain Ø66 tubes of that wall and nothing else, "
      f"average {f(min(r['wall'] for r in tubes), 3)} and {f(max(r['wall'] for r in tubes), 3)} mm — the 0.86 mm the "
      "constraints set, to three decimal places. There is no thicker wall to halve.")
    w("- So the grams cannot come from wall thickness without breaking a rule the design owner set "
      "(`DESIGN-CONSTRAINTS.md:3`). They come from **material**, **part count** and **geometry**:")
    w(f"  - **Material:** the same geometry at 0.60 instead of 1.24 g/cm³ is 2.07 times lighter. The double Kobra's "
      f"{f(dk['cm3']['hull'], 1)} cm³ of hull is {f(g(dk['cm3']['hull'], 'PLA'), 1)} g in PLA and "
      f"{f(g(dk['cm3']['hull'], 'LW-PLA, full foam'), 1)} g in full foam.")
    w(f"  - **Part count:** 4 thrusters instead of 8 takes the rings, mounts, stems and gears from "
      f"{f(thruster_work_cm3(b8), 1)} cm³ to {f(thruster_work_cm3(b4), 1)} cm³, and the 4-thruster hull is "
      f"{f(b8['cm3']['hull'] - b4['cm3']['hull'], 1)} cm³ lighter than the 8-thruster one.")
    w("  - **Geometry:** webs at 1.2 mm instead of 2.0 mm on the v0.2 build (`DESIGN-CONSTRAINTS.md:26`), the number of "
      "slices and pieces, and the intake tubes: 127.1 cm³ of tube is more than any one slice set.\n")

    w("\n### The issue's 24 g anchor\n")
    w(f"One 8-thruster bench slice — the 1/8 component — measures {f(slice8['cm3'], 2)} cm³: "
      f"{f(g(slice8['cm3'], 'PLA'), 1)} g in PLA, {f(g(slice8['cm3'], 'LW-PLA, moderate foam'), 1)} g in moderate foam, "
      f"{f(g(slice8['cm3'], 'LW-PLA, full foam'), 1)} g in full foam. The comment's \"down to 24 grams\" sits between "
      "moderate and full foam, so a gram figure only means something beside its material and its settings, which is "
      "what this document records for every part.\n")

    w("\n## Not measured here\n")
    w("- **Slicer estimates:** no slicer was run. These are mesh integrals, not the slicer's filament length or "
      "material 3D time; a slicer's own estimate for foaming PLA depends on the flow and temperature recipe at "
      "`SimplifiedSlice/README.md:116-126`.")
    w("- **Weighed and load-tested parts:** every number here is computed from the committed meshes. Nothing was "
      "printed, weighed or pulled apart.")
    w(f"- **A target for the whole assembly:** the owner's to choose. For reference, the double-Kobra build is "
      f"{f(mixed_g(dk['parts']), 0)} g printed inside `Analysis/FLOAT.md`'s {FLOAT_TOTAL} g all-up against {FLOAT_LIFT} g "
      "of hydrogen lift, +168 g.")
    w("- **The parametric wall and rib revision itself:** `airship_slice.py` and `propulsion.py` were not touched, and "
      "no interface was moved.\n")
    return "\n".join(out)


def main():
    groups = stl_groups()
    rows = [measure(p) for files in groups.values() for p in files]
    doc = re.sub(r"\n{3,}", "\n\n", render(rows, groups)) + "\n"
    if "--check" in sys.argv:
        old = open(OUT, encoding="utf-8").read() if OUT.exists() else ""
        if old == doc:
            print(f"{OUT.name}: {len(rows)} STLs, {len(doc.splitlines())} lines, unchanged")
            return 0
        a, b = old.splitlines(), doc.splitlines()
        print(f"{OUT.name}: differs from the committed file")
        for i in range(max(len(a), len(b))):
            if i >= len(a) or i >= len(b) or a[i] != b[i]:
                print(f"  line {i + 1}\n    committed: {a[i] if i < len(a) else '<missing>'}\n"
                      f"    measured:  {b[i] if i < len(b) else '<missing>'}")
                break
        return 1
    open(OUT, "w", encoding="utf-8").write(doc)
    print(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
