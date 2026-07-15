# SofaTendon — cable/tendon actuation path (SoftRobots CableConstraint)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs (right-click each input -> Type hint):
#   pts       : list of Point3d — ordered cable routing points, all      [list, Point3d]
#               INSIDE the body volume (barycentric-mapped). Typical:
#               Divide Curve on the tendon path -> points.
#   ptsFile   : str — OR path to a JSON file with [[x,y,z],...] points   [item, str]
#               (LETIAS interpolated_trunk_cable_N.json format)
#   channel   : int — column in input.csv driving this tendon           [item, int]
#   name      : str — optional, defaults to "cable_<channel>"           [item, str]
#   valueType : str — "displacement" (mm, default) or "force" (mN)      [item, str]
#   pullPoint : Point3d — optional external anchor the cable exits      [item, Point3d]
#               toward (motor/pulley location, outside the body).
#               Empty = closed loop through the points only.
# Outputs:
#   tendon    : str token, feed into SofaBody.tendons
#   pathPts   : list of Point3d — the routing points (preview)
#
# Channel semantics match cavities: input.csv column k drives it.
# displacement values are applied raw (mm); force values follow the
# same x dt convention as pressures (handled in the controller).
# NOTE (from the LETIAS reference): driving SEVERAL cables at once
# works reliably in 'force' mode; simultaneous displacement control of
# coupled cables fights the constraint solver.

import builtins
import json

ptsFile = globals().get("ptsFile")

if not hasattr(builtins, "_sofagh_registry"):
    builtins._sofagh_registry = {}


def _put(kind, data):
    key = f"sofagh::{kind}::{len(builtins._sofagh_registry)}::{id(data)}"
    builtins._sofagh_registry[key] = data
    return key


tendon = None
pathPts = []

points = [[p.X, p.Y, p.Z] for p in (pts or []) if p]
if not points and ptsFile:
    with open(ptsFile.strip().strip('"\'')) as f:
        points = [[float(c) for c in p] for p in json.load(f)]

if points:
    import Rhino.Geometry as rg
    pathPts = [rg.Point3d(x, y, z) for x, y, z in points]
    ch = int(channel) if channel is not None else 1
    vt = (valueType or "displacement").strip().lower()
    if vt not in ("displacement", "force"):
        raise ValueError("valueType must be 'displacement' or 'force'")
    tendon = _put("tendon", {
        "kind": "tendon",
        "points": points,
        "channel": ch,
        "name": name if name else f"cable_{ch}",
        "value_type": vt,
        "pull_point": [pullPoint.X, pullPoint.Y, pullPoint.Z] if pullPoint else None,
    })
# Output is a str token (shared in-session registry) — GH-marshalling-proof.
