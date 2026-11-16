#!/bin/sh
set -e
cd "/home/rhy/strata-fleet/repos/OpenAirShips"
export OAS_VARIANT=8T OAS_SLICES=8 OAS_SCALE=1
echo "== airship_slice =="
/home/rhy/.venvs/cadquery/bin/python "CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py"
echo "== make_fcstd =="
flatpak run --command=freecadcmd org.freecad.FreeCAD "CurrentModel/CAD Files/SimplifiedSlice/make_fcstd.py"
echo "== check =="
flatpak run --command=freecadcmd org.freecad.FreeCAD CurrentModel/Analysis/check_outputs.py --pass "--filter 8T.stl"
