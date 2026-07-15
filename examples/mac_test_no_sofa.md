# Testing on Mac without SOFA

Everything except `SofaRun` works without SOFA installed. Three tests,
in increasing effort.

## Test 0 — package sanity, no Rhino (Terminal)

```bash
cd ~/Documents/Claude/Projects/sofa-gh
python3 -c "import sys; sys.path.insert(0,'.'); from sofagh import inputs; \
print(inputs.write_csv([{'channel':1,'times':[0,0.5],'values':[0,40]}], '/tmp/in.csv'))"
```

Already verified (2026-07-07): inputs/results/project round-trip against
Anderson's real files, gmsh STL→VTK meshing.

## Test 1 — replay Anderson's grasp data in Rhino (no SOFA, no meshing)

Validates `SofaResults` + gives an animated trajectory viewer for
existing data.

1. Make a fake project folder:
   ```bash
   mkdir -p /tmp/mu_replay/monitor
   cp <Monolithic_Unit_version_0.4>/monitor/spine1_sensor0_input_grasp_x.txt \
      /tmp/mu_replay/monitor/actuator1_x.txt
   touch /tmp/mu_replay/scene.py
   ```
2. GH: Script component with `gh/components/SofaResults.py`.
   Inputs: `scenePath` = `/tmp/mu_replay/scene.py`, `bodyName` =
   `actuator1`, `repo` = the sofa-gh folder, `refresh` = Button.
3. `points` output is a tree, one branch per frame (133 frames, 6 spine
   points). Wire through **Tree Branch** + a slider (0–132) → preview →
   scrub the grasp motion. `lastPts` shows the final deformed spine.

## Test 2 — full export path from GH geometry (no SOFA)

Validates STL/STEP export, gmsh tet meshing inside Rhino, scene.json
and input.csv writing.

1. Model in Rhino/GH: a solid cylinder Brep (say r=15, h=100 mm,
   axis z) as the body; a smaller closed cylinder mesh inside as the
   cavity.
2. Components:
   - `SofaCavity`: geo = inner mesh, channel = 1
   - `PressureProfile`: channel 1, times `[0, 1.0]`, values `[0, 20]`
   - `SofaBody`: geo = Brep, name `test1`, E 18, mass 0.05,
     meshSize 1.0, cavities from above, one fixation Box around the
     top face, a few monitorPts down the axis
   - `SofaScene`: projDir `/tmp/test_proj`, repo path, write = Button
3. First run: Rhino pip-installs gmsh (needs internet, ~1 min).
4. Check `/tmp/test_proj/`:
   - `meshes/test1.step` (or `test1_volume.stl` if STEP export fell
     back) and `meshes/test1.vtk` — open the VTK in a text editor,
     header should read `DATASET UNSTRUCTURED_GRID` with a
     `CELLS`/tetra section
   - `scene.json` — bodies/cavities/fixations as expected
   - `input.csv` — 101 rows ramping 0→20 in column 1
5. Membrane shell: `SofaRegion` with surface = cavity mesh,
   thickness = 2 → `shell` output previews the closed hollow shell.

That folder is then runnable as-is on any Windows box with SOFA:
`python -m sofagh.runner \tmp\test_proj\scene.py`.

## Packaging note (.rhproj → .gha)

Once wiring is validated, use Rhino 8 ScriptEditor projects
(https://developer.rhino3d.com/guides/scripting/projects-create/):
New Project → add the Grasshopper script components → Publish. Output
is a compiled `.gha` (+ `.rhp`) without any C# — distributable via Yak.
Keep `sofagh/` importable by shipping it inside the project or pointing
`repo` at an install location.
