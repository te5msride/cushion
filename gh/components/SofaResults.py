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
#   forces    : DataTree of Vector3d — branch {i} = nodal force (mN) at the
#               tracked points, frame i. Needs the Monitor's ExportForces
#               (default on). At contact-zone monitorPts this is the grip
#               reaction (net nodal: internal FEM + contact). Empty if the
#               scene was written before ExportForces existed.
#   pTimes    : list of float — actuation sample times
#   pressures : DataTree of float — branch {k} = channel k history
#   cableNames: list of str — cable names (body.cable), if any tendons
#   cableDisp : DataTree of float — branch {k} = cable k displacement, mm
#   cableForce: DataTree of float — branch {k} = cable k force, mN
#   contactPairs: list of str — "body__target" pair names (ContactListener)
#   contactCount: DataTree of int — branch {p} = # contacts per step, pair p
#   contactTimes: DataTree of float — branch {p} = step times for pair p
#   contactPts : DataTree of Point3d — branch {p;i} = contact points (on the
#                body surface) at step i, pair p. NOTE: contact GEOMETRY only,
#                not force. Empty if scene has no targets/collision or predates
#                the ContactListener wiring.

import os
import sys

import Rhino.Geometry as rg
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

times = []
points = DataTree[rg.Point3d]()
lastPts = []
forces = DataTree[rg.Vector3d]()
pTimes = []
pressures = DataTree[float]()
cableNames = []
cableDisp = DataTree[float]()
cableForce = DataTree[float]()
contactPairs = []
contactCount = DataTree[int]()
contactTimes = DataTree[float]()
contactPts = DataTree[rg.Point3d]()
info = "wire scenePath (from SofaScene, needs write=True) and bodyName"

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

        # nodal forces at the same monitor points (ExportForces)
        if os.path.isfile(os.path.join(proj, "monitor", bodyName + "_f.txt")):
            _, fframes = results.read_monitor(proj, bodyName, quantity="f")
            for i, frame in enumerate(fframes):
                forces.AddRange([rg.Vector3d(fx, fy, fz) for fx, fy, fz in frame],
                                GH_Path(i))
            lines.append(f"forces: {len(fframes)} frames (mN, at monitorPts)")
        else:
            lines.append("no forces file (scene predates ExportForces — "
                         "rewrite the scene to enable)")

    out = os.path.join(proj, "output", "output.csv")
    if os.path.isfile(out):
        pT, channels = results.read_pressures(proj)
        pTimes = pT
        for k, series in enumerate(channels):
            pressures.AddRange(series, GH_Path(k))
        lines.append(f"output.csv: {len(pT)} samples, {len(channels)} channels")
    else:
        lines.append(f"no output.csv yet ({out})")

    if os.path.isfile(os.path.join(proj, "output", "cables.csv")):
        cableNames, cT, disp, force = results.read_cables(proj)
        for k in range(len(cableNames)):
            cableDisp.AddRange(disp[k], GH_Path(k))
            cableForce.AddRange(force[k], GH_Path(k))
        lines.append(f"cables.csv: {len(cableNames)} cables, {len(cT)} samples")

    # contact map (ContactListener: points + count per body/target pair)
    if os.path.isfile(os.path.join(proj, "output", "contacts.csv")):
        pairs, cdata = results.read_contacts(proj)
        for pi, pair in enumerate(pairs):
            cts, counts, cframes = cdata[pair]
            contactPairs.append(pair)
            contactCount.AddRange(counts, GH_Path(pi))
            contactTimes.AddRange(cts, GH_Path(pi))
            for fi, frame in enumerate(cframes):
                contactPts.AddRange([rg.Point3d(x, y, z) for x, y, z in frame],
                                    GH_Path(pi, fi))
        peak = max((max(cdata[p][1]) for p in pairs if cdata[p][1]), default=0)
        lines.append(f"contacts.csv: {len(pairs)} pair(s), peak {peak} contacts/step")
    else:
        lines.append("no contacts.csv (no targets/collision, or scene written "
                     "before ContactListener support)")

    info = "\n".join(lines)
