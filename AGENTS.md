# Rules for anyone editing this repo (coding agent or human)

## Read the manual first

**Before any AirShip edit, read `CurrentModel/CONSTRUCTION-NOTES.md` section 0 (INDEX) and the
sections it points to for your kind of edit.** Do not read `airship_slice.py` end to end to find
out how it works — it is ~2,800 lines, and tasks f147 and f148 spent their whole budgets
re-reading it and shipped nothing. The manual has the generator map (every function, what it
builds, who calls it), the frames, the joint rules, the lattice rules, the duct/servo/brace rules,
the build workflow, and a failure-mode table with the task that found each one.

**Before you finish:** update the sections your change affects, add your task id to section 10
(LESSONS LOG), and run

    python3 CurrentModel/Analysis/check_construction_notes.py

It exits 1 and prints what is stale if the manual cites a generator name, constant, checker flag,
or file path that no longer exists, or if the INDEX line ranges no longer match the sections.
Fix the manual, not the checker.

## The five rules that break the print if you break them

1. **One wall, `T` = 0.86 mm** (2 perimeters of 0.45 mm at 0.2 mm layers) everywhere. Only what
   the `EXCEPTIONS` list in `airship_slice.py` names may be thicker, and each entry needs a reason.
2. **No cut boundary may land on a face the part already has** — nothing within 0.05 mm. That is
   what `CREST_EDGE_CLEAR`, `BRACE_EDGE_CLEAR`, `PAD_RING_CLEAR`, `BOSS_INSET`, `SKIN_TRIM` and the
   "guard solid strictly looser than the uv clip" idiom are for. Coincident faces give 0.005-0.05 mm
   sliver walls, self-intersecting meshes and invalid solids — issue #36.
3. **The duct uses the hull skin as its outer wall, and no lattice window is cut over a duct**
   (`CREST_BAND`, half the duct bore either side of a duct seam): a window there is a hole in the
   airtight air path. `AIR_KEEP` = 0.6 mm of wall for every hole toward any air.
4. **The lattice runs right out to the edges; every full cell is an open window, only the partial
   cells an edge cuts stay filled** (`MIN_WEB` = 0). A cell a keep-out trims is cut **clipped** if
   it keeps >= `MIN_KEEP` (50 %) of its own area inside the lattice's bounds, corners rounded to
   `CELL_CLOSE`; below that it stays solid. Never drop a whole cell for a keep-out that only bit it.
5. **A joint sits where two walls actually meet and is fused into both of them**, computed as the
   intersection of the two wall faces (never as a fraction of the way along a duct), keeping
   `JOINT_CLEAR` = 1.0 mm from the plenum air and the impeller's swept volume. If no wall can hold
   the hole, the joint does not exist.

Thrusters stay exactly on the equator (`OUT_Z` = 0). Never scale a printed STL uniformly: only
`OAS_SCALE` on the hull, walls/ribs/joints/fan/ducts/brace/pad keep their size.

## Workflow (details and timings in section 7)

Foreground commands must finish in under 3 minutes — prefix with `timeout 170`. The generator,
`make_fcstd.py` and the checker all take minutes, so run them in the background and poll:

    OAS_VARIANT=8T OAS_SCALE=1 /home/rhy/.venvs/cadquery/bin/python \
        "CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py"        # .step + .joints.json
    OAS_VARIANT=8T OAS_SCALE=1 flatpak run --command=freecadcmd org.freecad.FreeCAD \
        "CurrentModel/CAD Files/SimplifiedSlice/make_fcstd.py"           # .FCStd + print .stl
    nohup bash <the two commands above, in a script> > CurrentModel/Analysis/build/<task>/r1.log 2>&1 &
    sleep 120; tail -5 CurrentModel/Analysis/build/<task>/r1.log
    nice -n 10 flatpak run --command=freecadcmd org.freecad.FreeCAD \
        CurrentModel/Analysis/check_outputs.py --pass "--only print --filter 8T.stl"

All of the checker's own arguments go in one quoted string after `--pass` (freecadcmd eats
anything else that looks like an option). Use `--thin-report`, `--samples 20000` and
`--joints <joints.json>` when chasing a wall reading. Scratch goes in the git-ignored
`CurrentModel/Analysis/build/<task>/`, never under `CurrentModel/CAD Files` or
`CurrentModel/Print Files` (the checker walks those), never in /tmp.

Do not stop early: in this harness a reply with no tool call ends the task. Make the first edit
within 30 minutes and keep going until the gate passes or the timeout.
