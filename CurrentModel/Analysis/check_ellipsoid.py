#!/usr/bin/env python
"""Prove that the CR-10 Pro slice stays on or inside its exact ellipsoid.

Run under the repository's FreeCAD Flatpak:

    flatpak-spawn --host flatpak run --command=freecadcmd org.freecad.FreeCAD \
        CurrentModel/Analysis/check_ellipsoid.py --pass "--scale 1.41"

FreeCAD consumes normal-looking command-line options itself, so this script's
arguments must be placed in the quoted string following ``--pass``.

The containment check tessellates every BREP face and rejects any point outside
the prescribed ellipsoid.  Separately, it identifies the trimmed outer-skin
faces by their boundary vertices and samples their underlying analytic surfaces.
That second check prevents a faceted or merely close approximation from passing.
"""

import argparse
import math
import os
import shlex
import sys

import Part


HERE = os.path.dirname(os.path.abspath(__file__))
CURRENT = os.path.dirname(HERE)
DEFAULT_STEP = os.path.join(
    CURRENT,
    "CAD Files",
    "SimplifiedSlice",
    "airship pie slice 1026 CR10Pro.step",
)

# The unscaled semi-axes are fixed by DESIGN-CONSTRAINTS.md and airship_slice.py.
BASE_A = 207.765
BASE_B = 104.0


def script_argv():
    """Drop FreeCAD's duplicate script argument and retain arguments after it."""
    me = os.path.splitext(os.path.abspath(__file__))[0]
    out = []
    for arg in sys.argv[1:]:
        if os.path.splitext(os.path.abspath(arg))[0] == me:
            continue
        out.append(arg)
    return out


def ellipsoid_distance(point, a, b):
    """First-order signed normal distance to rho^2/a^2 + z^2/b^2 = 1."""
    rho = math.hypot(point.x, point.y)
    f = (rho / a) ** 2 + (point.z / b) ** 2 - 1.0
    gradient_half = math.hypot(rho / (a * a), point.z / (b * b))
    if gradient_half == 0.0:
        return -min(a, b)
    return f / (2.0 * gradient_half)


def surface_point(face, u_fraction, v_fraction):
    u0, u1, v0, v1 = face.ParameterRange
    u = u0 + (u1 - u0) * u_fraction
    v = v0 + (v1 - v0) * v_fraction
    return face.Surface.value(u, v)


def main(argv):
    parser = argparse.ArgumentParser(prog="check_ellipsoid.py", add_help=False)
    parser.add_argument("--step", default=DEFAULT_STEP)
    parser.add_argument("--scale", type=float, default=1.41)
    parser.add_argument("--deflection", type=float, default=0.02)
    parser.add_argument("--containment-tol", type=float, default=0.001)
    parser.add_argument("--surface-tol", type=float, default=1e-6)
    parser.add_argument("--candidate-band", type=float, default=0.02)
    parser.add_argument("--expected-faces", type=int, default=3)
    args = parser.parse_args(shlex.split(" ".join(a for a in argv if a != "--pass")))

    shape = Part.Shape()
    try:
        shape.read(os.path.abspath(args.step))
    except Exception as exc:
        print("FAIL ellipsoid: STEP read failed: %s" % exc)
        return 1

    problems = []
    if shape.isNull():
        problems.append("shape is null")
    if not shape.isValid():
        problems.append("shape is not valid")
    if len(shape.Solids) != 1:
        problems.append("expected 1 solid, found %d" % len(shape.Solids))

    a = BASE_A * args.scale
    b = BASE_B * args.scale
    vertices, triangles = shape.tessellate(args.deflection)
    distances = [ellipsoid_distance(point, a, b) for point in vertices]
    max_outside = max(distances) if distances else float("inf")
    outside = sum(distance > args.containment_tol for distance in distances)
    if outside:
        problems.append(
            "%d tessellated points protrude; maximum %.9f mm (limit %.6f mm)"
            % (outside, max_outside, args.containment_tol)
        )

    outer_faces = []
    for face in shape.Faces:
        boundary = [ellipsoid_distance(vertex.Point, a, b) for vertex in face.Vertexes]
        if boundary and max(abs(distance) for distance in boundary) <= args.candidate_band:
            outer_faces.append(face)

    if len(outer_faces) != args.expected_faces:
        problems.append(
            "expected %d exact outer-skin faces, found %d"
            % (args.expected_faces, len(outer_faces))
        )

    sample_error = 0.0
    sample_count = 0
    surface_types = []
    for face in outer_faces:
        surface_types.append(getattr(face.Surface, "TypeId", type(face.Surface).__name__))
        for u_fraction in (0.2, 0.5, 0.8):
            for v_fraction in (0.2, 0.5, 0.8):
                error = abs(ellipsoid_distance(
                    surface_point(face, u_fraction, v_fraction), a, b
                ))
                sample_error = max(sample_error, error)
                sample_count += 1
    if sample_error > args.surface_tol:
        problems.append(
            "outer analytic surface error %.9f mm exceeds %.9f mm"
            % (sample_error, args.surface_tol)
        )

    status = "FAIL" if problems else "PASS"
    print(
        "%s ellipsoid: A %.6f B %.6f mm; solid %d valid %s; "
        "%d BREP faces, %d exact exterior faces (%.3f mm2); "
        "analytic error %.9f mm at %d samples; envelope max protrusion %.9f mm "
        "at %d vertices / %d triangles"
        % (
            status,
            a,
            b,
            len(shape.Solids),
            shape.isValid(),
            len(shape.Faces),
            len(outer_faces),
            sum(face.Area for face in outer_faces),
            sample_error,
            sample_count,
            max(0.0, max_outside),
            len(vertices),
            len(triangles),
        )
    )
    if surface_types:
        print("  exterior surface types: %s" % ", ".join(surface_types))
    for problem in problems:
        print("  PROBLEM %s" % problem)
    return 1 if problems else 0


if __name__ in ("__main__", os.path.splitext(os.path.basename(__file__))[0]):
    exit_code = main(script_argv())
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(exit_code)
