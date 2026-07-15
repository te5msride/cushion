"""sofagh — Grasshopper <-> SOFA bridge (Tier 1: file-based batch).

Pure-Python package, no Rhino dependencies. Rhino/Grasshopper-specific
helpers live in gh/ghcommon.py.

Pipeline:
    GH geometry -> STL/STEP export -> gmsh tet mesh (meshing.py)
    -> scene.json + input.csv (project.py / inputs.py)
    -> runSofa batch (runner.py)
    -> Monitor txt / output csv parsed back (results.py)

Units follow the Monolithic Unit convention: mm, kPa, kg, seconds,
gravity in mm/s^2 (earth = -9810 in z).
"""

__version__ = "0.1.0"
