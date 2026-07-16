# SofaTendons — multiple tendons from one component (tree input)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs (right-click each input -> Type hint AND set pts access to TREE):
#   pts       : TREE of Point3d — one branch per tendon              [tree, Point3d]
#               (e.g. Divide Curve on a list of 3 lines -> 3 branches;
#                do NOT flatten)
#   channels  : list of int — channel per branch (optional;          [list, int]
#               default 1..N in branch order)
#   valueType : str — "displacement" (mm) or "force" (mN), all       [item, str]
#               tendons (default displacement; use force for multi-
#               tendon systems — coupled displacement control fights
#               the constraint solver)
#   pullPoints: list of Point3d — optional external anchor per       [list, Point3d]
#               tendon (motor/pulley), matched by index
# Outputs:
#   tendons   : list of str tokens -> SofaBody.tendons (no Merge needed)
#   info      : str — what was created

import builtins

if not hasattr(builtins, "_sofagh_registry"):
    builtins._sofagh_registry = {}


def _put(kind, data):
    key = f"sofagh::{kind}::{len(builtins._sofagh_registry)}::{id(data)}"
    builtins._sofagh_registry[key] = data
    return key


tendons = []
info = "wire pts as a TREE (one branch per tendon; set input access to Tree)"

if pts is not None and pts.BranchCount > 0:
    n = pts.BranchCount
    chs = [int(c) for c in (channels or [])]
    while len(chs) < n:
        chs.append((chs[-1] + 1) if chs else 1)

    vt = (valueType or "displacement").strip().lower()
    if vt not in ("displacement", "force"):
        raise ValueError("valueType must be 'displacement' or 'force'")

    made = []
    for i in range(n):
        points = [[p.X, p.Y, p.Z] for p in pts.Branch(i) if p]
        if len(points) < 2:
            continue
        pp = None
        if pullPoints and i < len(pullPoints) and pullPoints[i]:
            q = pullPoints[i]
            pp = [q.X, q.Y, q.Z]
        tendons.append(_put("tendon", {
            "kind": "tendon",
            "points": points,
            "channel": chs[i],
            "name": f"cable_{chs[i]}",
            "value_type": vt,
            "pull_point": pp,
        }))
        made.append(f"cable_{chs[i]}({len(points)}pts)")
    info = f"{len(made)} tendons [{vt}]: " + ", ".join(made)
