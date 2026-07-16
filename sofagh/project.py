"""Assemble a SOFA project directory from component dicts.

A "project" is a self-contained folder runSofa can execute:

    <project_dir>/
        scene.py        (copied from runtime/, generic, reads scene.json)
        controller.py   (copied from runtime/)
        scene.json      (the spec built here)
        input.csv       (actuation schedule)
        meshes/*.stl, *.vtk
        monitor/        (SOFA Monitor output)
        output/         (controller CSV output)

Geometry export (Rhino mesh -> STL) happens on the Grasshopper side
(gh/ghcommon.py) BEFORE calling write_project; body/cavity/region dicts
arrive here with file paths already filled in.
"""

import json
import math
import os
import shutil

from . import inputs as _inputs
from . import meshing as _meshing

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime")

DEFAULTS = {
    "dt": 0.01,
    "gravity": [0.0, 0.0, -9810.0],
    "sample_rate": 100,
    "pre_time": 0.1,
    "pos_time": 0.3,
    "save_output": True,
    "n_channels": 10,
    "contacts": {
        "enabled": True,
        "alarm_distance": 5.0,
        "contact_distance": 1.0,
        "response": "FrictionContactConstraint",
        "rules": "",  # e.g. "target actuator FrictionContactConstraint"
    },
    "floor": None,  # {"point":[x,y,z], "size": 400.0} -> inline plane, z-up
}


def write_project(project_dir, bodies, profiles, options=None, targets=None):
    """Build scene.json + input.csv, tet-mesh bodies, copy runtime files.

    bodies: list of body dicts (see runtime/scene.py for consumed keys).
      Each body needs either body["volume_vtk"] (pre-meshed) or
      body["volume_source"] (.step/.stl path) + body["mesh_size"].
    profiles: list of {"channel", "times", "values"} for inputs.write_csv.
    targets: rigid interaction objects [{"name","mesh","mass",...}].
    Returns path to scene.py.
    """
    opts = dict(DEFAULTS)
    if options:
        for k, v in options.items():
            if v is not None:
                opts[k] = v

    os.makedirs(project_dir, exist_ok=True)
    for sub in ("meshes", "monitor", "output", "shape"):
        os.makedirs(os.path.join(project_dir, sub), exist_ok=True)

    # Volume meshing
    for body in bodies:
        if not body.get("volume_vtk"):
            src = body.get("volume_source")
            if not src:
                raise ValueError(f"body '{body.get('name')}' has no volume_vtk or volume_source")
            vtk_path = os.path.join(project_dir, "meshes", body["name"] + ".vtk")
            _meshing.volume_mesh(src, vtk_path, mesh_size=body.get("mesh_size", 1.0))
            body["volume_vtk"] = vtk_path
        body["volume_vtk"] = _relpath(body["volume_vtk"], project_dir)
        for key in ("collision_mesh",):
            if body.get(key):
                body[key] = _relpath(body[key], project_dir)
        for group in ("cavities", "regions", "visuals"):
            for item in body.get(group, []):
                if item.get("mesh"):
                    item["mesh"] = _relpath(item["mesh"], project_dir)

    targets = list(targets or [])
    for tgt in targets:
        tgt["mesh"] = _relpath(tgt["mesh"], project_dir)

    # Actuation CSV
    csv_path = os.path.join(project_dir, "input.csv")
    _, n_rows, input_duration = _inputs.write_csv(
        profiles, csv_path, sample_rate=opts["sample_rate"],
        n_channels=opts["n_channels"])

    duration = opts["pre_time"] + input_duration + opts["pos_time"]
    spec = {
        "name": os.path.basename(os.path.normpath(project_dir)),
        "dt": opts["dt"],
        "gravity": opts["gravity"],
        "sample_rate": opts["sample_rate"],
        "pre_time": opts["pre_time"],
        "pos_time": opts["pos_time"],
        "duration": duration,
        "n_steps": int(math.ceil(duration / opts["dt"])) + 10,
        "save_output": opts["save_output"],
        "input_csv": "input.csv",
        "contacts": opts["contacts"],
        "floor": opts["floor"],
        "camera": opts.get("camera"),
        "targets": targets,
        "bodies": bodies,
    }

    with open(os.path.join(project_dir, "scene.json"), "w") as f:
        json.dump(spec, f, indent=2)

    for fname in ("scene.py", "controller.py"):
        shutil.copy(os.path.join(RUNTIME_DIR, fname),
                    os.path.join(project_dir, fname))

    scene_path = os.path.join(project_dir, "scene.py")

    # Camera: runSofa's Qt viewer ignores scene cameras but always loads
    # <scene>.qglviewer.view — so the camera option is materialized as
    # that file. A user-saved .view file (Save View button) wins.
    if opts.get("view_file"):
        shutil.copy(opts["view_file"], scene_path + ".qglviewer.view")
    elif opts.get("camera"):
        _write_view_file(scene_path, opts["camera"])

    return scene_path


def _write_view_file(scene_path, camera):
    """Write <scene>.qglviewer.view: 'px py pz' + 'qx qy qz qw'.

    QGLViewer convention: camera looks along its local -z, up = +y.
    World up assumed +z (Rhino)."""
    px, py, pz = camera["position"]
    tx, ty, tz = camera["look_at"]

    def sub(a, b):
        return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]

    def cross(a, b):
        return [a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0]]

    def norm(v):
        n = math.sqrt(sum(c * c for c in v)) or 1.0
        return [c / n for c in v]

    zc = norm(sub([px, py, pz], [tx, ty, tz]))     # camera z = backward
    up = [0.0, 0.0, 1.0]
    if abs(zc[0] * up[0] + zc[1] * up[1] + zc[2] * up[2]) > 0.999:
        up = [0.0, 1.0, 0.0]                        # looking along world z
    xc = norm(cross(up, zc))
    yc = cross(zc, xc)

    # rotation matrix (columns xc, yc, zc) -> quaternion (x, y, z, w)
    m = [[xc[0], yc[0], zc[0]],
         [xc[1], yc[1], zc[1]],
         [xc[2], yc[2], zc[2]]]
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        qw = 0.25 * s
        qx = (m[2][1] - m[1][2]) / s
        qy = (m[0][2] - m[2][0]) / s
        qz = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        qw = (m[2][1] - m[1][2]) / s
        qx = 0.25 * s
        qy = (m[0][1] + m[1][0]) / s
        qz = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        qw = (m[0][2] - m[2][0]) / s
        qx = (m[0][1] + m[1][0]) / s
        qy = 0.25 * s
        qz = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        qw = (m[1][0] - m[0][1]) / s
        qx = (m[0][2] + m[2][0]) / s
        qy = (m[1][2] + m[2][1]) / s
        qz = 0.25 * s

    with open(scene_path + ".qglviewer.view", "w") as f:
        f.write(f"{px} {py} {pz}\n{qx} {qy} {qz} {qw}\n")


def _relpath(path, project_dir):
    """Store mesh paths relative to the project dir (portable folder)."""
    ap, ad = os.path.abspath(path), os.path.abspath(project_dir)
    if ap.startswith(ad + os.sep):
        return os.path.relpath(ap, ad).replace("\\", "/")
    return ap.replace("\\", "/")
