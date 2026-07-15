# SofaTarget — rigid interaction object (graspable target, obstacle)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs (right-click each input -> Type hint):
#   geo      : Mesh/Brep — object surface, placed in world coords  [item, Geometry]
#   meshFile : str — OR path to an existing closed .stl            [item, str]
#   name     : str — default "target1"                             [item, str]
#   mass     : float — kg (default 0.01)                           [item, float]
# Output:
#   target   : dict (wrapped), feed into SofaScene.targets
#
# Notes:
# * Collision models are named "target" — usable in contactRules, e.g.
#   "target actuator1 FrictionContactConstraint". With no rules, the
#   default friction contact applies to everything anyway.
# * The body needs collisionGeo wired for contact to happen at all,
#   and usually a floor (floorZ) so the target has somewhere to rest.
# * v0 approximation: rotational inertia is not computed from the
#   shape (unit inertia). Good enough for grasp/poke tests.

from Grasshopper.Kernel.Types import GH_ObjectWrapper

target = None

if geo is not None or meshFile:
    target = GH_ObjectWrapper({
        "kind": "target",
        "geo": geo,
        "mesh_file": meshFile.strip().strip('"\'') if meshFile else None,
        "name": name if name else "target1",
        "mass": float(mass) if mass else 0.01,
    })
