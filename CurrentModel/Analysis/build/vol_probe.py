import FreeCAD as App
import Part, Mesh
import os
cur = os.path.abspath("CurrentModel")
s = Part.Shape()
s.read(os.path.join(cur, "CAD Files/SimplifiedSlice/airship pie slice 1026.step"))
print("STEP solids", len(s.Solids), "faces", len(s.Faces), "vol", s.Volume)
m = Mesh.Mesh(os.path.join(cur, "Print Files/PieSlice1026-v0.2.1-8T.stl"))
print("STL facets", m.CountFacets, "pts", m.CountPoints, "solid", m.isSolid(), "vol", m.Volume, "comps", m.countComponents())
