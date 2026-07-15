# PressureProfile — actuation keyframes for one channel
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs:
#   channel : int — cavity channel (matches SofaCavity.channel)  [item, int]
#   times   : list of float — keyframe times, seconds            [list, float]
#   values  : list of float — pressures at keyframes, kPa        [list, float]
#             (linear interpolation between keyframes; MU grasp
#              example: times [0, 0.2, 0.8], values [0, -20, 40] —
#              at 100 Hz sampling that reproduces input_grasp.csv's
#              1 kPa-per-row ramps)
# Output:
#   profile : dict, feed into SofaScene.profiles

from Grasshopper.Kernel.Types import GH_ObjectWrapper

profile = None

if channel is not None and times and values:
    if len(times) != len(values):
        raise ValueError(f"times ({len(times)}) and values ({len(values)}) differ")
    profile = GH_ObjectWrapper({
        "channel": int(channel),
        "times": [float(t) for t in times],
        "values": [float(v) for v in values],
    })
