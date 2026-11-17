import Part, FreeCAD as App, time
s = Part.Shape()
s.read("/home/rhy/strata-fleet/repos/OpenAirShips/CurrentModel/CAD Files/SimplifiedSlice/airship pie slice 1026.step")
s.rotate(App.Vector(), App.Vector(0,0,1), 22.5)
f = Part.Face(Part.makePolygon([App.Vector(-10,0,-120),App.Vector(230,0,-120),App.Vector(230,0,120),App.Vector(-10,0,120),App.Vector(-10,0,-120)]))
t=time.time()
sec = s.section(f)
print("section edges %d in %.1fs, length %.1f" % (len(sec.Edges), time.time()-t, sec.Length))
w = sec.Wires
print("wires", len(w))
