#!/bin/sh
# f084: rebuild the 8T bench variant end to end (generator -> STEP -> FCStd + print STL)
REPO="/home/rhy/strata-fleet/repos/OpenAirShips"
SL="$REPO/CurrentModel/CAD Files/SimplifiedSlice"

echo "== 1 generator: 8T bench slice -> STEP + joints.json =="
cd "$SL" || exit 1
OAS_VARIANT=8T OAS_SLICES=8 OAS_SCALE=1 /home/rhy/.venvs/cadquery/bin/python airship_slice.py
echo "generator exit $?"

echo "== 2 FCStd + print STL =="
OAS_VARIANT=8T OAS_SLICES=8 OAS_SCALE=1 flatpak run --command=freecadcmd org.freecad.FreeCAD "$SL/make_fcstd.py"
echo "make_fcstd exit $?"

echo "== 3 checker: the 8T print STL (the gate) =="
cd "$REPO" || exit 1
flatpak run --command=freecadcmd org.freecad.FreeCAD "$REPO/CurrentModel/Analysis/check_outputs.py" \
    --pass "--only print --filter 8T.stl --thin-report"
echo "checker exit $?"
echo "== done =="
