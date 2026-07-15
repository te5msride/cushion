# SofaCavity — pneumatic chamber definition
#
# Rhino 8 Grasshopper Script component (Python 3).
# Inputs (right-click each input -> Type hint):
#   geo      : Mesh/Brep — closed cavity surface              [item, Geometry]
#   meshFile : str — OR path to an existing closed .stl       [item, str]
#              (skips export; use for pre-made meshes like the
#               Monolithic Unit cavity1.stl/cavity2.stl)
#   channel  : int — column in input.csv driving this cavity  [item, int]
#   name     : str — optional, defaults to "cavity_<channel>" [item, str]
# Output:
#   cavity   : dict (wrapped), feed into SofaBody.cavities

from Grasshopper.Kernel.Types import GH_ObjectWrapper

meshFile = globals().get("meshFile")

cavity = None

if geo is not None or meshFile:
    ch = int(channel) if channel is not None else 1
    cavity = GH_ObjectWrapper({
        "kind": "cavity",
        "geo": geo,
        "mesh_file": meshFile.strip().strip('"\'') if meshFile else None,
        "channel": ch,
        "name": name if name else f"cavity_{ch}",
    })
