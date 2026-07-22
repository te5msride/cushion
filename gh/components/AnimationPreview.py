# AnimationPreview — scrub the finished simulation in the Rhino viewport
# [EXPERIMENTAL — not part of the v0.1 release set; use SetupPreview + SofaShape]
#
# Rhino 8 Grasshopper Script component (Python 3).
# Frame slider -> deformed body volumes, moved rigid targets, tracked
# points at that instant, plus the static fixation boxes and tendon
# paths for context. Wire outputs through Custom Preview components.
#
# Requirements: exportShape > 0 on each SofaBody you want animated
# (volumes come from those frames); targets animate automatically.
#
# Inputs (right-click each input -> Type hint):
#   scenePath : str — from SofaScene                          [item, str]
#   frame     : int — frame index; empty = last               [item, int]
#   repo      : str — path to the Cushion folder              [item, str]
#   refresh   : bool — toggle to re-read                      [item, bool]
# Outputs:
#   volumes    : list of Mesh — deformed body surfaces at the frame
#   targets    : list of Mesh — rigid targets at their frame pose
#   trackPts   : list of Point3d — monitored points at the frame
#   tendonCrvs : list of Curve — tendon routing (rest position, static)
#   fixBoxes   : list of Box — fixation boxes (static)
#   nFrames    : int — frames available (wire slider 0..nFrames-1)
#   time       : float — sim time of the frame, s
#   info       : str

import json
import os
import sys
import traceback

import Rhino.Geometry as rg

volumes, targets, trackPts, tendonCrvs, fixBoxes = [], [], [], [], []
nFrames = 0
time = None
info = "wire scenePath; needs exportShape on bodies for volumes"


def _mesh(points, faces):
    m = rg.Mesh()
    for x, y, z in points:
        m.Vertices.Add(x, y, z)
    for f in faces:
        m.Faces.AddFace(f[0], f[1], f[2])
    m.Vertices.CombineIdentical(True, True)
    m.Normals.ComputeNormals()
    m.Compact()
    return m if m.IsValid and m.Faces.Count else None


def _closest_row(times_list, t):
    if not times_list:
        return None
    return min(range(len(times_list)), key=lambda i: abs(times_list[i] - t))


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
        with open(os.path.join(proj, "scene.json")) as f:
            spec = json.load(f)
        dt = spec.get("dt", 0.01)

        def _abs(p):
            return p if os.path.isabs(p) else os.path.join(proj, p)

        lines = []

        # ---- deformed volumes (per body with exportShape)
        body_frames = []
        for body in spec.get("bodies", []):
            if body.get("export_shape"):
                files = results.list_shape_frames(proj, body["name"])
                if files:
                    body_frames.append((body, files))
        if body_frames:
            nFrames = min(len(f) for _, f in body_frames)
        idx = int(frame) if frame is not None else -1
        if nFrames and (idx < 0 or idx >= nFrames):
            idx = nFrames - 1

        for body, files in body_frames:
            pts, tets = results.read_vtk_frame(files[idx])
            m = _mesh(pts, results.boundary_triangles(tets))
            if m:
                volumes.append(m)
            time = dt * int(body["export_shape"]) * (idx + 1)
        if body_frames:
            lines.append(f"frame {idx + 1}/{nFrames}"
                         + (f", t = {time:.2f} s" if time is not None else ""))

        # ---- rigid targets: 3-point pose track -> plane-to-plane transform
        for tgt in spec.get("targets", []):
            base = _mesh(*meshload.read_stl(_abs(tgt["mesh"])))
            if base is None:
                continue
            try:
                tms, tframes = results.read_monitor(proj, "target_" + tgt["name"])
            except FileNotFoundError:
                targets.append(base)
                continue
            row = _closest_row(tms, time) if time is not None else len(tframes) - 1
            if row is not None and tframes and len(tframes[0]) >= 3 and len(tframes[row]) >= 3:
                def plane(fr):
                    a, b, c = [rg.Point3d(*fr[i]) for i in range(3)]
                    return rg.Plane(a, b - a, c - a)
                xf = rg.Transform.PlaneToPlane(plane(tframes[0]), plane(tframes[row]))
                base.Transform(xf)
            targets.append(base)
        if targets:
            lines.append(f"targets {len(targets)}")

        # ---- tracked body points at the frame
        for body in spec.get("bodies", []):
            if body.get("monitor_points"):
                try:
                    mts, mframes = results.read_monitor(proj, body["name"])
                except FileNotFoundError:
                    continue
                row = _closest_row(mts, time) if time is not None else len(mframes) - 1
                if row is not None and mframes:
                    trackPts.extend(rg.Point3d(x, y, z) for x, y, z in mframes[row])

        # ---- static context: tendons + fixation boxes
        for body in spec.get("bodies", []):
            for cable in body.get("cables", []):
                pl = rg.Polyline()
                pp = cable.get("pull_point")
                if pp:
                    pl.Add(pp[0], pp[1], pp[2])
                for x, y, z in cable.get("points", []):
                    pl.Add(x, y, z)
                if pl.Count >= 2:
                    tendonCrvs.append(pl.ToPolylineCurve())
            for bx in body.get("fixations", []):
                bb = rg.BoundingBox(
                    rg.Point3d(min(bx[0], bx[3]), min(bx[1], bx[4]), min(bx[2], bx[5])),
                    rg.Point3d(max(bx[0], bx[3]), max(bx[1], bx[4]), max(bx[2], bx[5])))
                fixBoxes.append(rg.Box(bb))


        info = "; ".join(lines) if lines else \
            "no shape frames — set exportShape on SofaBody, rewrite, rerun"
except Exception:
    info = "AnimationPreview failed:\n" + traceback.format_exc()
