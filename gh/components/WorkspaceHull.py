# r: scipy
# WorkspaceHull — 3D convex hull of a point cloud (workspace bounds)
#
# Rhino 8 Grasshopper Script component (Python 3). The "# r: scipy"
# line pip-installs scipy into Rhino's CPython on first run.
#
# Inputs (right-click each input -> Type hint):
#   pts : list of Point3d — e.g. flattened SofaResults.points   [list, Point3d]
# Outputs:
#   hull    : Mesh — convex hull of the cloud
#   volume  : float — hull volume (mm^3)
#   area    : float — hull surface area (mm^2)
#   info    : str

import Rhino.Geometry as rg

hull = None
volume = None
area = None
info = "wire pts (3+ non-coplanar points)"

if pts and len(pts) >= 4:
    import numpy as np
    from scipy.spatial import ConvexHull

    arr = np.array([[p.X, p.Y, p.Z] for p in pts if p])
    try:
        h = ConvexHull(arr)
    except Exception as e:  # degenerate (coplanar/collinear) cloud
        info = f"hull failed: {e}"
    else:
        m = rg.Mesh()
        for x, y, z in arr:
            m.Vertices.Add(x, y, z)
        for a, b, c in h.simplices:
            m.Faces.AddFace(int(a), int(b), int(c))
        m.Vertices.CullUnused()
        m.UnifyNormals()
        m.Normals.ComputeNormals()
        m.Compact()
        hull = m
        volume = float(h.volume)
        area = float(h.area)
        info = (f"{len(arr)} pts -> {len(h.simplices)} hull faces, "
                f"V = {volume:.0f} mm3, A = {area:.0f} mm2")
