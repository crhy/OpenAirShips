import Part, sys, shlex, os
me = os.path.splitext(os.path.abspath(__file__))[0]
argv = [a for a in shlex.split(" ".join(sys.argv[1:])) if a != "--pass" and os.path.splitext(os.path.abspath(a))[0] != me]
s = Part.Shape(); s.read(argv[0])
px, py, pz = [float(v) for v in argv[1].split(",")]
rad = float(argv[2]) if len(argv) > 2 else 3.0
for f in s.Faces:
    c = f.CenterOfMass
    if (c.x-px)**2 + (c.y-py)**2 + (c.z-pz)**2 < rad*rad:
        srf = f.Surface
        print("area %.4f %s" % (f.Area, srf.__class__.__name__))
        for a in ("Axis","Location","Center","Radius","AxisDirection","BasePath","Degree"):
            if hasattr(srf, a):
                try: print("   %s = %s" % (a, getattr(srf, a)))
                except Exception: pass
