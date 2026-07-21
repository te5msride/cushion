# SofaProtocol — keyframed rigid motion of a body (pick-and-place moves)
#
# Rhino 8 Grasshopper Script component (Python 3).
# Keyframes an offset applied to the whole body over time — e.g. a
# gripper carried down to an object, held, and lifted back up. The
# motion is applied through the body's rest positions, so the body is
# dragged by its FIXATIONS: a body without a fixation box will not
# follow the protocol.
#
# Inputs (right-click each input -> Type hint):
#   times   : list of float — keyframe times, seconds            [list, float]
#   offsets : list of Vector3d (or Point3d) — body offset FROM   [list, Vector3d]
#             ITS START POSITION at each keyframe. First keyframe
#             is typically (0,0,0). Linear interpolation between
#             keyframes; held outside the span.
#   name    : str — optional label                               [item, str]
# Output:
#   protocol : str token, feed into SofaBody.protocol
#
# Example (grasp-and-lift, with cavity profiles timed to match):
#   times   [0,  1,   2,   3,  4 ]
#   offsets (0,0,0) (0,0,-40) (0,0,-40) (0,0,20) (0,0,20)

import builtins

if not hasattr(builtins, "_sofagh_registry"):
    builtins._sofagh_registry = {}


def _put(kind, data):
    key = f"sofagh::{kind}::{len(builtins._sofagh_registry)}::{id(data)}"
    builtins._sofagh_registry[key] = data
    return key


protocol = None

if times and offsets:
    if len(times) != len(offsets):
        raise ValueError(f"times ({len(times)}) and offsets ({len(offsets)}) differ")
    offs = [[o.X, o.Y, o.Z] for o in offsets]
    protocol = _put("protocol", {
        "kind": "protocol",
        "times": [float(t) for t in times],
        "offsets": offs,
        "name": name if name else "protocol",
    })
