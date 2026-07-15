# SofaCavity — pneumatic chamber definition
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs (right-click each input -> Type hint):
#   geo      : Mesh/Brep — closed cavity surface              [item, Geometry]
#   meshFile : str — OR path to an existing closed .stl       [item, str]
#   channel  : int — column in input.csv driving this cavity  [item, int]
#   name     : str — optional, defaults to "cavity_<channel>" [item, str]
# Output:
#   cavity   : str token, feed into SofaBody.cavities
#
# Data passes between sofa-gh components as token strings referencing a
# shared in-session registry — immune to Grasshopper type marshalling.
# Type hint on consuming inputs no longer matters (str or none, both fine).

import builtins

meshFile = globals().get("meshFile")

if not hasattr(builtins, "_sofagh_registry"):
    builtins._sofagh_registry = {}


def _put(kind, data):
    key = f"sofagh::{kind}::{len(builtins._sofagh_registry)}::{id(data)}"
    builtins._sofagh_registry[key] = data
    return key


cavity = None

if geo is not None or meshFile:
    ch = int(channel) if channel is not None else 1
    cavity = _put("cavity", {
        "kind": "cavity",
        "geo": geo,
        "mesh_file": meshFile.strip().strip('"\'') if meshFile else None,
        "channel": ch,
        "name": name if name else f"cavity_{ch}",
    })
