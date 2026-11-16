#!/bin/sh
# Regenerate every .FCStd under CurrentModel/CAD Files with the fixed writer.
# OAS_FCSTD_ONLY=1: rebuild the documents from the STEP files already on disk;
# the .step and .stl files are not touched (that is f074's job).
set -e
export OAS_FCSTD_ONLY=1
CAD="/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files"
FC="flatpak run --command=freecadcmd org.freecad.FreeCAD"

echo "=== SimplifiedSlice: 6 whole-slice documents ==="
cd "$CAD/SimplifiedSlice"
$FC make_fcstd.py
OAS_SCALE=1.9 $FC make_fcstd.py
OAS_VARIANT=4T OAS_SIDE=L $FC make_fcstd.py
OAS_VARIANT=4T OAS_SIDE=R $FC make_fcstd.py
OAS_VARIANT=4T OAS_SIDE=L OAS_SCALE=1.9 $FC make_fcstd.py
OAS_VARIANT=4T OAS_SIDE=R OAS_SCALE=1.9 $FC make_fcstd.py

echo "=== SimplifiedSlice: 3 pieces documents ==="
OAS_VARIANT=4T OAS_SLICES=12 OAS_THRUSTER=S OAS_PIECES=1 OAS_SCALE=3.8 OAS_RIB=1.2 $FC make_pieces.py

echo "=== Propulsion: 5 assembly documents ==="
cd "$CAD/Propulsion"
$FC make_fcstd.py
OAS_SCALE=1.9 $FC make_fcstd.py
OAS_VARIANT=4T OAS_THRUSTER=L $FC make_fcstd.py
OAS_VARIANT=4T OAS_THRUSTER=L OAS_SCALE=1.9 $FC make_fcstd.py
OAS_VARIANT=4T OAS_SLICES=12 OAS_THRUSTER=S OAS_SCALE=3.8 $FC make_fcstd.py

echo "=== done ==="
ls -l "$CAD/SimplifiedSlice"/*.FCStd "$CAD/SimplifiedSlice/pieces"/*.FCStd \
     "$CAD/Propulsion"/*.FCStd "$CAD/Propulsion/x1.9"/*.FCStd \
     "$CAD/Propulsion/4T"/*.FCStd "$CAD/Propulsion/4T/x1.9"/*.FCStd \
     "$CAD/Propulsion/4T/small/12s/x3.8"/*.FCStd
