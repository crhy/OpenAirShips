import importlib.util, math, os
os.environ.setdefault("OAS_VARIANT", "8T")
os.environ.setdefault("OAS_SCALE", "1.0")
spec = importlib.util.spec_from_file_location(
    "airship_slice", "CurrentModel/CAD Files/SimplifiedSlice/airship_slice.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.windows()
target = (187.2, -65.9, -29.5)
for idx, pts in enumerate(m._WIN_OUTLINES):
    d = min(math.dist((p.x, p.y, p.z), target) for p, _ in pts)
    if d < 2.0:
        near = sorted(math.dist((p.x, p.y, p.z), target) for p, _ in pts)[:4]
        print("outline %d: pts %d  nearest %.3f mm  %s" % (idx, len(pts), d, ["%.3f" % x for x in near]))
        for p, nv in pts:
            if True:
                print("    (%.3f, %.3f, %.3f) r %.2f az %.2f z %.2f  n (%.2f, %.2f, %.2f)"
                      % (p.x, p.y, p.z, math.hypot(p.x, p.y), math.degrees(math.atan2(p.y, p.x)),
                         p.z, nv.x, nv.y, nv.z))
