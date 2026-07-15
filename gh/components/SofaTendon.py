# SofaTendon — cable/tendon actuation path (SoftRobots CableConstraint)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs (right-click each input -> Type hint):
#   pts       : list of Point3d — ordered cable routing points, all      [list, Point3d]
#               INSIDE the body volume (barycentric-mapped). Typical:
#               Divide Curve on the tendon path -> points.
#   channel   : int — column in input.csv driving this tendon           [item, int]
#   name      : str — optional, defaults to "cable_<channel>"           [item, str]
#   valueType : str — "displacement" (mm, default) or "force" (mN)      [item, str]
#   pullPoint : Point3d — optional external anchor the cable exits      [item, Point3d]
#               toward (motor/pulley location, outside the body).
#               Empty = closed loop through the points only.
# Output:
#   tendon    : dict (wrapped), feed into SofaBody.tendons
#
# Channel semantics match cavities: input.csv column k drives it.
# displacement values are applied raw (mm); force values follow the
# same x dt convention as pressures (handled in the controller).

import builtins

if not hasattr(builtins, "_sofagh_registry"):
    builtins._sofagh_registry = {}


def _put(kind, data):
    key = f"sofagh::{kind}::{len(builtins._sofagh_registry)}::{id(data)}"
    builtins._sofagh_registry[key] = data
    return key


tendon = None

if pts:
    ch = int(channel) if channel is not None else 1
    vt = (valueType or "displacement").strip().lower()
    if vt not in ("displacement", "force"):
        raise ValueError("valueType must be 'displacement' or 'force'")
    tendon = _put("tendon", {
        "kind": "tendon",
        "points": [[p.X, p.Y, p.Z] for p in pts if p],
        "channel": ch,
        "name": name if name else f"cable_{ch}",
        "value_type": vt,
        "pull_point": [pullPoint.X, pullPoint.Y, pullPoint.Z] if pullPoint else None,
    })
# Output is a str token (shared in-session registry) — GH-marshalling-proof.
