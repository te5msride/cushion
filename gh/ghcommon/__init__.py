"""Rhino/Grasshopper-side helpers (RhinoCommon required).

Imported by the gh/components/*.py scripts inside Rhino 8 Script
components. Everything geometry-touching lives here; sofagh/ stays
Rhino-free.
"""

import os
import struct

import Rhino
import Rhino.Geometry as rg


# ---------------------------------------------------------------- meshes

def to_mesh(geo, max_edge=0.0):
    """Coerce Brep/Mesh/Extrusion to a single joined Rhino mesh."""
    if isinstance(geo, rg.Mesh):
        m = geo.DuplicateMesh()
    elif isinstance(geo, rg.Extrusion):
        return to_mesh(geo.ToBrep(), max_edge)
    elif isinstance(geo, rg.Brep):
        mp = rg.MeshingParameters.QualityRenderMesh
        if max_edge and max_edge > 0:
            mp.MaximumEdgeLength = max_edge
        parts = rg.Mesh.CreateFromBrep(geo, mp)
        if not parts:
            raise ValueError("Brep meshing failed")
        m = rg.Mesh()
        for p in parts:
            m.Append(p)
    else:
        raise TypeError(f"Cannot convert {type(geo).__name__} to mesh")
    m.Faces.ConvertQuadsToTriangles()
    m.UnifyNormals()
    m.Normals.ComputeNormals()
    m.Compact()
    return m


def write_stl(geo, path, max_edge=0.0):
    """Write binary STL. Returns absolute path."""
    m = to_mesh(geo, max_edge)
    faces = m.Faces
    verts = m.Vertices
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"sofagh binary stl".ljust(80, b"\0"))
        f.write(struct.pack("<I", faces.Count))
        for i in range(faces.Count):
            fa = faces[i]
            a, b, c = verts[fa.A], verts[fa.B], verts[fa.C]
            n = rg.Vector3d.CrossProduct(
                rg.Point3d(b) - rg.Point3d(a), rg.Point3d(c) - rg.Point3d(a))
            n.Unitize()
            f.write(struct.pack("<3f", n.X, n.Y, n.Z))
            for v in (a, b, c):
                f.write(struct.pack("<3f", v.X, v.Y, v.Z))
            f.write(struct.pack("<H", 0))
    return os.path.abspath(path)


def write_step(brep, path):
    """Export a Brep to STEP via a headless doc. Returns path or None."""
    try:
        doc = Rhino.RhinoDoc.CreateHeadless(None)
        doc.ModelUnitSystem = Rhino.UnitSystem.Millimeters
        doc.Objects.AddBrep(brep)
        ok = doc.Export(path)
        doc.Dispose()
        return os.path.abspath(path) if ok else None
    except Exception:
        return None


def shell_from_surface(mesh, thickness):
    """Closed shell mesh from a (closed) surface mesh, offset outward.

    Solves the 'hollow membrane with no inlet is not a valid GH Brep'
    problem: MeshROI in SOFA only needs a closed triangle mesh, so we
    build the shell as mesh geometry directly.
    """
    m = to_mesh(mesh)
    shell = m.Offset(thickness, True)  # solidify=True stitches walls
    if shell is None:
        raise ValueError("Mesh.Offset failed; check normals/watertightness")
    shell.Faces.ConvertQuadsToTriangles()
    shell.UnifyNormals()
    shell.Normals.ComputeNormals()
    return shell


def reduce_mesh(mesh, target_faces):
    """Quadric-decimate a display mesh (visual-only; never simulated).

    Heavy MultiPipe/lattice meshes only exist in SOFA as OglModel
    visuals mapped onto the FEM envelope — decimating them costs
    nothing physically.
    """
    m = to_mesh(mesh)
    if target_faces and m.Faces.Count > target_faces:
        m.Reduce(int(target_faces), False, 10, True)
        m.Faces.ConvertQuadsToTriangles()
        m.Compact()
    return m


def box_to_list(box):
    """GH Box / BoundingBox -> [xmin, ymin, zmin, xmax, ymax, zmax]."""
    if isinstance(box, rg.Box):
        bb = box.BoundingBox
    elif isinstance(box, rg.BoundingBox):
        bb = box
    else:
        bb = box.GetBoundingBox(True)
    return [bb.Min.X, bb.Min.Y, bb.Min.Z, bb.Max.X, bb.Max.Y, bb.Max.Z]
