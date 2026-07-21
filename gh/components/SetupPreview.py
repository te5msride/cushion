# SetupPreview — view everything the written scene contains, in Rhino
#
# Rhino 8 Grasshopper Script component (Python 3).
# Reads the project folder (scene.json + mesh files) after SofaScene
# writes it, so it previews exactly what SOFA will simulate — including
# the gmsh-meshed volume surface and any file-path meshes that never
# existed as GH geometry. Wire each output through a Custom Preview
# with its own color.
#
# Inputs (right-click each input -> Type hint):
#   scenePath : str — from SofaScene                          [item, str]
#   repo      : str — path to the sofa-gh folder              [item, str]
#   refresh   : bool — toggle to re-read                      [item, bool]
# Outputs:
#   volumes   : list of Mesh — FEM volume surfaces (the real sim mesh)
#   cavities  : list of Mesh
#   regions   : list of Mesh
#   targets   : list of Mesh
#   tendonCrvs: list of Curve — cable routing paths
#   tendonChs : list of int — channel per tendon (Text Tag the start points)
#   monitorPts: list of Point3d
#   fixBoxes  : list of Box
#   info      : str — ALWAYS read this when something is off

import json
import os
import sys
import traceback

import Rhino.Geometry as rg

volumes, cavities, regions, targets, monitorPts, fixBoxes = [], [], [], [], [], []
tendonCrvs, tendonChs = [], []
info = "wire scenePath (SofaScene, write=True)"


_skipped = []


def _mesh(points, faces, label=""):
    """Build a Rhino mesh; return None (and record why) if degenerate —
    invalid meshes crash Grasshopper's output marshalling."""
    if len(points) < 3 or len(faces) < 1:
        _skipped.append(f"{label}: empty ({len(points)} pts, {len(faces)} faces)")
        return None
    m = rg.Mesh()
    for x, y, z in points:
        m.Vertices.Add(x, y, z)
    for f in faces:
        m.Faces.AddFace(f[0], f[1], f[2])
    m.Vertices.CombineIdentical(True, True)
    m.Normals.ComputeNormals()
    m.Compact()
    if not m.IsValid:
        _skipped.append(f"{label}: mesh invalid after build")
        return None
    return m


def _keep(seq, m):
    if m is not None:
        seq.append(m)


try:
    if scenePath:
        scenePath = str(scenePath).strip().strip('"\'')
        repo = repo or os.environ.get("SOFAGH_ROOT")
        if repo:
            repo = str(repo).strip().strip('"\'').rstrip("\\/")
            if repo not in sys.path:
                sys.path.append(repo)
        from sofagh import meshload, results

        proj = os.path.dirname(scenePath)
        spec_file = os.path.join(proj, "scene.json")
        if not os.path.isfile(spec_file):
            info = f"missing {spec_file}"
        else:
            with open(spec_file) as f:
                spec = json.load(f)
            counts = []

            def _abs(p):
                return p if os.path.isabs(p) else os.path.join(proj, p)

            import math as _m

            def _place_xf(body):
                pl = body.get("placement")
                if not pl:
                    return None
                ax, ay, az = [_m.radians(a) for a in pl["rotation"]]
                xf = rg.Transform.Rotation(az, rg.Vector3d.ZAxis, rg.Point3d.Origin)
                xf *= rg.Transform.Rotation(ay, rg.Vector3d.YAxis, rg.Point3d.Origin)
                xf *= rg.Transform.Rotation(ax, rg.Vector3d.XAxis, rg.Point3d.Origin)
                return rg.Transform.Translation(*pl["translation"]) * xf

            def _placed(mesh, xf):
                if mesh is not None and xf is not None:
                    mesh.Transform(xf)
                return mesh

            def _oriented_box(ob):
                p0 = rg.Point3d(ob[0], ob[1], ob[2])
                p1 = rg.Point3d(ob[3], ob[4], ob[5])
                p2 = rg.Point3d(ob[6], ob[7], ob[8])
                vx, vy = p1 - p0, p2 - p1
                pln = rg.Plane(p0, vx, vy)
                return rg.Box(pln, rg.Interval(0, vx.Length),
                              rg.Interval(0, vy.Length),
                              rg.Interval(-ob[9] / 2.0, ob[9] / 2.0))

            for body in spec.get("bodies", []):
                xf = _place_xf(body)
                if body.get("volume_vtk"):
                    pts_, tets = meshload.read_vtk(_abs(body["volume_vtk"]))
                    _keep(volumes, _placed(_mesh(pts_, results.boundary_triangles(tets),
                                                 body["volume_vtk"]), xf))
                for c in body.get("cavities", []):
                    _keep(cavities, _placed(_mesh(*meshload.read_stl(_abs(c["mesh"])),
                                                  label=c["mesh"]), xf))
                for r in body.get("regions", []):
                    _keep(regions, _placed(_mesh(*meshload.read_stl(_abs(r["mesh"])),
                                                 label=r["mesh"]), xf))
                for cable in body.get("cables", []):
                    cpts = [rg.Point3d(p[0], p[1], p[2])
                            for p in cable.get("points", [])]
                    pp = cable.get("pull_point")
                    if pp:
                        # SoftRobots pulls from the FIRST cable point
                        cpts.insert(0, rg.Point3d(pp[0], pp[1], pp[2]))
                    if len(cpts) >= 2:
                        pl = rg.Polyline()
                        for q in cpts:
                            pl.Add(q.X, q.Y, q.Z)
                        tendonCrvs.append(pl.ToPolylineCurve())
                        tendonChs.append(int(cable.get("channel", 0)))
                for p in body.get("monitor_points", []):
                    monitorPts.append(rg.Point3d(p[0], p[1], p[2]))
                for bx in body.get("fixations", []):
                    bb = rg.BoundingBox(
                        rg.Point3d(min(bx[0], bx[3]), min(bx[1], bx[4]), min(bx[2], bx[5])),
                        rg.Point3d(max(bx[0], bx[3]), max(bx[1], bx[4]), max(bx[2], bx[5])))
                    fixBoxes.append(rg.Box(bb))
                for ob in body.get("fixations_oriented", []):
                    fixBoxes.append(_oriented_box(ob))
                counts.append(f"{body['name']}: vol {len(volumes)}, "
                              f"cav {len(body.get('cavities', []))}, "
                              f"reg {len(body.get('regions', []))}")

            for t in spec.get("targets", []):
                _keep(targets, _mesh(*meshload.read_stl(_abs(t["mesh"])),
                                     label=t["mesh"]))

            info = ("; ".join(counts)
                    + (f"; tendons {len(tendonCrvs)}" if tendonCrvs else "")
                    + (f"; targets {len(targets)}" if targets else ""))
            if _skipped:
                info += "\nSKIPPED (bad mesh files):\n" + "\n".join(_skipped)
except Exception:
    info = "SetupPreview failed:\n" + traceback.format_exc()
