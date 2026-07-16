# SofaPreview — view everything the written scene contains, in Rhino
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


def _mesh(points, faces):
    m = rg.Mesh()
    for x, y, z in points:
        m.Vertices.Add(x, y, z)
    for f in faces:
        m.Faces.AddFace(f[0], f[1], f[2])
    m.Vertices.CombineIdentical(True, True)
    m.Normals.ComputeNormals()
    m.Compact()
    return m


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

            for body in spec.get("bodies", []):
                if body.get("volume_vtk"):
                    pts_, tets = meshload.read_vtk(_abs(body["volume_vtk"]))
                    volumes.append(_mesh(pts_, results.boundary_triangles(tets)))
                for c in body.get("cavities", []):
                    cavities.append(_mesh(*meshload.read_stl(_abs(c["mesh"]))))
                for r in body.get("regions", []):
                    regions.append(_mesh(*meshload.read_stl(_abs(r["mesh"]))))
                for cable in body.get("cables", []):
                    cpts = [rg.Point3d(p[0], p[1], p[2])
                            for p in cable.get("points", [])]
                    pp = cable.get("pull_point")
                    if pp:
                        cpts.append(rg.Point3d(pp[0], pp[1], pp[2]))
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
                counts.append(f"{body['name']}: vol {len(volumes)}, "
                              f"cav {len(body.get('cavities', []))}, "
                              f"reg {len(body.get('regions', []))}")

            for t in spec.get("targets", []):
                targets.append(_mesh(*meshload.read_stl(_abs(t["mesh"]))))

            info = ("; ".join(counts)
                    + (f"; tendons {len(tendonCrvs)}" if tendonCrvs else "")
                    + (f"; targets {len(targets)}" if targets else ""))
except Exception:
    info = "SofaPreview failed:\n" + traceback.format_exc()
