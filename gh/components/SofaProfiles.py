# SofaProfiles — multiple actuation profiles from one component (trees)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs (set times AND values access to TREE):
#   channels : list of int — channel per branch (optional;      [list, int]
#              default 1..N in values-branch order)
#   times    : TREE of float — keyframe times per channel, s    [tree, float]
#              (a single branch is shared by all channels)
#   values   : TREE of float — keyframe values per channel      [tree, float]
#              (kPa for cavities / mm or mN for tendons)
# Outputs:
#   profiles : list of str tokens -> SofaScene.profiles (no Merge needed)
#   info     : str
#
# Reminder: values hold at the last keyframe — add an explicit return
# to 0 if a channel should release.

import builtins

if not hasattr(builtins, "_sofagh_registry"):
    builtins._sofagh_registry = {}


def _put(kind, data):
    key = f"sofagh::{kind}::{len(builtins._sofagh_registry)}::{id(data)}"
    builtins._sofagh_registry[key] = data
    return key


profiles = []
info = "wire times + values as TREES (one branch per channel)"

if values is not None and values.BranchCount > 0 and times is not None \
        and times.BranchCount > 0:
    n = values.BranchCount
    chs = [int(c) for c in (channels or [])]
    while len(chs) < n:
        chs.append((chs[-1] + 1) if chs else 1)

    made = []
    for i in range(n):
        t = [float(x) for x in times.Branch(min(i, times.BranchCount - 1))]
        v = [float(x) for x in values.Branch(i)]
        if len(t) != len(v):
            raise ValueError(
                f"channel {chs[i]}: {len(t)} times vs {len(v)} values")
        profiles.append(_put("profile", {
            "channel": chs[i], "times": t, "values": v,
        }))
        made.append(f"ch{chs[i]}({len(t)}kf)")
    info = f"{len(made)} profiles: " + ", ".join(made)
