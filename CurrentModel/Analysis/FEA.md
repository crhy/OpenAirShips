# Slice2 FEA (task a03)

Real CalculiX FEA of the Slice2 hull, run by `CurrentModel/Analysis/fea_slice.py`.

## Toolchain

- Mesher: gmsh 4.15.2 (pip wheel, venv `/home/rhy/.venvs/fea`), STEP -> 10-node
  tetrahedra (C3D10), uniform size 2.5 mm (~2 elements across the 0.86 mm wall).
- Solver: CalculiX 2.23 from the FreeCAD flatpak, no install needed:
  `flatpak run --filesystem=host --command=ccx org.freecad.FreeCAD <job>`.
  This build needs an explicit `*STATIC` card (without it ccx assembles the
  matrix and exits silently), rejects `*NODE PRINT` (use `*NODE FILE` + ASCII
  .frd parse), and wants `ELSET,GRAV,...` / `ELSET,PRES,...` on `*DLOAD`.
  gmsh's 10-node tet midside order is (12,23,13,14,34,24); CalculiX C3D10 is
  (12,23,13,14,24,34) - the last two columns are swapped. Midside nodes are
  projected to straight-edge midpoints (ccx has no curved elements).
- Units mm / N / MPa / tonne. PLA: E = 3500 MPa, nu = 0.36, rho = 1.24e-9 t/mm3.
  Yield 50 MPa derated x 1/3 for layer lines -> allowable 16.67 MPa.
  SF = allowable / max von Mises. BC: both 45 deg seam faces fully encastre
  (conservative: the real joint is a glued sleeve, not a rigid wall).

## Load cases (SPEC R18 / STRUCTURE-ESTIMATES.md section 3)

| case | load |
|---|---|
| L1 | 0.92 N, -Z on the servo pad face |
| L2 | 215.8 N.mm couple on the spline bore (4 N arm, +-F tangential) |
| L3 | 12.0 N tangential + 4.4 N radial-in on the spline bore |
| L4 | 0.75 N along each duct sleeve bore (x2) |
| L6 | 10 N ring break-out at each duct (x2) |
| L7 | GRAV 20 g, -Z |
| L8 | 1.9 kPa internal pressure on the plenum walls - not solved: ccx 2.23 flatpak rejects the PRES card on this deck; analytic membrane stress p*r/2t = 1.9e-3*30/(2*0.86) ~ 0.03 MPa, SF ~ 500, never governing. |

## Results - a02-8T.step (92.5 g, 242747 nodes, 300350 tets, size 2.5 mm)

| case | max VM MPa | max U mm | SF |
|---|---|---|---|
| L1 | 0.163 | 0.001 | 102.4 |
| L2 | 1.166 | 0.012 | 14.3 |
| L3 | 0.543 | 0.005 | 30.7 |
| L4 | 0.386 | 0.005 | 43.1 |
| L6 | 6.291 | 0.093 | **2.65** |
| L7 | 0.486 | 0.005 | 34.3 |

min SF = 2.65 (case L6, 10 N ring break-out at the duct root, x=183 y=-48 z=-43).
The governing case is the ring break-out at the duct/skin junction, not the
servo loads: the duct root needs more material (or the ring load path needs
the brace) before mass can come down.

## CAD cleanliness iterations (check_cad.py, sliver/short/hairline/internal)

| round | change | CR10Pro | 8T |
|---|---|---|---|
| a02 baseline | - | 0/55/146/17 | 0/0/8/19 |
| 1 | 2 deg meridian, +-88 poles, lattice cap 38, square windows, spline cutter -1.2 deep, STEM_HOLE 25.4, boss p1 outside rib | 12/5/72/28 | 14/2/95/42 |
| 2 | meridian back to 3 deg, keep +-88 | 10/43/108/27 | 19/2/23/30 |
| 3 | poles back to on-axis +-90 (a02 closure) | **0/37/98/19** | 0/0/14/25 |
| 4 | arc-closed poles (sphere-like tip) | OCC revolve fails (StdFail_NotDone), reverted | - |

Round 3 is the current state: CR10Pro failures 218 -> 154, slivers 0 at both
scales. Remaining: 37 short + 98 hairline edges (top-row window tangent
planes, concentric duct bores, polygon-chord dips) and 19 internal faces
(the on-axis pole cone chain + joint boss faces). The pole chain is inherent
to the on-axis meridian closure; every alternative tried (flat land, arc cap)
regressed other checks or failed the revolve.

## Reproduce

    /home/rhy/.venvs/fea/bin/python CurrentModel/Analysis/fea_slice.py \
        "CurrentModel/CAD Files/Slice2/slice-8T.step" --size 2.5 \
        --jobdir CurrentModel/Analysis/build/a03/fea25 \
        --json CurrentModel/Analysis/build/a03/fea-a02-8T-25.json
