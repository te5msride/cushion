# SofaTarget — rigid interaction object (graspable target, obstacle)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs (right-click each input -> Type hint):
#   geo      : Mesh/Brep — object surface, placed in world coords  [item, Geometry]
#   meshFile : str — OR path to an existing closed .stl            [item, str]
#   name     : str — default "target1"                             [item, str]
#   mass     : float — kg (default 0.01)                           [item, float]
# Output:
#   target   : str token, feed into SofaScene.targets
#
# Notes:
# * Collision models are named "target" — usable in contactRules.
# * The body needs collisionGeo wired for contact, usually + a floor.
# * v0: unit rotational inertia (fine for grasp/poke tests).

import builtins

meshFile = globals().get("meshFile")

if not hasattr(builtins, "_sofagh_registry"):
    builtins._sofagh_registry = {}


def _put(kind, data):
    key = f"sofagh::{kind}::{len(builtins._sofagh_registry)}::{id(data)}"
    builtins._sofagh_registry[key] = data
    return key


target = None

if geo is not None or meshFile:
    target = _put("target", {
        "kind": "target",
        "geo": geo,
        "mesh_file": meshFile.strip().strip('"\'') if meshFile else None,
        "name": name if name else "target1",
        "mass": float(mass) if mass else 0.01,
    })
