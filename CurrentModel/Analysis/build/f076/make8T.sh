#!/bin/sh
# f076: rebuild the 8T bench variant end to end, then check it.
REPO="/home/rhy/strata-fleet/repos/OpenAirShips"
SL="$REPO/CurrentModel/CAD Files/SimplifiedSlice"
BUILD="$REPO/CurrentModel/Analysis/build/f076"

echo "== 1 generator: 8T bench slice -> STEP =="
cd "$SL" || exit 1
OAS_VARIANT=8T OAS_SLICES=8 OAS_SCALE=1 /home/rhy/.venvs/cadquery/bin/python airship_slice.py

echo "== 2 FCStd + print STL =="
OAS_VARIANT=8T OAS_SLICES=8 OAS_SCALE=1 flatpak run --command=freecadcmd org.freecad.FreeCAD "$SL/make_fcstd.py"

echo "== 3 the old STL measured against the new STEP (the volume change) =="
mkdir -p "$BUILD/old"
cp "$BUILD/baseline.stl" "$BUILD/old/PieSlice1026-v0.2.1-8T.stl"
cd "$REPO" || exit 1
flatpak run --command=freecadcmd org.freecad.FreeCAD "$BUILD/../check_outputs.py" \
    --pass "--stl-root $BUILD/old --no-tess --json $BUILD/checkold.json"

echo "== 4 checker on the new 8T print STL =="
flatpak run --command=freecadcmd org.freecad.FreeCAD "$REPO/CurrentModel/Analysis/check_outputs.py" \
    --pass "--filter PieSlice1026-v0.2.1-8T.stl --json $BUILD/check8T.json"

echo "== 6 checker on the new 8T STEP and FCStd =="
flatpak run --command=freecadcmd org.freecad.FreeCAD "$REPO/CurrentModel/Analysis/check_outputs.py" \
    --pass "--only cad --filter 'airship pie slice 1026.' --no-tess --json $BUILD/check8Tcad.json"

echo "== 5 where the thin walls are =="
flatpak run --command=freecadcmd org.freecad.FreeCAD "$BUILD/thin_probe.py" \
    --pass "'$REPO/CurrentModel/Print Files/PieSlice1026-v0.2.1-8T.stl'"
echo "== done (checker exit above if any) =="
