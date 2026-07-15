# Validation: reproduce Anderson's Monolithic Unit grasp sim

Goal: run the `input_grasp` case from `Monolithic_Unit_version_0.4`
through the sofa-gh pipeline and compare spine trajectories against his
`monitor/spine1_sensor*_input_grasp_x.txt`.

Two stages: first bypass Grasshopper entirely (validates runtime +
runner on Windows against known-good meshes), then rebuild from GH
geometry (validates export + meshing).

## Stage 1 — known-good meshes, no GH

On the Windows machine with SOFA v24.06, in Python (any 3.x):

```python
import sys; sys.path.insert(0, r"path\to\sofa-gh")
from sofagh import project, runner

AND = r"path\to\Monolithic_Unit_version_0.4"
M = AND + r"\data\mesh"

scene = project.write_project(
    r"C:\temp\mu_grasp",
    bodies=[{
        "name": "actuator1",
        "volume_vtk": M + r"\jvolume.vtk",     # pre-meshed, skips gmsh
        "young_modulus": 18.0, "poisson_ratio": 0.4, "total_mass": 0.05,
        # reference clamp: box around the neck at the top of the volume.
        # His box was [-12, ymin, zmax, 12, ymax, zmax-5] with the mesh
        # rotated [180,0,0] — compute zmax/ymin/ymax from the rotated mesh
        # or read them from his environment.py log output.
        "fixations": [[-12, -40, 95, 12, 40, 100]],
        "monitor_points": [[25,0,-12.5],[25,0,-25],[25,0,-37.5],
                            [25,0,-50],[25,0,-62.5],[25,0,-75]],
        "cavities": [
            {"name": "cavity_1", "channel": 1, "mesh": M + r"\cavity1.stl"},
            {"name": "cavity_2", "channel": 2, "mesh": M + r"\cavity2.stl"}],
        "regions": [
            {"name": "membrane1", "mesh": M + r"\membrane1.stl",
             "young_modulus": 2000, "poisson_ratio": 0.4},
            {"name": "membrane2", "mesh": M + r"\membrane2.stl",
             "young_modulus": 2000, "poisson_ratio": 0.4}],
        "collision_mesh": M + r"\jvolume.stl",
        "visuals": [{"mesh": M + r"\lattice.stl", "color": [0.7,0.9,0.9,0.1]}],
    }],
    # input_grasp.csv: channels 1+2 ramp 0 -> -20 kPa (rows 2..21),
    # hold, then -20 -> +40 (1 kPa/row). Keyframes at 100 Hz sampling:
    profiles=[
        {"channel": 1, "times": [0, .01, .21, .31, .91], "values": [0, 0, -20, -20, 40]},
        {"channel": 2, "times": [0, .01, .21, .31, .91], "values": [0, 0, -20, -20, 40]},
    ],
    options={"floor": {"point": [0, 0, -100], "size": 400}},
)
runner.run(scene, gui=True)   # or gui=False for batch
```

**Caveats vs the reference scene** (expect small differences):

* His mesh is loaded with `rotation=[180,0,0]` inside SOFA; sofa-gh
  exports geometry in world coordinates instead. For exact comparison
  either pre-rotate the VTK or compare in his frame.
* Exact grasp timing: check `input/input_grasp.csv` (92 rows) and match
  keyframes to it; the profile above is the idealized version.
* He runs two mirrored floor planes from `floorFlat.obj`; sofa-gh uses
  one flat plane.

Compare: `monitor/actuator1_x.txt` (ours) vs
`monitor/spine1_sensor0_input_grasp_x.txt` (his, sensor 0 = no sensor).
Plot nodal deviation over time; agreement should be tight since solver,
materials, meshes identical.

## Stage 1b — same thing wired in Grasshopper (file-input mode)

Components now accept existing mesh files directly (`volumeFile` /
`meshFile` inputs) — no Rhino geometry, no gmsh. Exact values, raw
(unrotated) jvolume.vtk coordinates — bbox: x ±50, y ±18.75, z 0→87.5,
neck at z=0:

* **SofaBody**: `volumeFile` = `...\data\mesh\jvolume.vtk`, name
  `actuator1`, E `18`, nu `0.4`, mass `0.05`
  * `fixations`: Center Box at (0, 0, 2.5), extents X 24 x Y 37.5 x Z 5
    (covers the neck slab z 0–5)
  * `monitorPts`: (25,0,12.5) (25,0,25) (25,0,37.5) (25,0,50)
    (25,0,62.5) (25,0,75)
* **SofaCavity** x2: `meshFile` = `cavity1.stl` / `cavity2.stl`,
  channels 1 / 2
* **SofaRegion** x2: `meshFile` = `membrane1.stl` / `membrane2.stl`,
  E `2000`
* **PressureProfile** x2 (ch 1 and 2): times `[0, 0.2, 0.3, 0.9]`,
  values `[0, -20, -20, 40]` (the grasp: extend then flex)
* **SofaScene**: `gravityZ` = `0` for functionality test. For exact
  parity with his run use `+9810` — his scene rotates the mesh 180
  degrees about x and pulls gravity in -z, which in the raw frame is +z.
  No floor, no contactRules.
* collisionGeo / visualGeo: skip (no contact in this test). To see the
  lattice, import `lattice.stl` into Rhino and wire the mesh to
  visualGeo.

Expected: both chambers extend under vacuum then the unit flexes as
pressure rises to +40 kPa; monitor writes 6 spine trajectories.

## Stage 2 — from Grasshopper geometry

1. Import `data/models/jvolume.STEP`, `cavity*.stp`, `membrane*.STEP`
   into Rhino (they're the CAD sources of the STLs).
2. Wire components per README; `meshSize = 0.22` on SofaBody.
3. Membranes: either import his membrane STEPs into `SofaRegion.geo`,
   or test the shell path — feed cavity mesh + measured wall thickness
   into `SofaRegion.surface/thickness` and compare stiffened-tet counts
   in the SOFA log.
4. Run, read back with SofaResults, overlay trajectories on Stage 1/1b.
