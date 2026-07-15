# SofaResults — read monitor trajectories + pressures back into GH
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs:
#   scenePath : str — from SofaScene / SofaRun                 [item, str]
#   bodyName  : str — body whose Monitor to read               [item, str]
#   repo      : str — path to the sofa-gh folder               [item, str]
#   refresh   : bool — toggle to re-read files                 [item, bool]
# Outputs:
#   info      : str — what was looked for / found (read this first)
#   times     : list of float — one per recorded frame
#   points    : DataTree of Point3d — branch {i} = tracked points at frame i
#   lastPts   : list of Point3d — final frame (quick preview)
#   pTimes    : list of float — actuation sample times
#   pressures : DataTree of float — branch {k} = channel k history

import os
import sys

import Rhino.Geometry as rg
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

times = []
points = DataTree[rg.Point3d]()
lastPts = []
pTimes = []
pressures = DataTree[float]()
info = "wire scenePath (from SofaScene, needs write=True) and bodyName"

if scenePath and bodyName:
    scenePath = scenePath.strip().strip('"\'')
    bodyName = bodyName.strip()
    if repo:
        repo = repo.strip().strip('"\'').rstrip("\\/")
        if repo not in sys.path:
            sys.path.append(repo)
    from sofagh import results

    proj = os.path.dirname(scenePath)
    lines = [f"project: {proj}"]

    mon = os.path.join(proj, "monitor", bodyName + "_x.txt")
    if not os.path.isfile(mon):
        lines.append(f"MISSING: {mon}")
        lines.append("-> sim not run yet, or no monitorPts were wired into "
                     "SofaBody when the scene was written, or bodyName wrong "
                     f"(scene bodies: check {os.path.join(proj, 'scene.json')})")
    else:
        t_, frames = results.read_monitor(proj, bodyName)
        times = t_
        for i, frame in enumerate(frames):
            points.AddRange([rg.Point3d(x, y, z) for x, y, z in frame],
                            GH_Path(i))
        if frames:
            lastPts = [rg.Point3d(x, y, z) for x, y, z in frames[-1]]
        lines.append(f"monitor: {len(frames)} frames, "
                     f"{len(frames[0]) if frames else 0} points, "
                     f"t = {times[0]:.2f}..{times[-1]:.2f} s"
                     if frames else "monitor file exists but has no data rows "
                     "(sim not animated yet? press Animate in the SOFA GUI)")

    out = os.path.join(proj, "output", "output.csv")
    if os.path.isfile(out):
        pT, channels = results.read_pressures(proj)
        pTimes = pT
        for k, series in enumerate(channels):
            pressures.AddRange(series, GH_Path(k))
        lines.append(f"output.csv: {len(pT)} samples, {len(channels)} channels")
    else:
        lines.append(f"no output.csv yet ({out})")

    info = "\n".join(lines)
