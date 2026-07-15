# r: gmsh
# SofaScene — assemble and write a runnable SOFA project folder
#
# Rhino 8 Grasshopper Script component (Python 3).
# The "# r: gmsh" line above makes Rhino pip-install gmsh into its own
# CPython automatically (first run needs internet + a minute).
#
# Inputs:
#   bodies    : list of SofaBody dicts                       [list, No Type Hint]
#   profiles  : list of PressureProfile dicts                [list, No Type Hint]
#   targets   : list of SofaTarget dicts (optional)          [list, No Type Hint]
#   camPos    : Point3d — SOFA camera position (optional)    [item, Point3d]
#   camTarget : Point3d — SOFA camera look-at (optional)     [item, Point3d]
#   viewFile  : str — path to a saved SOFA .view file to use [item, str]
#               instead of camPos/camTarget (Save View in the SOFA GUI
#               writes <scene>.py.qglviewer.view — copy it anywhere and
#               point here; wins over camPos/camTarget)
#   projDir   : str — output folder (created if missing)     [item, str]
#   repo      : str — path to the sofa-gh folder             [item, str]
#   dt        : float — timestep, s (default 0.01)           [item, float]
#   gravityZ  : float — mm/s^2 (default -9810; 0 disables)   [item, float]
#   floorZ    : float — adds a static floor plane at z (optional) [item, float]
#   floorSize : float — floor edge length, mm (default 400)  [item, float]
#   contactRules : str — RuleBasedContactManager rules, e.g.
#                  "target actuator FrictionContactConstraint" (optional) [item, str]
#   write     : bool — set True to (re)write the project     [item, bool]
# Outputs:
#   scenePath : str — path to scene.py (feed into SofaRun)
#   info      : str — summary of what was written

import os
import sys

scenePath = None
info = "set write=True"

if write and bodies and projDir:
    projDir = projDir.strip().strip('"\'')
    # repo path only needed in prototype mode; published .gha bundles
    # ghcommon + sofagh in the project's Shared folder.
    if repo:
        repo = repo.strip().strip('"\'').rstrip("\\/")
        for p in (repo, os.path.join(repo, "gh")):
            if p not in sys.path:
                sys.path.append(p)

    try:
        import ghcommon
        from sofagh import project as sofaproject
    except ImportError as e:
        checked = os.path.join(repo or "<no repo>", "gh", "ghcommon.py")
        raise ImportError(
            f"{e}. repo must point at the sofa-gh folder; "
            f"expected file: {checked} "
            f"(exists: {os.path.isfile(checked) if repo else False})")

    mesh_dir = os.path.join(projDir, "meshes")
    os.makedirs(mesh_dir, exist_ok=True)
    lines = []

    from Grasshopper.Kernel.Types import GH_ObjectWrapper

    def _unwrap(x):
        return x.Value if isinstance(x, GH_ObjectWrapper) else x

    spec_bodies = []
    for bd in bodies:
        bd = _unwrap(bd)
        if not bd:
            continue
        if not isinstance(bd, dict):
            raise TypeError(
                f"bodies input received {type(bd).__name__} instead of a dict — "
                "set the 'bodies' input Type hint to 'No Type Hint' and make "
                "sure it comes straight from a SofaBody component")
        bname = bd["name"]

        # --- volume: existing file, or Brep -> STEP (preferred), else STL
        import Rhino.Geometry as rg
        vol_src, vol_vtk = None, None
        vfile = bd.get("volume_file")
        if vfile:
            if not os.path.isfile(vfile):
                raise FileNotFoundError(f"{bname}: volumeFile not found: {vfile}")
            if vfile.lower().endswith(".vtk"):
                vol_vtk = vfile          # pre-meshed tets, used as-is
            else:
                vol_src = vfile          # .step/.stl, gmsh will mesh it
        else:
            geo = bd["geo"]
            if isinstance(geo, (rg.Brep, rg.Extrusion)):
                brep = geo.ToBrep() if isinstance(geo, rg.Extrusion) else geo
                vol_src = ghcommon.write_step(brep, os.path.join(mesh_dir, bname + ".step"))
            if vol_src is None:
                vol_src = ghcommon.write_stl(geo, os.path.join(mesh_dir, bname + "_volume.stl"))
        lines.append(f"{bname}: volume {os.path.basename(vol_vtk or vol_src)}")

        cavities = []
        for c in bd.get("cavity_defs", []):
            if c.get("mesh_file"):
                p = c["mesh_file"]
            else:
                p = ghcommon.write_stl(c["geo"], os.path.join(mesh_dir, f"{bname}_{c['name']}.stl"))
            cavities.append({"name": c["name"], "channel": c["channel"], "mesh": p})

        cables = []
        for t in bd.get("tendon_defs", []):
            cables.append({"name": t["name"], "channel": t["channel"],
                           "points": t["points"], "value_type": t["value_type"],
                           "pull_point": t.get("pull_point")})

        regions = []
        for r in bd.get("region_defs", []):
            if r.get("mesh_file"):
                p = r["mesh_file"]
            else:
                p = ghcommon.write_stl(r["geo"], os.path.join(mesh_dir, f"{bname}_{r['name']}.stl"))
            regions.append({"name": r["name"], "mesh": p,
                            "young_modulus": r["young_modulus"],
                            "poisson_ratio": r["poisson_ratio"]})

        collision_mesh = None
        if bd.get("collision_geo") is not None:
            collision_mesh = ghcommon.write_stl(
                bd["collision_geo"], os.path.join(mesh_dir, f"{bname}_collision.stl"))

        visuals = []
        for vi, vg in enumerate(bd.get("visual_geos", [])):
            if bd.get("visual_faces"):
                vg = ghcommon.reduce_mesh(vg, bd["visual_faces"])
            p = ghcommon.write_stl(vg, os.path.join(mesh_dir, f"{bname}_visual{vi}.stl"))
            visuals.append({"mesh": p})
        for vf in bd.get("visual_files", []):
            if not os.path.isfile(vf):
                raise FileNotFoundError(f"{bname}: visual file not found: {vf}")
            visuals.append({"mesh": vf})

        spec_bodies.append({
            "name": bname,
            "volume_source": vol_src,
            "volume_vtk": vol_vtk,
            "mesh_size": bd.get("mesh_size", 1.0),
            "young_modulus": bd["young_modulus"],
            "poisson_ratio": bd["poisson_ratio"],
            "total_mass": bd["total_mass"],
            "fixations": [ghcommon.box_to_list(b) for b in bd.get("fixation_boxes", [])],
            "monitor_points": bd.get("monitor_points", []),
            "cavities": cavities,
            "cables": cables,
            "regions": regions,
            "collision_mesh": collision_mesh,
            "visuals": visuals,
        })

    spec_targets = []
    for tg in (targets or []):
        tg = _unwrap(tg)
        if not tg:
            continue
        if not isinstance(tg, dict):
            raise TypeError(
                f"targets input received {type(tg).__name__} instead of a dict — "
                "set the 'targets' input Type hint to 'No Type Hint'")
        if tg.get("mesh_file"):
            p = tg["mesh_file"]
        else:
            p = ghcommon.write_stl(tg["geo"],
                                   os.path.join(mesh_dir, tg["name"] + ".stl"))
        spec_targets.append({"name": tg["name"], "mesh": p, "mass": tg["mass"]})
        lines.append(f"target {tg['name']}: {os.path.basename(p)}")

    options = {
        "dt": float(dt) if dt else None,
        "camera": ({"position": [camPos.X, camPos.Y, camPos.Z],
                    "look_at": [camTarget.X, camTarget.Y, camTarget.Z]}
                   if (camPos is not None and camTarget is not None) else None),
        "view_file": viewFile.strip().strip('"\'') if viewFile else None,
        "gravity": [0.0, 0.0, float(gravityZ)] if gravityZ is not None else None,
        "floor": ({"point": [0.0, 0.0, float(floorZ)],
                   "size": float(floorSize) if floorSize else 400.0}
                  if floorZ is not None else None),
        "contacts": {"enabled": True,
                     "alarm_distance": 5.0, "contact_distance": 1.0,
                     "response": "FrictionContactConstraint",
                     "rules": contactRules or ""},
    }

    scenePath = sofaproject.write_project(
        projDir, spec_bodies,
        [_unwrap(p) for p in (profiles or []) if p], options,
        targets=spec_targets)
    lines.append(f"scene: {scenePath}")
    info = "\n".join(lines)
