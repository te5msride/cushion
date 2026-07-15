# SofaRegion — locally stiffened sub-region (membrane / sensor / waveguide)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Three ways to define the region:
#   A) geo       : closed Mesh enclosing the tets to stiffen
#   B) surface + thickness : any closed surface mesh (e.g. the cavity mesh)
#      is offset outward into a closed shell — this is how you get a
#      "hollow membrane with no inlet" that GH cannot represent as a Brep.
#   C) meshFile  : path to an existing closed .stl (e.g. membrane1.stl)
#
# Inputs:
#   geo       : Mesh — ready-made closed region mesh          [item, Geometry]
#   surface   : Mesh — base surface for auto-shell (option B) [item, Geometry]
#   thickness : float — shell offset (mm), used with surface  [item, float]
#   meshFile  : str — path to existing closed .stl (option C) [item, str]
#   name      : str                                           [item, str]
#   E         : float — Young's modulus overlay (kPa)         [item, float]
#   nu        : float — Poisson ratio (default 0.4)           [item, float]
#   repo      : str — path to the sofa-gh folder              [item, str]
# Output:
#   region    : dict, feed into SofaBody.regions
#   shell     : Mesh — generated shell (preview, option B only)

import sys

meshFile = globals().get("meshFile")

shell = None
region = None

if repo:
    repo = repo.strip().strip('"\'').rstrip("\\/")
    for _p in (repo, repo + "/gh"):
        if _p not in sys.path:
            sys.path.append(_p)

if geo is not None or surface is not None or meshFile:
    mesh = geo
    if mesh is None and surface is not None:
        import ghcommon
        t = float(thickness) if thickness else 1.0
        mesh = ghcommon.shell_from_surface(surface, t)
        shell = mesh

    from Grasshopper.Kernel.Types import GH_ObjectWrapper
    region = GH_ObjectWrapper({
        "kind": "region",
        "geo": mesh,
        "mesh_file": meshFile.strip().strip('"\'') if meshFile else None,
        "name": name if name else "region",
        "young_modulus": float(E) if E else 2000.0,
        "poisson_ratio": float(nu) if nu else 0.4,
    })
