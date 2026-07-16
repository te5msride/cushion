# SofaShape — deformed body shape at a chosen time (VTK frame playback)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Requires SofaBody.exportShape > 0 when the scene was written (exports
# the full volume mesh every N steps during the sim).
#
# Inputs (right-click each input -> Type hint):
#   scenePath : str — from SofaScene                          [item, str]
#   bodyName  : str — body to read                            [item, str]
#   frame     : int — frame index; -1 or empty = last         [item, int]
#   repo      : str — path to the sofa-gh folder              [item, str]
#   refresh   : bool — toggle to re-read                      [item, bool]
# Outputs:
#   mesh    : Mesh — deformed surface at that frame
#   nFrames : int — frames available (wire a slider 0..nFrames-1)
#   time    : float — sim time of the frame, s
#   info    : str

import os
import sys

import Rhino.Geometry as rg

mesh = None
nFrames = 0
time = None
info = "wire scenePath + bodyName; needs exportShape set on SofaBody"

if scenePath and bodyName:
    scenePath = scenePath.strip().strip('"\'')
    bodyName = bodyName.strip()
    repo = repo or __import__("os").environ.get("SOFAGH_ROOT")
    if repo:
        repo = repo.strip().strip('"\'').rstrip("\\/")
        if repo not in sys.path:
            sys.path.append(repo)
    from sofagh import results

    proj = os.path.dirname(scenePath)
    files = results.list_shape_frames(proj, bodyName)
    nFrames = len(files)

    if not files:
        info = (f"no shape frames in {os.path.join(proj, 'shape')} — "
                "set exportShape (e.g. 10) on SofaBody, rewrite scene, rerun sim")
    else:
        idx = int(frame) if frame is not None else -1
        if idx < 0 or idx >= nFrames:
            idx = nFrames - 1
        points, tetras = results.read_vtk_frame(files[idx])
        tris = results.boundary_triangles(tetras)

        m = rg.Mesh()
        for x, y, z in points:
            m.Vertices.Add(x, y, z)
        for a, b, c in tris:
            m.Faces.AddFace(a, b, c)
        m.Normals.ComputeNormals()
        m.Compact()
        mesh = m

        # frame time = export interval * dt * (index+1), from scene.json
        try:
            import json
            with open(os.path.join(proj, "scene.json")) as f:
                spec = json.load(f)
            body = next(b for b in spec["bodies"] if b["name"] == bodyName)
            time = spec["dt"] * int(body.get("export_shape", 0)) * (idx + 1)
        except Exception:
            time = None

        info = (f"frame {idx + 1}/{nFrames}, {len(points)} pts, "
                f"{len(tris)} surface tris"
                + (f", t = {time:.2f} s" if time is not None else ""))
