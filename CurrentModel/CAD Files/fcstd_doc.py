"""fcstd_doc.py - write a .FCStd that the FreeCAD GUI shows as soon as it opens.

Used by `SimplifiedSlice/make_fcstd.py`, `Propulsion/make_fcstd.py` and
`SimplifiedSlice/make_pieces.py`.

Two things a plain `doc.saveAs()` from `freecadcmd` leaves out, which is why
the shipped files opened on an empty 3D view (see Analysis/OUTPUT-CHECK.md):

* `GuiDocument.xml` - a console run has no GUI, so FreeCAD never writes it.
  Without it the GUI restores no camera, no per-object visibility flag and no
  colour, and nothing is switched on for the viewer.
* one copy of each shape - wrapping the part in a PartDesign Body over a base
  feature stores the same brep three times, so the viewer loads three identical
  solids sitting exactly on each other and z-fighting.

So every document written through here gets:

* one `Part::Feature` per part, each holding a real, valid, closed solid -
  `add_part()` refuses a null, invalid or open-shell shape instead of saving it;
* a document `Label` equal to the file name, so the tree matches the file;
* `GuiDocument.xml`: a ViewProvider entry per part (Visibility on, its own
  colour, shaded display) plus a camera framed on the parts. `freecadcmd`
  cannot write that file, so it is built here in FreeCAD's own dialect and
  appended to the .FCStd zip after `saveAs()`.
"""
import os
import re
import zipfile

import FreeCAD as App

# the colours the parts get in the viewer, so the pieces of a build read apart
PALETTE = [(0.80, 0.45, 0.20), (0.25, 0.55, 0.80), (0.45, 0.75, 0.40),
           (0.80, 0.75, 0.30), (0.70, 0.40, 0.70), (0.35, 0.70, 0.65),
           (0.85, 0.55, 0.55), (0.55, 0.55, 0.75)]


def new_document(label):
    """A document whose Label is the file name it is about to be saved as."""
    doc = App.newDocument(re.sub(r"[^A-Za-z0-9_]", "_", label))
    doc.Label = label
    return doc


def add_part(doc, name, shape, label=None):
    """Add one Part::Feature, and refuse to store a shape that is not a solid."""
    if shape.isNull():
        raise ValueError("%s: shape is null" % name)
    if not shape.isValid():
        raise ValueError("%s: shape is not valid: %s"
                         % (name, shape.check(False) or "no detail"))
    if not shape.Solids:
        raise ValueError("%s: shape has no solid" % name)
    for shell in shape.Shells:
        if not shell.isClosed():
            raise ValueError("%s: shape has an open shell" % name)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    if label:
        obj.Label = label
    return obj


def _camera(doc):
    """An OpenInventor camera that frames every part in the document.

    FreeCAD writes the camera orientation as an axis and an angle, not a
    quaternion, so this matches what the GUI itself saves.
    """
    box = None
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            bb = obj.Shape.BoundBox
            box = bb if box is None else box.united(bb)
    if box is None:
        box = App.BoundBox(-100, -100, -100, 100, 100, 100)
    diag = box.DiagonalLength
    if diag <= 0:
        diag = 200.0
    centre = box.Center
    # look at the model from the +x +y +z octant, as FreeCAD's isometric view
    # does: the camera's own Z axis points back at the model.
    towards = App.Vector(-1, -1, -1)
    towards.normalize()
    rot = App.Rotation(App.Vector(0, 0, 1), towards)
    eye = centre - towards * (diag * 1.5)
    return ("OrthographicCamera {"
            "&#10;  viewportMapping ADJUST_CAMERA"
            "&#10;  position %.6f %.6f %.6f"
            "&#10;  orientation %.8f %.8f %.8f %.8f"
            "&#10;  nearDistance %.6f"
            "&#10;  farDistance %.6f"
            "&#10;  aspectRatio 1"
            "&#10;  focalDistance %.6f"
            "&#10;  height %.6f"
            "&#10;&#10;}&#10;"
            % (eye.x, eye.y, eye.z,
               rot.Axis.x, rot.Axis.y, rot.Axis.z, rot.Angle,
               diag * 0.5, diag * 2.5, diag * 1.5, diag * 1.2))


def _view_provider(obj, index):
    """One ViewProvider entry: switched on, shaded, in its own colour."""
    r, g, b = PALETTE[index % len(PALETTE)]
    packed = (int(r * 255) << 24) | (int(g * 255) << 16) | (int(b * 255) << 8)
    return ('        <ViewProvider name="%(name)s" expanded="0">'
            '<Properties Count="4">'
            '<Property name="Visibility" type="App::PropertyBool" status="1">'
            '<Bool value="true"/></Property>'
            '<Property name="ShapeColor" type="App::PropertyColor" status="1">'
            '<PropertyColor value="%(colour)s"/></Property>'
            '<Property name="DisplayMode" type="App::PropertyEnumeration" status="1">'
            '<Integer value="0"/></Property>'
            '<Property name="Transparency" type="App::PropertyPercent" status="1">'
            '<Integer value="0"/></Property>'
            '</Properties></ViewProvider>'
            % {"name": obj.Name, "colour": packed})


def gui_document_xml(doc):
    """The GuiDocument.xml FreeCAD's GUI reads back on open."""
    parts = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!--\n'
            ' FreeCAD Document, see https://www.freecad.org for more information...\n'
            '-->\n'
            '<Document SchemaVersion="1" FileVersion="1">\n'
            '    <ViewProviderData Count="%(count)s">\n'
            '%(providers)s\n'
            '    </ViewProviderData>\n'
            '    <Camera settings="%(camera)s" />\n'
            '</Document>\n'
            % {"count": len(parts),
               "providers": "\n".join(
                   "      %s" % _view_provider(o, i)
                   for i, o in enumerate(parts)),
               "camera": _camera(doc)})


def save(doc, path):
    """Save the document, then make the GUI able to show it, then check it."""
    doc.recompute()
    if os.path.exists(path):
        os.remove(path)                       # no .FCBak backup next to it
    doc.saveAs(path)

    parts = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
    if not parts:
        raise ValueError("%s: no part to store" % path)
    with zipfile.ZipFile(path, "a", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("GuiDocument.xml", gui_document_xml(doc))

    # what the file must contain before anyone opens it in the GUI
    names = zipfile.ZipFile(path).namelist()
    for must in ("Document.xml", "GuiDocument.xml"):
        if must not in names:
            raise ValueError("%s: %s missing after save" % (path, must))
    for obj in parts:
        entry = "%s.Shape.brp" % obj.Name
        if entry not in names:
            raise ValueError("%s: %s not stored" % (path, entry))
    return path
