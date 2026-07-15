# SofaBody — one deformable FEM body (actuator)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs:
#   geo        : Brep or Mesh — solid to tet-mesh (Brep preferred:    [item, Geometry]
#                exported as STEP for gmsh, like the reference pipeline)
#   volumeFile : str — OR path to existing mesh file:                 [item, str]
#                .vtk = pre-meshed tets used as-is (e.g. jvolume.vtk),
#                .step/.stl = gmsh will tet-mesh it. Overrides geo.
#   name       : str — node name, unique per body                     [item, str]
#   E          : float — homogenized Young's modulus, kPa (MU: 18.34) [item, float]
#   nu         : float — Poisson ratio (default 0.4)                  [item, float]
#   mass       : float — total mass, kg (MU: 0.050)                   [item, float]
#   meshSize   : float — gmsh MeshSizeFactor (MU jvolume: 0.22)       [item, float]
#   cavities   : list of SofaCavity dicts                             [list, No Type Hint]
#   tendons    : list of SofaTendon dicts                             [list, No Type Hint]
#   regions    : list of SofaRegion dicts                             [list, No Type Hint]
#   fixations  : list of Box — nodes inside are clamped               [list, Box]
#   monitorPts : list of Point3d — tracked points (Monitor export)    [list, Point3d]
#   collisionGeo : Mesh — collision surface (optional; enables contact) [item, Geometry]
#   visualGeo  : list of Mesh — display surfaces (e.g. lattice)       [list, Geometry]
#   visualFiles : list of str — OR paths to existing .stl files       [list, str]
#                 (e.g. lattice.stl; used as-is, no export)
#   visualFaces : int — decimate visuals to this face count on export [item, int]
#                 (0/empty = keep full resolution; visuals are never
#                  simulated, so decimation is free physically)
# Output:
#   body       : dict, feed into SofaScene.bodies

from Grasshopper.Kernel.Types import GH_ObjectWrapper


def _unwrap(x):
    # upstream dicts arrive wrapped in GH_ObjectWrapper
    return x.Value if isinstance(x, GH_ObjectWrapper) else x


body = None

if geo is not None or volumeFile:
    body = GH_ObjectWrapper({
        "kind": "body",
        "geo": geo,
        "volume_file": volumeFile.strip().strip('"\'') if volumeFile else None,
        "name": name if name else "actuator1",
        "young_modulus": float(E) if E else 18.0,
        "poisson_ratio": float(nu) if nu else 0.4,
        "total_mass": float(mass) if mass else 0.05,
        "mesh_size": float(meshSize) if meshSize else 1.0,
        "cavity_defs": [_unwrap(c) for c in (cavities or []) if c],
        "tendon_defs": [_unwrap(t) for t in (tendons or []) if t],
        "region_defs": [_unwrap(r) for r in (regions or []) if r],
        "fixation_boxes": [b for b in (fixations or []) if b],
        "monitor_points": [[p.X, p.Y, p.Z] for p in (monitorPts or []) if p],
        "collision_geo": collisionGeo,
        "visual_geos": [v for v in (visualGeo or []) if v],
        "visual_files": [f.strip().strip('"\'') for f in (visualFiles or []) if f],
        "visual_faces": int(visualFaces) if visualFaces else 0,
    })
