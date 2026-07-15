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

RUNTIME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "runtime")

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


def write_project(project_dir, bodies, profiles, options=None):
    """Build scene.json + input.csv, tet-mesh bodies, copy runtime files.

    bodies: list of body dicts (see runtime/scene.py for consumed keys).
      Each body needs either body["volume_vtk"] (pre-meshed) or
      body["volume_source"] (.step/.stl path) + body["mesh_size"].
    profiles: list of {"channel", "times", "values"} for inputs.write_csv.
    Returns path to scene.py.
    """
    opts = dict(DEFAULTS)
    if options:
        for k, v in options.items():
            if v is not None:
                opts[k] = v

    os.makedirs(project_dir, exist_ok=True)
    for sub in ("meshes", "monitor", "output"):
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
        "bodies": bodies,
    }

    with open(os.path.join(project_dir, "scene.json"), "w") as f:
        json.dump(spec, f, indent=2)

    for fname in ("scene.py", "controller.py"):
        shutil.copy(os.path.join(RUNTIME_DIR, fname),
                    os.path.join(project_dir, fname))

    return os.path.join(project_dir, "scene.py")


def _relpath(path, project_dir):
    """Store mesh paths relative to the project dir (portable folder)."""
    ap, ad = os.path.abspath(path), os.path.abspath(project_dir)
    if ap.startswith(ad + os.sep):
        return os.path.relpath(ap, ad).replace("\\", "/")
    return ap.replace("\\", "/")
