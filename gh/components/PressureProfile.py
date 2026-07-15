# PressureProfile — actuation keyframes for one channel
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs:
#   channel : int — cavity/tendon channel                        [item, int]
#   times   : list of float — keyframe times, seconds            [list, float]
#   values  : list of float — kPa (cavity) / mm or mN (tendon)   [list, float]
#             (linear interpolation between keyframes; MU grasp
#              example: times [0, 0.2, 0.3, 0.9], values [0, -20, -20, 40])
# Output:
#   profile : str token, feed into SofaScene.profiles

import builtins

if not hasattr(builtins, "_sofagh_registry"):
    builtins._sofagh_registry = {}


def _put(kind, data):
    key = f"sofagh::{kind}::{len(builtins._sofagh_registry)}::{id(data)}"
    builtins._sofagh_registry[key] = data
    return key


profile = None

if channel is not None and times and values:
    if len(times) != len(values):
        raise ValueError(f"times ({len(times)}) and values ({len(values)}) differ")
    profile = _put("profile", {
        "channel": int(channel),
        "times": [float(t) for t in times],
        "values": [float(v) for v in values],
    })
