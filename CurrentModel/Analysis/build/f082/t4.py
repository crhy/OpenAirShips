import Part, FreeCAD as App
s = Part.Shape()
s.read("/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/SimplifiedSlice/airship pie slice 1026.step")
print("solids", len(s.Solids), "vol", round(s.Volume/1000,2))
s.rotate(App.Vector(), App.Vector(0,0,1), 22.5)
try:
    w = s.slice(App.Vector(0,1,0), 0.0)
    print("slice wires", len(w))
    tot = 0
    for x in w:
        tot += x.Length
    print("total wire length %.1f mm" % tot)
except Exception as e:
    print("slice failed:", e)
