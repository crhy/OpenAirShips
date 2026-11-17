import Mesh, MeshPart, FreeCAD as App, Part
m = MeshPart.meshFromShape(Shape=Part.makeBox(10,20,30), LinearDeflection=0.1, AngularDeflection=0.1, Relative=False)
m2 = m.copy(); m2.transformGeometry(App.Rotation(App.Vector(1,0,0), -90).toMatrix())
print("mesh rot", m2.BoundBox)
c = Part.makeCylinder(2,5,App.Vector(),App.Vector(0,0,1))
c.Placement = App.Placement(App.Vector(50,0,0), App.Rotation(App.Vector(0,1,0), 90))
print("cyl bb", c.BoundBox, round(c.Volume,2))
s = Part.Face(Part.makePolygon([App.Vector(0,0,0),App.Vector(10,0,0),App.Vector(10,0,10),App.Vector(0,0,0)])).revolve(App.Vector(),App.Vector(0,0,1),360)
print("revolved vol", round(s.Volume,2), s.BoundBox)
